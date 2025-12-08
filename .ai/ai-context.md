File: .ai/ai-context.md

Purpose: Development context and patterns for AI agents working on SafeShell

Exports: Project overview, architecture, key patterns, conventions

Depends: index.yaml, ai-rules.md

Overview: Comprehensive development context document that provides AI agents with
    everything needed to understand this project. Includes project purpose, CLI
    architecture, code patterns, and development conventions.

# AI Development Context

**Purpose**: Everything an agent needs to understand this project for development

---

## Project Summary

**SafeShell** is a command-line safety layer for AI coding assistants. It intercepts shell commands, evaluates them against configurable policies, and enforces decisions before execution.

### What This Repo Does

- Intercepts shell commands from AI tools (Claude Code, Cursor, etc.)
- Evaluates commands against configurable plugin-based policies
- Provides automatic denial for prohibited operations
- Enables soft-delete of files to recoverable trash
- Offers human approval workflow for risky operations via monitor TUI

### What This Repo Does NOT Do

- Create infrastructure or cloud resources
- Manage AI tool configurations
- Replace your shell - it wraps it

### Architecture Context

SafeShell operates as a shell wrapper. AI tools set `SHELL=/path/to/safeshell`, and SafeShell:
1. Intercepts every command
2. Queries the daemon for applicable plugins
3. Evaluates policy and determines action (allow/deny/soft-delete/approval)
4. Executes via the user's real shell if allowed

### The safeshell CLI

The `safeshell` command is the primary interface. It uses a hierarchical structure:

```
safeshell <command> [options]
```

Commands: `version`, `check`, `status`

Example workflows:
- Check SafeShell version: `safeshell version`
- Check if a command is safe: `safeshell check "rm -rf /tmp/test"`
- Show daemon status: `safeshell status`

---

## Key Patterns

### CLI Commands

Use Typer for CLI commands:

```python
import typer
from rich.console import Console

app = typer.Typer()
console = Console()

@app.command()
def my_command(name: str, verbose: bool = False) -> None:
    """Command description."""
    console.print(f"Hello {name}")
```

### Logging

Use Loguru for all logging output:

```python
from loguru import logger

logger.info("Operation completed")
logger.debug("Debug details")
logger.error("Something failed")
```

### Rich Output

Use Rich console for formatted output:

```python
from rich.console import Console

console = Console()
console.print("[green]Success[/green]")
console.print("[red]Error:[/red] Something went wrong")
```

---

## File Headers

All Python files require standardized headers. See [how_tos/how-to-write-file-headers.md](./howtos/how-to-write-file-headers.md) for the complete specification.

---

## Adding a New Module

1. Create directory: `src/safeshell/<module>/`
2. Add `__init__.py` with public API exports
3. Add `cli.py` with Typer command group if adding CLI commands
4. Add `models.py` with Pydantic models if needed
5. Register CLI in main `cli.py`
6. Add tests in `tests/test_<module>/`
7. Update AGENTS.md if adding new CLI commands

---

## Adding a New Plugin

1. Create plugin file: `src/safeshell/plugins/<plugin_name>.py`
2. Implement the Plugin interface
3. Add tests in `tests/plugins/test_<plugin_name>.py`
4. Document in README.md

---

## Project Structure

```
safeshell/
├── .ai/
│   ├── index.yaml            # This index - documentation navigation
│   ├── ai-context.md         # Development context and patterns (this file)
│   ├── ai-rules.md           # Rules and quality gates
│   ├── docs/
│   │   ├── PROJECT_CONTEXT.md
│   │   └── PYTHON_STANDARDS.md
│   ├── howtos/
│   │   ├── how-to-roadmap.md
│   │   ├── how-to-write-file-headers.md
│   │   └── how-to-use-safeshell-cli.md
│   └── templates/
│       ├── roadmap-*.md.template
│       └── file-header-python.template
├── .roadmap/
│   ├── planning/             # New roadmaps being designed
│   ├── in-progress/          # Active implementation
│   └── complete/             # Archived completed roadmaps
├── src/safeshell/
│   ├── __init__.py
│   ├── cli.py                # Main CLI entry point
│   ├── plugins/              # Policy plugins (rm-protect, etc.)
│   ├── daemon/               # Background daemon process
│   ├── monitor/              # TUI for approval workflow
│   └── wrapper/              # Shell wrapper logic
├── tests/
│   ├── test_cli.py
│   └── plugins/
├── .github/workflows/
│   ├── lint.yml
│   └── test.yml
├── pyproject.toml            # Poetry configuration
├── justfile                  # Build commands
├── Dockerfile
└── docker-compose.yml
```

---

## DO NOT

- Use bash-style exit codes (use proper exceptions or return values)
- Use stdlib logging (use Loguru)
- Use print() statements (use Rich console or Loguru)
- Skip type hints (MyPy strict mode)
- Commit without running quality gates
- Skip reading `.ai/index.yaml` before starting work
