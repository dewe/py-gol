# Common variables
PYTHON := python
PIP := pip
PYTEST := pytest
BLACK := black
RUFF := ruff check
MYPY := mypy

.PHONY: init test clean format lint help

# Default target
help:
	@echo "Available targets:"
	@echo "  make init      - Install package in development mode with all dependencies"
	@echo "  make test      - Run tests (depends on init)"
	@echo "  make clean     - Remove build/test artifacts"
	@echo "  make format    - Format code with black and ruff"
	@echo "  make lint      - Run all linters (depends on format)"

# Development setup
init:
	@echo "Installing development dependencies..."
	@$(PIP) install -e ".[dev]"

# Testing
test:
	@echo "Running tests..."
	@$(PYTEST) -v tests/

# Clean up
clean:
	@echo "Cleaning build artifacts..."
	@rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .coverage __pycache__/ **/__pycache__/
	@find . -type d -name "__pycache__" -exec rm -r {} +
	@find . -type f -name "*.pyc" -delete

# Code formatting
format:
	@echo "Formatting code..."
	@$(BLACK) .
	@$(RUFF) --fix .

# Linting
lint: format
	@echo "Running linters..."
	@$(BLACK) --check .
	@$(RUFF) .
	@$(MYPY) .

# Set error handling
.SHELLFLAGS := -e 