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
import os
import socket
from typing import Any, Generator, Optional, Type
import pytest
import threading
import http.server
import socketserver

pytest_plugins = ["pytester"]


def pytest_configure(config: Any) -> None:
    config.addinivalue_line("markers", "no_add_ini: mark test to skip adding ini file")


# The testdir fixture which we use to perform unit tests will set the home directory
# To a temporary directory of the created test. This would result that the browsers will
# be re-downloaded each time. By setting the pw browser path directory we can prevent that.
if sys.platform == "darwin":
    playwright_browser_path = os.path.expanduser("~/Library/Caches/ms-playwright")
elif sys.platform == "linux":
    playwright_browser_path = os.path.expanduser("~/.cache/ms-playwright")
elif sys.platform == "win32":
    user_profile = os.environ["USERPROFILE"]
    playwright_browser_path = f"{user_profile}\\AppData\\Local\\ms-playwright"

os.environ["PLAYWRIGHT_BROWSERS_PATH"] = playwright_browser_path


class HTTPTestServer:
    PREFIX = ""
    EMPTY_PAGE = ""

    def __init__(self) -> None:
        self._server: Optional[socketserver.TCPServer] = None
        self._server_thread: Optional[threading.Thread] = None
        self._port: int = 0

    def start(self) -> None:
        """Start the test server."""

        # Efficiently find an available port using a raw socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("localhost", 0))
            self._port = s.getsockname()[1]

        # Create the actual server
        self._server = socketserver.TCPServer(
            ("localhost", self._port), self._create_handler()
        )
        self._server_thread = threading.Thread(target=self._server.serve_forever)
        self._server_thread.daemon = True
        self._server_thread.start()

        self.PREFIX = f"http://localhost:{self._port}"
        self.EMPTY_PAGE = f"{self.PREFIX}/empty.html"
        self.CROSS_PROCESS_PREFIX = f"http://127.0.0.1:{self._port}"

    def stop(self) -> None:
        """Stop the test server."""
        if self._server:
            self._server.shutdown()
            self._server.server_close()

    def _create_handler(self) -> Type[http.server.SimpleHTTPRequestHandler]:
        """Create a request handler class."""

        class SimpleHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
            def do_GET(self) -> None:
                """Handle GET requests and return simple HTML with the path."""
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()

                html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Test Server</title>
</head>
<body>
    <h1>Test Server Response</h1>
    <p>Path: {self.path}</p>
    <span id="foo">bar</span>
</body>
</html>"""
                self.wfile.write(html_content.encode("utf-8"))

        return SimpleHTTPRequestHandler


@pytest.fixture(scope="session")
def test_server() -> Generator[HTTPTestServer, None, None]:
    server = HTTPTestServer()
    server.start()
    yield server
    server.stop()
