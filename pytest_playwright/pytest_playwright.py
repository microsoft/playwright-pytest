# Copyright (c) Microsoft Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from pathlib import Path
from re import Pattern
import shutil
import sys
import tempfile
from typing import (
    Any,
    Dict,
    Generator,
    List,
    Literal,
    Optional,
    Protocol,
    Sequence,
    Union,
)
import warnings
import pytest
import hashlib
import os

from playwright.sync_api import (
    BrowserContext,
    ProxySettings,
    StorageState,
    HttpCredentials,
    Geolocation,
    ViewportSize,
)
from slugify import slugify


class CreateContextCallback(Protocol):
    def __call__(
        self,
        viewport: Optional[ViewportSize] = None,
        screen: Optional[ViewportSize] = None,
        no_viewport: Optional[bool] = None,
        ignore_https_errors: Optional[bool] = None,
        java_script_enabled: Optional[bool] = None,
        bypass_csp: Optional[bool] = None,
        user_agent: Optional[str] = None,
        locale: Optional[str] = None,
        timezone_id: Optional[str] = None,
        geolocation: Optional[Geolocation] = None,
        permissions: Optional[Sequence[str]] = None,
        extra_http_headers: Optional[Dict[str, str]] = None,
        offline: Optional[bool] = None,
        http_credentials: Optional[HttpCredentials] = None,
        device_scale_factor: Optional[float] = None,
        is_mobile: Optional[bool] = None,
        has_touch: Optional[bool] = None,
        color_scheme: Optional[
            Literal["dark", "light", "no-preference", "null"]
        ] = None,
        reduced_motion: Optional[Literal["no-preference", "null", "reduce"]] = None,
        forced_colors: Optional[Literal["active", "none", "null"]] = None,
        accept_downloads: Optional[bool] = None,
        default_browser_type: Optional[str] = None,
        proxy: Optional[ProxySettings] = None,
        record_har_path: Optional[Union[str, Path]] = None,
        record_har_omit_content: Optional[bool] = None,
        record_video_dir: Optional[Union[str, Path]] = None,
        record_video_size: Optional[ViewportSize] = None,
        storage_state: Optional[Union[StorageState, str, Path]] = None,
        base_url: Optional[str] = None,
        strict_selectors: Optional[bool] = None,
        service_workers: Optional[Literal["allow", "block"]] = None,
        record_har_url_filter: Optional[Union[str, Pattern[str]]] = None,
        record_har_mode: Optional[Literal["full", "minimal"]] = None,
        record_har_content: Optional[Literal["attach", "embed", "omit"]] = None,
    ) -> BrowserContext: ...


class PytestPlaywright:
    VSCODE_PYTHON_EXTENSION_ID = "ms-python.python"

    def pytest_generate_tests(self, metafunc: Any) -> None:
        if "browser_name" in metafunc.fixturenames:
            browsers = metafunc.config.option.browser or ["chromium"]
            metafunc.parametrize("browser_name", browsers, scope="session")

    def pytest_configure(self, config: Any) -> None:
        config.addinivalue_line(
            "markers", "skip_browser(name): mark test to be skipped a specific browser"
        )
        config.addinivalue_line(
            "markers", "only_browser(name): mark test to run only on a specific browser"
        )
        config.addinivalue_line(
            "markers",
            "browser_context_args(**kwargs): provide additional arguments to browser.new_context()",
        )

    # Making test result information available in fixtures
    # https://docs.pytest.org/en/latest/example/simple.html#making-test-result-information-available-in-fixtures
    @pytest.hookimpl(tryfirst=True, hookwrapper=True)
    def pytest_runtest_makereport(
        self, item: pytest.Item
    ) -> Generator[None, Any, None]:
        # execute all other hooks to obtain the report object
        outcome = yield
        rep = outcome.get_result()

        # set a report attribute for each phase of a call, which can
        # be "setup", "call", "teardown"

        setattr(item, "rep_" + rep.when, rep)

    @pytest.fixture(scope="session")
    def _pw_artifacts_folder(
        self,
    ) -> Generator[tempfile.TemporaryDirectory, None, None]:
        artifacts_folder = tempfile.TemporaryDirectory(prefix="playwright-pytest-")
        yield artifacts_folder
        try:
            # On Windows, files can be still in use.
            # https://github.com/microsoft/playwright-pytest/issues/163
            artifacts_folder.cleanup()
        except (PermissionError, NotADirectoryError):
            pass

    @pytest.fixture(scope="session", autouse=True)
    def _delete_output_dir(self, pytestconfig: Any) -> None:
        output_dir = pytestconfig.getoption("--output")
        if os.path.exists(output_dir):
            try:
                shutil.rmtree(output_dir)
            except (FileNotFoundError, PermissionError):
                # When running in parallel, another thread may have already deleted the files
                pass
            except OSError as error:
                if error.errno != 16:
                    raise
                # We failed to remove folder, might be due to the whole folder being mounted inside a container:
                #   https://github.com/microsoft/playwright/issues/12106
                #   https://github.com/microsoft/playwright-python/issues/1781
                # Do a best-effort to remove all files inside of it instead.
                entries = os.listdir(output_dir)
                for entry in entries:
                    shutil.rmtree(entry)

    @pytest.fixture
    def output_path(self, pytestconfig: Any, request: pytest.FixtureRequest) -> str:
        output_dir = Path(pytestconfig.getoption("--output")).absolute()
        return os.path.join(
            output_dir, _truncate_file_name(slugify(request.node.nodeid))
        )

    @pytest.fixture(scope="session")
    def browser_channel(self, pytestconfig: Any) -> Optional[str]:
        return pytestconfig.getoption("--browser-channel")

    @pytest.fixture(scope="session")
    def device(self, pytestconfig: Any) -> Optional[str]:
        return pytestconfig.getoption("--device")

    @pytest.fixture(scope="session")
    def browser_name(self, pytestconfig: Any) -> Optional[str]:
        # When using unittest.TestCase it won't use pytest_generate_tests
        # For that we still try to give the user a slightly less feature-rich experience
        browser_names = pytestconfig.getoption("--browser")
        if len(browser_names) == 0:
            return "chromium"
        if len(browser_names) == 1:
            return browser_names[0]
        warnings.warn(
            "When using unittest.TestCase specifying multiple browsers is not supported"
        )
        return browser_names[0]

    @pytest.fixture(scope="session")
    def is_webkit(self, browser_name: str) -> bool:
        return browser_name == "webkit"

    @pytest.fixture(scope="session")
    def is_firefox(self, browser_name: str) -> bool:
        return browser_name == "firefox"

    @pytest.fixture(scope="session")
    def is_chromium(self, browser_name: str) -> bool:
        return browser_name == "chromium"


def _is_debugger_attached() -> bool:
    pydevd = sys.modules.get("pydevd")
    if not pydevd or not hasattr(pydevd, "get_global_debugger"):
        return False
    debugger = pydevd.get_global_debugger()
    if not debugger or not hasattr(debugger, "is_attached"):
        return False
    return debugger.is_attached()


def _create_guid() -> str:
    return hashlib.sha256(os.urandom(16)).hexdigest()


def _truncate_file_name(file_name: str) -> str:
    if len(file_name) < 256:
        return file_name
    return f"{file_name[:100]}-{hashlib.sha256(file_name.encode()).hexdigest()[:7]}-{file_name[-100:]}"


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("playwright", "Playwright")
    group.addoption(
        "--browser",
        action="append",
        default=[],
        help="Browser engine which should be used",
        choices=["chromium", "firefox", "webkit"],
    )
    group.addoption(
        "--headed",
        action="store_true",
        default=False,
        help="Run tests in headed mode.",
    )
    group.addoption(
        "--browser-channel",
        action="store",
        default=None,
        help="Browser channel to be used.",
    )
    group.addoption(
        "--slowmo",
        default=0,
        type=int,
        help="Run tests with slow mo",
    )
    group.addoption(
        "--device",
        default=None,
        action="store",
        help="Device to be emulated.",
    )
    group.addoption(
        "--output",
        default="test-results",
        help="Directory for artifacts produced by tests, defaults to test-results.",
    )
    group.addoption(
        "--tracing",
        default="off",
        choices=["on", "off", "retain-on-failure"],
        help="Whether to record a trace for each test.",
    )
    group.addoption(
        "--video",
        default="off",
        choices=["on", "off", "retain-on-failure"],
        help="Whether to record video for each test.",
    )
    group.addoption(
        "--screenshot",
        default="off",
        choices=["on", "off", "only-on-failure"],
        help="Whether to automatically capture a screenshot after each test.",
    )
    group.addoption(
        "--full-page-screenshot",
        action="store_true",
        default=False,
        help="Whether to take a full page screenshot",
    )
    parser.addini(
        "playwright_pytest_asyncio",
        "Use asyncio Playwright fixtures. Default: when 'pytest-asyncio' plugin is activated=True, otherwise False",
        type="bool",
        default=None,
    )


def _get_skiplist(item: pytest.Item, values: List[str], value_name: str) -> List[str]:
    skipped_values: List[str] = []
    # Allowlist
    only_marker = item.get_closest_marker(f"only_{value_name}")
    if only_marker:
        skipped_values = values
        skipped_values.remove(only_marker.args[0])

    # Denylist
    skip_marker = item.get_closest_marker(f"skip_{value_name}")
    if skip_marker:
        skipped_values.append(skip_marker.args[0])

    return skipped_values


def pytest_runtest_setup(item: pytest.Item) -> None:
    if not hasattr(item, "callspec"):
        return
    browser_name = item.callspec.params.get("browser_name")
    if not browser_name:
        return

    skip_browsers_names = _get_skiplist(
        item, ["chromium", "firefox", "webkit"], "browser"
    )

    if browser_name in skip_browsers_names:
        pytest.skip("skipped for this browser: {}".format(browser_name))


def pytest_configure(config: pytest.Config) -> None:
    if config.getini("playwright_pytest_asyncio"):
        from pytest_playwright.asyncio import PytestPlaywrightAsyncio

        config.pluginmanager.register(PytestPlaywrightAsyncio())
    else:
        from pytest_playwright.sync import PytestPlaywrightSync

        config.pluginmanager.register(PytestPlaywrightSync())
