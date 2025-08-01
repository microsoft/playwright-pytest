# Development Quick Start

Quick setup guide for experienced developers. For comprehensive documentation, see [CONTRIBUTING.md](CONTRIBUTING.md).

## TL;DR Setup

```bash
# Clone and setup
git clone https://github.com/microsoft/playwright-pytest.git
cd playwright-pytest
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies and packages
pip install --upgrade pip
pip install -r local-requirements.txt
pip install -e pytest-playwright -e pytest-playwright-asyncio
playwright install --with-deps

# Setup pre-commit
pre-commit install

# Verify installation
pytest  # On Linux: xvfb-run pytest
```

## Key Commands

```bash
# Testing
pytest                           # Run all tests
pytest tests/test_sync.py        # Sync plugin tests
pytest tests/test_asyncio.py     # Async plugin tests
pytest -k "test_name"            # Specific test
xvfb-run pytest                 # Linux headless

# Code Quality
pre-commit run --all-files       # All checks
black .                          # Format
mypy pytest-playwright/pytest_playwright pytest-playwright-asyncio/pytest_playwright_asyncio  # Type check
flake8 .                         # Lint

# Development
git checkout -b feature/name     # New branch
git add -A && git commit         # Commit (triggers pre-commit)
```

## Project Structure

```
pytest-playwright/
├── pytest-playwright/          # Sync plugin
├── pytest-playwright-asyncio/  # Async plugin
├── tests/                      # Test suite
├── setup.cfg                   # Pytest/tool config
├── local-requirements.txt      # Dev dependencies
└── .pre-commit-config.yaml     # Code quality
```

## Key Files

- **Plugin code**: `*/pytest_playwright/pytest_playwright.py`
- **Test config**: `setup.cfg`
- **Dev deps**: `local-requirements.txt`
- **Package config**: `*/pyproject.toml`
- **CI**: `.github/workflows/ci.yml`

## Important Notes

- **Dual packages**: Both plugins are mutually exclusive
- **Editable installs**: Required for development (`-e` flag)
- **Browser install**: `playwright install --with-deps` needed for tests
- **Platform testing**: Linux requires `xvfb-run`
- **Pre-commit**: Runs automatically on commit (black, mypy, flake8)

## Quick Debugging

```bash
# Test issues
pytest --cache-clear            # Clear cache
pytest -v -s                    # Verbose output
pytest --pdb                    # Drop into debugger

# Environment issues
pip list | grep playwright      # Check installations
pip install -e pytest-playwright -e pytest-playwright-asyncio  # Reinstall

# Browser issues
playwright install --with-deps  # Reinstall browsers
```

## Making Changes

1. Create feature branch from `main`
2. Make changes in appropriate plugin directory
3. Add/update tests
4. Run `pytest` and `pre-commit run --all-files`
5. Commit and push
6. Create PR with clear title and description

For detailed information, troubleshooting, and contribution guidelines, see [CONTRIBUTING.md](CONTRIBUTING.md).
