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
import sys
import pytest_asyncio
from pathlib import Path
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Protocol,
    Sequence,
    Union,
    Pattern,
    cast,
)

import pytest
from playwright.async_api import (
    Browser,
    BrowserContext,
    BrowserType,
    Error,
    Page,
    Playwright,
    async_playwright,
    ProxySettings,
    StorageState,
    HttpCredentials,
    Geolocation,
    ViewportSize,
)
from slugify import slugify
import tempfile
from pytest_playwright.pytest_playwright import (
    PytestPlaywright,
    _create_guid,
    _is_debugger_attached,
    _truncate_file_name,
)


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


class PytestPlaywrightAsyncio(PytestPlaywright):
    @pytest.fixture(scope="session")
    def browser_type_launch_args(self, pytestconfig: Any) -> Dict:
        launch_options = {}
        headed_option = pytestconfig.getoption("--headed")
        if headed_option:
            launch_options["headless"] = False
        elif self.VSCODE_PYTHON_EXTENSION_ID in sys.argv[0] and _is_debugger_attached():
            # When the VSCode debugger is attached, then launch the browser headed by default
            launch_options["headless"] = False
        browser_channel_option = pytestconfig.getoption("--browser-channel")
        if browser_channel_option:
            launch_options["channel"] = browser_channel_option
        slowmo_option = pytestconfig.getoption("--slowmo")
        if slowmo_option:
            launch_options["slow_mo"] = slowmo_option
        return launch_options

    @pytest.fixture(scope="session")
    def browser_context_args(
        self,
        pytestconfig: Any,
        playwright: Playwright,
        device: Optional[str],
        base_url: Optional[str],
        _pw_artifacts_folder: tempfile.TemporaryDirectory,
    ) -> Dict:
        context_args = {}
        if device:
            context_args.update(playwright.devices[device])
        if base_url:
            context_args["base_url"] = base_url

        video_option = pytestconfig.getoption("--video")
        capture_video = video_option in ["on", "retain-on-failure"]
        if capture_video:
            context_args["record_video_dir"] = _pw_artifacts_folder.name

        return context_args

    @pytest_asyncio.fixture(loop_scope="session")
    async def _artifacts_recorder(
        self,
        request: pytest.FixtureRequest,
        output_path: str,
        playwright: Playwright,
        pytestconfig: Any,
        _pw_artifacts_folder: tempfile.TemporaryDirectory,
    ) -> AsyncGenerator["ArtifactsRecorder", None]:
        artifacts_recorder = ArtifactsRecorder(
            pytestconfig, request, output_path, playwright, _pw_artifacts_folder
        )
        yield artifacts_recorder
        # If request.node is missing rep_call, then some error happened during execution
        # that prevented teardown, but should still be counted as a failure
        failed = (
            request.node.rep_call.failed if hasattr(request.node, "rep_call") else True
        )
        await artifacts_recorder.did_finish_test(failed)

    @pytest_asyncio.fixture(scope="session", loop_scope="session")
    async def playwright(self) -> AsyncGenerator[Playwright, None]:
        pw = await async_playwright().start()
        yield pw
        await pw.stop()

    @pytest.fixture(scope="session")
    def browser_type(self, playwright: Playwright, browser_name: str) -> BrowserType:
        return getattr(playwright, browser_name)

    @pytest.fixture(scope="session")
    def launch_browser(
        self,
        browser_type_launch_args: Dict,
        browser_type: BrowserType,
    ) -> Callable[..., Browser]:
        async def launch(**kwargs: Dict) -> Browser:
            launch_options = {**browser_type_launch_args, **kwargs}
            browser = await browser_type.launch(**launch_options)
            return browser

        return launch

    @pytest_asyncio.fixture(scope="session", loop_scope="session")
    async def browser(
        self, launch_browser: Callable[[], Browser]
    ) -> AsyncGenerator[Browser, None]:
        browser = await launch_browser()
        yield browser
        await browser.close()

    @pytest_asyncio.fixture(loop_scope="session")
    async def new_context(
        self,
        browser: Browser,
        browser_context_args: Dict,
        _artifacts_recorder: "ArtifactsRecorder",
        request: pytest.FixtureRequest,
    ) -> AsyncGenerator[CreateContextCallback, None]:
        browser_context_args = browser_context_args.copy()
        context_args_marker = next(
            request.node.iter_markers("browser_context_args"), None
        )
        additional_context_args = (
            context_args_marker.kwargs if context_args_marker else {}
        )
        browser_context_args.update(additional_context_args)
        contexts: List[BrowserContext] = []

        async def _new_context(**kwargs: Any) -> BrowserContext:
            context = await browser.new_context(**browser_context_args, **kwargs)
            original_close = context.close

            async def _close_wrapper(*args: Any, **kwargs: Any) -> None:
                contexts.remove(context)
                await _artifacts_recorder.on_will_close_browser_context(context)
                await original_close(*args, **kwargs)

            context.close = _close_wrapper
            contexts.append(context)
            await _artifacts_recorder.on_did_create_browser_context(context)
            return context

        yield cast(CreateContextCallback, _new_context)
        for context in contexts.copy():
            await context.close()

    @pytest_asyncio.fixture(loop_scope="session")
    async def context(self, new_context: CreateContextCallback) -> BrowserContext:
        return await new_context()

    @pytest_asyncio.fixture(loop_scope="session")
    async def page(self, context: BrowserContext) -> Page:
        return await context.new_page()


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

    async def did_finish_test(self, failed: bool) -> None:
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
                    await video.save_as(
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
                        await page.video.delete()
                    except Error:
                        pass

    async def on_did_create_browser_context(self, context: BrowserContext) -> None:
        context.on("page", lambda page: self._all_pages.append(page))
        if self._request and self._capture_trace:
            await context.tracing.start(
                title=slugify(self._request.node.nodeid),
                screenshots=True,
                snapshots=True,
                sources=True,
            )

    async def on_will_close_browser_context(self, context: BrowserContext) -> None:
        if self._capture_trace:
            trace_path = Path(self._pw_artifacts_folder.name) / _create_guid()
            await context.tracing.stop(path=trace_path)
            self._traces.append(str(trace_path))
        else:
            await context.tracing.stop()

        if self._pytestconfig.getoption("--screenshot") in ["on", "only-on-failure"]:
            for page in context.pages:
                try:
                    screenshot_path = (
                        Path(self._pw_artifacts_folder.name) / _create_guid()
                    )
                    await page.screenshot(
                        timeout=5000,
                        path=screenshot_path,
                        full_page=self._pytestconfig.getoption(
                            "--full-page-screenshot"
                        ),
                    )
                    self._screenshots.append(str(screenshot_path))
                except Error:
                    pass
