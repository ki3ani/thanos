.PHONY: install install-dev lint format test test-verbose clean help

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install production dependencies
	pip install -r recommendation-agent/requirements.txt
	pip install -r frontend-proxy/requirements.txt

install-dev:  ## Install development dependencies
	pip install -r dev-requirements.txt

lint:  ## Run linting tools
	@echo "Running flake8..."
	flake8 recommendation-agent/main.py frontend-proxy/main.py
	@echo "Running mypy..."
	mypy recommendation-agent/main.py frontend-proxy/main.py --ignore-missing-imports
	@echo "Linting completed!"

format:  ## Format code with black
	black recommendation-agent/main.py frontend-proxy/main.py
	@echo "Code formatting completed!"

format-check:  ## Check code formatting without making changes
	black --check recommendation-agent/main.py frontend-proxy/main.py

test:  ## Run tests with coverage
	pytest

test-verbose:  ## Run tests with verbose output
	pytest -v

test-unit:  ## Run only unit tests
	pytest -m unit

test-integration:  ## Run only integration tests  
	pytest -m integration

clean:  ## Clean up generated files
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf htmlcov
	rm -rf .coverage

check-all: format-check lint test  ## Run all checks (format, lint, test)