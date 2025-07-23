# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python project that provides examples for using the `jutge_api_client` library to interact with the Jutge online judge platform. The project focuses on demonstrating various API operations like problem retrieval, user authentication, submissions, and profile management.

## Essential Commands

**Development environment setup:**
```bash
# Install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate
```

**Code quality and testing:**
```bash
# Run linter and fix issues (excludes examples/ folder)
uv run ruff check . --fix --exclude examples

# Format code (excludes examples/ folder)
uv run ruff format . --exclude examples

# Type checking (excludes examples/ folder)
uv run mypy . --exclude examples

# Run tests (excludes examples/ folder)
uv run pytest --ignore=examples

# Run tests with coverage (excludes examples/ folder)
uv run pytest --cov --ignore=examples
```

**Pre-commit hooks:**
```bash
# Install hooks
uv run pre-commit install

# Run on all files
uv run pre-commit run --all-files
```

## Architecture and Structure

The project is organized as a collection of example scripts that demonstrate different aspects of the Jutge API:

- **examples/**: Contains standalone Python scripts showcasing API usage (excluded from linting/testing as they are official examples)
  - `get_server_time.py`: Basic API connectivity test
  - `submit_problem.py`: Full submission workflow with authentication
  - `read_problem.py`: Problem retrieval and content access
  - `show_user_profile.py`: User authentication and profile access
  - `list_available_compilers.py`: Compiler enumeration
  - `print_problems_status.py`: Problem status checking

**Key API patterns:**
- All examples use `JutgeApiClient()` as the main entry point
- Authentication is handled via `jutge.login(email, password)`
- API calls follow the pattern `jutge.{service}.{operation}()`
- Main services: `misc`, `problems`, `student.profile`, `student.submissions`

**Environment setup:**
- Uses `uv` for dependency management instead of pip
- Follows modern Python tooling with ruff for linting/formatting
- Type checking with mypy
- Testing with pytest
- Pre-commit hooks for code quality

**Authentication:**
Examples demonstrate two authentication patterns:
1. Environment variables (`JUTGE_EMAIL`, `JUTGE_PASSWORD`) 
2. Interactive prompts using `rich.Prompt`

When working with this codebase, focus on the API usage patterns in the examples and maintain consistency with the established authentication and error handling approaches.