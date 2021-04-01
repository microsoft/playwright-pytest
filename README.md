# Pytest plugin for Playwright [![PyPI](https://img.shields.io/pypi/v/pytest-playwright)](https://pypi.org/project/pytest-playwright/)

Write end-to-end tests for your web apps with [Playwright](https://github.com/microsoft/playwright-python) and [pytest](https://docs.pytest.org/en/stable/).

- Support for **all modern browsers** including Chromium, WebKit and Firefox.
- Support for **headless and headed** execution.
- **Built-in fixtures** that provide browser primitives to test functions.

## Usage

```txt
pip install pytest-playwright
```

Use the `page` fixture to write a basic test. See [more examples](#examples).

```py
def test_example_is_working(page):
    page.goto("https://example.com")
    assert page.inner_text('h1') == 'Example Domain'
    page.click("text=More information")
```

To run your tests, use pytest CLI.

```sh
# Run tests (Chromium and headless by default)
pytest

# Run tests in headed mode
pytest --headed

# Run tests in a different browser (chromium, firefox, webkit)
pytest --browser firefox

# Run tests in multiple browsers
pytest --browser chromium --browser webkit
```

If you want to add the CLI arguments automatically without specifying them, you can use the [pytest.ini](https://docs.pytest.org/en/stable/reference.html#ini-options-ref) file:

```ini
# content of pytest.ini
[pytest]
# Run firefox with UI
addopts = --headed --browser firefox
```

## Fixtures

This plugin configures Playwright-specific [fixtures for pytest](https://docs.pytest.org/en/latest/fixture.html). To use these fixtures, use the fixture name as an argument to the test function.

```py
def test_my_app_is_working(fixture_name):
    # Test using fixture_name
    # ...
```

**Function scope**: These fixtures are created when requested in a test function and destroyed when the test ends.

- `context`: New [browser context](https://playwright.dev/python/docs/core-concepts#browser-contexts) for a test.
- `page`: New [browser page](https://playwright.dev/python/docs/core-concepts#pages-and-frames) for a test.

**Session scope**: These fixtures are created when requested in a test function and destroyed when all tests end.

- `browser`: Browser instance launched by Playwright.
- `browser_name`: Browser name as string.
- `is_chromium`, `is_webkit`, `is_firefox`: Booleans for the respective browser types.

**Customizing fixture options**: For `browser` and `context` fixtures, use the the following fixtures to define custom launch options.

- `browser_type_launch_args`: Override launch arguments for [`browserType.launch()`](https://playwright.dev/python/docs/api/class-browsertype#browser_typelaunchoptions). It should return a Dict.
- `browser_context_args`: Override the options for [`browser.new_context()`](https://playwright.dev/python/docs/api/class-browser#browsernew_contextoptions). It should return a Dict.

## Examples

### Configure Mypy typings for auto-completion

```py
from playwright.sync_api import Page

def test_visit_admin_dashboard(page: Page):
    page.goto("/admin")
    # ...
```

### Configure slow mo

Run tests with slow mo with the `--slowmo` argument.

```bash
pytest --slowmo 100
```

### Skip test by browser

```py
import pytest

@pytest.mark.skip_browser("firefox")
def test_visit_example(page):
    page.goto("https://example.com")
    # ...
```

### Run on a specific browser

```py
import pytest

@pytest.mark.only_browser("chromium")
def test_visit_example(page):
    page.goto("https://example.com")
    # ...
```

### Run with a custom browser channel like Google Chrome or Microsoft Edge

```sh
pytest --browser-channel chrome # or chrome-beta, chrome-dev, chrome-canary, msedge, msedge-beta, msedge-dev, msedge-canary
```

```python
def test_example(page):
    page.goto("https://example.com")
```

### Configure base-url

Start Pytest with the `base-url` argument.

```sh
pytest --base-url http://localhost:8080
```

```py
def test_visit_example(page):
    page.goto("/admin")
    # -> Will result in http://localhost:8080/admin
```

### Ignore HTTPS errors

conftest.py

```py
import pytest

@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "ignore_https_errors": True
    }
```

### Use custom viewport size

conftest.py

```py
import pytest

@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "viewport": {
            "width": 1920,
            "height": 1080,
        }
    }
```

### Device emulation

conftest.py

```py
import pytest

@pytest.fixture(scope="session")
def browser_context_args(browser_context_args, playwright):
    iphone_11 = playwright.devices['iPhone 11 Pro']
    return {
        **browser_context_args,
        **iphone_11,
    }
```

## Debugging

### Use with pdb

Use the `breakpoint()` statement in your test code to pause execution and get a [pdb](https://docs.python.org/3/library/pdb.html) REPL.

```py
def test_bing_is_working(page):
    page.goto("https://bing.com")
    breakpoint()
    # ...
```

### Screenshot on test failure

You can capture screenshots for failed tests with a [pytest runtest hook](https://docs.pytest.org/en/6.1.0/reference.html?highlight=pytest_runtest_makereport#test-running-runtest-hooks). Add this to your `conftest.py` file.

Note that this snippet uses `slugify` to convert test names to file paths, which can be installed with `pip install python-slugify`.

```py
# In conftest.py
from slugify import slugify
from pathlib import Path

def pytest_runtest_makereport(item, call) -> None:
    if call.when == "call":
        if call.excinfo is not None and "page" in item.funcargs:
            page = item.funcargs["page"]
            screenshot_dir = Path(".playwright-screenshots")
            screenshot_dir.mkdir(exist_ok=True)
            page.screenshot(path=str(screenshot_dir / f"{slugify(item.nodeid)}.png"))
```

## Deploy to CI

Use the [Playwright GitHub Action](https://github.com/microsoft/playwright-github-action) or [guides for other CI providers](https://playwright.dev/python/docs/ci) to deploy your tests to CI/CD

## Special thanks

Thanks to [Max Schmitt](https://github.com/mxschmitt) for creating and maintaining this project.
