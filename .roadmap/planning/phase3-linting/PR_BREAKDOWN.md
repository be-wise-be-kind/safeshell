# Phase 3: Linting & Code Quality - PR Breakdown

**Purpose**: Detailed implementation breakdown of Phase 3: Linting & Code Quality into manageable, atomic pull requests

**Scope**: Complete feature implementation from basic linting setup through comprehensive quality tooling with zero violations

**Overview**: Comprehensive breakdown of the Phase 3: Linting & Code Quality feature into 3 manageable, atomic
    pull requests. Each PR is designed to be self-contained, testable, and maintains application functionality
    while incrementally building toward the complete feature. Includes detailed implementation steps, file
    structures, testing requirements, and success criteria for each PR.

**Dependencies**:
- Ruff, MyPy, Pylint, Bandit, ThaiLint already installed
- Pre-commit hooks framework configured
- Justfile infrastructure in place
- Reference: /home/stevejackson/Projects/thai-lint/pyproject.toml

**Exports**: PR implementation plans, file structures, testing strategies, and success criteria for each development phase

**Related**: AI_CONTEXT.md for feature overview, PROGRESS_TRACKER.md for status tracking

**Implementation**: Atomic PR approach with detailed step-by-step implementation guidance and comprehensive testing validation

---

## Overview
This document breaks down the Phase 3: Linting & Code Quality feature into manageable, atomic PRs. Each PR is designed to be:
- Self-contained and testable
- Maintains a working application
- Incrementally builds toward the complete feature
- Revertible if needed

---

## PR #1: Tool Configuration Refinement

### Goal
Refine and enhance configuration for all linting tools (Ruff, MyPy, Pylint, Bandit) based on thai-lint's proven configuration, adding missing type stubs and ensuring optimal strictness levels.

### Rationale
Before fixing violations, the tools must be properly configured. This PR establishes the quality standards that subsequent PRs will enforce.

### Files Changed
```
pyproject.toml                    # Enhanced tool configurations
```

### Implementation Steps

#### 1. Add Missing Type Stubs
```toml
[tool.poetry.group.dev.dependencies]
# Add:
types-pyyaml = "^6.0.0"
```

#### 2. Enhance Ruff Configuration
Review thai-lint's Ruff config and add missing rule categories:
```toml
[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "N",   # pep8-naming
    "UP",  # pyupgrade
    "B",   # flake8-bugbear
    "A",   # flake8-builtins (already present)
    "C4",  # flake8-comprehensions
    "SIM", # flake8-simplify (already present)
    "RET", # flake8-return (already present)
    "S",   # flake8-bandit (already present)
    "PTH", # flake8-use-pathlib (ADD THIS - from thai-lint)
]
ignore = [
    "S101",  # Allow assert in tests (already present)
]

[tool.ruff.lint.per-file-ignores]
"src/safeshell/cli.py" = ["F401"]  # Already present
"tests/*" = ["S101"]  # Allow assert in tests
```

#### 3. Refine MyPy Configuration
Keep strict mode, add overrides for known issues:
```toml
[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false

[[tool.mypy.overrides]]
module = "plumbum.*"
ignore_missing_imports = true
```

#### 4. Review Pylint Configuration
Compare with thai-lint and document all disables:
```toml
[tool.pylint.main]
max-line-length = 100

[tool.pylint.messages_control]
disable = [
    "R0903",  # too-few-public-methods (Pydantic models)
    "C0415",  # import-outside-toplevel (CLI lazy loading)
    "R0912",  # too-many-branches (validation logic)
    "R0911",  # too-many-return-statements (early returns)
    "W0718",  # broad-exception-caught (daemon error handling)
]
```

#### 5. Review Bandit Configuration
Ensure security rules are appropriate:
```toml
[tool.bandit]
exclude_dirs = ["tests"]
skips = ["B101"]  # Allow assert
```

### Testing Strategy
1. Run `poetry install` to install new type stubs
2. Run `poetry run ruff check src/ tests/` - should still pass
3. Run `poetry run mypy src/safeshell` - will show existing errors but no new ones
4. Run `poetry run pylint src/safeshell` - should pass with new config
5. Run `poetry run bandit -r src/safeshell -c pyproject.toml` - should pass

### Success Criteria
- [ ] types-pyyaml added to dev dependencies
- [ ] Ruff configuration enhanced with PTH rules
- [ ] MyPy configuration refined with appropriate overrides
- [ ] Pylint configuration documented and justified
- [ ] Bandit configuration reviewed
- [ ] poetry.lock updated
- [ ] All existing passing checks still pass
- [ ] No new violations introduced

### Commit Message Template
```
feat: Refine linting tool configurations

Enhance Ruff, MyPy, Pylint, and Bandit configurations based on
thai-lint's proven setup:
- Add types-pyyaml for proper YAML type checking
- Add PTH (pathlib) rules to Ruff for modern path handling
- Refine MyPy overrides for third-party libraries
- Document and justify all Pylint disables
- Review Bandit security rule configuration

Based on: /home/stevejackson/Projects/thai-lint/pyproject.toml
```

---

## PR #2: Pre-commit & Justfile Enhancement

### Goal
Enhance pre-commit hooks and justfile recipes to include all linting tools and ensure comprehensive automated quality enforcement.

### Rationale
Automation ensures quality standards are enforced consistently. This PR completes the infrastructure before fixing violations.

### Files Changed
```
.pre-commit-config.yaml          # Enhanced hook configuration
justfile                         # Verified and documented recipes
```

### Implementation Steps

#### 1. Review Pre-commit Configuration
Current hooks:
- pre-commit: ruff-check, ruff-format (on changed files)
- pre-push: mypy, bandit, pytest, check-ai-index (full codebase)

Enhancements needed:
```yaml
repos:
  - repo: local
    hooks:
      # COMMIT HOOKS remain the same (ruff only for speed)

      # PUSH HOOKS - add comprehensive checks
      - id: pylint
        name: pylint linting
        entry: poetry run pylint src/safeshell
        language: system
        types: [python]
        pass_filenames: false
        stages: [pre-push]

      - id: thailint-magic-numbers
        name: thailint magic numbers check
        entry: poetry run thailint magic-numbers src/
        language: system
        pass_filenames: false
        stages: [pre-push]

      - id: thailint-nesting
        name: thailint nesting check
        entry: poetry run thailint nesting src/
        language: system
        pass_filenames: false
        stages: [pre-push]

      - id: thailint-srp
        name: thailint SRP check
        entry: poetry run thailint srp src/
        language: system
        pass_filenames: false
        stages: [pre-push]
```

#### 2. Verify Justfile Recipes
Current recipes are comprehensive. Verify:
- `just lint` - fast (Ruff only)
- `just lint-all` - comprehensive (Ruff + Pylint + MyPy)
- `just lint-security` - Bandit
- `just lint-complexity` - Radon
- `just lint-thai` - ThaiLint checks
- `just lint-full` - ALL checks

Ensure `lint-thai` recipe works correctly with current thailint installation.

#### 3. Test Hook Installation
```bash
poetry run pre-commit install --hook-type pre-commit --hook-type pre-push
poetry run pre-commit run --all-files --hook-stage pre-commit
poetry run pre-commit run --all-files --hook-stage pre-push
```

### Testing Strategy
1. Install hooks: `poetry run pre-commit install --hook-type pre-commit --hook-type pre-push`
2. Test pre-commit stage: `poetry run pre-commit run --all-files --hook-stage pre-commit`
3. Test pre-push stage: `poetry run pre-commit run --all-files --hook-stage pre-push`
4. Test justfile recipes:
   - `just lint`
   - `just lint-all`
   - `just lint-security`
   - `just lint-complexity`
   - `just lint-thai`
   - `just lint-full`

### Success Criteria
- [ ] Pre-commit hooks include all linters
- [ ] Pylint added to pre-push hooks
- [ ] ThaiLint checks (magic-numbers, nesting, SRP) added to pre-push
- [ ] All justfile recipes verified functional
- [ ] Hooks tested and working
- [ ] Documentation updated if needed

### Commit Message Template
```
feat: Enhance pre-commit hooks and verify justfile recipes

Add comprehensive linting to pre-push hooks:
- Add Pylint to catch code quality issues
- Add ThaiLint checks (magic-numbers, nesting, SRP) for self-dogfooding
- Verify all justfile recipes are functional
- Test hook installation and execution

Pre-commit hooks now enforce:
- Fast feedback (Ruff) on commit
- Comprehensive validation (all tools) on push
```

---

## PR #3: Fix All Lint Violations

### Goal
Fix all existing lint violations across MyPy, ThaiLint, and any other tools, achieving zero violations across the entire codebase.

### Rationale
With tools configured and automation in place, this PR applies the quality standards to achieve a violation-free codebase.

### Current Known Issues
MyPy errors (11 total):
1. `daemon/protocol.py:43` - Returning Any from dict function
2. `config.py:13` - Missing yaml type stubs (fixed in PR #1)
3. `wrapper/client.py:203-204` - Missing plumbum stubs
4. `rules/loader.py:11` - Missing yaml type stubs (fixed in PR #1)
5. `wrapper/shell.py:115-116` - Missing plumbum stubs
6. `wrapper/shell.py:128` - Returning Any from int function
7. `shims/manager.py:193` - Missing type annotation for result
8. `monitor/client.py:168` - Returning Any from bool function
9. `monitor/app.py:258` - Return type incompatibility

### Implementation Steps

#### 1. Fix MyPy Type Errors

**daemon/protocol.py:43** - Add explicit return type casting:
```python
def to_dict(self) -> dict[str, Any]:
    """Convert to dictionary."""
    result: dict[str, Any] = json.loads(self.json())
    return result
```

**wrapper/client.py:203-204, wrapper/shell.py:115-116** - Already handled by MyPy override in PR #1

**wrapper/shell.py:128** - Add type casting:
```python
def run_shell(self) -> int:
    """Run interactive shell."""
    retcode: int = os.system(...)
    return retcode
```

**shims/manager.py:193** - Add type annotation:
```python
result: dict[str, Any] = subprocess.run(...)
```

**monitor/client.py:168** - Add explicit type:
```python
def is_alive(self) -> bool:
    """Check if process is alive."""
    result: bool = self.process.poll() is None
    return result
```

**monitor/app.py:258** - Make async:
```python
async def action_quit(self) -> None:
    """Quit the application."""
    await self.exit()
```

#### 2. Run ThaiLint Checks and Fix

```bash
# Check for violations
poetry run thailint magic-numbers src/
poetry run thailint nesting src/
poetry run thailint srp src/

# Fix any violations found
```

Common fixes:
- Magic numbers: Extract to named constants
- Nesting: Refactor deeply nested code
- SRP: Split functions with multiple responsibilities

#### 3. Verify All Linters Pass

```bash
just lint-full
```

### Testing Strategy
1. Fix MyPy errors one file at a time
2. Run `poetry run mypy src/safeshell` after each fix
3. Run tests after each significant change
4. Run ThaiLint checks and fix violations
5. Run `just lint-full` to verify all checks pass
6. Run full test suite: `just test`

### Success Criteria
- [ ] Zero MyPy errors
- [ ] Zero ThaiLint violations (magic-numbers, nesting, SRP)
- [ ] Zero Ruff violations
- [ ] Zero Pylint violations
- [ ] Zero Bandit violations
- [ ] All tests passing
- [ ] `just lint-full` completes successfully
- [ ] Pre-commit hooks pass on all files

### Commit Message Template
```
fix: Resolve all lint violations for Phase 3

Fix all linting violations across the codebase:
- Fix 11 MyPy type errors with explicit type annotations
- Fix ThaiLint magic-numbers violations with named constants
- Fix ThaiLint nesting violations with refactoring
- Fix ThaiLint SRP violations by splitting functions
- All quality checks now pass: just lint-full

Files modified:
- daemon/protocol.py - explicit dict typing
- wrapper/shell.py - explicit int typing
- shims/manager.py - add result type annotation
- monitor/client.py - explicit bool typing
- monitor/app.py - make action_quit async
- [other files per ThaiLint fixes]
```

---

## Implementation Guidelines

### Code Standards
- All Python code follows PEP 8 (enforced by Ruff)
- Type hints required on all functions (enforced by MyPy strict mode)
- No magic numbers (enforced by ThaiLint)
- Maximum nesting depth enforced by ThaiLint
- Single Responsibility Principle enforced by ThaiLint
- Security best practices enforced by Bandit

### Testing Requirements
- All tests must pass before and after changes
- Run full test suite for each PR
- Test coverage should not decrease
- Integration tests for command-line tools

### Documentation Standards
- All configuration changes documented in commit messages
- Tool disables must be justified with comments
- Justfile recipes include helpful descriptions
- Pre-commit hooks documented in .pre-commit-config.yaml

### Security Considerations
- Bandit security scanning on all code
- No secrets in code or configuration
- Secure defaults for all settings
- Input validation enforced

### Performance Targets
- Pre-commit hooks complete in < 30 seconds
- Pre-push hooks complete in < 2 minutes
- Linting should not significantly slow development workflow
- Justfile recipes provide clear progress feedback

## Rollout Strategy

### Phase 1: Configuration (PR #1)
1. Add type stubs to dependencies
2. Enhance tool configurations
3. Verify existing checks still pass
4. Document all configuration decisions

### Phase 2: Automation (PR #2)
1. Enhance pre-commit hooks
2. Verify justfile recipes
3. Test hook installation
4. Document automation behavior

### Phase 3: Remediation (PR #3)
1. Fix MyPy errors systematically
2. Run and fix ThaiLint violations
3. Verify all tools pass
4. Celebrate zero violations!

## Success Metrics

### Launch Metrics
- Zero lint violations across all tools
- All pre-commit hooks passing
- All justfile recipes functional
- Complete documentation of tool configurations

### Ongoing Metrics
- Pre-commit hooks prevent violations from entering codebase
- Developers can easily run `just lint-full` locally
- CI/CD can integrate linting checks
- Code quality trends tracked via Radon complexity scores
