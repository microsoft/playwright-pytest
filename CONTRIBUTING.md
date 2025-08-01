# Contributing to pytest-playwright

This project welcomes contributions and suggestions. This guide will help you get started with local development and submitting pull requests.

## Legal Requirements

Most contributions require you to agree to a Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us the rights to use your contribution. For details, visit https://cla.opensource.microsoft.com.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/). For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Development Setup

### Prerequisites

- **Python 3.9 or higher** (Python 3.9, 3.10, 3.11, 3.12, and 3.13 are supported)
- **Git** for version control
- **Virtual environment** tool (venv, virtualenv, or conda)

### Local Environment Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/microsoft/playwright-pytest.git
   cd playwright-pytest
   ```

2. **Create and activate a virtual environment**

   Using Python's built-in venv:
   ```bash
   # Create virtual environment
   python -m venv venv

   # Activate virtual environment
   # On macOS/Linux:
   source venv/bin/activate

   # On Windows:
   venv\Scripts\activate
   ```

3. **Install development dependencies**
   ```bash
   pip install --upgrade pip
   pip install -r local-requirements.txt
   ```

4. **Install both packages in editable mode**
   ```bash
   pip install -e pytest-playwright
   pip install -e pytest-playwright-asyncio
   ```

5. **Install Playwright browsers**
   ```bash
   playwright install --with-deps
   ```

6. **Set up pre-commit hooks**
   ```bash
   pre-commit install
   ```

### Verify Installation

Run the test suite to ensure everything is working:

```bash
# Run all tests
pytest

# On Linux, you may need xvfb for browser tests
xvfb-run pytest
```

## Development Workflow

### Making Changes

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b bugfix/issue-description
   ```

2. **Make your changes**
   - Edit code in either `pytest-playwright/` or `pytest-playwright-asyncio/` directories
   - Follow the existing code style and patterns
   - Add tests for new functionality

3. **Run tests and code quality checks**
   ```bash
   # Run tests
   pytest

   # Run pre-commit hooks manually (optional, they run automatically on commit)
   pre-commit run --all-files
   ```

### Testing Your Changes

The project uses a comprehensive test suite with the following structure:

- **Test Configuration**: Tests are configured in `setup.cfg`
- **Test Files**:
  - `tests/test_sync.py` - Tests for the sync plugin
  - `tests/test_asyncio.py` - Tests for the async plugin
- **Test Isolation**: Each plugin is tested separately using pytest addopts configuration

#### Running Tests

```bash
# Run all tests
pytest

# Run tests for specific plugin
pytest tests/test_sync.py
pytest tests/test_asyncio.py

# Run specific test
pytest -k "test_name"

# Run with coverage
pytest --cov=pytest_playwright --cov-report xml

# Run tests in parallel
pytest -n auto
```

#### Platform-Specific Testing

- **Linux**: Use `xvfb-run pytest` for headless browser testing
- **macOS/Windows**: Tests can run directly with `pytest`

### Code Quality Tools

This project uses several tools to maintain code quality:

#### Automated Tools (via pre-commit)

- **black**: Code formatting
- **mypy**: Type checking
- **flake8**: Linting
- **trailing-whitespace**: Removes trailing whitespace
- **end-of-file-fixer**: Ensures files end with newline

#### Manual Execution

```bash
# Format code
black .

# Type checking
mypy pytest-playwright/pytest_playwright pytest-playwright-asyncio/pytest_playwright_asyncio

# Linting
flake8 .

# Run all pre-commit hooks
pre-commit run --all-files
```

### Project Structure

This repository contains two related but separate pytest plugins:

```
pytest-playwright/
├── pytest-playwright/           # Sync plugin package
│   ├── pytest_playwright/
│   │   ├── __init__.py
│   │   └── pytest_playwright.py  # Main plugin implementation
│   └── pyproject.toml           # Package configuration
├── pytest-playwright-asyncio/   # Async plugin package
│   ├── pytest_playwright_asyncio/
│   │   ├── __init__.py
│   │   └── pytest_playwright.py  # Async plugin implementation
│   └── pyproject.toml           # Package configuration
├── tests/                       # Test suite
│   ├── test_sync.py            # Tests for sync plugin
│   └── test_asyncio.py         # Tests for async plugin
├── .github/workflows/          # CI/CD configuration
├── setup.cfg                  # Test and tool configuration
├── local-requirements.txt     # Development dependencies
└── .pre-commit-config.yaml   # Code quality automation
```

#### Key Files

- **`pyproject.toml`** files: Package metadata and dependencies
- **`setup.cfg`**: Pytest configuration and tool settings
- **`local-requirements.txt`**: Development dependencies (black, mypy, etc.)
- **`.pre-commit-config.yaml`**: Automated code quality checks
- **`.github/workflows/ci.yml`**: Continuous integration pipeline

### Understanding Plugin Architecture

Both plugins follow the same architecture but target different Python async patterns:

- **pytest-playwright**: For synchronous tests using Playwright's sync API
- **pytest-playwright-asyncio**: For async tests using Playwright's async API with pytest-asyncio

#### Plugin Compatibility

The two plugins are **mutually exclusive** and cannot be used together. The codebase includes compatibility checks to prevent conflicts.

#### Plugin Hooks

Both plugins implement several pytest hooks:
- `pytest_addoption`: Adds command-line options
- `pytest_configure`: Plugin configuration
- `pytest_generate_tests`: Test parametrization
- Various fixtures for browser automation

## Submitting Pull Requests

### Before Submitting

1. **Ensure all tests pass**
   ```bash
   pytest
   ```

2. **Verify code quality checks pass**
   ```bash
   pre-commit run --all-files
   ```

3. **Update documentation** if needed

4. **Add tests** for new functionality

### PR Guidelines

1. **Create a clear title**
   - Use conventional commit format: `feat:`, `fix:`, `docs:`, `test:`, etc.
   - Be descriptive: `feat: add browser timeout configuration option`

2. **Write a comprehensive description**
   - Explain what changes were made and why
   - Reference related issues: `Fixes #123` or `Related to #456`
   - Include testing instructions if applicable

3. **Keep PRs focused**
   - One feature or fix per PR
   - Avoid mixing unrelated changes

4. **Respond to feedback**
   - Address review comments promptly
   - Update the PR based on maintainer suggestions
   - Ask questions if feedback is unclear

### PR Review Process

1. **Automated checks**: CI will run tests across multiple Python versions and platforms
2. **Code review**: Maintainers will review your code for quality and correctness
3. **Feedback incorporation**: You may be asked to make changes
4. **Merge**: Once approved, maintainers will merge your PR

## Common Development Tasks

### Adding New Browser Options

If you're adding new command-line options:

1. Add the option in `pytest_addoption` function in both plugin files
2. Add corresponding fixture if needed
3. Update tests to verify the new option works
4. Update documentation

### Working with Browser Fixtures

The plugins provide several browser-related fixtures:
- `browser_name`: Current browser being tested
- `browser`: Browser instance
- `context`: Browser context
- `page`: Browser page

### Debugging Test Failures

1. **Run tests with verbose output**
   ```bash
   pytest -v
   ```

2. **Run specific failing test**
   ```bash
   pytest tests/test_sync.py::test_specific_test -v
   ```

3. **Use pytest debugging**
   ```bash
   pytest --pdb  # Drop into debugger on failure
   ```

4. **Check browser screenshots** (saved in test-results directory)

5. **Enable test artifacts for debugging**
   ```bash
   pytest --screenshot=on --video=on --tracing=on  # Generate debugging artifacts
   ```

## Troubleshooting

### Common Issues

#### Virtual Environment Issues
```bash
# If packages seem not installed
pip list | grep playwright

# Reinstall in editable mode
pip install -e pytest-playwright -e pytest-playwright-asyncio
```

#### Playwright Browser Issues
```bash
# Reinstall browsers
playwright install --with-deps

# Check browser installation
playwright install --help
```

#### Test Failures
```bash
# Clear pytest cache
pytest --cache-clear

# Run tests with more verbose output
pytest -v -s
```

#### Pre-commit Hook Issues
```bash
# Reinstall pre-commit
pre-commit uninstall
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

### Getting Help

- **GitHub Issues**: Report bugs or request features
- **GitHub Discussions**: Ask questions or discuss ideas
- **Maintainer Contact**: Tag maintainers in issues or PRs for assistance

## Code Standards

### Python Style

- **Formatting**: Use `black` (enforced by pre-commit)
- **Type Hints**: Required for new code (checked by `mypy`)
- **Import Organization**: Follow `isort` conventions
- **Line Length**: 88 characters (black default)

### Error Handling

- Use appropriate exception types
- Provide clear error messages
- Include context when raising exceptions

### Testing Standards

- **Test Coverage**: Aim for comprehensive coverage of new functionality
- **Test Naming**: Use descriptive test names that explain what is being tested
- **Fixtures**: Leverage existing fixtures when possible
- **Assertions**: Use clear, specific assertions

### Documentation Standards

- **Docstrings**: Use for public functions and classes
- **Comments**: Explain complex logic, not obvious code
- **README Updates**: Update README.md if adding user-facing features
- **Type Annotations**: Required for all new code

## Release Process

This information is primarily for maintainers:

1. **Version Bumping**: Update version in `pyproject.toml` files
2. **Changelog**: Update release notes
3. **Testing**: Ensure all tests pass across supported Python versions
4. **Publishing**: Automated via GitHub Actions on tag creation

## Contributing to Documentation

Documentation improvements are always welcome:

- Fix typos or unclear explanations
- Add examples for common use cases
- Improve setup instructions
- Add troubleshooting guides

Thank you for contributing to pytest-playwright! 🎭
