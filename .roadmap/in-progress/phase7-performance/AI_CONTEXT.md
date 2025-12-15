# Phase 7: Performance Optimization - AI Context

**Purpose**: AI agent context document for implementing Phase 7: Performance Optimization

**Scope**: Eliminate command overhead through daemon-based execution

**Current Status**: PR4-6 Complete, PR7 (Daemon-Based Execution) is highest priority

---

## Quick Links for AI Agents

| Document | Purpose |
|----------|---------|
| **[Architecture Proposal](../../../docs/architecture-proposal.html)** | Detailed design with diagrams for PR7 |
| **[PROGRESS_TRACKER.md](./PROGRESS_TRACKER.md)** | Current status and requirements |
| **[docs/](../../../docs/)** | Project documentation |

---

## Current State (Post PR4-6)

### What's Complete
- **Structured Python Conditions** - All 9 condition types implemented as Pydantic models
- **Pure Python Evaluation** - No bash subprocess spawning for conditions
- **Condition Performance** - Evaluation is <0.1ms (was 5-20ms)

### The Remaining Problem
Even with fast conditions, every command pays **~250ms Python startup overhead**:

```
User: "ls"
  → Bash shim intercepts
  → Spawns NEW Python process (safeshell-wrapper)  ← 250ms!
  → Python imports modules
  → Wrapper connects to daemon
  → Daemon evaluates (fast, ~1ms)
  → Wrapper executes command
  → Wrapper exits

User: "git status"
  → Spawns ANOTHER new Python process  ← 250ms AGAIN!
  → Same cycle repeats...
```

The daemon is warm (modules loaded), but we spawn a new Python wrapper for every command.

---

## PR7: Daemon-Based Execution

### The Solution
Move command execution INTO the daemon. The shim becomes pure socket client (no Python).

```
Current: Shim → Python Wrapper (250ms) → Daemon → Wrapper executes
New:     Shim → Daemon evaluates AND executes (via fork) → Results
```

### Requirements

| Requirement | Target |
|-------------|--------|
| Command overhead | **< 1ms** |
| `ls` command total | **< 1ms** |
| Logging for allowed commands | **Minimal (DEBUG only)** |
| Shim implementation | **No Python** (bash + socat) |

### Key Files to Modify

| File | Changes |
|------|---------|
| `src/safeshell/models.py` | Add `RequestType.EXECUTE`, response fields for stdout/stderr/exit_code |
| `src/safeshell/daemon/manager.py` | Add `_handle_execute()` method |
| `src/safeshell/daemon/executor.py` | NEW: Fork, capture output, return results |
| `src/safeshell/shims/safeshell-check` | Bash client for socket I/O |
| `src/safeshell/shims/safeshell-shim` | Update to use bash client |
| `src/safeshell/shims/init.bash` | Update builtin overrides to use bash client |

### Protocol Changes

**New Request Type**: `execute`
```json
{
    "type": "execute",
    "command": "ls -la",
    "working_dir": "/home/user/project",
    "env": {"PATH": "...", "HOME": "..."},
    "execution_context": "human"
}
```

**New Response Format**:
```json
{
    "success": true,
    "decision": "allow",
    "executed": true,
    "exit_code": 0,
    "stdout": "file1.txt\nfile2.txt\n",
    "stderr": "",
    "execution_time_ms": 5
}
```

### Implementation Steps

1. **Protocol** - Add `RequestType.EXECUTE` and response fields
2. **Executor** - Create `daemon/executor.py` with fork/exec logic
3. **Manager** - Add `_handle_execute()` that evaluates then executes
4. **Bash Client** - Create `safeshell-check` bash script (socket I/O only)
5. **Shims** - Update to use bash client instead of Python wrapper
6. **Logging** - Reduce verbosity for allowed commands (DEBUG level)
7. **Tests** - Add tests for execution flow
8. **Benchmark** - Verify <1ms overhead

### Open Questions

See [Architecture Proposal](../../../docs/architecture-proposal.html) Section 8 for:
1. TTY handling for interactive commands
2. Environment inheritance (daemon env vs request env)
3. Streaming vs buffered output
4. Timeout handling for long-running commands

---

## Key Technical Context

### Why Fork?
The daemon uses `os.fork()` to create a child process for command execution:
- Fork is fast (~1-5ms on Linux)
- Child inherits daemon's Python environment (no startup cost)
- Child can `chdir` to working directory and `exec` the command
- Parent daemon continues serving other requests

### Why Not Keep Python Wrapper?
- Python startup is ~100ms minimum
- Module imports add another ~150ms
- This happens for EVERY command
- The daemon already has Python warm - use it!

### Logging Requirements
For allowed commands, logging should be minimal:
- **DEBUG**: Socket connection, evaluation result
- **INFO**: Only for DENY or REQUIRE_APPROVAL
- **No events published** for routine allowed commands (reduces overhead)

---

## Files Reference

### Core Implementation
```
src/safeshell/
├── daemon/
│   ├── manager.py      # Add _handle_execute()
│   ├── executor.py     # NEW: Fork and execute
│   └── server.py       # No changes needed
├── models.py           # Add EXECUTE request type
└── shims/
    ├── safeshell-check # Bash socket client
    ├── safeshell-shim  # Update to use bash client
    └── init.bash       # Update builtin overrides
```

### Tests
```
tests/
├── daemon/
│   ├── test_manager.py    # Add execute tests
│   └── test_executor.py   # NEW: Executor tests
└── shims/
    └── test_integration.py # End-to-end tests
```

---

## Success Criteria

- [ ] `ls` command completes in <1ms overhead
- [ ] No Python process spawned for command evaluation
- [ ] Daemon forks and executes approved commands
- [ ] Shim is pure bash (no Python imports)
- [ ] Allowed commands produce no INFO-level logs
- [ ] All existing tests pass
- [ ] New tests for execution flow
