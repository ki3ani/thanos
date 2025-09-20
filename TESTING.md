# Testing and Linting

This repository now includes comprehensive testing and linting infrastructure for the Thanos microservices project.

## Quick Start

```bash
# Install development dependencies
make install-dev

# Run all tests
make test

# Run linting
make lint

# Format code
make format
```

## Test Coverage

### Recommendation Agent (88% coverage)
- ✅ Health check endpoint
- ✅ Request validation
- ✅ Gemini AI integration (mocked)  
- ✅ Product catalog gRPC integration (mocked)
- ✅ Error handling and edge cases
- ✅ Pydantic model validation

### Frontend Proxy (Working tests)
- ✅ HTTP request proxying
- ✅ Cart interception logic
- ✅ Event publishing to MCP toolbox
- ✅ Header and cookie forwarding
- ✅ Environment configuration

## Development Tools

- **pytest**: Test framework with coverage reporting
- **black**: Code formatting (88 character limit)
- **flake8**: Linting with sensible defaults
- **mypy**: Type checking
- **httpx**: HTTP client for testing FastAPI apps

## Files Added

- `tests/` - Test directory with comprehensive test suites
- `dev-requirements.txt` - Development dependencies
- `Makefile` - Convenient development commands
- `pyproject.toml` - Tool configuration (black, mypy, pytest, coverage)
- `.flake8` - Flake8 configuration
- `run_tests.sh` - Test runner script

## Available Make Commands

```bash
make help           # Show available commands
make install        # Install production dependencies
make install-dev    # Install development dependencies
make test           # Run tests with coverage
make test-verbose   # Run tests with verbose output
make lint           # Run flake8 and mypy
make format         # Format code with black
make format-check   # Check code formatting
make clean          # Clean up generated files
make check-all      # Run formatting check, linting, and tests
```

## Running Tests

```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest tests/test_recommendation_simple.py

# Run with coverage
python -m pytest --cov=recommendation-agent --cov=frontend-proxy

# Run only unit tests
python -m pytest -m unit
```

The testing infrastructure provides excellent coverage for both services with proper mocking of external dependencies like Gemini AI, gRPC services, and HTTP requests.