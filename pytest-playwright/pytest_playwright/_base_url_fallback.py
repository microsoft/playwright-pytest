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

# Provides the base_url fixture when pytest-base-url is not in use, see
# pytest_load_initial_conftests in pytest_playwright.py. It is a module rather
# than a class instance, as pytest 9.2 deprecates session-scoped fixtures defined
# as instance methods: https://github.com/microsoft/playwright-pytest/issues/341

from typing import Any, Optional

import pytest


@pytest.fixture(scope="session")
def base_url(pytestconfig: Any) -> Optional[str]:
    return (
        pytestconfig.getoption("--base-url") or pytestconfig.getini("base_url") or None
    )
