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

import pytest


def test_default(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
        import pytest

        def test_default(page, browser_name):
            assert browser_name == "chromium"
            user_agent = page.evaluate("window.navigator.userAgent")
            assert "HeadlessChrome" in user_agent
            page.set_content('<span id="foo">bar</span>')
            assert page.query_selector("#foo")
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(passed=1)


def test_slowmo(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
        from time import monotonic
        def test_slowmo(page):
            start_time = monotonic()
            email = "test@test.com"
            page.set_content("<input type='text'/>")
            page.type("input", email)
            end_time = monotonic()
            assert end_time - start_time >= len(email)
    """
    )
    result = testdir.runpytest("--browser", "chromium", "--slowmo", "1000", "--headed")
    result.assert_outcomes(passed=1)


@pytest.mark.parametrize(
    "channel",
    [
        "chrome",
        "msedge",
    ],
)
def test_browser_channel(channel: str, testdir: pytest.Testdir) -> None:
    if channel == "msedge" and sys.platform == "linux":
        pytest.skip("msedge not supported on linux")
    testdir.makepyfile(
        f"""
        import pytest

        def test_browser_channel(page, browser_name, browser_channel):
            assert browser_name == "chromium"
            assert browser_channel == "{channel}"
    """
    )
    result = testdir.runpytest("--browser-channel", channel)
    result.assert_outcomes(passed=1)


def test_invalid_browser_channel(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
        import pytest

        def test_browser_channel(page, browser_name, browser_channel):
            assert browser_name == "chromium"
    """
    )
    result = testdir.runpytest("--browser-channel", "not-exists")
    result.assert_outcomes(errors=1)
    assert "channel: expected one of " in "\n".join(result.outlines)


def test_unittest_class(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
        import pytest
        import unittest
        from playwright.sync_api import Page


        class MyTest(unittest.TestCase):
            @pytest.fixture(autouse=True)
            def setup(self, page: Page):
                self.page = page

            def test_foobar(self):
                assert self.page.evaluate("1 + 1") == 2
    """
    )
    result = testdir.runpytest("--browser", "chromium")
    result.assert_outcomes(passed=1)


def test_unittest_class_multiple_browsers(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
        import pytest
        import unittest
        from playwright.sync_api import Page


        class MyTest(unittest.TestCase):
            @pytest.fixture(autouse=True)
            def setup(self, page: Page):
                self.page = page

            def test_foobar(self):
                assert "Firefox" in self.page.evaluate("navigator.userAgent")
                assert self.page.evaluate("1 + 1") == 2
    """
    )
    result = testdir.runpytest("--browser", "firefox", "--browser", "webkit")
    result.assert_outcomes(passed=1)
    assert any("multiple browsers is not supported" in line for line in result.outlines)


def test_multiple_browsers(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
        def test_multiple_browsers(page):
            page.set_content('<span id="foo">bar</span>')
            assert page.query_selector("#foo")
    """
    )
    result = testdir.runpytest(
        "--browser", "chromium", "--browser", "firefox", "--browser", "webkit"
    )
    result.assert_outcomes(passed=3)


def test_browser_context_args(testdir: pytest.Testdir) -> None:
    testdir.makeconftest(
        """
        import pytest

        @pytest.fixture(scope="session")
        def browser_context_args():
            return {"user_agent": "foobar"}
    """
    )
    testdir.makepyfile(
        """
        def test_browser_context_args(page):
            assert page.evaluate("window.navigator.userAgent") == "foobar"
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(passed=1)


def test_chromium(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
        def test_is_chromium(page, browser_name, is_chromium, is_firefox, is_webkit):
            assert browser_name == "chromium"
            assert is_chromium
            assert is_firefox is False
            assert is_webkit is False
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(passed=1)


def test_firefox(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
        def test_is_firefox(page, browser_name, is_chromium, is_firefox, is_webkit):
            assert browser_name == "firefox"
            assert is_chromium is False
            assert is_firefox
            assert is_webkit is False
    """
    )
    result = testdir.runpytest("--browser", "firefox")
    result.assert_outcomes(passed=1)


def test_webkit(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
        def test_is_webkit(page, browser_name, is_chromium, is_firefox, is_webkit):
            assert browser_name == "webkit"
            assert is_chromium is False
            assert is_firefox is False
            assert is_webkit
    """
    )
    result = testdir.runpytest("--browser", "webkit")
    result.assert_outcomes(passed=1)


def test_goto(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
        def test_base_url(page, base_url):
            assert base_url == "https://example.com"
            page.goto("/foobar")
            assert page.url == "https://example.com/foobar"
            page.goto("http://whatsmyuseragent.org")
            assert page.url == "http://whatsmyuseragent.org/"
    """
    )
    result = testdir.runpytest("--base-url", "https://example.com")
    result.assert_outcomes(passed=1)


def test_skip_browsers(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
        import pytest

        @pytest.mark.skip_browser("firefox")
        def test_base_url(page, browser_name):
            assert browser_name in ["chromium", "webkit"]
    """
    )
    result = testdir.runpytest(
        "--browser", "chromium", "--browser", "firefox", "--browser", "webkit"
    )
    result.assert_outcomes(passed=2, skipped=1)


def test_only_browser(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
        import pytest

        @pytest.mark.only_browser("firefox")
        def test_base_url(page, browser_name):
            assert browser_name == "firefox"
    """
    )
    result = testdir.runpytest(
        "--browser", "chromium", "--browser", "firefox", "--browser", "webkit"
    )
    result.assert_outcomes(passed=1, skipped=2)


def test_parameterization(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
        def test_all_browsers(page):
            pass

        def test_without_browser():
            pass
    """
    )
    result = testdir.runpytest(
        "--verbose",
        "--browser",
        "chromium",
        "--browser",
        "firefox",
        "--browser",
        "webkit",
    )
    result.assert_outcomes(passed=4)
    assert "test_without_browser PASSED" in "\n".join(result.outlines)


def test_headed(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
        def test_base_url(page, browser_name):
            user_agent = page.evaluate("window.navigator.userAgent")
            assert "HeadlessChrome" not in user_agent
    """
    )
    result = testdir.runpytest("--browser", "chromium", "--headed")
    result.assert_outcomes(passed=1)


def test_invalid_browser_name(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
        def test_base_url(page):
            pass
    """
    )
    result = testdir.runpytest("--browser", "test123")
    result.assert_outcomes(errors=1)
    assert "'test123' is not allowed" in "\n".join(result.outlines)


def test_django(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
    from django.test import TestCase
    class Proj1Test(TestCase):
        def test_one(self):
            self.assertTrue(True)

    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(passed=1)


def test_device_emulation(testdir: pytest.Testdir) -> None:
    testdir.makeconftest(
        """
        import pytest

        @pytest.fixture(scope="session")
        def browser_context_args(browser_context_args, playwright):
            iphone_11 = playwright.devices['iPhone 11 Pro']
            return {**browser_context_args, **iphone_11}
    """
    )
    testdir.makepyfile(
        """
        def test_browser_context_args(page):
            assert "iPhone" in page.evaluate("window.navigator.userAgent")
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(passed=1)


def test_launch_persistent_context(testdir: pytest.Testdir) -> None:
    testdir.makeconftest(
        """
        import pytest
        from playwright.sync_api import BrowserType
        from typing import Dict

        @pytest.fixture(scope="session")
        def context(
            browser_type: BrowserType,
            browser_type_launch_args: Dict,
            browser_context_args: Dict
        ):
            context = browser_type.launch_persistent_context("./foobar", **{
                **browser_type_launch_args,
                **browser_context_args,
                "locale": "de-DE",
            })
            yield context
            context.close()
    """
    )
    testdir.makepyfile(
        """
        def test_browser_context_args(page):
            assert page.evaluate("navigator.language") == "de-DE"
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(passed=1)
