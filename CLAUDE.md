# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI-powered system that automatically solves programming problems from the Jutge online judge platform. The project combines API interaction with OpenAI GPT models to read problems, generate solutions, submit them, and analyze results. It includes a comprehensive CLI interface, benchmarking system, and batch processing capabilities for automated problem solving.

## Essential Commands

**Development environment setup:**
```bash
# Install dependencies
uv sync

# Install with benchmark dependencies (for AI model comparison)
uv sync --extra benchmark

# Install development dependencies
uv sync --extra dev

# Activate virtual environment (if needed)
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

**CLI Usage:**
```bash
# Interactive configuration setup
uv run python cli.py config --interactive

# Solve a specific problem
uv run python cli.py solve P12345

# Solve multiple problems from a list
uv run python cli.py solve P12345 P67890 P11111

# Run benchmarks comparing different AI models
uv run python cli.py benchmark --config benchmark_config.yaml

# View benchmark results
uv run python view_benchmark_results.py
```

**Pre-commit hooks:**
```bash
# Install hooks
uv run pre-commit install

# Run on all files
uv run pre-commit run --all-files
```

## Architecture and Structure

The project is organized as a comprehensive AI-powered problem solving system:

**Core modules (jutge_solver/):**
- `solver.py`: Main problem solving orchestration
- `problem_analyzer.py`: AI-powered problem analysis and approach detection
- `solution_generator.py`: Code generation using OpenAI models
- `verdict_manager.py`: Submission tracking and result analysis
- `benchmark.py`: Performance comparison across different AI models
- `config.py`: Configuration management and validation

**Entry points:**
- `cli.py`: Main CLI interface for interactive usage
- `main.py`: Alternative entry point for programmatic usage
- `view_benchmark_results.py`: Benchmark results visualization

**API layer:**
- `jutge_api_client.py`: Direct API client for Jutge platform interaction

**Configuration files:**
- `config.yaml`: Main system configuration
- `benchmark_config.yaml`: Benchmark-specific settings
- `pyproject.toml`: Project dependencies and build configuration

**Examples and reference:**
- `examples/`: Standalone scripts demonstrating API usage patterns
- `tests/`: Comprehensive test suite with unit and integration tests
- `results/`: Benchmark results and execution logs

**Key architectural patterns:**
- **Modular design**: Separate concerns for analysis, generation, and execution
- **Configuration-driven**: YAML-based configuration for flexibility
- **AI integration**: OpenAI API for intelligent problem solving
- **Async processing**: Support for batch operations and concurrent submissions
- **Comprehensive logging**: Detailed execution tracking and debugging
- **Error resilience**: Robust error handling and retry mechanisms

**Technology stack:**
- **Package management**: `uv` for fast, reliable dependency management
- **AI models**: OpenAI GPT-4, GPT-3.5-turbo with model comparison capabilities
- **HTTP client**: `requests` with `requests-toolbelt` for file uploads
- **Configuration**: `pyyaml` and `pydantic` for robust config management
- **CLI**: `rich` for beautiful terminal interfaces
- **Testing**: `pytest` with coverage reporting and async support

**Authentication and security:**
- Environment variables for credentials (`JUTGE_EMAIL`, `JUTGE_PASSWORD`, `OPENROUTER_API_KEY`)
- Interactive credential prompts with `rich.Prompt`
- Secure credential storage and validation
- API key management for multiple AI providers

When working with this codebase, focus on the modular architecture, maintain consistency with the AI-driven workflow, and ensure proper error handling throughout the problem-solving pipeline.