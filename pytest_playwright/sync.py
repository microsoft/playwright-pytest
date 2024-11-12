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

import shutil
import os
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    List,
    cast,
)

import pytest
from playwright.sync_api import (
    Browser,
    BrowserContext,
    BrowserType,
    Error,
    Page,
    Playwright,
    sync_playwright,
)
from slugify import slugify
import tempfile
from pytest_playwright.pytest_playwright import (
    PytestPlaywright,
    _create_guid,
    _truncate_file_name,
    CreateContextCallback,
)


class PytestPlaywrightSync(PytestPlaywright):
    @pytest.fixture()
    def _artifacts_recorder(
        self,
        request: pytest.FixtureRequest,
        output_path: str,
        playwright: Playwright,
        pytestconfig: Any,
        _pw_artifacts_folder: tempfile.TemporaryDirectory,
    ) -> Generator["ArtifactsRecorder", None, None]:
        artifacts_recorder = ArtifactsRecorder(
            pytestconfig, request, output_path, playwright, _pw_artifacts_folder
        )
        yield artifacts_recorder
        # If request.node is missing rep_call, then some error happened during execution
        # that prevented teardown, but should still be counted as a failure
        failed = (
            request.node.rep_call.failed if hasattr(request.node, "rep_call") else True
        )
        artifacts_recorder.did_finish_test(failed)

    @pytest.fixture(scope="session")
    def playwright(self) -> Generator[Playwright, None, None]:
        pw = sync_playwright().start()
        yield pw
        pw.stop()

    @pytest.fixture(scope="session")
    def browser_type(self, playwright: Playwright, browser_name: str) -> BrowserType:
        return getattr(playwright, browser_name)

    @pytest.fixture(scope="session")
    def launch_browser(
        self,
        browser_type_launch_args: Dict,
        browser_type: BrowserType,
    ) -> Callable[..., Browser]:
        def launch(**kwargs: Dict) -> Browser:
            launch_options = {**browser_type_launch_args, **kwargs}
            browser = browser_type.launch(**launch_options)
            return browser

        return launch

    @pytest.fixture(scope="session")
    def browser(
        self, launch_browser: Callable[[], Browser]
    ) -> Generator[Browser, None, None]:
        browser = launch_browser()
        yield browser
        browser.close()

    @pytest.fixture
    def new_context(
        self,
        browser: Browser,
        browser_context_args: Dict,
        _artifacts_recorder: "ArtifactsRecorder",
        request: pytest.FixtureRequest,
    ) -> Generator[CreateContextCallback, None, None]:
        browser_context_args = browser_context_args.copy()
        context_args_marker = next(
            request.node.iter_markers("browser_context_args"), None
        )
        additional_context_args = (
            context_args_marker.kwargs if context_args_marker else {}
        )
        browser_context_args.update(additional_context_args)
        contexts: List[BrowserContext] = []

        def _new_context(**kwargs: Any) -> BrowserContext:
            context = browser.new_context(**browser_context_args, **kwargs)
            original_close = context.close

            def _close_wrapper(*args: Any, **kwargs: Any) -> None:
                contexts.remove(context)
                _artifacts_recorder.on_will_close_browser_context(context)
                original_close(*args, **kwargs)

            context.close = _close_wrapper
            contexts.append(context)
            _artifacts_recorder.on_did_create_browser_context(context)
            return context

        yield cast(CreateContextCallback, _new_context)
        for context in contexts.copy():
            context.close()

    @pytest.fixture
    def context(self, new_context: CreateContextCallback) -> BrowserContext:
        return new_context()

    @pytest.fixture
    def page(self, context: BrowserContext) -> Page:
        return context.new_page()


class ArtifactsRecorder:
    def __init__(
        self,
        pytestconfig: Any,
        request: pytest.FixtureRequest,
        output_path: str,
        playwright: Playwright,
        pw_artifacts_folder: tempfile.TemporaryDirectory,
    ) -> None:
        self._request = request
        self._pytestconfig = pytestconfig
        self._playwright = playwright
        self._output_path = output_path
        self._pw_artifacts_folder = pw_artifacts_folder

        self._all_pages: List[Page] = []
        self._screenshots: List[str] = []
        self._traces: List[str] = []
        self._tracing_option = pytestconfig.getoption("--tracing")
        self._capture_trace = self._tracing_option in ["on", "retain-on-failure"]

    def _build_artifact_test_folder(self, folder_or_file_name: str) -> str:
        return os.path.join(
            self._output_path,
            _truncate_file_name(folder_or_file_name),
        )

    def did_finish_test(self, failed: bool) -> None:
        screenshot_option = self._pytestconfig.getoption("--screenshot")
        capture_screenshot = screenshot_option == "on" or (
            failed and screenshot_option == "only-on-failure"
        )
        if capture_screenshot:
            for index, screenshot in enumerate(self._screenshots):
                human_readable_status = "failed" if failed else "finished"
                screenshot_path = self._build_artifact_test_folder(
                    f"test-{human_readable_status}-{index + 1}.png",
                )
                os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
                shutil.move(screenshot, screenshot_path)
        else:
            for screenshot in self._screenshots:
                os.remove(screenshot)

        if self._tracing_option == "on" or (
            failed and self._tracing_option == "retain-on-failure"
        ):
            for index, trace in enumerate(self._traces):
                trace_file_name = (
                    "trace.zip" if len(self._traces) == 1 else f"trace-{index + 1}.zip"
                )
                trace_path = self._build_artifact_test_folder(trace_file_name)
                os.makedirs(os.path.dirname(trace_path), exist_ok=True)
                shutil.move(trace, trace_path)
        else:
            for trace in self._traces:
                os.remove(trace)

        video_option = self._pytestconfig.getoption("--video")
        preserve_video = video_option == "on" or (
            failed and video_option == "retain-on-failure"
        )
        if preserve_video:
            for index, page in enumerate(self._all_pages):
                video = page.video
                if not video:
                    continue
                try:
                    video_file_name = (
                        "video.webm"
                        if len(self._all_pages) == 1
                        else f"video-{index + 1}.webm"
                    )
                    video.save_as(
                        path=self._build_artifact_test_folder(video_file_name)
                    )
                except Error:
                    # Silent catch empty videos.
                    pass
        else:
            for page in self._all_pages:
                # Can be changed to "if page.video" without try/except once https://github.com/microsoft/playwright-python/pull/2410 is released and widely adopted.
                if video_option in ["on", "retain-on-failure"]:
                    try:
                        page.video.delete()
                    except Error:
                        pass

    def on_did_create_browser_context(self, context: BrowserContext) -> None:
        context.on("page", lambda page: self._all_pages.append(page))
        if self._request and self._capture_trace:
            context.tracing.start(
                title=slugify(self._request.node.nodeid),
                screenshots=True,
                snapshots=True,
                sources=True,
            )

    def on_will_close_browser_context(self, context: BrowserContext) -> None:
        if self._capture_trace:
            trace_path = Path(self._pw_artifacts_folder.name) / _create_guid()
            context.tracing.stop(path=trace_path)
            self._traces.append(str(trace_path))
        else:
            context.tracing.stop()

        if self._pytestconfig.getoption("--screenshot") in ["on", "only-on-failure"]:
            for page in context.pages:
                try:
                    screenshot_path = (
                        Path(self._pw_artifacts_folder.name) / _create_guid()
                    )
                    page.screenshot(
                        timeout=5000,
                        path=screenshot_path,
                        full_page=self._pytestconfig.getoption(
                            "--full-page-screenshot"
                        ),
                    )
                    self._screenshots.append(str(screenshot_path))
                except Error:
                    pass
