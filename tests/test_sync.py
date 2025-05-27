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

import os
from pathlib import Path
import signal
import subprocess
import sys

import pytest


@pytest.fixture
def pytester(pytester: pytest.Pytester) -> pytest.Pytester:
    # Pytester internally in their constructor overrides the HOME and USERPROFILE env variables. This confuses Chromium hence we unset them.
    # See https://github.com/pytest-dev/pytest/blob/83536b4b0074ca35d90933d3ad46cb6efe7f5145/src/_pytest/pytester.py#L704-L705
    os.environ.pop("HOME", None)
    os.environ.pop("USERPROFILE", None)
    return pytester


@pytest.fixture(autouse=True)
def _add_ini(testdir: pytest.Testdir) -> None:
    testdir.makefile(
        ".ini",
        pytest="""
        [pytest]
        addopts = -p no:playwright-asyncio
    """,
    )


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
            email = "test@test.com"
            page.set_content("<input type='text'/>")
            start_time = monotonic()
            page.type("input", email)
            end_time = monotonic()
            assert end_time - start_time >= 1
            assert end_time - start_time < 2
    """
    )
    result = testdir.runpytest("--browser", "chromium", "--slowmo", "1000")
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
    assert "Unsupported chromium channel" in "\n".join(result.outlines)


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


def test_user_defined_browser_context_args(testdir: pytest.Testdir) -> None:
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
        import pytest

        @pytest.mark.browser_context_args(user_agent="overwritten", locale="new-locale")
        def test_browser_context_args(page):
            assert page.evaluate("window.navigator.userAgent") == "overwritten"
            assert page.evaluate("window.navigator.languages") == ["new-locale"]
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(passed=1)


def test_user_defined_browser_context_args_clear_again(testdir: pytest.Testdir) -> None:
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
        import pytest

        @pytest.mark.browser_context_args(user_agent="overwritten")
        def test_browser_context_args(page):
            assert page.evaluate("window.navigator.userAgent") == "overwritten"

        def test_browser_context_args2(page):
            assert page.evaluate("window.navigator.userAgent") == "foobar"
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(passed=2)


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
            page.goto("https://example.org")
            assert page.url == "https://example.org/"
    """
    )
    result = testdir.runpytest("--base-url", "https://example.com")
    result.assert_outcomes(passed=1)


def test_base_url_via_fixture(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
        import pytest

        @pytest.fixture(scope="session")
        def base_url():
            return "https://example.com"

        def test_base_url(page, base_url):
            assert base_url == "https://example.com"
            page.goto("/foobar")
            assert page.url == "https://example.com/foobar"
    """
    )
    result = testdir.runpytest()
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


def test_xdist(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
        def test_a(page):
            page.set_content('<span id="foo">a</span>')
            page.wait_for_timeout(200)
            assert page.query_selector("#foo")

        def test_b(page):
            page.wait_for_timeout(2000)
            page.set_content('<span id="foo">a</span>')
            assert page.query_selector("#foo")

        def test_c(page):
            page.set_content('<span id="foo">a</span>')
            page.wait_for_timeout(200)
            assert page.query_selector("#foo")

        def test_d(page):
            page.set_content('<span id="foo">a</span>')
            page.wait_for_timeout(200)
            assert page.query_selector("#foo")
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
        "--numprocesses",
        "2",
    )
    result.assert_outcomes(passed=12)
    assert "gw0" in "\n".join(result.outlines)
    assert "gw1" in "\n".join(result.outlines)


def test_xdist_should_not_print_any_warnings(testdir: pytest.Testdir) -> None:
    original = os.environ.get("PYTHONWARNINGS")
    os.environ["PYTHONWARNINGS"] = "always"
    try:
        testdir.makepyfile(
            """
            import pytest

            def test_default(page):
                pass
        """
        )
        result = testdir.runpytest(
            "--numprocesses",
            "2",
        )
        result.assert_outcomes(passed=1)
        assert "ResourceWarning" not in "".join(result.stderr.lines)
    finally:
        if original is not None:
            os.environ["PYTHONWARNINGS"] = original
        else:
            del os.environ["PYTHONWARNINGS"]


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
    assert any(["--browser: invalid choice" in line for line in result.errlines])


def test_django(testdir: pytest.Testdir) -> None:
    # Workaround for https://github.com/pytest-dev/pytest/issues/10651
    os.environ.setdefault("PYTHONPATH", str(Path(__file__).parent.parent))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.assets.django.settings")
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


def test_browser_context_args_device(testdir: pytest.Testdir) -> None:
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


def test_launch_persistent_context_session(testdir: pytest.Testdir) -> None:
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


def test_context_page_on_session_level(testdir: pytest.Testdir) -> None:
    testdir.makeconftest(
        """
        import pytest
        from playwright.sync_api import Browser, BrowserContext
        from typing import Dict

        @pytest.fixture(scope="session")
        def context(
            browser: Browser,
            browser_context_args: Dict
        ):
            context = browser.new_context(**{
                **browser_context_args,
            })
            yield context
            context.close()

        @pytest.fixture(scope="session")
        def page(
            context: BrowserContext,
        ):
            page = context.new_page()
            yield page
    """
    )
    testdir.makepyfile(
        """
        def test_a(page):
            page.goto("data:text/html,<div>B</div>")
            assert page.text_content("div") == "B"

        def test_b(page):
            assert page.text_content("div") == "B"
        """
    )
    result = testdir.runpytest()
    result.assert_outcomes(passed=2)


def test_launch_persistent_context_function(testdir: pytest.Testdir) -> None:
    testdir.makeconftest(
        """
        import pytest
        from playwright.sync_api import BrowserType
        from typing import Dict

        @pytest.fixture()
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


def test_device_emulation(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
        import pytest
        def test_device_emulation(page, device):
            assert device == 'iPhone 11 Pro'
            assert "iPhone" in page.evaluate("window.navigator.userAgent")
    """
    )
    result = testdir.runpytest("--device", "iPhone 11 Pro")
    result.assert_outcomes(passed=1)


def test_rep_call_keyboard_interrupt(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
        import pytest

        def test_rep_call(page):
            assert page.evaluate("1 + 1") == 2
            raise KeyboardInterrupt
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(passed=0, failed=0, skipped=0)


def test_artifacts_by_default_it_should_not_store_anything(
    testdir: pytest.Testdir,
) -> None:
    testdir.makepyfile(
        """
        def test_passing(page):
            assert 2 == page.evaluate("1 + 1")

        def test_failing(page):
            raise Exception("Failed")
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(passed=1, failed=1)
    for dir in testdir.tmpdir.listdir():
        assert dir.basename != "test-results"


def test_artifacts_new_folder_on_run(
    testdir: pytest.Testdir,
) -> None:
    test_results_dir = os.path.join(testdir.tmpdir, "test-results")
    os.mkdir(os.path.join(test_results_dir))
    with open(os.path.join(test_results_dir, "example.json"), "w") as f:
        f.write("foo")

    testdir.makepyfile(
        """
        def test_passing(page):
            assert 2 == page.evaluate("1 + 1")
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(passed=1)
    for dir in testdir.tmpdir.listdir():
        assert dir.basename != "test-results"


def test_artifacts_should_store_everything_if_on(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
        def test_passing(page, output_path):
            print(f"\\n\\noutput_path = {output_path}\\n\\n")
            assert 2 == page.evaluate("1 + 1")

        def test_failing(page, output_path):
            print(f"\\n\\noutput_path = {output_path}\\n\\n")
            raise Exception("Failed")
    """
    )
    result = testdir.runpytest(
        "--screenshot", "on", "--video", "on", "--tracing", "on", "-s"
    )
    result.assert_outcomes(passed=1, failed=1)
    test_results_dir = os.path.join(testdir.tmpdir, "test-results")
    _assert_folder_structure(
        test_results_dir,
        """
- test-artifacts-should-store-everything-if-on-py-test-failing-chromium:
  - test-failed-1.png
  - trace.zip
  - video.webm
- test-artifacts-should-store-everything-if-on-py-test-passing-chromium:
  - test-finished-1.png
  - trace.zip
  - video.webm
""",
    )
    output_path = str(testdir.tmpdir)
    output_paths = [
        line[14:] for line in result.outlines if f"output_path = {output_path}" in line
    ]
    assert output_paths == [
        testdir.tmpdir.join(
            "test-results/test-artifacts-should-store-everything-if-on-py-test-passing-chromium"
        ).strpath,
        testdir.tmpdir.join(
            "test-results/test-artifacts-should-store-everything-if-on-py-test-failing-chromium"
        ).strpath,
    ]


def test_artifacts_retain_on_failure(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
        def test_passing(page):
            assert 2 == page.evaluate("1 + 1")

        def test_failing(page):
            raise Exception("Failed")
    """
    )
    result = testdir.runpytest(
        "--screenshot",
        "only-on-failure",
        "--video",
        "retain-on-failure",
        "--tracing",
        "retain-on-failure",
    )
    result.assert_outcomes(passed=1, failed=1)
    test_results_dir = os.path.join(testdir.tmpdir, "test-results")
    _assert_folder_structure(
        test_results_dir,
        """
- test-artifacts-retain-on-failure-py-test-failing-chromium:
  - test-failed-1.png
  - trace.zip
  - video.webm
""",
    )


def test_should_work_with_test_names_which_exceeds_256_characters(
    testdir: pytest.Testdir,
) -> None:
    long_test_name = "abcdefghijklmnopqrstuvwxyz" * 100
    testdir.makepyfile(
        f"""
        def test_{long_test_name}(page):
            pass
    """
    )
    result = testdir.runpytest("--tracing", "on")
    result.assert_outcomes(passed=1, failed=0)
    test_results_dir = os.path.join(testdir.tmpdir, "test-results")
    _assert_folder_structure(
        test_results_dir,
        """
- test-should-work-with-test-names-which-exceeds-256-characters-py-test-abcdefghijklmnopqrstuvwxyzabcd-23f2441-nopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyz-chromium:
  - trace.zip
""",
    )


def _make_folder_list(root: str, level: int = 0) -> str:
    if not os.path.exists(root):
        return ""
    tree = []
    for entry in sorted(os.scandir(root), key=lambda e: e.name):
        prefix = f"{'  ' * level}- "
        if entry.is_dir():
            tree.append(f"{prefix}{entry.name}:\n")
            tree.append(_make_folder_list(entry.path, level + 1))
        else:
            tree.append(f"{prefix}{entry.name}\n")
    return "".join(tree)


def _assert_folder_structure(root: str, expected: str) -> None:
    __tracebackhide__ = True
    actual = _make_folder_list(root)
    if actual.strip() != expected.strip():
        print("Actual:")
        print(actual)
        print("Expected:")
        print(expected)
        raise AssertionError("Actual tree does not match expected tree")


def test_is_able_to_set_expect_timeout_via_conftest(testdir: pytest.Testdir) -> None:
    testdir.makeconftest(
        """
        from playwright.sync_api import expect
        expect.set_options(timeout=1111)
    """
    )
    testdir.makepyfile(
        """
        from playwright.sync_api import expect

        def test_small_timeout(page):
            page.goto("data:text/html,")
            expect(page.locator("#A")).to_be_visible()
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(passed=0, failed=1, skipped=0)
    result.stdout.fnmatch_lines("*AssertionError: Locator expected to be visible*")
    result.stdout.fnmatch_lines("*LocatorAssertions.to_be_visible with timeout 1111ms*")


def test_artifact_collection_should_work_for_manually_created_contexts_keep_open(
    testdir: pytest.Testdir,
) -> None:
    testdir.makepyfile(
        """
        import pytest
        from pytest_playwright.pytest_playwright import CreateContextCallback

        def test_artifact_collection(browser, page, new_context: CreateContextCallback):
            page.goto("data:text/html,<div>hello</div>")

            other_context = new_context()
            other_context_page = other_context.new_page()
            other_context_page.goto("data:text/html,<div>hello</div>")
        """
    )
    result = testdir.runpytest("--screenshot", "on", "--video", "on", "--tracing", "on")
    result.assert_outcomes(passed=1)
    test_results_dir = os.path.join(testdir.tmpdir, "test-results")
    _assert_folder_structure(
        test_results_dir,
        """
- test-artifact-collection-should-work-for-manually-created-contexts-keep-open-py-test-artifact-collection-chromium:
  - test-finished-1.png
  - test-finished-2.png
  - trace-1.zip
  - trace-2.zip
  - video-1.webm
  - video-2.webm
""",
    )


def test_artifact_collection_should_work_for_manually_created_contexts_get_closed(
    testdir: pytest.Testdir,
) -> None:
    testdir.makepyfile(
        """
        import pytest

        def test_artifact_collection(browser, page, new_context):
            page.goto("data:text/html,<div>hello</div>")

            other_context = new_context()
            other_context_page = other_context.new_page()
            other_context_page.goto("data:text/html,<div>hello</div>")
            other_context_page.evaluate("new Promise(fulfill => requestAnimationFrame(() => requestAnimationFrame(fulfill)))")
            other_context.close()
        """
    )
    result = testdir.runpytest("--video", "on", "--tracing", "on")
    result.assert_outcomes(passed=1)
    test_results_dir = os.path.join(testdir.tmpdir, "test-results")
    _assert_folder_structure(
        test_results_dir,
        """
- test-artifact-collection-should-work-for-manually-created-contexts-get-closed-py-test-artifact-collection-chromium:
  - trace-1.zip
  - trace-2.zip
  - video-1.webm
  - video-2.webm
""",
    )


def test_artifact_collection_should_work_for_manually_created_contexts_retain_on_failure_failed(
    testdir: pytest.Testdir,
) -> None:
    testdir.makepyfile(
        """
        import pytest

        def test_artifact_collection(browser, page, new_context):
            page.goto("data:text/html,<div>hello</div>")

            other_context = new_context()
            other_context_page = other_context.new_page()
            other_context_page.goto("data:text/html,<div>hello</div>")

            raise Exception("Failed")
        """
    )
    result = testdir.runpytest(
        "--video", "retain-on-failure", "--tracing", "retain-on-failure"
    )
    result.assert_outcomes(failed=1)
    test_results_dir = os.path.join(testdir.tmpdir, "test-results")
    _assert_folder_structure(
        test_results_dir,
        """
- test-artifact-collection-should-work-for-manually-created-contexts-retain-on-failure-failed-py-test-artifact-collection-chromium:
  - trace-1.zip
  - trace-2.zip
  - video-1.webm
  - video-2.webm
""",
    )


def test_artifact_collection_should_work_for_manually_created_contexts_retain_on_failure_pass(
    testdir: pytest.Testdir,
) -> None:
    testdir.makepyfile(
        """
        import pytest

        def test_artifact_collection(browser, page, new_context):
            page.goto("data:text/html,<div>hello</div>")

            other_context = new_context()
            other_context_page = other_context.new_page()
            other_context_page.goto("data:text/html,<div>hello</div>")
        """
    )
    result = testdir.runpytest(
        "--video", "retain-on-failure", "--tracing", "retain-on-failure"
    )
    result.assert_outcomes(passed=1)
    test_results_dir = os.path.join(testdir.tmpdir, "test-results")
    _assert_folder_structure(test_results_dir, "")


def test_new_context_allow_passing_args(
    testdir: pytest.Testdir,
) -> None:
    testdir.makepyfile(
        """
        import pytest

        def test_artifact_collection(new_context):
            context1 = new_context(user_agent="agent1")
            page1 = context1.new_page()
            assert page1.evaluate("window.navigator.userAgent") == "agent1"
            context1.close()

            context2 = new_context(user_agent="agent2")
            page2 = context2.new_page()
            assert page2.evaluate("window.navigator.userAgent") == "agent2"
            context2.close()
            """
    )
    result = testdir.runpytest()
    result.assert_outcomes(passed=1)


def test_output_path_via_pytest_runtest_makereport_hook(
    testdir: pytest.Testdir,
) -> None:
    testdir.makeconftest(
        """
import pytest

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    if report.when == "call":
        output_path = item.funcargs.get("output_path")
        print("\\n\\noutput_path = {}".format(output_path))
"""
    )

    testdir.makepyfile(
        """
def test_without_output_path():
    pass

def test_with_page(page):
    pass
"""
    )

    result = testdir.runpytest("--screenshot", "on", "-s")
    result.assert_outcomes(passed=2)
    output_paths = [line[14:] for line in result.outlines if "output_path = " in line]
    assert output_paths == [
        "None",
        testdir.tmpdir.join(
            "test-results/test-output-path-via-pytest-runtest-makereport-hook-py-test-with-page-chromium"
        ).strpath,
    ]


def test_connect_options_should_work(testdir: pytest.Testdir) -> None:
    server_process = None
    try:
        testdir.makeconftest(
            """
            import pytest

            @pytest.fixture(scope="session")
            def connect_options():
                return {
                    "ws_endpoint": "ws://localhost:1234",
                }
            """
        )
        testdir.makepyfile(
            """
            def test_connect_options(page):
                assert page.evaluate("1 + 1") == 2
            """
        )
        result = testdir.runpytest()
        assert "connect ECONNREFUSED" in "".join(result.outlines)
        server_process = subprocess.Popen(
            ["playwright", "run-server", "--port=1234"],
            stdout=subprocess.PIPE,
        )
        while True:
            stdout = server_process.stdout
            assert stdout
            if "Listening on" in str(stdout.readline()):
                break
        result = testdir.runpytest()
        result.assert_outcomes(passed=1)
    finally:
        assert server_process
        # TODO: Playwright CLI on Windows via Python does not forward the signal
        # hence we need to send it to the whole process group.
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(server_process.pid)])
        else:
            os.kill(server_process.pid, signal.SIGINT)
        server_process.wait()
