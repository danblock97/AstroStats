# AstroStats Test Suite

This directory contains unit tests for the AstroStats Discord bot.

## Setup

1. Install the test dependencies:
```bash
pip install -r requirements-dev.txt
```

2. Run the tests:
```bash
pytest
```

## Test Organization

The tests are organized to mirror the structure of the application:

- `test_core/` - Tests for core functionality
- `test_cogs/` - Tests for bot commands organized by category
- `test_services/` - Tests for API and database services

## Running Specific Tests

You can run specific test files or test functions:

```bash
# Run all tests in a directory
pytest tests/test_core/

# Run a specific test file
pytest tests/test_core/test_utils.py

# Run a specific test function
pytest tests/test_core/test_utils.py::test_create_progress_bar
```

## Code Coverage

To generate a code coverage report:

```bash
pytest --cov=. --cov-report=html
```

This will create an HTML report in the `htmlcov` directory.

## Mocking

Most tests use mocking to avoid making actual API calls or database connections. The mock objects and fixtures are defined in `conftest.py`.

## Asynchronous Testing

For testing async functions, use the `@pytest.mark.asyncio` decorator and make your test function `async`.