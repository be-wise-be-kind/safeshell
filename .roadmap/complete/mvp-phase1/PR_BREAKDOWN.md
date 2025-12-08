# SafeShell MVP Phase 1 - PR Breakdown

**Purpose**: Detailed implementation breakdown of MVP Phase 1 into manageable, atomic pull requests

**Scope**: Complete MVP from scaffolding through working git-protect demo

**Overview**: Breaks down MVP Phase 1 into 4 PRs. Each PR is self-contained, testable, and maintains application functionality while incrementally building toward the complete feature.

**Dependencies**: Python 3.11+, pydantic, loguru, pyyaml, plumbum

**Exports**: PR implementation plans, file structures, testing strategies

**Related**: AI_CONTEXT.md for feature overview, PROGRESS_TRACKER.md for status tracking

**Implementation**: Atomic PR approach with detailed step-by-step guidance

---

## Overview

This document breaks down MVP Phase 1 into 4 PRs:

| PR | Title | Status | Complexity |
|----|-------|--------|------------|
| PR-1 | Foundation: Models, Exceptions, Config | 🟢 COMPLETE | Low |
| PR-2 | Plugin System and Git-Protect Plugin | 🟢 COMPLETE | Medium |
| PR-3 | Daemon: Server, Protocol, Manager | 🟢 COMPLETE | High |
| PR-4 | Wrapper and CLI Integration | 🟢 COMPLETE | Medium |

---

## PR-1: Foundation - Models, Exceptions, Config

**Status**: 🟢 COMPLETE (implemented during planning session)

### Summary
Core data structures that all other components depend on.

### Files Created
- `src/safeshell/models.py` - Pydantic models (Decision, CommandContext, EvaluationResult, DaemonRequest, DaemonResponse)
- `src/safeshell/exceptions.py` - Exception hierarchy (SafeShellError, DaemonError, PluginError, etc.)
- `src/safeshell/config.py` - Config loading from `~/.safeshell/config.yaml`

### Files Modified
- `pyproject.toml` - Added dependencies: pydantic, loguru, pyyaml, plumbum, pytest-asyncio

### Key Implementation Details

**models.py**:
- `Decision` enum: ALLOW, DENY, REQUIRE_APPROVAL
- `CommandContext`: Includes git detection via `_detect_git_context()`
- `DaemonRequest/Response`: IPC message types
- All models are Pydantic BaseModel

**config.py**:
- `UnreachableBehavior` enum: FAIL_CLOSED (default), FAIL_OPEN
- `SafeShellConfig`: delegate_shell, unreachable_behavior, log_level
- `load_config()`: Loads from YAML with defaults

### Testing Requirements
- [x] Test Pydantic model validation
- [x] Test CommandContext.from_command() parsing
- [x] Test git context detection
- [x] Test config loading with missing file
- [x] Test config loading with invalid YAML

---

## PR-2: Plugin System and Git-Protect Plugin

**Status**: 🟢 COMPLETE (implemented during planning session)

### Summary
Plugin base class and the git-protect plugin that blocks commits on protected branches.

### Files Created
- `src/safeshell/plugins/__init__.py` - Package exports
- `src/safeshell/plugins/base.py` - Plugin ABC with matches(), evaluate()
- `src/safeshell/plugins/git_protect.py` - Git branch protection plugin

### Key Implementation Details

**base.py**:
```python
class Plugin(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    def matches(self, ctx: CommandContext) -> bool:
        return True  # Override for filtering

    @abstractmethod
    def evaluate(self, ctx: CommandContext) -> EvaluationResult: ...

    # Helpers: _allow(), _deny(), _require_approval()
```

**git_protect.py**:
- Protected branches: main, master, develop
- `matches()`: Only git commands in git repos
- `evaluate()`: Blocks commits on protected branches, blocks force-push

### Testing Requirements
- [x] Test Plugin ABC contract
- [x] Test GitProtectPlugin.matches() filtering
- [x] Test commit blocked on main branch
- [x] Test commit allowed on feature branch
- [x] Test force-push blocked on protected branch

---

## PR-3: Daemon - Server, Protocol, Manager

**Status**: 🟢 COMPLETE (implemented during planning session)

### Summary
The daemon process that runs in the background, loads plugins, and evaluates commands.

### Files Created
- `src/safeshell/daemon/__init__.py` - Package exports
- `src/safeshell/daemon/protocol.py` - JSON lines encoding/decoding
- `src/safeshell/daemon/lifecycle.py` - PID file, socket management
- `src/safeshell/daemon/manager.py` - Plugin loading, command evaluation
- `src/safeshell/daemon/server.py` - asyncio Unix socket server
- `src/safeshell/daemon/cli.py` - start, stop, status, restart commands

### Key Implementation Details

**protocol.py**:
- JSON lines format (newline-delimited JSON)
- `encode_message()`, `decode_message()`
- `read_message()`, `write_message()` for async streams

**lifecycle.py**:
- Socket at `~/.safeshell/daemon.sock`
- PID at `~/.safeshell/daemon.pid`
- `is_running()`: Tests socket connectivity
- `cleanup_on_start()`: Removes stale socket

**manager.py**:
- `PluginManager`: Loads built-in plugins
- `process_request()`: Routes to evaluate, ping, status handlers
- `_aggregate_decisions()`: Most restrictive wins (DENY > REQUIRE_APPROVAL > ALLOW)

**server.py**:
- `DaemonServer`: asyncio Unix socket server
- Signal handlers for graceful shutdown
- `run_daemon()`: Entry point for foreground mode

**cli.py**:
- `safeshell daemon start [--foreground]`
- `safeshell daemon stop`
- `safeshell daemon status`
- `safeshell daemon restart`
- Uses double-fork for daemonization

### Testing Requirements
- [x] Test protocol encode/decode round-trip
- [x] Test lifecycle socket detection
- [x] Test manager plugin loading
- [x] Test manager decision aggregation
- [ ] Test server accepts connections (integration) - Deferred to Phase 3

---

## PR-4: Wrapper and CLI Integration

**Status**: 🟢 COMPLETE

### Summary
The shell wrapper that AI tools invoke, and CLI integration.

### Files Created
- `src/safeshell/wrapper/__init__.py` - Package exports
- `src/safeshell/wrapper/client.py` - Sync socket client for daemon
- `src/safeshell/wrapper/shell.py` - Main wrapper entry point
- `src/safeshell/wrapper/cli.py` - `safeshell wrapper install` command

### Files Modified
- `src/safeshell/cli.py` - Wired up daemon and wrapper subcommands

### Key Implementation Details

**client.py** (Complete):
- `DaemonClient`: Synchronous socket client
- `evaluate()`: Send command for evaluation
- `ping()`: Health check
- `ensure_daemon_running()`: Auto-start if needed
- Uses plumbum for process spawning

**shell.py** (Complete):
- Entry point: `safeshell-wrapper -c "command"`
- `_evaluate_and_execute()`: Main flow
- `_execute()`: Uses plumbum for execution
- `_passthrough()`: For non -c invocations
- Respects fail-closed/fail-open config

**wrapper/cli.py** (TODO):
```python
@app.command()
def install() -> None:
    """Print setup instructions for AI tools."""
    # Show SHELL= instructions
    # Show SAFESHELL_REAL_SHELL= if needed
```

**cli.py modifications** (TODO):
```python
from safeshell.daemon.cli import app as daemon_app
from safeshell.wrapper.cli import app as wrapper_app

app.add_typer(daemon_app, name="daemon")
app.add_typer(wrapper_app, name="wrapper")
```

### Testing Requirements
- [ ] Test client connection to daemon - Deferred to Phase 3
- [ ] Test client auto-start behavior - Deferred to Phase 3
- [ ] Test wrapper -c invocation - Deferred to Phase 3
- [ ] Test wrapper passthrough mode - Deferred to Phase 3
- [ ] Test wrapper fail-closed behavior - Deferred to Phase 3
- [ ] Test wrapper fail-open behavior - Deferred to Phase 3
- [x] Integration: Full command flow blocked on main - **MANUALLY VERIFIED**
- [x] Integration: Full command flow allowed on feature - **MANUALLY VERIFIED**

---

## Implementation Guidelines

### Code Standards

| Standard | Requirement |
|----------|-------------|
| No print() | Use loguru or rich.console |
| Pydantic models | All data classes must be BaseModel |
| No subprocess | Use plumbum for execution |
| Type hints | All functions fully typed |
| Docstrings | Google-style for public APIs |

### Testing Requirements

- Unit tests for all modules
- Integration tests for full command flow
- Tests must pass: `just test` or `poetry run pytest`
- Lint must pass: `just lint` or `poetry run ruff check`

### Documentation Standards

- File headers with Purpose, Exports, Depends, Overview
- Docstrings for public classes and functions
- Update .ai/ai-rules.md with new coding standards

### Security Considerations

- Socket permissions: 0600 (owner only)
- No secrets in logs
- Validate all IPC messages with Pydantic

### Performance Targets

- Wrapper overhead (daemon running): < 50ms
- Daemon startup: < 2s
- Plugin evaluation: < 10ms

---

## Rollout Strategy

### Phase 1: MVP (This Roadmap)
1. Complete PR-4 (wrapper CLI integration)
2. Update ai-rules.md with coding standards
3. Write unit tests for all modules
4. Manual testing of full flow
5. Create PR, merge to main

### Phase 2: Approval Workflow (Separate Roadmap)
1. Monitor TUI with Rich/Textual
2. Challenge code mechanism
3. Event streaming from daemon

### Phase 3: CI/CD Hardening (Separate Roadmap)
1. Integration tests
2. Coverage thresholds
3. CI workflow updates

---

## Success Metrics

### Launch Metrics
- [x] `safeshell daemon start` succeeds
- [x] `safeshell daemon status` shows running
- [x] Git commit on main branch is blocked
- [x] Git commit on feature branch succeeds
- [x] All tests pass (75 tests)

### Ongoing Metrics
- Test coverage > 80% - To measure
- No MyPy errors - To verify
- No Ruff errors ✅
- No Bandit warnings - To verify

---

## Learnings

### Implementation Notes

1. **Pydantic field/method collision**: `error` field conflicted with `error()` classmethod in DaemonResponse. Renamed to `error_message`.

2. **YAML enum serialization**: Use `model_dump(mode="json")` for proper primitive type serialization.

3. **Health check noise**: Wrapper's `ensure_daemon_running()` makes test connections that appear as errors. Handle "Connection closed" at debug level.

4. **Async exception handling**: `contextlib.suppress` doesn't work with await. Use try-except with file-level noqa.

5. **BrokenPipeError in finally**: Wrap `writer.wait_closed()` in try-except for early client disconnects.
