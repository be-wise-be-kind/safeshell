# Phase 2: CI/CD Pipeline - PR Breakdown

**Purpose**: Detailed implementation breakdown of Phase 2: CI/CD Pipeline into manageable, atomic pull requests

**Scope**: Complete CI/CD implementation from basic workflows through production-grade testing, quality checks, and security scanning

**Overview**: Comprehensive breakdown of the Phase 2: CI/CD Pipeline feature into 3 manageable, atomic
    pull requests. Each PR is designed to be self-contained, testable, and maintains application functionality
    while incrementally building toward the complete feature. Includes detailed implementation steps, file
    structures, testing requirements, and success criteria for each PR.

**Dependencies**: Poetry, GitHub Actions, pytest, coverage, ruff, pylint, mypy, bandit, thailint, safety, pip-audit, gitleaks, codecov

**Exports**: PR implementation plans, file structures, testing strategies, and success criteria for each development phase

**Related**: AI_CONTEXT.md for feature overview, PROGRESS_TRACKER.md for status tracking

**Implementation**: Atomic PR approach with detailed step-by-step implementation guidance and comprehensive testing validation

---

## Overview
This document breaks down the Phase 2: CI/CD Pipeline feature into manageable, atomic PRs. Each PR is designed to be:
- Self-contained and testable
- Maintains a working application
- Incrementally builds toward the complete feature
- Revertible if needed

---

## PR1: Enhanced Test Workflow

### Overview
Enhance the existing test.yml workflow with production-grade features: multi-Python version matrix testing, optimized Poetry dependency caching, coverage reporting to Codecov, and enforced 80%+ coverage threshold.

### Motivation
Current test.yml workflow tests only on Python 3.11 and lacks coverage threshold enforcement. SafeShell targets Python ^3.11, so testing on both 3.11 and 3.12 ensures compatibility. Coverage threshold enforcement prevents quality regression.

### Files Changed
```
.github/workflows/test.yml (modified)
```

### Implementation Steps

#### 1. Add Python Version Matrix
```yaml
strategy:
  matrix:
    python-version: ['3.11', '3.12']
```

#### 2. Update Python Setup Step
```yaml
- name: Set up Python ${{ matrix.python-version }}
  uses: actions/setup-python@v5
  with:
    python-version: ${{ matrix.python-version }}
```

#### 3. Optimize Poetry Caching
```yaml
- name: Install Poetry
  uses: snok/install-poetry@v1
  with:
    version: 2.1.4
    virtualenvs-create: true
    virtualenvs-in-project: true

- name: Load cached venv
  id: cached-poetry-dependencies
  uses: actions/cache@v4
  with:
    path: .venv
    key: venv-${{ runner.os }}-${{ matrix.python-version }}-${{ hashFiles('**/poetry.lock') }}
```

#### 4. Add Coverage Threshold Check
```yaml
- name: Run tests with coverage
  run: poetry run pytest tests/ --cov=src/safeshell --cov-report=term --cov-report=xml

- name: Check coverage threshold
  run: poetry run coverage report --fail-under=80
```

#### 5. Configure Codecov Upload
```yaml
- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v5
  if: matrix.python-version == '3.11'
  with:
    file: ./coverage.xml
    fail_ci_if_error: false
```

#### 6. Update Workflow Triggers
```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:
```

### Complete Workflow Structure
```yaml
name: Test

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11', '3.12']

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install Poetry
        uses: snok/install-poetry@v1
        with:
          version: 2.1.4
          virtualenvs-create: true
          virtualenvs-in-project: true

      - name: Load cached venv
        id: cached-poetry-dependencies
        uses: actions/cache@v4
        with:
          path: .venv
          key: venv-${{ runner.os }}-${{ matrix.python-version }}-${{ hashFiles('**/poetry.lock') }}

      - name: Install dependencies
        if: steps.cached-poetry-dependencies.outputs.cache-hit != 'true'
        run: poetry install --no-interaction --no-root

      - name: Install project
        run: poetry install --no-interaction

      - name: Run tests
        run: poetry run pytest tests/ -v --tb=short

      - name: Run tests with coverage
        run: poetry run pytest tests/ --cov=src/safeshell --cov-report=term --cov-report=xml

      - name: Check coverage threshold
        run: poetry run coverage report --fail-under=80

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v5
        if: matrix.python-version == '3.11'
        with:
          file: ./coverage.xml
          fail_ci_if_error: false
```

### Testing Strategy
1. Create draft PR with workflow changes
2. Push commit to trigger workflow
3. Verify both Python 3.11 and 3.12 jobs run
4. Confirm cache is created on first run
5. Push another commit to verify cache hit
6. Check coverage threshold enforcement
7. Verify Codecov receives coverage report

### Success Criteria
- [x] Workflow runs on Python 3.11 and 3.12
- [x] Poetry cache reduces installation time by 50%+
- [x] Coverage threshold enforced at 80%
- [x] Codecov receives and displays coverage
- [x] Workflow completes in < 5 minutes per Python version
- [x] Clear error messages when coverage below threshold

### PR Description Template
```markdown
## Summary
Enhances test.yml workflow with production-grade features for robust CI testing.

## Changes
- Add Python 3.11 and 3.12 matrix testing
- Implement Poetry dependency caching with version-specific keys
- Add 80% coverage threshold enforcement
- Configure Codecov integration for coverage reporting
- Add push to main trigger for continuous testing

## Testing
- Verified workflow runs on both Python versions
- Confirmed cache optimization reduces run time
- Tested coverage threshold enforcement
- Validated Codecov integration

## Reference
Based on thai-lint/.github/workflows/test.yml
```

---

## PR2: Enhanced Lint Workflow

### Overview
Enhance the existing lint.yml workflow with comprehensive quality checks: Ruff linting and formatting, Pylint for code quality, MyPy for type checking, Bandit for security, and thailint for advanced checks.

### Motivation
Current lint.yml workflow has basic quality checks but lacks comprehensive coverage. Adding multiple linting dimensions (code quality, type safety, security, complexity) ensures high code quality standards.

### Files Changed
```
.github/workflows/lint.yml (modified)
```

### Implementation Steps

#### 1. Update Workflow Header Documentation
```yaml
# Purpose: Comprehensive code quality checks on pull requests and pushes to main
# Triggers: pull_request to main, push to main, workflow_dispatch
# Jobs:
#   - lint: Run ruff, pylint, mypy, bandit, and thailint checks
```

#### 2. Add Push to Main Trigger
```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:
```

#### 3. Optimize Poetry Caching
```yaml
- name: Install Poetry
  uses: snok/install-poetry@v1
  with:
    version: 2.1.4
    virtualenvs-create: true
    virtualenvs-in-project: true

- name: Load cached venv
  id: cached-poetry-dependencies
  uses: actions/cache@v4
  with:
    path: .venv
    key: venv-${{ runner.os }}-${{ hashFiles('**/poetry.lock') }}
```

#### 4. Ensure All Quality Tools Run
Current workflow already includes:
- Ruff linting
- Ruff format checking
- Pylint
- MyPy
- Bandit
- thailint (magic-numbers, nesting, srp)

Verify all steps are present and properly configured.

### Complete Workflow Structure
```yaml
name: Lint

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:

jobs:
  lint:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install Poetry
        uses: snok/install-poetry@v1
        with:
          version: 2.1.4
          virtualenvs-create: true
          virtualenvs-in-project: true

      - name: Load cached venv
        id: cached-poetry-dependencies
        uses: actions/cache@v4
        with:
          path: .venv
          key: venv-${{ runner.os }}-${{ hashFiles('**/poetry.lock') }}

      - name: Install dependencies
        if: steps.cached-poetry-dependencies.outputs.cache-hit != 'true'
        run: poetry install --no-interaction --no-root

      - name: Install project
        run: poetry install --no-interaction

      - name: Run Ruff
        run: poetry run ruff check src/ tests/

      - name: Run Ruff Format Check
        run: poetry run ruff format --check src/ tests/

      - name: Run Pylint
        run: poetry run pylint src/safeshell

      - name: Run MyPy
        run: poetry run mypy src/safeshell

      - name: Run Bandit
        run: poetry run bandit -r src/safeshell -c pyproject.toml

      - name: Run thailint magic-numbers
        run: poetry run thailint magic-numbers src/

      - name: Run thailint nesting
        run: poetry run thailint nesting src/

      - name: Run thailint srp
        run: poetry run thailint srp src/
```

### Testing Strategy
1. Create draft PR with workflow changes
2. Trigger workflow on commit
3. Verify all linting tools execute
4. Introduce intentional violations to test each tool
5. Verify cache optimization works
6. Check error reporting clarity

### Success Criteria
- [x] All 8 quality checks run successfully
- [x] Each tool uses pyproject.toml configuration
- [x] Poetry cache improves subsequent run times
- [x] Workflow completes in < 3 minutes
- [x] Clear, actionable error messages for violations
- [x] Workflow runs on both push and PR events

### PR Description Template
```markdown
## Summary
Enhances lint.yml workflow with comprehensive code quality checks and optimized caching.

## Changes
- Add push to main trigger for continuous quality checks
- Optimize Poetry caching for faster runs
- Update Poetry version to 2.1.4 for consistency
- Ensure all quality tools properly configured

## Quality Checks
- Ruff: Fast linting and formatting
- Pylint: Comprehensive code quality
- MyPy: Static type checking
- Bandit: Security scanning
- thailint: Advanced checks (magic-numbers, nesting, srp)

## Testing
- Verified all 8 quality checks execute
- Confirmed cache optimization works
- Tested error reporting for each tool

## Reference
Based on thai-lint workflows and justfile patterns
```

---

## PR3: Security Workflow

### Overview
Create new security.yml workflow for automated vulnerability scanning with Bandit (code security), Safety (dependency vulnerabilities), pip-audit (OSV database), and Gitleaks (secret scanning). Includes weekly scheduled scans.

### Motivation
Proactive security scanning catches vulnerabilities early. Weekly scheduled scans detect newly disclosed vulnerabilities in dependencies. Multiple tools provide comprehensive coverage across different security dimensions.

### Files Created
```
.github/workflows/security.yml (new)
```

### Implementation Steps

#### 1. Create Workflow File with Header
```yaml
name: Security

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sundays at midnight UTC
  workflow_dispatch:
```

#### 2. Define Security Scanning Job
```yaml
jobs:
  security:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for Gitleaks
```

#### 3. Set Up Python and Poetry
```yaml
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install Poetry
        uses: snok/install-poetry@v1
        with:
          version: 2.1.4
          virtualenvs-create: true
          virtualenvs-in-project: true

      - name: Install dependencies
        run: poetry install --no-interaction
```

#### 4. Add Security Scanning Steps
```yaml
      - name: Run Bandit (security scanner)
        run: poetry run bandit -r src/ -c pyproject.toml || true

      - name: Run Safety (dependency vulnerabilities)
        run: poetry run safety check --json || true

      - name: Run pip-audit (OSV database)
        run: poetry run pip-audit || true

      - name: Run Gitleaks (secret scanning)
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Complete Workflow Structure
```yaml
name: Security

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sundays at midnight UTC
  workflow_dispatch:

jobs:
  security:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Fetch all history for gitleaks to scan commits properly

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install Poetry
        uses: snok/install-poetry@v1
        with:
          version: 2.1.4
          virtualenvs-create: true
          virtualenvs-in-project: true

      - name: Install dependencies
        run: poetry install --no-interaction

      - name: Run Bandit (security scanner)
        run: poetry run bandit -r src/ -c pyproject.toml || true

      - name: Run Safety (dependency vulnerabilities)
        run: poetry run safety check --json || true

      - name: Run pip-audit (OSV database)
        run: poetry run pip-audit || true

      - name: Run Gitleaks (secret scanning)
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Testing Strategy
1. Create PR with new security.yml workflow
2. Trigger workflow on commit
3. Verify all 4 security tools run
4. Check scheduled scan configuration in GitHub UI
5. Verify Gitleaks scans full history (fetch-depth: 0)
6. Confirm workflow completes successfully

### Success Criteria
- [x] All 4 security tools execute successfully
- [x] Weekly scheduled scans configured (visible in GitHub Actions UI)
- [x] Gitleaks scans with full history
- [x] Workflow completes in < 5 minutes
- [x] Security reports are clear and actionable
- [x] Tools run non-blocking (|| true for some tools)

### PR Description Template
```markdown
## Summary
Adds comprehensive security scanning workflow with automated vulnerability detection and weekly scheduled scans.

## Changes
- Create new security.yml workflow
- Add Bandit for code security scanning
- Add Safety for dependency vulnerability checking
- Add pip-audit for OSV database scanning
- Add Gitleaks for secret detection
- Configure weekly scheduled scans (Sundays at midnight)

## Security Tools
- **Bandit**: Scans Python code for security issues
- **Safety**: Checks dependencies against vulnerability database
- **pip-audit**: Scans packages using OSV database
- **Gitleaks**: Scans git history for exposed secrets

## Testing
- Verified all security tools execute
- Confirmed scheduled scan configuration
- Validated Gitleaks full history scanning

## Reference
Based on thai-lint/.github/workflows/security.yml
```

---

## Implementation Guidelines

### Code Standards
- Follow GitHub Actions YAML best practices
- Use latest stable action versions (@v4, @v5)
- Include clear step names describing actions
- Use Poetry version 2.1.4 for consistency
- Implement caching to optimize run times

### Testing Requirements
- Test workflows on draft PRs before merging
- Verify both success and failure scenarios
- Confirm cache optimization works
- Test all triggers (push, PR, schedule, manual)
- Validate error reporting clarity

### Documentation Standards
- Include workflow purpose in file header
- Document trigger conditions
- Explain job responsibilities
- Add inline comments for complex steps
- Reference source templates where applicable

### Security Considerations
- Use GITHUB_TOKEN for Gitleaks authentication
- Run security scans non-blocking (|| true)
- Fetch full history for Gitleaks (fetch-depth: 0)
- Schedule regular security scans
- Use Bandit with pyproject.toml configuration

### Performance Targets
- Test workflow: < 5 minutes per Python version
- Lint workflow: < 3 minutes total
- Security workflow: < 5 minutes total
- Cache hit rate: > 80% on repeat runs
- Overall CI time: < 10 minutes for all workflows

---

## Rollout Strategy

### Phase 1: Enhanced Testing (PR1)
- Merge enhanced test.yml to main
- Monitor workflow performance
- Verify coverage threshold enforcement
- Validate Codecov integration

### Phase 2: Enhanced Linting (PR2)
- Merge enhanced lint.yml to main
- Monitor comprehensive quality checks
- Verify all tools execute correctly
- Validate cache optimization

### Phase 3: Security Scanning (PR3)
- Merge new security.yml to main
- Monitor security scan results
- Verify scheduled scans execute
- Review security reports for actionability

---

## Success Metrics

### Launch Metrics
- All 3 PRs merged successfully
- All workflows execute without errors
- Coverage threshold maintained at 80%+
- Weekly security scans scheduled and running
- CI run time < 10 minutes total

### Ongoing Metrics
- Test pass rate: > 95%
- Coverage trend: maintaining or increasing
- Security vulnerabilities: detected and tracked
- CI reliability: > 98% uptime
- Cache efficiency: > 80% hit rate
