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

import asyncio
import warnings
from asyncio import AbstractEventLoop
from typing import Any, Callable, Dict, Generator, List, Optional

import pytest
from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    sync_playwright,
    BrowserType,
)


def pytest_generate_tests(metafunc: Any) -> None:
    if "browser_name" in metafunc.fixturenames:
        browsers = metafunc.config.option.browser or ["chromium"]
        for browser in browsers:
            if browser not in ["chromium", "firefox", "webkit"]:
                raise ValueError(
                    f"'{browser}' is not allowed. Only chromium, firefox, or webkit are valid browser names."
                )
        metafunc.parametrize("browser_name", browsers, scope="session")


def pytest_configure(config: Any) -> None:
    config.addinivalue_line(
        "markers", "skip_browser(name): mark test to be skipped a specific browser"
    )
    config.addinivalue_line(
        "markers", "only_browser(name): mark test to run only on a specific browser"
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


@pytest.fixture(scope="session")
def event_loop() -> Generator[AbstractEventLoop, None, None]:
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def browser_type_launch_args(pytestconfig: Any) -> Dict:
    launch_options = {}
    headed_option = pytestconfig.getoption("--headed")
    if headed_option:
        launch_options["headless"] = False
    browser_channel_option = pytestconfig.getoption("--browser-channel")
    if browser_channel_option:
        launch_options["channel"] = browser_channel_option
    slowmo_option = pytestconfig.getoption("--slowmo")
    if slowmo_option:
        launch_options["slow_mo"] = slowmo_option
    return launch_options


@pytest.fixture(scope="session")
def browser_context_args() -> Dict:
    return {}


@pytest.fixture(scope="session")
def playwright() -> Generator[Playwright, None, None]:
    pw = sync_playwright().start()
    yield pw
    pw.stop()


@pytest.fixture(scope="session")
def browser_type(playwright: Playwright, browser_name: str) -> BrowserType:
    return getattr(playwright, browser_name)


@pytest.fixture(scope="session")
def launch_browser(
    playwright: Playwright,
    browser_type_launch_args: Dict,
    browser_type: BrowserType,
) -> Callable[..., Browser]:
    def launch(**kwargs: Dict) -> Browser:
        launch_options = {**browser_type_launch_args, **kwargs}
        browser = browser_type.launch(**launch_options)
        return browser

    return launch


@pytest.fixture(scope="session")
def browser(launch_browser: Callable[[], Browser]) -> Generator[Browser, None, None]:
    browser = launch_browser()
    yield browser
    browser.close()


@pytest.fixture
def context(
    browser: Browser, browser_context_args: Dict
) -> Generator[BrowserContext, None, None]:
    context = browser.new_context(**browser_context_args)
    yield context
    context.close()


def _handle_page_goto(
    page: Page, args: List[Any], kwargs: Dict[str, Any], base_url: str
) -> None:
    url = args.pop()
    if not (url.startswith("http://") or url.startswith("https://")):
        url = base_url + url
    return page._goto(url, *args, **kwargs)  # type: ignore


@pytest.fixture
def page(context: BrowserContext, base_url: str) -> Generator[Page, None, None]:
    page = context.new_page()
    page._goto = page.goto  # type: ignore
    page.goto = lambda *args, **kwargs: _handle_page_goto(  # type: ignore
        page, list(args), kwargs, base_url
    )
    yield page
    page.close()


@pytest.fixture(scope="session")
def is_webkit(browser_name: str) -> bool:
    return browser_name == "webkit"


@pytest.fixture(scope="session")
def is_firefox(browser_name: str) -> bool:
    return browser_name == "firefox"


@pytest.fixture(scope="session")
def is_chromium(browser_name: str) -> bool:
    return browser_name == "chromium"


@pytest.fixture(scope="session")
def browser_name(pytestconfig: Any) -> Optional[str]:
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
def browser_channel(pytestconfig: Any) -> Optional[str]:
    return pytestconfig.getoption("--browser-channel")


def pytest_addoption(parser: Any) -> None:
    group = parser.getgroup("playwright", "Playwright")
    group.addoption(
        "--browser",
        action="append",
        default=[],
        help="Browser engine which should be used",
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
        help="Run tests in slow mo",
    )
