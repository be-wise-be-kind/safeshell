# Phase 3: Linting & Code Quality - AI Context

**Purpose**: AI agent context document for implementing Phase 3: Linting & Code Quality

**Scope**: Comprehensive code quality tooling including Ruff, MyPy, Pylint, Bandit, ThaiLint, pre-commit hooks, and justfile recipes

**Overview**: Comprehensive context document for AI agents working on the Phase 3: Linting & Code Quality feature.
    This phase focuses on ensuring all code meets strict quality standards through comprehensive tooling configuration,
    automated enforcement via pre-commit hooks, and fixing all existing violations. Includes self-dogfooding ThaiLint
    to validate its effectiveness on SafeShell's codebase.

**Dependencies**:
- Ruff (linting and formatting)
- MyPy (static type checking)
- Pylint (code quality analysis)
- Bandit (security scanning)
- ThaiLint (AI-specific linting)
- Radon (complexity analysis)
- Pre-commit framework
- Justfile (command runner)

**Exports**: Refined tool configurations, automated quality enforcement, zero-violation codebase

**Related**: PR_BREAKDOWN.md for implementation tasks, PROGRESS_TRACKER.md for current status

**Implementation**: Phased approach with configuration refinement, automation setup, and systematic violation fixing

---

## Overview

Phase 3: Linting & Code Quality establishes comprehensive quality standards for SafeShell through proper tooling configuration, automated enforcement, and systematic remediation of existing violations. This phase is critical for maintaining code quality as the project grows and serves as a demonstration of ThaiLint's value through self-dogfooding.

## Project Background

SafeShell is a command-line safety layer for AI coding assistants that wraps dangerous shell commands with approval prompts. The codebase includes:
- CLI interface (Typer-based)
- Configuration management (YAML-based)
- Rule engine for command approval
- Daemon for background monitoring
- TUI for interactive approvals (Textual-based)
- Shell wrapper integration

Current state:
- Basic linting setup exists (Ruff, MyPy, Pylint, Bandit configured)
- Pre-commit hooks configured but may need enhancement
- Justfile with comprehensive quality recipes
- 11 MyPy errors detected (type safety issues)
- Ruff checks passing
- Unknown status of ThaiLint checks

## Feature Vision

The Phase 3: Linting & Code Quality feature enables:

1. **Strict Quality Standards**: All code meets industry-leading quality standards through comprehensive tooling
2. **Type Safety**: MyPy strict mode enforced with zero type errors
3. **Security Assurance**: Bandit security scanning catches potential vulnerabilities
4. **Code Maintainability**: Pylint ensures code quality and maintainability
5. **Modern Python**: Ruff enforces modern Python practices (pathlib, comprehensions, etc.)
6. **AI-Specific Quality**: ThaiLint enforces AI-appropriate patterns (no magic numbers, limited nesting, SRP)
7. **Automated Enforcement**: Pre-commit hooks prevent violations from entering the codebase
8. **Developer Experience**: Justfile recipes make quality checks easy to run

## Current Application Context

### Existing Infrastructure
- **pyproject.toml**: Contains tool configurations for Ruff, MyPy, Pylint, Bandit, Radon
- **.pre-commit-config.yaml**: Configured with Ruff on commit, MyPy/Bandit/pytest on push
- **justfile**: Comprehensive recipes including lint, lint-all, lint-security, lint-complexity, lint-thai, lint-full

### Tool Configuration Status
- **Ruff**: Basic configuration (E, F, W, I, N, UP, B, A, C4, SIM, RET, S) - missing PTH
- **MyPy**: Strict mode enabled but has 11 errors
- **Pylint**: Basic configuration with minimal disables
- **Bandit**: Excludes tests, skips B101 (assert)
- **ThaiLint**: Installed but not integrated into pre-commit hooks

### Known Issues
1. Missing type stubs for PyYAML (types-pyyaml)
2. 11 MyPy type errors across 8 files
3. Unknown ThaiLint violation count
4. Pylint may have violations (not recently checked)
5. Pre-commit hooks don't include Pylint or ThaiLint

## Target Architecture

### Core Components

#### 1. Tool Configuration Layer (pyproject.toml)
Central configuration for all quality tools:
```toml
[tool.ruff]
# Comprehensive rule selection
[tool.mypy]
# Strict mode with pragmatic overrides
[tool.pylint]
# Quality checks with justified disables
[tool.bandit]
# Security scanning configuration
[tool.radon]
# Complexity thresholds
```

#### 2. Automation Layer (pre-commit hooks)
Two-stage enforcement:
- **pre-commit**: Fast feedback (Ruff formatting and linting on changed files)
- **pre-push**: Comprehensive validation (MyPy, Pylint, Bandit, ThaiLint, tests on full codebase)

#### 3. Manual Execution Layer (justfile)
Recipes for all quality commands:
- `just lint` - Fast linting (Ruff only)
- `just lint-all` - Comprehensive linting (Ruff + Pylint + MyPy)
- `just lint-security` - Security scanning (Bandit)
- `just lint-complexity` - Complexity analysis (Radon)
- `just lint-thai` - ThaiLint checks
- `just lint-full` - ALL quality checks

### User Journey

#### Developer Workflow
1. **Code**: Write new feature or fix
2. **Commit**: Pre-commit hooks run Ruff (fast feedback, auto-fixes)
3. **Push**: Pre-push hooks run comprehensive checks (MyPy, Pylint, Bandit, ThaiLint, tests)
4. **Manual Check**: Run `just lint-full` before creating PR

#### Quality Assurance Flow
1. **Configuration**: Tools configured in pyproject.toml
2. **Automated Enforcement**: Pre-commit hooks enforce standards
3. **Manual Validation**: Justfile recipes for on-demand checking
4. **CI/CD Integration**: Future integration point for automated PR checks

### Quality Tool Responsibilities

#### Ruff
- Code formatting (Black-compatible)
- Linting (multiple categories)
- Import sorting (isort-compatible)
- Modern Python enforcement (pyupgrade)
- Pathlib usage (PTH rules)

#### MyPy
- Static type checking
- Strict mode for maximum safety
- Catch type-related bugs early
- Enforce type annotations

#### Pylint
- Code quality analysis
- Complexity checking
- Naming conventions
- Documentation checking

#### Bandit
- Security vulnerability scanning
- Catch common security issues
- Enforce secure coding practices

#### ThaiLint
- AI-specific quality checks
- Magic number detection
- Nesting depth limits
- Single Responsibility Principle enforcement

#### Radon
- Cyclomatic complexity analysis
- Code maintainability metrics
- Identify refactoring candidates

## Key Decisions Made

### Configuration Philosophy
**Decision**: Use thai-lint's proven configurations as reference baseline
**Rationale**: Thai-lint has been battle-tested and represents industry best practices
**Impact**: Higher confidence in configuration choices, less trial-and-error

### Strictness Level
**Decision**: Enable MyPy strict mode with pragmatic overrides
**Rationale**: Maximum type safety while allowing necessary flexibility
**Impact**: Catch more bugs early, better IDE support, clearer APIs

### Pre-commit Strategy
**Decision**: Two-stage hooks (fast commit, thorough push)
**Rationale**: Balance between quick feedback and comprehensive validation
**Impact**: Developers get fast feedback without waiting for full checks on every commit

### ThaiLint Integration
**Decision**: Self-dogfood ThaiLint on SafeShell codebase
**Rationale**: Validate ThaiLint's effectiveness, demonstrate value to users
**Impact**: Better quality code, real-world testing of ThaiLint rules

### Automation Priority
**Decision**: Automate via pre-commit hooks, not git hooks directly
**Rationale**: Pre-commit framework is more maintainable and portable
**Impact**: Easier to manage, better developer experience, portable across environments

### Justfile Over Makefile
**Decision**: Use justfile instead of Makefile
**Rationale**: More readable syntax, better error messages, cross-platform
**Impact**: Easier for developers to understand and extend

## Integration Points

### With Existing Features

#### Configuration System
- Linting tools read configuration from pyproject.toml
- Consistent configuration location
- No scattered config files

#### CLI Development
- Type hints improve CLI parameter definitions
- Better autocomplete in IDEs
- Clearer command signatures

#### Rule Engine
- Security scanning validates rule evaluation logic
- Type checking ensures rule data structures are correct
- Complexity analysis identifies refactoring opportunities

#### Testing Infrastructure
- Linting runs before tests in pre-push
- Test files have relaxed rules (assert allowed)
- Coverage integrated with quality checks

### With Development Workflow

#### Git Integration
- Pre-commit hooks run automatically
- Prevent violations from being committed
- Enforce quality standards consistently

#### IDE Integration
- Type hints enable better autocomplete
- Linting violations shown in real-time
- MyPy integration provides instant feedback

#### CI/CD Integration (Future)
- Same tools and configurations used in CI/CD
- Justfile recipes can be called from CI scripts
- Consistent quality enforcement across environments

## Success Metrics

### Technical Metrics
- Zero MyPy errors in strict mode
- Zero Ruff violations
- Zero Pylint violations
- Zero Bandit security issues
- Zero ThaiLint violations
- Cyclomatic complexity < B threshold (Radon)
- 100% type coverage

### Process Metrics
- Pre-commit hooks run successfully on all commits
- Pre-push hooks catch violations before push
- `just lint-full` passes cleanly
- All developers can run quality checks locally
- Quality checks complete in reasonable time (< 2 min)

### Quality Metrics
- Code maintainability improved (measurable via Radon)
- Fewer bugs related to type errors
- More consistent code style
- Better security posture
- Clearer code intent (fewer magic numbers)

## Technical Constraints

### Tool Compatibility
- All tools must work with Python 3.11+
- Must support Poetry virtual environments
- Must integrate with pre-commit framework
- Must work on Linux, macOS, Windows

### Performance Constraints
- Pre-commit hooks should complete in < 30 seconds
- Pre-push hooks should complete in < 2 minutes
- Full lint check (just lint-full) should complete in < 3 minutes

### Configuration Constraints
- All configuration in pyproject.toml (no scattered configs)
- Exception: pre-commit-config.yaml (framework requirement)
- Type stubs must be in dev dependencies
- No global tool installation required

### Compatibility Constraints
- Must not break existing tests
- Must maintain Python 3.11 compatibility
- Must work with existing Poetry setup
- Must preserve CLI functionality

## AI Agent Guidance

### When Configuring Tools

1. **Review Reference Configuration**: Always check /home/stevejackson/Projects/thai-lint/pyproject.toml first
2. **Document Decisions**: Add comments explaining why rules are disabled
3. **Test Incrementally**: Verify each configuration change doesn't break existing functionality
4. **Maintain Strictness**: Only disable rules when absolutely necessary
5. **Consider Context**: Different rules for test files vs. production code

Example:
```toml
[tool.pylint.messages_control]
disable = [
    "R0903",  # too-few-public-methods (Pydantic models are intentionally simple DTOs)
    "C0415",  # import-outside-toplevel (CLI lazy loading for performance)
]
```

### When Fixing Violations

1. **Fix, Don't Disable**: Always try to fix the code before disabling a rule
2. **Understand the Error**: Read the tool documentation to understand why it's flagged
3. **Preserve Intent**: Don't change code behavior while fixing lint issues
4. **Test After Each Fix**: Run tests to ensure functionality is preserved
5. **Commit Incrementally**: Smaller commits are easier to review and revert

Example MyPy fix:
```python
# Before (Any return type)
def to_dict(self):
    return json.loads(self.json())

# After (explicit type)
def to_dict(self) -> dict[str, Any]:
    result: dict[str, Any] = json.loads(self.json())
    return result
```

### When Setting Up Automation

1. **Test Hooks Thoroughly**: Run pre-commit on all files before committing hook changes
2. **Balance Speed and Coverage**: Fast feedback on commit, thorough checks on push
3. **Provide Clear Output**: Ensure hook failures have helpful error messages
4. **Document Installation**: Update docs with hook installation instructions
5. **Handle Edge Cases**: Test with no files changed, all files changed, etc.

Example hook installation:
```bash
poetry run pre-commit install --hook-type pre-commit --hook-type pre-push
```

### Common Patterns

#### Adding Type Stubs
```toml
[tool.poetry.group.dev.dependencies]
types-pyyaml = "^6.0.0"  # Type stubs for PyYAML library
```

#### Handling Missing Third-Party Stubs
```toml
[[tool.mypy.overrides]]
module = "plumbum.*"
ignore_missing_imports = true
```

#### Excluding Test Files from Strict Rules
```toml
[tool.ruff.lint.per-file-ignores]
"tests/*" = ["S101"]  # Allow assert statements in tests
```

#### Running ThaiLint Checks
```bash
poetry run thailint magic-numbers src/
poetry run thailint nesting src/
poetry run thailint srp src/
```

## Risk Mitigation

### Risk: Breaking Existing Functionality
**Mitigation**: Run full test suite after each change, commit incrementally
**Detection**: Automated test failures, manual smoke testing
**Recovery**: Git revert to last known good state

### Risk: Pre-commit Hooks Too Slow
**Mitigation**: Keep pre-commit hooks to fast checks only (Ruff), move slow checks to pre-push
**Detection**: Developer complaints, timing measurements
**Recovery**: Move slow checks to pre-push or manual execution

### Risk: Too Many Disabled Rules
**Mitigation**: Document justification for every disabled rule, review periodically
**Detection**: Code review, configuration review
**Recovery**: Re-enable rules and fix violations

### Risk: Configuration Conflicts
**Mitigation**: Use consistent line length and style across all tools
**Detection**: Tools reporting conflicting violations
**Recovery**: Align configurations in pyproject.toml

### Risk: Type Stub Bloat
**Mitigation**: Only add type stubs for libraries actually used in code
**Detection**: Unused dependencies in poetry.lock
**Recovery**: Remove unused type stub packages

## Future Enhancements

### Phase 4: CI/CD Integration
- Run linting in GitHub Actions
- Block PRs with violations
- Generate quality reports
- Track quality metrics over time

### Enhanced ThaiLint Integration
- Custom rules specific to SafeShell patterns
- Integration with IDE plugins
- Real-time feedback in editor
- Quality dashboard

### Documentation Generation
- Auto-generate docs from type hints
- API documentation from docstrings
- Quality reports in markdown
- Coverage badges

### Performance Optimization
- Parallel linting execution
- Incremental type checking (MyPy daemon)
- Cache lint results
- Smart file selection

### Quality Metrics Dashboard
- Radon complexity trends over time
- Test coverage trends
- Violation count trends
- Code churn vs. quality metrics
