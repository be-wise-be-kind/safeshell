# SafeShell Architecture Review

**Purpose**: Comprehensive architecture analysis of SafeShell POC for production readiness assessment

**Scope**: Daemon, Rules Engine, Shim System, Approval Workflow, Module Dependencies, Technical Debt

---

## Executive Summary

SafeShell demonstrates a well-architected command interception system with clear separation of concerns. The codebase shows evidence of thoughtful design decisions and consistent patterns throughout.

### Key Strengths
- Clean module boundaries with minimal coupling
- Consistent use of Pydantic for data validation
- Proper async/await patterns in daemon and events
- Comprehensive error handling with custom exception hierarchy
- Good test coverage foundation (51%+)

### Key Weaknesses
- Dual protection paths (shims vs hooks) add complexity
- Blocking approval flow may impact UX for rapid command sequences
- No rule caching across evaluations
- Limited observability/metrics infrastructure

### Overall Assessment
The architecture is production-ready with minor improvements needed. The POC achieved its goals of validating the interception approach while maintaining code quality.

---

## Daemon Architecture

### Current Implementation

The daemon uses Python's asyncio with Unix domain sockets for IPC. Two separate sockets serve different purposes:

- **daemon.sock**: Command evaluation requests from shell wrapper
- **monitor.sock**: Event streaming to Monitor TUI

**Key Files:**
- `src/safeshell/daemon/server.py` - Main server with connection handlers
- `src/safeshell/daemon/manager.py` - Rule loading and command evaluation
- `src/safeshell/daemon/protocol.py` - JSON lines message format
- `src/safeshell/daemon/lifecycle.py` - PID/socket management
- `src/safeshell/daemon/approval.py` - Approval request state management
- `src/safeshell/daemon/events.py` - Event publisher for monitor communication
- `src/safeshell/daemon/monitor.py` - Monitor connection handler

### Design Rationale

**Asyncio over threading/multiprocessing:**
- Efficient handling of many concurrent connections with low overhead
- Single-threaded avoids locking complexity for shared state
- Python's asyncio is mature and well-supported

**Unix sockets over TCP:**
- Security: No network exposure, file permissions control access
- Performance: Lower latency than TCP loopback
- Simplicity: No port management or binding issues

**Separate monitor socket:**
- Isolates event streaming from command evaluation path
- Prevents slow monitors from blocking command processing
- Enables future multi-monitor support

### Strengths

1. **Clean connection lifecycle**: `DaemonServer` properly handles setup, signal handlers, and graceful shutdown
2. **Request routing**: `RuleManager.process_request()` cleanly dispatches by request type
3. **Event-driven architecture**: `EventBus` provides clean pub/sub for monitor updates
4. **Proper error isolation**: Connection errors don't crash the daemon

### Weaknesses

1. **Rules reload per-request**: `load_rules()` is called for every evaluation (line 131 in manager.py). This is correct for picking up rule changes but has overhead.

2. **No connection pooling or limits**: The daemon accepts unlimited connections without backpressure.

3. **Limited daemon metrics**: Only tracks uptime and command count; no latency percentiles, error rates, or rule evaluation timing.

### Alternatives Considered

| Alternative | Trade-offs |
|-------------|------------|
| Threading | Simpler code but GIL limits parallelism; need locks for shared state |
| Multiprocessing | True parallelism but complex IPC; overkill for CPU-light I/O |
| HTTP/REST | More tooling available but higher overhead; TCP exposure |
| gRPC | Type-safe protocol but heavy dependency; complexity overkill |

### Recommendations

1. **Add rule caching**: Cache loaded rules with file modification time check; invalidate on change
2. **Add connection limits**: Implement max connections and queue depth
3. **Add metrics collection**: Track evaluation latency, rule match counts, approval times
4. **Consider health endpoint**: Simple status endpoint for monitoring integration

---

## Rules Engine

### Current Implementation

YAML-based rule configuration with bash subprocess conditions. Rules are loaded from two locations:

1. **Global rules**: `~/.safeshell/rules.yaml` (user's protections)
2. **Repo rules**: `.safeshell/rules.yaml` (project-specific, additive only)

**Key Files:**
- `src/safeshell/rules/schema.py` - Pydantic models: `Rule`, `RuleAction`, `RuleContext`
- `src/safeshell/rules/evaluator.py` - `RuleEvaluator` with command index and condition evaluation
- `src/safeshell/rules/loader.py` - YAML loading and rule merging
- `src/safeshell/rules/defaults.py` - Default rules for `safeshell init`

### Design Rationale

**YAML over JSON/TOML:**
- Human-readable and familiar to developers
- Supports comments for documentation
- Rich ecosystem of editors and linters

**Bash conditions over Python expressions:**
- Leverages existing shell scripting knowledge
- Allows complex logic (grep, git commands, etc.)
- Security concern is mitigated by user-controlled config

**Command index for fast-path:**
- O(1) lookup for commands not in any rule
- Majority of commands pass through without condition evaluation

### Strengths

1. **Fast-path optimization**: Commands not in any rule skip evaluation entirely (`evaluator.py:69-76`)
2. **Flexible conditions**: Bash subprocess allows arbitrary logic with environment variables ($CMD, $ARGS, $PWD)
3. **Configurable timeout**: Conditions timeout to prevent hanging (default 100ms)
4. **Clear precedence**: Most restrictive rule wins (DENY > REQUIRE_APPROVAL > REDIRECT > ALLOW)
5. **Context-aware**: Rules can target AI-only, human-only, or both

### Weaknesses

1. **Subprocess overhead**: Each bash condition spawns a process. Multiple conditions compound this cost.

2. **No condition result caching**: Same condition on same command re-executes each time.

3. **Security surface**: Bash execution from YAML config requires trust in config file source.

4. **Limited rule validation**: Schema validates structure but not condition syntax.

### Alternatives Considered

| Alternative | Trade-offs |
|-------------|------------|
| Python expressions | Safer sandboxing via RestrictedPython, but less flexible |
| Custom DSL | Type-safe conditions but learning curve; maintenance burden |
| Lua/Starlark | Good sandboxing but adds dependency; less familiar |
| Regex-only | Simple but insufficient for complex matching logic |

### Recommendations

1. **Add condition caching**: Cache (command, condition) -> result for repeated commands
2. **Add rule validation command**: `safeshell rules validate` to check syntax and test rules
3. **Add rule profiling**: Time each condition execution for optimization insights
4. **Document security model**: Clarify that rules.yaml must be user-controlled

---

## Shim System

### Current Implementation

Symlink-based command interception with shell function overrides for builtins:

1. **External commands** (git, rm, etc.): Symlinks in `~/.safeshell/shims/` pointing to `safeshell-shim` script
2. **Shell builtins** (cd, source, eval, echo): Function overrides in `init.bash`

**Key Files:**
- `src/safeshell/shims/manager.py` - Shim creation, removal, and refresh
- `src/safeshell/shims/init.bash` - Shell initialization with function overrides
- `src/safeshell/shims/safeshell-shim` - Universal shim script (symlink target)

### Design Rationale

**Symlinks over wrapper scripts:**
- Single shim script handles all commands
- Easy to add/remove by creating/deleting symlinks
- Binary name passed via `$0` allows shim to know what command was invoked

**PATH prepending:**
- Shim directory at front of PATH intercepts before real binaries
- Non-destructive: real commands still accessible via full path

**Function overrides for builtins:**
- Shell builtins cannot be intercepted via PATH
- Functions take precedence over builtins in bash/zsh
- Fail-open: if daemon unavailable, commands proceed

### Strengths

1. **Transparent interception**: Commands work normally when allowed
2. **Minimal overhead**: Symlink resolution is fast
3. **Fail-open design**: Shell remains usable if daemon is down
4. **Tool detection**: `init.bash` detects Claude Code (`$CLAUDECODE`) and skips shim loading to avoid double-checking

### Weaknesses

1. **Bash/zsh only**: Function overrides use bash syntax; other shells need adaptation

2. **PATH dependency**: User must source init.bash for protection to work

3. **No automatic refresh**: Rule changes don't auto-update shims; requires `safeshell refresh`

4. **Potential conflicts**: User-defined functions with same names would be overridden

### Alternatives Considered

| Alternative | Trade-offs |
|-------------|------------|
| LD_PRELOAD | Intercepts all exec; invasive, complex, platform-specific |
| Shell alias | Easy to bypass with backslash or command builtin |
| PTY wrapper | Full control but high overhead; complex implementation |
| FUSE filesystem | Powerful but heavyweight; requires kernel support |

### Recommendations

1. **Add zsh-specific testing**: Verify function override syntax works in zsh
2. **Auto-refresh on rule change**: Watch rules.yaml and refresh shims automatically
3. **Conflict detection**: Warn if user has existing functions with same names
4. **Document BASH_ENV**: Note that non-interactive shells need BASH_ENV set

---

## Approval Workflow

### Current Implementation

Blocking approval flow where commands requiring approval pause execution until human decision via Monitor TUI:

1. Wrapper sends command to daemon
2. Daemon evaluates rules, returns REQUIRE_APPROVAL
3. Daemon sends "waiting for approval" intermediate response to wrapper
4. Daemon publishes `approval_needed` event to monitors
5. Wrapper displays waiting message and blocks
6. Human clicks Approve/Deny in Monitor TUI
7. Daemon resolves approval and sends final response
8. Wrapper allows/blocks command

**Key Files:**
- `src/safeshell/wrapper/shell.py` - Shell wrapper entry point
- `src/safeshell/wrapper/client.py` - Synchronous daemon client
- `src/safeshell/daemon/approval.py` - `ApprovalManager` with pending requests and futures

### Design Rationale

**Blocking over async/polling:**
- Simple and reliable: command doesn't proceed until decision
- Clear user experience: waiting message visible
- No risk of missing approval window

**Timeout with auto-deny:**
- Prevents indefinite hanging (default 5 minutes)
- Safe default: uncertain becomes blocked
- Configurable per-deployment

**Intermediate response protocol:**
- Wrapper receives "waiting" message immediately
- Can display status to user while blocking
- Final response arrives when decision is made

### Strengths

1. **Clean state management**: `ApprovalManager` uses asyncio futures for waiting
2. **Timeout handling**: Automatic deny after configurable timeout
3. **Approval ID tracking**: Unique IDs prevent approval of wrong command
4. **Event visibility**: Monitor TUI shows pending approvals in real-time

### Weaknesses

1. **Blocking nature**: Rapid command sequences each require separate approval wait

2. **No batch approval**: Cannot approve "all git commands" or similar patterns

3. **Single monitor support**: Currently assumes one monitor; multiple monitors could cause race

4. **No approval persistence**: Pending approvals lost on daemon restart

### Alternatives Considered

| Alternative | Trade-offs |
|-------------|------------|
| Non-blocking | Complex state; risk of missing approval |
| Queue-based | More flexible but harder to reason about |
| Pre-approval | Approve patterns in advance; reduces safety |
| Time-limited allow | Allow for N minutes after approval; reduces friction |

### Recommendations

1. **Add batch approval option**: "Approve all from this rule for 5 minutes"
2. **Persist pending approvals**: Survive daemon restart for long-running approvals
3. **Add approval audit log**: Record all approval decisions for review
4. **Multi-monitor coordination**: Define behavior when multiple monitors connected

---

## Module Dependencies

### Dependency Graph

```
                              safeshell.cli
                                   │
           ┌───────────────────────┼───────────────────────┐
           │                       │                       │
           v                       v                       v
    safeshell.daemon         safeshell.shims        safeshell.wrapper
           │                       │                       │
           │                       │                       │
           v                       v                       v
    safeshell.rules          safeshell.rules        safeshell.daemon
           │                                               │
           │                                               │
           v                                               v
    safeshell.config                               safeshell.config
           │
           v
    safeshell.daemon.lifecycle
           │
           v
    safeshell.exceptions
           │
           v
    safeshell.models
```

### Module Responsibilities

| Module | Responsibility |
|--------|---------------|
| `cli` | Main entry point, subcommand routing |
| `daemon` | Background service, IPC, events |
| `rules` | YAML schema, evaluation, loading |
| `shims` | Symlink management, shell init |
| `wrapper` | Shell wrapper, client communication |
| `monitor` | TUI app, widgets, daemon client |
| `hooks` | AI tool integrations (Claude Code) |
| `events` | Event types, pub/sub bus |
| `config` | Configuration loading, validation |
| `models` | Shared data models |
| `exceptions` | Custom exception hierarchy |

### Analysis

**Coupling Assessment:**
- Modules are loosely coupled through well-defined interfaces
- Most dependencies flow downward (high-level -> low-level)
- `models.py` and `exceptions.py` serve as shared foundations

**Cohesion Assessment:**
- Each module has a clear, focused purpose
- Internal cohesion is high within modules

**Circular Dependencies:**
- None detected
- Some `TYPE_CHECKING` imports used appropriately to avoid runtime circularity

**Interface Clarity:**
- Public APIs are well-defined via `__all__` in `__init__.py` files
- Docstrings present on public functions and classes

### Recommendations

1. **Consider extracting common utilities**: Socket operations, path utilities could be shared
2. **Add interface contracts**: Define abstract base classes for key interfaces
3. **Document public vs internal APIs**: Mark internal modules/functions explicitly

---

## Technical Debt Catalog

### High Priority

*None identified.* The codebase is clean with no TODO/FIXME comments, no unused imports, and consistent patterns.

### Medium Priority

#### DEBT-001: Backward Compatibility Alias

**Location**: `src/safeshell/daemon/manager.py:282`
**Severity**: Medium
**Description**: `PluginManager = RuleManager` alias maintained for backward compatibility
**Rationale**: Plugin system was replaced with rules system; alias prevents breaking changes
**Impact**: Confusion for new developers; suggests old system still exists
**Resolution**: Remove alias, update any references
**Effort**: Low (search and replace)

#### DEBT-002: Event Data Type Flexibility

**Location**: `src/safeshell/events/types.py:97`
**Severity**: Medium
**Description**: `Event.data` is `dict[str, Any]` rather than typed union
**Rationale**: Simplifies serialization and allows flexible event data
**Impact**: Type safety reduced; consumers must cast or validate
**Resolution**: Use discriminated union or generic Event[T]
**Effort**: Medium (refactor all event creation/consumption)

### Low Priority

#### DEBT-003: Wrapper Client Timeout Hardcoded

**Location**: `src/safeshell/wrapper/client.py:107`
**Severity**: Low
**Description**: 600-second socket timeout hardcoded (10 minutes for approval)
**Rationale**: Must exceed approval timeout (default 5 min) with margin
**Impact**: Not configurable; may be too long for some deployments
**Resolution**: Derive from config.approval_timeout_seconds
**Effort**: Low

#### DEBT-004: Development Path Discovery

**Location**: `src/safeshell/shims/init.bash:49-52`
**Severity**: Low
**Description**: Hardcoded development path check for poetry wrapper
**Rationale**: Enables development without install
**Impact**: Only affects developers; harmless in production
**Resolution**: Remove or make configurable via environment variable
**Effort**: Low

---

## Recommendations Summary

### Immediate (PR2-PR4 Scope)

1. Remove `PluginManager` backward compatibility alias
2. Make wrapper client timeout derived from config
3. Remove hardcoded development path in init.bash

### Near-Term (Future PRs)

1. Add rule caching with file modification time check
2. Add `safeshell rules validate` command
3. Add metrics collection (latency, error rates)
4. Add approval audit logging
5. Document security model for rules.yaml

### Long-Term (Future Phases)

1. Multi-shell support (fish, nushell)
2. Batch approval patterns
3. Rule condition profiling and optimization
4. Distributed daemon support for team environments

---

## Conclusion

SafeShell's architecture successfully validates the command interception approach with a clean, maintainable codebase. The identified technical debt items are minor and the recommendations focus on optimization and feature enhancement rather than fundamental architectural changes.

The codebase is ready for production use with the understanding that the identified improvements can be addressed incrementally through the remaining PRs in this phase.
