# Phase 2: CI/CD Pipeline - AI Context

**Purpose**: AI agent context document for implementing Phase 2: CI/CD Pipeline

**Scope**: Production-grade GitHub Actions workflows for testing, linting, and security scanning

**Overview**: Comprehensive context document for AI agents working on the Phase 2: CI/CD Pipeline feature.
    Establishes production-grade CI/CD infrastructure with multi-Python version testing, comprehensive code
    quality checks, and automated security scanning. Implements GitHub Actions workflows that run on push,
    pull requests, and scheduled intervals to maintain code quality and security standards.

**Dependencies**: Poetry, GitHub Actions, pytest, coverage, ruff, pylint, mypy, bandit, thailint, safety, pip-audit, gitleaks, codecov

**Exports**: Three production-grade GitHub Actions workflows: test.yml (testing), lint.yml (quality), security.yml (security)

**Related**: PR_BREAKDOWN.md for implementation tasks, PROGRESS_TRACKER.md for current status

**Implementation**: Sequential PR approach enhancing existing workflows and adding security scanning

---

## Overview

Phase 2: CI/CD Pipeline establishes production-grade continuous integration and continuous deployment infrastructure for SafeShell. The phase transforms basic GitHub Actions workflows into a comprehensive quality and security system that runs automatically on every code change.

The implementation follows proven patterns from the thai-lint project, adapting them to SafeShell's architecture while maintaining compatibility with existing tools and workflows.

---

## Project Background

**SafeShell**: A command-line safety layer for AI coding assistants that provides interactive approval workflows, configurable rulesets, and context-aware command filtering.

**Current State**:
- Basic test.yml workflow exists with single Python version
- Basic lint.yml workflow exists with quality tools
- No security scanning workflow
- No coverage threshold enforcement
- No scheduled vulnerability scans
- Limited caching optimization

**Problem Statement**:
The current CI/CD infrastructure lacks production-grade features necessary for maintaining code quality and security at scale. Testing only on Python 3.11 misses compatibility issues with 3.12. Missing coverage thresholds allow quality regression. Absent security scanning leaves vulnerabilities undetected.

---

## Feature Vision

Phase 2: CI/CD Pipeline provides:

1. **Multi-Python Testing**
   - Matrix testing on Python 3.11 and 3.12
   - Ensures compatibility across supported versions
   - Catches version-specific issues early

2. **Coverage Enforcement**
   - 80%+ coverage threshold required
   - Prevents quality regression
   - Codecov integration for trend tracking

3. **Comprehensive Quality Checks**
   - Ruff: Fast linting and formatting
   - Pylint: Code quality analysis
   - MyPy: Static type checking
   - Bandit: Security scanning
   - thailint: Advanced checks (magic-numbers, nesting, srp)

4. **Automated Security Scanning**
   - Bandit: Code security issues
   - Safety: Dependency vulnerabilities
   - pip-audit: OSV database scanning
   - Gitleaks: Secret detection
   - Weekly scheduled scans

5. **Performance Optimization**
   - Poetry dependency caching
   - Version-specific cache keys
   - Reduced CI run times

---

## Current Application Context

### Existing Infrastructure

**Test Workflow** (`.github/workflows/test.yml`):
- Runs pytest on pull requests
- Single Python version (3.11)
- Basic coverage reporting
- No coverage threshold
- Basic caching

**Lint Workflow** (`.github/workflows/lint.yml`):
- Runs comprehensive quality checks
- Ruff, Pylint, MyPy, Bandit, thailint
- Triggered on pull requests
- Basic Poetry caching

**Project Configuration** (`pyproject.toml`):
- Poetry package management
- Python ^3.11 requirement
- Comprehensive tool configuration
- Test, lint, and dev dependencies

**Justfile** (`justfile`):
- Task automation recipes
- `test-coverage`: pytest with coverage
- `lint`: Ruff checks
- `lint-all`: Comprehensive quality checks

### Integration Points

- Poetry for dependency management
- pytest for testing framework
- coverage.py for coverage measurement
- Codecov for coverage tracking
- GitHub Actions for CI/CD automation

---

## Target Architecture

### Core Components

#### 1. Enhanced Test Workflow (`test.yml`)
```yaml
Purpose: Multi-Python version testing with coverage enforcement
Triggers: push to main, pull_request, workflow_dispatch
Matrix: Python 3.11, 3.12
Caching: Poetry dependencies with version-specific keys
Coverage: 80%+ threshold enforced
Reporting: Codecov integration (Python 3.11 only)
```

**Key Features**:
- Matrix strategy for multi-version testing
- Optimized Poetry caching with version in key
- Coverage threshold enforcement
- XML coverage report for Codecov
- Clear failure messages

#### 2. Enhanced Lint Workflow (`lint.yml`)
```yaml
Purpose: Comprehensive code quality checks
Triggers: push to main, pull_request, workflow_dispatch
Python: 3.11 (single version sufficient for linting)
Caching: Poetry dependencies
Tools: Ruff, Pylint, MyPy, Bandit, thailint
```

**Key Features**:
- Multiple linting dimensions
- Fast execution (< 3 minutes)
- All tools use pyproject.toml config
- Clear error reporting
- Non-blocking on warnings

#### 3. Security Workflow (`security.yml`)
```yaml
Purpose: Automated security vulnerability scanning
Triggers: push to main, pull_request, schedule (weekly), workflow_dispatch
Python: 3.11
Scanning: Bandit, Safety, pip-audit, Gitleaks
Schedule: Sundays at midnight UTC
```

**Key Features**:
- Multi-tool security coverage
- Weekly scheduled scans
- Full history scanning (Gitleaks)
- Non-blocking execution
- Clear security reports

### Workflow Interaction Diagram
```
┌─────────────────────────────────────────────────────────────┐
│                     GitHub Events                            │
│  push to main │ pull_request │ schedule │ workflow_dispatch │
└─────────────────────────────────────────────────────────────┘
                          │
           ┌──────────────┼──────────────┐
           ▼              ▼              ▼
      ┌────────┐    ┌──────────┐   ┌──────────┐
      │  Test  │    │   Lint   │   │ Security │
      │  3.11  │    │   Tools  │   │ Scanners │
      └────────┘    └──────────┘   └──────────┘
      ┌────────┐         │              │
      │  Test  │         │              │
      │  3.12  │         │              │
      └────────┘         │              │
           │             │              │
           ▼             ▼              ▼
      ┌─────────────────────────────────────┐
      │     Coverage & Quality Reports       │
      │  Codecov │ PR Comments │ Logs        │
      └─────────────────────────────────────┘
```

### Caching Strategy
```
Cache Key Pattern: venv-{os}-{python-version}-{poetry.lock-hash}

Examples:
- venv-Linux-3.11-a1b2c3d4...
- venv-Linux-3.12-a1b2c3d4...

Cache Hit: Skip poetry install (save ~30-60s)
Cache Miss: Run poetry install, cache result
```

---

## Key Decisions Made

### Decision 1: Multi-Python Version Testing
**Choice**: Test on Python 3.11 and 3.12
**Rationale**: SafeShell targets Python ^3.11, so both 3.11 and 3.12 must be supported. Testing both versions catches compatibility issues early.
**Alternative Considered**: Test only on 3.11 - Rejected because users may run on 3.12
**Impact**: Doubles test job runtime but ensures compatibility

### Decision 2: Coverage Threshold at 80%
**Choice**: Enforce 80% coverage threshold
**Rationale**: Balances thoroughness with practicality. High enough to catch most issues, achievable without excessive effort.
**Alternative Considered**: 90% threshold - Rejected as too strict for CLI tool, 70% - Rejected as too lenient
**Impact**: Prevents coverage regression, maintains quality standards

### Decision 3: Non-Blocking Security Scans
**Choice**: Use `|| true` for security tools
**Rationale**: Security scans should warn but not block development. Allows time to address issues without blocking PRs.
**Alternative Considered**: Blocking scans - Rejected as too disruptive to workflow
**Impact**: Security issues tracked but don't prevent merges

### Decision 4: Weekly Scheduled Scans
**Choice**: Run security scans weekly on Sundays at midnight UTC
**Rationale**: Catches newly disclosed vulnerabilities between code changes. Weekly frequency balances coverage with resource usage.
**Alternative Considered**: Daily scans - Rejected as excessive, Monthly - Rejected as too infrequent
**Impact**: Proactive vulnerability detection

### Decision 5: Codecov Only on Python 3.11
**Choice**: Upload coverage only from Python 3.11 job
**Rationale**: Avoids duplicate coverage reports, reduces API calls. Coverage doesn't vary significantly by Python version.
**Alternative Considered**: Upload from both versions - Rejected as redundant
**Impact**: Cleaner Codecov reports, faster workflow

### Decision 6: Poetry Version Pinning
**Choice**: Pin Poetry to version 2.1.4
**Rationale**: Ensures consistency across workflows and matches thai-lint reference. Prevents unexpected behavior from Poetry updates.
**Alternative Considered**: Use latest - Rejected for consistency, lock file compatibility
**Impact**: Predictable builds, easier debugging

---

## Integration Points

### With Existing Features

**Poetry Integration**:
- Use existing pyproject.toml configuration
- Leverage poetry.lock for reproducible builds
- Install with `--no-interaction` for CI
- Cache .venv directory for speed

**Justfile Integration**:
- Use `just test-coverage` recipe where applicable
- Align with local development workflow
- Maintain consistency between local and CI

**pyproject.toml Configuration**:
- All tools configured in single file
- Ruff, Pylint, MyPy, Bandit, pytest settings
- Consistent rules between local and CI

### With External Services

**Codecov Integration**:
- Requires XML coverage report
- Uses codecov/codecov-action@v5
- Set fail_ci_if_error: false for resilience
- Upload only from Python 3.11 job

**GitHub Actions Ecosystem**:
- actions/checkout@v4 for code checkout
- actions/setup-python@v5 for Python setup
- actions/cache@v4 for dependency caching
- snok/install-poetry@v1 for Poetry installation
- gitleaks/gitleaks-action@v2 for secret scanning

### Security Token Management

**GITHUB_TOKEN**:
- Automatically provided by GitHub Actions
- Used by Gitleaks for authentication
- No manual configuration required
- Scoped to repository access

---

## Success Metrics

### Coverage Metrics
- Test coverage maintained at 80%+
- Coverage trend tracking via Codecov
- No coverage regression on PRs

### Performance Metrics
- Test workflow: < 5 minutes per Python version
- Lint workflow: < 3 minutes total
- Security workflow: < 5 minutes total
- Cache hit rate: > 80% on repeat runs
- Overall CI time: < 10 minutes

### Quality Metrics
- All quality tools execute successfully
- Clear, actionable error messages
- No false positives blocking PRs
- Consistent results between local and CI

### Security Metrics
- All security tools run on every PR
- Weekly scheduled scans execute
- Vulnerabilities detected and reported
- Secret scanning covers full history

---

## Technical Constraints

### GitHub Actions Limits
- Job timeout: 6 hours (SafeShell runs complete in minutes)
- Concurrent jobs: 20 for free tier
- Cache size: 10 GB per repository
- Cache retention: 7 days

### Python Version Support
- Minimum: Python 3.11
- Maximum tested: Python 3.12
- Future: Add 3.13 when stable

### Tool Dependencies
- Poetry 2.1.4 for package management
- pytest for testing framework
- coverage.py for coverage measurement
- All quality tools in dev dependencies

### Performance Targets
- Keep total CI time under 10 minutes
- Optimize caching for 80%+ hit rate
- Minimize redundant operations
- Parallel execution where possible

---

## AI Agent Guidance

### When Implementing Test Workflow Enhancement

1. **Review Current State**:
   - Read existing `.github/workflows/test.yml`
   - Understand current test setup
   - Identify gaps vs. reference implementation

2. **Follow Reference Pattern**:
   - Use `thai-lint/.github/workflows/test.yml` as template
   - Adapt Python versions to SafeShell (3.11, 3.12)
   - Match Poetry caching strategy

3. **Key Implementation Points**:
   - Add matrix strategy for Python versions
   - Include Python version in cache key
   - Add coverage threshold check
   - Configure Codecov upload with conditional
   - Update triggers to include push to main

4. **Testing Approach**:
   - Create draft PR to test workflow
   - Verify both Python versions run
   - Confirm cache creation and reuse
   - Test coverage threshold enforcement

### When Implementing Lint Workflow Enhancement

1. **Review Current State**:
   - Read existing `.github/workflows/lint.yml`
   - Verify all tools present
   - Check Poetry configuration

2. **Key Changes**:
   - Add push to main trigger
   - Update Poetry version to 2.1.4
   - Optimize caching configuration
   - Verify all 8 quality checks run

3. **Validation**:
   - All tools use pyproject.toml config
   - Error messages are clear
   - Workflow completes quickly (< 3 min)

### When Implementing Security Workflow

1. **Create New File**:
   - Create `.github/workflows/security.yml`
   - Use `thai-lint/.github/workflows/security.yml` as reference
   - Adapt to SafeShell structure

2. **Critical Elements**:
   - Set fetch-depth: 0 for Gitleaks
   - Configure weekly schedule
   - Use || true for non-blocking
   - Include GITHUB_TOKEN for Gitleaks

3. **Tool Configuration**:
   - Bandit: Use pyproject.toml config
   - Safety: Use --json output
   - pip-audit: Default configuration
   - Gitleaks: GitHub Action integration

### Common Patterns

**Poetry Installation**:
```yaml
- name: Install Poetry
  uses: snok/install-poetry@v1
  with:
    version: 2.1.4
    virtualenvs-create: true
    virtualenvs-in-project: true
```

**Caching Pattern**:
```yaml
- name: Load cached venv
  id: cached-poetry-dependencies
  uses: actions/cache@v4
  with:
    path: .venv
    key: venv-${{ runner.os }}-${{ matrix.python-version }}-${{ hashFiles('**/poetry.lock') }}

- name: Install dependencies
  if: steps.cached-poetry-dependencies.outputs.cache-hit != 'true'
  run: poetry install --no-interaction --no-root
```

**Matrix Strategy**:
```yaml
strategy:
  matrix:
    python-version: ['3.11', '3.12']
```

**Conditional Execution**:
```yaml
- name: Upload coverage to Codecov
  if: matrix.python-version == '3.11'
  uses: codecov/codecov-action@v5
```

---

## Risk Mitigation

### Risk: Coverage Threshold Too Strict
**Mitigation**: Start at 80%, adjust based on actual coverage levels. Allow temporary exemptions for refactoring.
**Detection**: Monitor PR failures, gather team feedback
**Response**: Adjust threshold if consistently blocking valid PRs

### Risk: Security Scans Generate False Positives
**Mitigation**: Use || true for non-blocking. Review and triage issues regularly.
**Detection**: High volume of security warnings
**Response**: Configure tool exclusions, update to latest tool versions

### Risk: CI Run Time Exceeds Target
**Mitigation**: Implement aggressive caching, parallelize jobs where possible
**Detection**: Monitor workflow run times
**Response**: Optimize slow steps, reduce redundant operations

### Risk: Cache Corruption
**Mitigation**: Include poetry.lock hash in cache key, automatic cache invalidation
**Detection**: Unexpected test failures, dependency errors
**Response**: Clear cache manually, regenerate

### Risk: Tool Version Incompatibilities
**Mitigation**: Pin tool versions in pyproject.toml, test updates in isolation
**Detection**: Workflow failures after updates
**Response**: Rollback to known-good versions, investigate incrementally

---

## Future Enhancements

### Post-Phase 2 Improvements

**Phase 3: Performance Monitoring**
- Add benchmark workflow
- Track performance regression
- Alert on slowdowns

**Phase 4: Automated Releases**
- Tag-triggered PyPI publishing
- Changelog generation
- GitHub release creation

**Phase 5: Advanced Security**
- SAST scanning with Semgrep
- Dependency review automation
- Security policy enforcement

**Phase 6: Quality Gates**
- Code review automation
- Complexity threshold enforcement
- Technical debt tracking

### Potential Optimizations

**Caching Improvements**:
- Cache test database fixtures
- Cache compiled Python bytecode
- Implement layered caching strategy

**Parallel Execution**:
- Run lint and test in parallel
- Split test suite across multiple jobs
- Parallel security scanning

**Conditional Workflows**:
- Skip tests when only docs changed
- Run security scans only on dependency changes
- Smart workflow triggering based on changed files

### Integration Opportunities

**Codecov Enhancements**:
- Coverage comparison in PR comments
- Coverage badges in README
- Trend analysis and alerts

**GitHub Integration**:
- Status checks for required workflows
- Branch protection rules
- Required reviews configuration

**Notification System**:
- Slack notifications for failures
- Email alerts for security issues
- Dashboard for workflow status
