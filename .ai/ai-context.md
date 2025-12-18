File: .ai/ai-context.md

Purpose: Development context and patterns for AI agents working on SafeShell

Exports: Project overview, architecture, key patterns, conventions

Depends: index.yaml, ai-rules.md

Overview: Comprehensive development context document that provides AI agents with
    everything needed to understand this project. Includes project purpose, system
    architecture, daemon design, rules engine internals, code patterns, and
    development conventions.

# AI Development Context

**Purpose**: Everything an agent needs to understand this project for development

---

## Project Summary

**SafeShell** is a command-line safety layer for AI coding assistants. It intercepts shell commands, evaluates them against configurable policies, and enforces decisions before execution.

### What This Repo Does

- Intercepts shell commands from AI tools (Claude Code, Cursor, etc.)
- Evaluates commands against YAML-configured rules with structured Python conditions
- Provides automatic denial for prohibited operations
- Enables soft-delete of files to recoverable trash
- Offers human approval workflow for risky operations via Monitor TUI

### What This Repo Does NOT Do

- Create infrastructure or cloud resources
- Manage AI tool configurations
- Replace your shell - it wraps it

### Design Philosophy

SafeShell assumes a **cooperative AI agent** and focuses on preventing accidents rather than containing adversaries. The goal is to catch mistakes before they happen, not to create an adversarial security boundary.

---

## Core Architecture

### Three-Layer Interception Strategy

SafeShell uses three complementary methods to intercept commands:

```
┌─────────────────────────────────────────────────────────┐
│                    Command Sources                       │
│  (Human Terminal, Claude Code, Cursor, Warp, etc.)      │
└─────────────────────┬───────────────────────────────────┘
                      │
          ┌───────────┼───────────┐
          │           │           │
          ▼           ▼           ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐
    │  Shims   │ │  Shell   │ │  Shell   │
    │  (PATH)  │ │ Functions│ │ Wrapper  │
    └────┬─────┘ └────┬─────┘ └────┬─────┘
          │           │           │
          └───────────┼───────────┘
                      │
                      ▼
              ┌──────────────┐
              │    Daemon    │
              │  (evaluate)  │
              └──────────────┘
```

1. **Command Shims** (PATH-based)
   - Symlinks in `~/.safeshell/shims/` intercept external commands
   - Commands like `git`, `rm`, `docker` go through shims
   - Works for all command sources

2. **Shell Function Overrides**
   - Functions in `init.bash` intercept shell builtins
   - Covers `cd`, `source`, `eval` and similar
   - Sourced via shell initialization

3. **Shell Wrapper**
   - Fallback for AI tools using `$SHELL -c "command"`
   - Catches commands that bypass shims
   - Set via `SHELL=/path/to/safeshell-wrapper`

This hybrid approach catches all command invocations regardless of source.

---

## Daemon Architecture

### Overview

SafeShell uses a long-running daemon to avoid Python startup overhead (~250ms per command).

```
┌─────────────────────────────────────────────────────────┐
│                      Daemon Server                       │
│                   (asyncio Unix sockets)                 │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │ Rule Loader │    │  Evaluator  │    │  Executor   │  │
│  │   (YAML)    │ -> │ (conditions)│ -> │   (fork)    │  │
│  └─────────────┘    └─────────────┘    └─────────────┘  │
│                                                          │
├─────────────────────────────────────────────────────────┤
│  Sockets:                                                │
│  - daemon.sock  (wrapper/shim requests)                  │
│  - monitor.sock (event streaming to TUI)                 │
└─────────────────────────────────────────────────────────┘
```

### Key Components

| Component | File | Purpose |
|-----------|------|---------|
| Server | `daemon/server.py` | Asyncio Unix socket server |
| Manager | `daemon/manager.py` | Rule loading and command evaluation |
| Executor | `daemon/executor.py` | Fork and execute approved commands |
| Approval | `daemon/approval.py` | Human approval workflow |
| Protocol | `daemon/protocol.py` | JSON-lines IPC protocol |
| Lifecycle | `daemon/lifecycle.py` | Start, stop, PID file management |

### IPC Protocol

Communication uses JSON-lines over Unix domain sockets:

```python
# Request
{"type": "EVALUATE", "command": "rm -rf /tmp/test", "context": {...}}

# Response
{"decision": "ALLOW", "reason": "No matching rules"}
```

---

## Rules Engine

### Evaluation Flow

```
Command → Extract Executable → Fast-Path Check → Directory Match
    → Context Filter → Condition Evaluation → Decision Aggregation
```

### Fast-Path Optimization

Rules with a `commands` field are indexed. Commands NOT in any rule's index skip evaluation entirely (<0.1ms).

```yaml
# Indexed under "git" - enables fast-path
- name: git-protection
  commands: ["git"]
  action: require_approval
```

### Structured Conditions

SafeShell uses Python condition classes (not bash) for performance and security:

| Condition | Purpose |
|-----------|---------|
| `command_matches` | Regex match on full command |
| `command_contains` | Substring match |
| `git_branch_in` | Current branch in list |
| `path_matches` | Path in command matches glob |
| `env_equals` | Environment variable check |

```yaml
# Modern structured conditions
- name: protect-main
  commands: ["git"]
  conditions:
    - type: git_branch_in
      branches: ["main", "master"]
  action: require_approval
```

### Decision Aggregation

When multiple rules match: **most restrictive wins**

```
DENY > REQUIRE_APPROVAL > REDIRECT > ALLOW
```

### Rule Loading Order

1. **Default rules** - Built into SafeShell
2. **Global rules** - `~/.safeshell/rules.yaml` (can override defaults)
3. **Repo rules** - `.safeshell/rules.yaml` (additive only, cannot override)

### Rule Overrides

Users can override or disable default rules in their global `~/.safeshell/rules.yaml`:

```yaml
# ~/.safeshell/rules.yaml
rules: []

overrides:
  - name: approve-force-push
    disabled: true  # Disable this default rule

  - name: deny-rm-rf-star
    action: require_approval  # Change from deny to approval
    message: "Custom message"
```

**Security**: Repo rules cannot override - only global rules can. This prevents
malicious repos from weakening your protections.

**Performance**: Overrides are applied at load time (daemon startup). Disabled
rules never enter the evaluator's index - zero runtime cost.

---

## Key Modules Reference

| Module | Purpose |
|--------|---------|
| `cli.py` | Main CLI entry point (Typer) |
| `daemon/server.py` | Asyncio Unix socket server |
| `daemon/manager.py` | Rule loading and evaluation |
| `rules/schema.py` | Pydantic rule models |
| `rules/evaluator.py` | Rule matching engine |
| `rules/condition_types.py` | Structured condition classes |
| `rules/loader.py` | YAML rule file loading |
| `wrapper/client.py` | Daemon client for shims/wrapper |
| `monitor/app.py` | Monitor TUI (Textual) |
| `shims/manager.py` | Shim creation and management |
| `gui/popup.py` | Approval popup (PyQt6) |

---

## CLI Structure

```
safeshell
├── version                  # Show version
├── init                     # Initialize configuration
├── check <cmd>              # Test command evaluation
├── status                   # Show daemon status
├── monitor [--debug]        # Launch Monitor TUI
├── up/down/restart          # Daemon + GUI lifecycle
├── refresh                  # Regenerate shims
├── daemon/                  # Daemon management
│   ├── start/stop/restart
│   ├── status
│   └── logs
├── wrapper/                 # Wrapper setup
│   ├── install
│   └── path
├── rules/                   # Rule management
│   └── validate
└── perf/                    # Performance
    └── benchmark
```

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

### Shell Execution

Use plumbum for shell execution (NOT subprocess):

```python
from plumbum import local

# Execute command
git = local["git"]
result = git["status"]()

# With arguments
ls = local["ls"]
result = ls["-la", "/tmp"]()
```

### Data Models

Use Pydantic for all data models (NOT dataclass):

```python
from pydantic import BaseModel, Field

class CommandContext(BaseModel):
    command: str
    executable: str
    args: list[str]
    working_dir: str
    git_branch: str | None = None
```

---

## Architectural Decisions

### Why Daemon-Based?

- **Performance**: Python startup (~250ms) amortized across all commands
- **State**: Rules loaded once, cached in memory
- **Coordination**: Single point for approval workflow

### Why YAML Configuration?

- **User-friendly**: Users edit YAML, not Python code
- **Flexible**: Complex conditions via structured types
- **Safe**: Schema validation catches errors early

### Why Shim-Based Interception?

- **Proven pattern**: Used by pyenv, rbenv
- **Universal**: Works for all command sources
- **Transparent**: Doesn't modify shell behavior

### Why Structured Conditions (Not Bash)?

- **Security**: No shell injection risk
- **Performance**: No subprocess spawning (~250ms saved)
- **Portability**: Works on all platforms
- **Testability**: Unit testable condition classes

---

## Common Gotchas

### Pydantic Field/Method Collision

```python
# WRONG - 'error' collides with BaseModel.error()
class MyModel(BaseModel):
    error: str

# CORRECT - use different name
class MyModel(BaseModel):
    error_message: str
```

### Enum YAML Serialization

```python
# WRONG - enum value not serializable
model.model_dump()

# CORRECT - use json mode
model.model_dump(mode="json")
```

### BrokenPipeError in Finally

```python
# WRONG - can raise in finally
finally:
    sys.stdout.write(data)

# CORRECT - wrap in try-except
finally:
    try:
        sys.stdout.write(data)
    except BrokenPipeError:
        pass
```

### Async Context in Sync Code

```python
# WRONG - blocking in async
def sync_function():
    result = asyncio.run(async_operation())  # Nested event loop

# CORRECT - use sync wrapper or stay async
async def async_function():
    result = await async_operation()
```

---

## Security Model

### Trust Boundaries

1. **Shim → Daemon**: Socket authentication, input validation
2. **YAML → Rules**: Safe parsing, schema validation
3. **Daemon → Executor**: Command injection prevention
4. **User → Daemon**: Runs as user, no privilege escalation

### Security Principles

- **Zero shell=True**: All subprocess calls use list-form arguments
- **Safe YAML**: `yaml.safe_load()` with Pydantic validation
- **Input validation**: All inputs validated before processing
- **Dependency management**: Version pinning, automated scanning

---

## File Headers

All Python files require standardized headers. See:
- [docs/file-header-format.md](./docs/file-header-format.md) - Specification
- [howtos/how-to-write-file-headers.md](./howtos/how-to-write-file-headers.md) - Guide

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

## Project Structure

```
safeshell/
├── .ai/
│   ├── index.yaml            # Documentation navigation
│   ├── ai-context.md         # This file
│   ├── ai-rules.md           # Quality gates
│   ├── docs/
│   │   ├── file-header-format.md
│   │   └── ...
│   ├── howtos/
│   │   ├── how-to-write-rules.md
│   │   ├── how-to-debug-rules.md
│   │   └── ...
│   └── templates/
│       └── ...
├── .roadmap/
│   ├── planning/
│   ├── in-progress/
│   └── complete/
├── src/safeshell/
│   ├── __init__.py
│   ├── cli.py                # Main CLI entry point
│   ├── models.py             # Core Pydantic models
│   ├── rules/                # Rule engine
│   │   ├── schema.py         # Rule models
│   │   ├── evaluator.py      # Evaluation logic
│   │   ├── condition_types.py # Structured conditions
│   │   └── loader.py         # YAML loading
│   ├── daemon/               # Background daemon
│   │   ├── server.py         # Socket server
│   │   ├── manager.py        # Rule management
│   │   └── lifecycle.py      # Start/stop
│   ├── monitor/              # TUI
│   │   └── app.py
│   ├── wrapper/              # Shell wrapper
│   │   └── client.py
│   ├── shims/                # Command shims
│   │   └── manager.py
│   └── gui/                  # GUI components
│       └── popup.py
├── tests/
├── pyproject.toml
├── justfile
└── docker-compose.yml
```

---

## DO NOT

- Use `subprocess` module (use plumbum)
- Use `print()` statements (use Rich console or Loguru)
- Use `@dataclass` (use Pydantic BaseModel)
- Use stdlib `logging` (use Loguru)
- Skip type hints (MyPy strict mode required)
- Add method-level noqa comments (use file-level)
- Commit without running `just lint-full`
- Skip reading `.ai/index.yaml` before starting work
