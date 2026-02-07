# SafeShell - Python CLI Justfile
# Usage: just <recipe>

# Default recipe to run when just is called without arguments
default:
    @just --list

# ============================================================================
# SETUP & ENVIRONMENT
# ============================================================================

# Initial setup (install dependencies)
init:
    @echo "🚀 Setting up SafeShell development environment..."
    uv sync
    @echo ""
    @echo "✅ Installation complete!"
    @echo ""
    @echo "Next steps:"
    @echo "  just lint     - Run linting"
    @echo "  just test     - Run tests"
    @echo "  just run      - Run SafeShell CLI"

# Install/update dependencies
install:
    uv sync

# ============================================================================
# LINTING & QUALITY
# ============================================================================

# Fast linting (Ruff only)
lint:
    @echo "▶ Running fast linting (Ruff)..."
    uv run ruff check src/ tests/
    uv run ruff format --check src/ tests/

# Comprehensive linting (Ruff + Pylint + MyPy)
lint-all:
    @echo ""
    @echo "════════════════════════════════════════════════════════════"
    @echo "  COMPREHENSIVE LINTING"
    @echo "════════════════════════════════════════════════════════════"
    @echo ""
    @echo "[1/4] Ruff (linter)"
    uv run ruff check src/ tests/
    @echo ""
    @echo "[2/4] Ruff (formatter)"
    uv run ruff format --check src/ tests/
    @echo ""
    @echo "[3/4] Pylint"
    uv run pylint src/safeshell
    @echo ""
    @echo "[4/4] MyPy (type checking)"
    uv run mypy src/safeshell

# Security scanning (Bandit)
lint-security:
    @echo ""
    @echo "════════════════════════════════════════════════════════════"
    @echo "  SECURITY SCANNING"
    @echo "════════════════════════════════════════════════════════════"
    @echo ""
    @echo "[1/1] Bandit (security linter)"
    uv run bandit -r src/safeshell -c pyproject.toml

# Complexity analysis (Radon)
lint-complexity:
    @echo ""
    @echo "════════════════════════════════════════════════════════════"
    @echo "  COMPLEXITY ANALYSIS"
    @echo "════════════════════════════════════════════════════════════"
    @echo ""
    @echo "[1/1] Radon (cyclomatic complexity)"
    uv run radon cc src/safeshell -a -s

# Thai-lint checks
lint-thai:
    @echo ""
    @echo "════════════════════════════════════════════════════════════"
    @echo "  THAI-LINT CHECKS"
    @echo "════════════════════════════════════════════════════════════"
    @echo ""
    uv run thailint file-header src/
    uv run thailint magic-numbers src/
    uv run thailint nesting src/
    uv run thailint srp src/

# ALL quality checks
lint-full:
    @echo ""
    @echo "╔════════════════════════════════════════════════════════════╗"
    @echo "║                  FULL QUALITY CHECK                        ║"
    @echo "╚════════════════════════════════════════════════════════════╝"
    @echo ""
    just lint-all
    @echo ""
    just lint-security
    @echo ""
    just lint-complexity
    @echo ""
    just lint-thai
    @echo ""
    @echo "✅ ALL QUALITY CHECKS PASSED!"

# Auto-fix formatting and linting issues
format:
    uv run ruff format src/ tests/
    uv run ruff check --fix src/ tests/

# ============================================================================
# TESTING
# ============================================================================

# Run tests
test:
    uv run pytest tests/ -v --tb=short

# Run tests with coverage
test-coverage:
    uv run pytest tests/ --cov=src/safeshell --cov-report=term --cov-report=html

# ============================================================================
# DOCKER
# ============================================================================

# Build Docker image
docker-build:
    docker build -t safeshell:dev .

# Run Docker container
docker-run *args:
    docker run --rm -it safeshell:dev {{args}}

# ============================================================================
# MAINTENANCE
# ============================================================================

# Clean cache and artifacts
clean:
    rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage .thailint-cache 2>/dev/null || true
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    @echo "✓ Cleaned cache and artifacts"

# Run the CLI
run *args:
    uv run safeshell {{args}}
