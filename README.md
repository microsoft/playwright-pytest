# Pytest Playwright Plugin

![CI](https://github.com/microsoft/playwright-pytest/workflows/CI/badge.svg)
[![PyPI](https://img.shields.io/pypi/v/pytest-playwright)](https://pypi.org/project/pytest-playwright/)
[![Coverage Status](https://coveralls.io/repos/github/microsoft/playwright-pytest/badge.svg?branch=main)](https://coveralls.io/github/microsoft/playwright-pytest?branch=main)
[![black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/python/black)

> A Pytest wrapper for [Playwright](https://github.com/microsoft/playwright-python) to automate web browsers (Chromium, Firefox, WebKit).

## Features

- Have a separate new page and context for each test with Pytest fixtures
- Run your end-to-end tests on multiple browsers by a CLI argument
- Run them headful with the `--headful` argument to debug them easily
- Using [base-url](https://github.com/pytest-dev/pytest-base-url) to only use the relative URL in your `Page.goto` calls

## Installation

```
pip install pytest-playwright
```

Basic example for more see the [examples sections](#examples) as a reference.

```py
def test_example_is_working(page):
    page.goto("https://example.com")
    page.waitForSelector("text=Example Domain")
    page.click("text=More information")
```

## Fixtures

### `browser_name` - session scope

A string that contains the current browser name.

### `browser` - session scope

A Playwright browser instance for the session.

### `context` - function scope

A separate Playwright context instance for each new test.

### `page` - function scope

A separate Playwright page instance for each new test.

### `browse_type_launch_args` - session scope

A fixture that you can define to overwrite the launch arguments for [`launch()`](https://playwright.dev/#path=docs%2Fapi.md&q=browsertypelaunchoptions). It should return a Dict.

### `browse_context_args` - session scope

A fixture that you can define to overwrite the context arguments for [`newContext()`](https://playwright.dev/#path=docs%2Fapi.md&q=browsernewcontextoptions). It should return a Dict.

### `is_chromium`, `is_firefox`, `is_webkit` - session scope

A fixture which is a boolean if a specific execution is made by the specified browser.

## CLI arguments

### `--browser`

By default, the tests run on the Chromium browser. You can pass multiple times the `--browser` flag to run it on different browsers or a single time to run it only on a specific browser.

Possible values: `chromium`, `firefox`, `webkit`

### `--headful`

By default, the tests run in headless mode. You can pass the `--headful` CLI flag to run the browser in headful mode.

## Examples

### Skipping by browser type

```py
import pytest

@pytest.mark.skip_browser("firefox")
def test_visit_example(page):
    page.goto("https://example.com")
    # ...
```

### Running only on a specific browser

```py
import pytest

@pytest.mark.only_browser("chromium")
def test_visit_example(page):
    page.goto("https://example.com")
    # ...
```

### Handle base-url

Start Pytest with the `base-url` argument. Example: `pytest --base-url http://localhost:8080`

```py
def test_visit_example(page):
    page.goto("/admin")
    # -> Will result in http://localhost:8080/admin
```

### Using Mypy types for auto completion

```py
from playwright.sync_api import Page

def test_visit_admin_dashboard(page: Page):
    page.goto("/admin")
    # ...
```

## Special thanks

[Max Schmitt](https://github.com/mxschmitt) for creating and maintaining the Pytest Playwright plugin.

## Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit https://cla.opensource.microsoft.com.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.
