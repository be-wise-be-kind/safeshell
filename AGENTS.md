# AI Agent Guide for SafeShell

**Purpose**: Primary entry point for AI agents working on this project

**Quick Start**: Read `.ai/docs/PROJECT_CONTEXT.md` for full context, then check `.ai/index.yaml` for navigation.

---

## Project Overview

SafeShell is a command-line safety layer for AI coding assistants. It intercepts shell commands, evaluates them against configurable policies, and enforces decisions before execution.

**Type**: python-cli
**Status**: in-development

## CRITICAL: First Steps

**Before doing anything else:**
1. Check if `.ai/index.yaml` exists - if not, the foundation plugin may not be installed
2. Check `.roadmap/` for any active roadmaps that should guide your work
3. Read `.ai/docs/PROJECT_CONTEXT.md` for architecture understanding

## Navigation

### Critical Documents
- **Project Context**: `.ai/docs/PROJECT_CONTEXT.md` - Architecture and philosophy
- **Index**: `.ai/index.yaml` - Repository structure and navigation
- **Layout**: `.ai/layout.yaml` - Directory organization

### How-To Guides
See `.ai/howtos/` for step-by-step guides on common tasks.

### Templates
See `.ai/templates/` for reusable file templates and boilerplate.

### Roadmaps
See `.roadmap/` for feature roadmaps and installation progress.

## Roadmap-Driven Development

### When User Requests Planning

If the user says any of the following:
- "I want to plan out..."
- "I want to roadmap..."
- "Create a roadmap for..."
- "Plan the implementation of..."
- "Break down the feature..."

**Your Actions**:
1. **Read** `.ai/howtos/how-to-roadmap.md` for roadmap workflow guidance
2. **Use templates** from `.ai/templates/roadmap-*.md.template`
3. **Create roadmap** in `.roadmap/planning/[feature-name]/`
4. **Follow** the three-document structure:
   - PROGRESS_TRACKER.md (required - primary handoff document)
   - PR_BREAKDOWN.md (required for multi-PR features)
   - AI_CONTEXT.md (optional - architectural context)

### When User Requests Continuation

If the user says any of the following:
- "I want to continue with..."
- "Continue the roadmap for..."
- "What's next in..."
- "Resume work on..."
- "Lets continue..."

**Your Actions**:
1. **Check** `.roadmap/in-progress/` for active roadmaps
2. **Read** the roadmap's `PROGRESS_TRACKER.md` FIRST
3. **Follow** the "Next PR to Implement" section
4. **Update** PROGRESS_TRACKER.md after completing each PR

### Roadmap Lifecycle

```
planning/ → in-progress/ → complete/
   ↓             ↓              ↓
Created      Implementing    Archived
```

See `.ai/howtos/how-to-roadmap.md` for detailed workflow instructions.

## Development Guidelines

### Code Style
- Python 3.11+ with full type hints
- Ruff for linting and formatting
- Thai-lint for code quality checks

### File Organization
See `.ai/layout.yaml` for the canonical directory structure.

**Key Directories**:
- Source code: `src/`
- Tests: `tests/`
- Documentation: `docs/`

### Documentation Standards
All files should include appropriate headers following the project's documentation standards.

## Build and Test Commands

### Using justfile (NOT Makefile)
This project uses `just` as the build system, consistent with thai-lint.

```bash
# Initial setup
just init

# Run tests
just test

# Run linting
just lint

# Full quality checks
just lint-full

# Format code
just format

# Thai-lint checks
just lint-thai
```

### Docker
```bash
# Build Docker image
just docker-build

# Run in container
just docker-run
```

## Git Workflow

### Commit Messages
Follow conventional commits format:
```
type(scope): Brief description

Detailed description if needed.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### Branch Strategy
- `main` - stable releases
- `feature/*` - new features
- `fix/*` - bug fixes

### Before Committing
- [ ] All tests pass (`just test`)
- [ ] Code is linted (`just lint`)
- [ ] Documentation updated
- [ ] No secrets committed

## Security Considerations

- Never commit secrets or credentials
- Secrets should be in `.env` (gitignored)
- SafeShell itself is a security tool - be extra careful with:
  - Plugin evaluation logic
  - Command parsing
  - Path resolution

## Common Tasks

### Adding a New Plugin
1. Check `.ai/howtos/` for plugin development guide (when available)
2. Create plugin in `src/plugins/`
3. Follow the Plugin API (see PROJECT_CONTEXT.md)
4. Add tests in `tests/plugins/`

### Debugging
1. Check logs in `~/.safeshell/safeshell.log`
2. Run tests with verbose output: `just test -v`
3. Use Python debugger as needed

## Resources

### External Dependencies
See `pyproject.toml` for Python dependencies managed by Poetry.

Key frameworks:
- **Typer**: CLI framework
- **Rich**: Terminal UI and formatting
- **pytest**: Testing framework

## Getting Help

### When Stuck
1. Check `.ai/docs/` for context and architecture
2. Review `.ai/howtos/` for guides
3. Check existing code for patterns
4. Review git history for similar changes

---

## Language-Specific Guidelines

<!-- BEGIN_LANGUAGE_GUIDELINES -->

### Python (PEP 8)

- **Style**: 100 char line length, 4-space indentation, double quotes
- **Naming**: snake_case (functions/vars), PascalCase (classes), UPPER_SNAKE_CASE (constants)
- **Imports**: stdlib -> third-party -> local (with blank lines between groups)
- **Type hints**: Required for all function signatures (use Python 3.11+ built-in types)
- **Docstrings**: Google-style for all public functions and classes
- **Complexity**: Maximum McCabe complexity of 5 (radon grade A)
- **Security**: No hardcoded secrets, use parameterized queries, validate all inputs

**Quality Commands**:
- `ruff check .` - Run Ruff linting
- `ruff format .` - Format code with Ruff
- `mypy src` - Run MyPy type checking
- `bandit -r src` - Run Bandit security scan
- `pytest` - Run tests
- `pytest --cov=src` - Run tests with coverage
- `radon cc src -a` - Cyclomatic complexity analysis
- `pylint src` - Comprehensive linting
- `thailint .` - Thai-lint quality checks

<!-- END_LANGUAGE_GUIDELINES -->

---

**Note**: This file is generated by ai-projen's ai-folder plugin. Customize sections based on your project's specific needs.
