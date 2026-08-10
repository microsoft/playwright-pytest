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

import re
import subprocess
import sys

import pytest


def attach_snapshot_resume(testdir: pytest.Testdir) -> None:
    proc = testdir.popen(
        [
            sys.executable,
            "-m",
            "pytest",
            str(testdir.tmpdir),
            "--browser",
            "chromium",
            "--playwright-debug=cli",
            "-s",
        ],
        cwd=str(testdir.tmpdir),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    assert proc.stdout is not None
    try:
        session_re = re.compile(rb"cli attach (tw-[0-9a-f]+)")
        output = b""
        session_name = None
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            output += line
            match = session_re.search(line)
            if match:
                session_name = match.group(1).decode()
                break

        if session_name is None:
            raise AssertionError(
                "pytest exited before printing attach instructions:\n"
                + output.decode(errors="replace")
            )

        cli = [sys.executable, "-m", "playwright", "cli"]
        for args in (
            ["attach", session_name],
            [f"--s={session_name}", "snapshot"],
            [f"--s={session_name}", "resume"],
        ):
            result = subprocess.run(
                [*cli, *args],
                cwd=str(testdir.tmpdir),
                capture_output=True,
                check=False,
            )
            assert result.returncode == 0, (result.stdout + result.stderr).decode(
                errors="replace"
            )

        output += proc.stdout.read()
        assert proc.wait(timeout=60) == 0
        out = output.decode(errors="replace")
        assert "python -m playwright cli attach tw-" in out
        assert "1 passed" in out
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
