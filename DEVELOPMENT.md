# Python Project Agent Rules

This is a Python project using modern tooling with uv, ruff, pre-commit hooks, typing, pytest, Docker, and GitHub Actions CI/CD.

## Project Setup Commands

**Package management and dependencies:**
```bash
# Install dependencies
uv sync

# Add a new dependency
uv add <package-name>

# Add a development dependency
uv add --dev <package-name>

# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate  # Unix/macOS
# or
.venv\Scripts\activate     # Windows
```

## Code Quality Commands

**Linting and formatting:**
```bash
# Run ruff linter
uv run ruff check .

# Fix auto-fixable issues
uv run ruff check . --fix

# Format code
uv run ruff format .

# Check formatting without changing files
uv run ruff format . --check
```

**Type checking:**
```bash
# Run mypy type checker
uv run mypy .

# Type check specific file
uv run mypy src/module.py
```

## Testing Commands

**Running tests:**
```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov

# Run specific test file
uv run pytest tests/test_module.py

# Run tests matching pattern
uv run pytest -k "test_pattern"

# Run tests in verbose mode
uv run pytest -v

# Run tests and stop on first failure
uv run pytest -x
```

## Pre-commit Hooks

**Setup and usage:**
```bash
# Install pre-commit hooks
uv run pre-commit install

# Run hooks on all files
uv run pre-commit run --all-files

# Update hook versions
uv run pre-commit autoupdate
```

## Development Workflow

### Local Development
1. **Install dependencies**: `uv sync`
2. **Install pre-commit hooks**: `uv run pre-commit install`
3. **Write code** with proper type hints
4. **Write tests** in `tests/` directory
5. **Run linter**: `uv run ruff check . --fix`
6. **Run formatter**: `uv run ruff format .`
7. **Run type checker**: `uv run mypy .`
8. **Run tests**: `uv run pytest --cov`
9. **Commit changes** (pre-commit hooks will run automatically)

### Docker Development
1. **Start development environment**: `docker-compose up app-dev`
2. **Run tests in container**: `docker-compose --profile test up test`
3. **Run linting in container**: `docker-compose --profile lint up lint`
4. **Build production image**: `docker build -t app:latest .`

### CI/CD Pipeline
1. **Push to GitHub** (triggers CI automatically)
2. **Create pull request** (triggers CI on PR)
3. **Review CI results** in GitHub Actions
4. **Merge after CI passes**

## Docker Commands

**Building and running with Docker:**
```bash
# Build production image
docker build -t app:latest .

# Build development image
docker build -f Dockerfile.dev -t app:dev .

# Run production container
docker run -p 8000:8000 app:latest

# Run with docker-compose (production)
docker-compose up app

# Run with docker-compose (development with hot reload)
docker-compose up app-dev

# Run tests in container
docker-compose --profile test up test

# Run linting in container
docker-compose --profile lint up lint

# Clean up containers and images
docker-compose down
docker system prune
```

## CI/CD with GitHub Actions

**Automated workflows:**
- **CI Pipeline**: Runs on push/PR to main/develop branches
  - Tests across Python 3.9-3.12
  - Linting with ruff
  - Type checking with mypy
  - Test coverage reporting
  - Docker image building and testing

**Manual triggers:**
```bash
# Trigger workflow manually (if configured)
gh workflow run ci.yml
```

## Project Structure

```
├── .github/
│   └── workflows/
│       └── ci.yml      # GitHub Actions CI/CD
├── src/                # Source code
├── tests/              # Test files
├── pyproject.toml      # Project configuration
├── .pre-commit-config.yaml  # Pre-commit hooks
├── Dockerfile          # Production container
├── Dockerfile.dev      # Development container
├── docker-compose.yml  # Container orchestration
├── .dockerignore       # Docker ignore rules
├── .gitignore          # Git ignore rules
├── uv.lock            # Lock file (generated)
└── .venv/             # Virtual environment (generated)
```

## Code Standards

- **Line length**: 88 characters (ruff default)
- **Type hints**: Required for all functions and methods
- **Test coverage**: Aim for >90% coverage
- **Import sorting**: Handled by ruff
- **Code formatting**: Handled by ruff format
- **Docstrings**: Use Google-style docstrings

## Troubleshooting

**Common commands for debugging:**
```bash
# Check project status
uv run python --version
uv run pip list

# Clear cache
uv cache clean

# Reinstall dependencies
rm uv.lock && uv sync
```