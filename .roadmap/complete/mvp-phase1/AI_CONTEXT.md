# SafeShell MVP Phase 1 - AI Context

**Purpose**: AI agent context document for implementing SafeShell MVP Phase 1

**Scope**: Git branch protection with daemon/wrapper architecture

**Overview**: SafeShell is a command-line safety layer for AI coding assistants. This MVP proves the core concept: AI tools use SafeShell as their shell, SafeShell intercepts commands, evaluates them against plugins, and blocks dangerous operations. Phase 1 focuses on blocking git commits on protected branches (main/master).

**Dependencies**: Python 3.11+, pydantic, loguru, pyyaml, plumbum, typer, rich

**Exports**: safeshell CLI, safeshell-wrapper shell entry point

**Related**: PR_BREAKDOWN.md for implementation tasks, PROGRESS_TRACKER.md for current status

**Implementation**: Daemon-based architecture with Unix socket IPC and plugin system

---

## Overview

SafeShell MVP Phase 1 implements the core interception architecture:

```
AI Tool (SHELL=/path/to/safeshell-wrapper)
    │
    ▼
┌─────────────────────────────┐
│  Shell Wrapper              │  ← Minimal Python, just IPC
│  safeshell-wrapper -c "cmd" │
└─────────────┬───────────────┘
              │ Unix socket (JSON lines)
              ▼
┌─────────────────────────────┐
│  Daemon (asyncio)           │  ← Long-running, plugins loaded
│  - Plugin manager           │
│  - Policy evaluation        │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Plugins (Python modules)   │
│  - git-protect (MVP)        │
└─────────────────────────────┘
```

## Project Background

AI coding tools (Claude Code, Cursor, Aider, etc.) execute shell commands on behalf of users. They can accidentally:
- Delete critical files or directories
- Commit/push to protected branches
- Expose sensitive data

SafeShell provides guardrails without requiring containers or VMs. The system assumes a cooperative (non-adversarial) AI agent and focuses on preventing mistakes.

## Feature Vision

1. **Shell Wrapper**: AI tools set `SHELL=/path/to/safeshell-wrapper`. All commands are intercepted.
2. **Daemon Process**: Long-running process with plugins loaded. Solves Python startup time problem.
3. **Plugin System**: All policy logic in plugins. Core is policy-agnostic.
4. **Git Protection**: MVP blocks commits on main/master branches.

## Current Application Context

The project was scaffolded with:
- Poetry for dependency management
- Typer/Rich for CLI
- GitHub Actions for CI/CD (lint.yml, test.yml)
- Pre-commit hooks configured
- Quality gates: Ruff, MyPy, Bandit, pytest

## Target Architecture

### Core Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Models | `src/safeshell/models.py` | Pydantic models for IPC |
| Exceptions | `src/safeshell/exceptions.py` | Error hierarchy |
| Config | `src/safeshell/config.py` | YAML config loading |
| Plugin Base | `src/safeshell/plugins/base.py` | Plugin ABC |
| Git Protect | `src/safeshell/plugins/git_protect.py` | Branch protection |
| Daemon | `src/safeshell/daemon/` | Server, protocol, manager |
| Wrapper | `src/safeshell/wrapper/` | Shell wrapper, client |

### User Journey

1. User runs `safeshell init` to create config
2. User configures AI tool: `SHELL=/path/to/safeshell-wrapper`
3. User starts daemon: `safeshell daemon start`
4. AI tool runs commands through wrapper
5. Wrapper sends to daemon for evaluation
6. Daemon returns ALLOW/DENY decision
7. Wrapper executes or blocks with message

## Key Decisions Made

### Coding Standards (MANDATORY)

| Rule | Rationale |
|------|-----------|
| **No `print()` statements** | Use `loguru` for logging. Use `rich.console.Console()` for user output. |
| **Pydantic for all models** | All data classes, configs must be Pydantic `BaseModel`. No `@dataclass`. |
| **No `subprocess` module** | Use `plumbum` for command execution. Cross-platform. |
| **Type hints required** | MyPy strict mode enforced. |

### Architecture Decisions

1. **asyncio for daemon**: Native Unix socket support, modern Python
2. **JSON lines protocol**: Simple, debuggable, no extra dependencies
3. **Fail-closed default**: If daemon unreachable, block commands (configurable)
4. **Simple plugin filtering**: No "watched commands" cache for MVP

## Integration Points

### With Existing Features

- CLI (`src/safeshell/cli.py`): Add daemon and wrapper subcommands
- pyproject.toml: Entry points for safeshell and safeshell-wrapper

## Success Metrics

### Phase 1 Complete When:
1. `safeshell daemon start` starts daemon successfully
2. `safeshell daemon status` shows running
3. `SHELL=.../safeshell-wrapper safeshell-wrapper -c "git commit -m test"` blocked on main
4. Same command succeeds on feature branch
5. All unit tests pass

## Technical Constraints

- Linux only for MVP (architecture supports macOS)
- Python 3.11+
- Unix domain sockets for IPC
- Socket at `~/.safeshell/daemon.sock`
- Config at `~/.safeshell/config.yaml`

## AI Agent Guidance

### When Implementing New Plugins

1. Inherit from `Plugin` base class
2. Implement `name`, `description` properties
3. Override `matches()` for performance filtering
4. Implement `evaluate()` returning `EvaluationResult`
5. Use helper methods: `_allow()`, `_deny()`, `_require_approval()`

### When Modifying Daemon

1. All IPC uses JSON lines (newline-delimited JSON)
2. Request/Response models in `models.py`
3. Protocol encoding in `daemon/protocol.py`
4. Plugin loading in `daemon/manager.py`

### Common Patterns

```python
# Plugin evaluation pattern
def evaluate(self, ctx: CommandContext) -> EvaluationResult:
    if dangerous_condition(ctx):
        return self._deny("Explanation for AI")
    return self._allow("Why it's safe")

# Config loading pattern
from safeshell.config import load_config
config = load_config()

# Daemon client pattern
from safeshell.wrapper.client import DaemonClient
client = DaemonClient()
response = client.evaluate(command, working_dir, env)
```

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Daemon crashes | Auto-restart on wrapper invocation |
| Daemon unreachable | Configurable fail-closed/fail-open |
| Slow startup | Daemon stays running, wrapper just does IPC |
| Plugin errors | Catch exceptions, log, allow command |

## Future Enhancements (Not in Phase 1)

- Phase 2: Approval workflow with challenge codes in monitor TUI
- Phase 3: CI/CD hardening with integration tests
- Future: rm-protect, path-protect, secrets-detect plugins
- Future: macOS support, packaging (Homebrew, Snap)

---

## Implementation Learnings

### Architecture Validation ✅

The daemon-based architecture works well:
- **Startup overhead is minimal**: Wrapper just does IPC, no Python module loading
- **Plugin system is clean**: ABC with matches/evaluate pattern works
- **JSON lines protocol**: Simple and debuggable
- **Auto-start**: Works reliably from wrapper

### Technical Gotchas

| Issue | Solution |
|-------|----------|
| Pydantic field/method name collision | Rename fields (e.g., `error` → `error_message`) |
| Enum YAML serialization | Use `model_dump(mode="json")` for primitives |
| Health check connection noise | Treat "Connection closed" as debug, not warning |
| `contextlib.suppress` with await | Doesn't work - use try-except with file-level noqa |
| BrokenPipeError in finally | Wrap `writer.wait_closed()` in try-except |

### Coding Standard Additions

Added to `.ai/ai-rules.md`:
- No method-level noqa comments - use file-level `# ruff: noqa: RULE`
- Pydantic for ALL models (no @dataclass)
- No subprocess module (use plumbum)
- No print() (use loguru/rich)
