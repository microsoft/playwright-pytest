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

import sys
from typing import Any, List, Optional
import warnings
import pytest
import hashlib
import os


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


def _get_skiplist(item: Any, values: List[str], value_name: str) -> List[str]:
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


def pytest_runtest_setup(item: Any) -> None:
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
