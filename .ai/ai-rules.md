File: .ai/ai-rules.md

Purpose: Mandatory development rules and quality gates for SafeShell

Exports: Quality gates, coding standards, git rules, documentation rules

Depends: ai-context.md, howtos/how-to-write-file-headers.md

Overview: Defines all mandatory rules for working on this project. Includes quality
    gate requirements, coding standards, git workflow rules, and documentation
    maintenance requirements. All rules must be followed for code to be accepted.

# AI Development Rules

**Purpose**: Mandatory rules for working on this project

---

## Quality Gates

All code must pass before push:

| Tool | Requirement | Command |
|------|-------------|---------|
| Ruff | All checks pass | `just lint` |
| Pylint | High score | `just lint-all` |
| MyPy | Zero errors (strict) | `just lint-all` |
| Bandit | All security checks | `just lint-security` |
| thailint | All checks pass | `just lint-thai` |
| Tests | All passing | `just test` |

**Run all checks**: `just lint-full`

---

## Coding Standards

1. **NO print statements** - Use Rich console or Loguru for all output
2. **Type hints everywhere** - MyPy strict mode must pass
3. **Pydantic for data models** - No plain dicts for structured data
4. **Proper file headers** - See [howtos/how-to-write-file-headers.md](./howtos/how-to-write-file-headers.md)
5. **No method-level noqa comments** - If a linting rule needs to be suppressed, prefer file-level (`# ruff: noqa: RULE`) or project-level (in pyproject.toml) configuration
6. **Standalone repository** - SafeShell must be completely self-contained

---

## Git Rules

1. **No commits to main** - Always use feature branches
2. **No `--no-verify`** - Except for documented temporary exceptions with follow-up task
3. **Run quality gates** - `just lint-full` before pushing

---

## Documentation Rules

1. **Keep docs up-to-date** - Update documentation when behavior changes
2. **Update index.yaml** - When adding, removing, or renaming files in `.ai/`
3. **Update AGENTS.md** - When adding new CLI commands
4. **Use atemporal language** - No "currently", "recently", "will be"
5. **Update CLI how-to** - When adding or modifying CLI commands, update `.ai/howtos/how-to-use-safeshell-cli.md`

---

## Pre-commit/Pre-push Hooks

| Stage | Hook | Purpose |
|-------|------|---------|
| commit | ruff, ruff-format | Check changed Python files |
| commit | mypy | Type check changed Python files |
| commit | bandit | Security check changed Python files |
| push | pytest | Run tests |

---

## Branch Naming

Use descriptive branch names:
- `feature/<description>` - New features
- `fix/<description>` - Bug fixes
- `refactor/<description>` - Code refactoring
- `docs/<description>` - Documentation updates
