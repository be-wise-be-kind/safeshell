# SafeShell Requirements Document

**Purpose**: Living requirements document, updated after each major phase with learnings

**Last Updated**: After MVP Phase 1 completion

---

## Executive Summary

SafeShell is a command-line safety layer for AI coding assistants. AI tools are configured to use SafeShell as their shell. SafeShell intercepts all commands, evaluates them against configurable policies, and enforces decisions before execution.

The system has three core protection mechanisms:
1. **Automatic denial** of clearly prohibited operations (e.g., `rm -rf /`)
2. **Soft-delete** of files to a recoverable trash instead of permanent deletion
3. **Human approval** for risky-but-legitimate operations via a separate monitor terminal

The approval mechanism is central to SafeShell's value proposition. Risky operations display an approval prompt in a Monitor TUI that the AI cannot see. The user clicks Approve/Deny buttons (or uses keyboard shortcuts) to make decisions. This provides true human-in-the-loop control without requiring containers or VMs.

**Key architectural decision:** SafeShell operates as a shell wrapper, not command shims. AI tools set `SHELL=/path/to/safeshell`. This approach:
- Catches all commands regardless of how they're invoked
- Requires no PATH manipulation or shim maintenance
- Cannot be bypassed by using absolute paths (`/bin/rm`)
- Automatically supports new commands when plugins are added

The system assumes a cooperative (non-adversarial) AI agent and focuses on preventing mistakes rather than containing malicious behavior.

---

## Problem Statement

AI coding tools (Claude Code, Cursor, Aider, GitHub Copilot CLI, etc.) execute shell commands on behalf of users. These tools can accidentally:

- Delete critical files or directories
- Expose sensitive data (SSH keys, environment variables, credentials)
- Execute destructive git operations (force push, hard reset)
- Modify system files or permissions inappropriately
- Perform irreversible operations without user awareness

Users need a lightweight mechanism to establish guardrails without abandoning their preferred terminals, shells, or development environments. Container-based solutions are rejected as too cumbersome for typical adoption.

---

## Core Design Principles

### Cooperative Agent Assumption

The system assumes AI tools are cooperative and will respect clear policy denials. When SafeShell blocks an operation and explains why, the AI is expected to comply rather than attempt bypass. This assumption dramatically simplifies the security model:

- The goal is preventing accidents, not containing adversaries
- Clear messaging to the AI is sufficient; cryptographic enforcement is unnecessary
- Soft boundaries with good feedback are preferable to hard boundaries with poor UX

### Transparency to Existing Tooling

Users must not be forced to change their terminal emulator (Warp, iTerm, Windows Terminal, etc.) or abandon their preferred shell (bash, zsh, fish, PowerShell). SafeShell operates as an intermediary layer that existing tools can point to.

### Plugin-Only Architecture

The SafeShell core provides only plumbing: command interception, plugin loading, event routing, and the monitor interface. ALL policy logic resides in plugins. SafeShell ships with a set of default plugins that provide sensible protections out of the box, but users can disable, configure, or replace any of them.

---

## System Architecture (Validated in MVP)

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
│  - Event publishing         │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Plugins (Python modules)   │
│  - git-protect (MVP)        │
│  - rm-protect (planned)     │
│  - path-protect (planned)   │
└─────────────────────────────┘
```

### MVP Validation Results

The daemon-based architecture was validated in Phase 1:
- **Startup overhead is minimal**: Wrapper just does IPC, no Python module loading per-command
- **Plugin system is clean**: ABC with matches/evaluate pattern works well
- **JSON lines protocol**: Simple and debuggable, no issues
- **Auto-start mechanism**: Works reliably from wrapper

---

## System Components

SafeShell consists of four core components, all of which are essential:

1. **Shell Wrapper** - Intercepts ALL commands as the shell itself
2. **Daemon** - Loads plugins, evaluates policy, manages trash, coordinates approval
3. **Monitor** - TUI for real-time visibility and human approval workflow
4. **Plugin System** - All policy logic; core is policy-agnostic

The monitor is NOT optional. It provides the human-in-the-loop approval mechanism that is central to SafeShell's protection model.

### Component 1: Shell Wrapper ✅ (MVP Complete)

**Implementation**: `src/safeshell/wrapper/shell.py`

SafeShell acts as a shell wrapper. AI tools are configured to use SafeShell as their shell. SafeShell intercepts every command, checks policy with the daemon, and delegates execution to the user's real shell.

**Shell wrapper behavior:**
1. Receive command (via `-c "command"`)
2. Connect to daemon (auto-start if needed)
3. Send command + context for policy evaluation
4. Handle response:
   - ALLOW: execute via delegate shell
   - DENY: print policy message, exit with error code
   - REQUIRE_APPROVAL: (Phase 2) wait for approval

**MVP Learnings:**
- Health check connections (ensure_daemon_running) cause "Connection closed" - handle gracefully at debug level
- Use plumbum for process spawning, not subprocess
- Fail-closed by default is the right choice

### Component 2: Daemon ✅ (MVP Complete)

**Implementation**: `src/safeshell/daemon/`

A background process that:
- Receives evaluation requests from wrapper
- Loads and manages plugins
- Routes requests to appropriate plugins
- Emits events to connected monitor clients (Phase 2)
- Manages pending approvals (Phase 2)

**Daemon IPC:**
- Unix domain socket at `~/.safeshell/daemon.sock`
- JSON lines protocol (newline-delimited JSON)
- Pydantic models for request/response validation

**MVP Learnings:**
- asyncio works well for the server
- Signal handlers for graceful shutdown are essential
- Double-fork for proper daemonization
- BrokenPipeError handling needed in finally blocks
- contextlib.suppress doesn't work with async await

### Component 3: Monitor (Phase 2 - Planned)

A terminal user interface (TUI) application that displays real-time activity from the daemon. Runs in a separate terminal from the AI workspace.

**Planned Features (Phase 2):**
- Three-pane layout: Debug logs | Command history | Approval prompt
- Mouse click support via Textual
- Approve/Deny buttons with optional reason text
- Reason text reported back to AI agent in denial message
- Keyboard shortcuts as alternative to mouse clicks

**Monitor TUI Design:**
```
┌─────────────────────┬─────────────────────┬─────────────────────┐
│  Debug/Log Pane     │  Command History    │  Approval Prompt    │
│                     │                     │                     │
│  [DEBUG] Plugin...  │  ✓ echo hello       │  ⚠️ APPROVAL NEEDED │
│  [INFO] Evaluating  │  ✗ git commit (blk) │                     │
│  [DEBUG] Result...  │  ✓ ls -la           │  git push --force   │
│                     │  ? git push (pend)  │  to origin/main     │
│                     │                     │                     │
│                     │                     │  [Approve] [Deny]   │
│                     │                     │                     │
│                     │                     │  Reason: ________   │
└─────────────────────┴─────────────────────┴─────────────────────┘
```

### Component 4: Plugin System ✅ (MVP Complete)

**Implementation**: `src/safeshell/plugins/`

All policy logic lives in plugins. The core SafeShell system is policy-agnostic.

**Plugin API:**
```python
class Plugin(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    def matches(self, ctx: CommandContext) -> bool:
        """Override for performance filtering."""
        return True

    @abstractmethod
    def evaluate(self, ctx: CommandContext) -> EvaluationResult: ...

    # Helpers
    def _allow(self, reason: str) -> EvaluationResult: ...
    def _deny(self, reason: str) -> EvaluationResult: ...
    def _require_approval(self, reason: str) -> EvaluationResult: ...
```

**MVP Plugin: git-protect**
- Blocks commits on main/master/develop branches
- Blocks force-push to protected branches
- Uses REQUIRE_APPROVAL for force-push (Phase 2 will activate this)

---

## Shipped Plugins (Planned)

### Plugin: git-protect ✅ (MVP Complete)

Guards against destructive git operations.

**Behaviors:**
- DENY: `git commit` on protected branches (main, master, develop)
- REQUIRE_APPROVAL: `git push --force` to protected branches (Phase 2)
- ALLOW: All other git operations

### Plugin: rm-protect (Future)

Protects against destructive file deletion.

**Behaviors:**
- DENY: `rm -rf /` and variations (catastrophic deletion - never allowed)
- REQUIRE_APPROVAL: Recursive deletion outside current working directory
- SOFT_DELETE: Deletion of paths matching configured patterns
- ALLOW: All other deletions

### Plugin: path-protect (Future)

Prevents read or write access to sensitive paths.

**Behaviors:**
- DENY: Any read/write operation on protected paths
- Protected paths: ~/.ssh/**, ~/.aws/**, **/.env*, **/*.pem, etc.

### Plugin: secrets-detect (Future)

Prevents commands that would expose secrets.

**Behaviors:**
- DENY: Commands that would print files containing secrets
- DENY: Commands that would expose secret environment variables

---

## Configuration

### Configuration File Location

Primary: `~/.safeshell/config.yaml`

**Current Schema (MVP):**
```yaml
# Behavior when daemon is unreachable
# fail_closed (default): block all commands
# fail_open: allow with warning
unreachable_behavior: fail_closed

# Shell to delegate commands to
delegate_shell: /bin/bash

# Log level
log_level: INFO
```

**Planned Additions (Future):**
```yaml
# Approval settings
approval:
  timeout_seconds: 300

# Trash settings
trash:
  directory: ~/.safeshell/trash
  retention_hours: 48

# Plugin configuration
plugins:
  git-protect:
    enabled: true
    config:
      protected_branches: [main, master, develop]
```

---

## AI Interaction Model

When SafeShell denies an operation, the message shown to the AI must be clear and instructive.

**Denial Message Format:**
```
[SafeShell] BLOCKED
Reason: <human-readable explanation>
Policy: <plugin-name>

This operation has been intentionally prevented by SafeShell policy.
Do not attempt to work around this restriction.
```

**Example (from MVP testing):**
```
[SafeShell] BLOCKED
Reason: Cannot commit directly to protected branch 'main'. Create a feature branch first.
Policy: git-protect

This operation has been intentionally prevented by SafeShell policy.
Do not attempt to work around this restriction.
```

---

## Platform Support

### Phase 1 (MVP) ✅
- Linux (x86_64) - Validated

### Phase 2+
- macOS (Apple Silicon and Intel) - Architecture supports it
- Windows (PowerShell integration) - Future

---

## Technical Constraints

| Constraint | Rationale | Status |
|------------|-----------|--------|
| Linux only (MVP) | macOS support planned but not tested | ✅ Validated |
| Python 3.11+ | Modern asyncio features required | ✅ Validated |
| Unix domain sockets | Fast, secure local IPC | ✅ Validated |
| Single daemon per user | Socket at ~/.safeshell/daemon.sock | ✅ Validated |
| Pydantic for all models | Type safety, validation | ✅ Validated |
| plumbum for execution | Cross-platform, no subprocess | ✅ Validated |
| loguru for logging | No print statements | ✅ Validated |

---

## Coding Standards

| Standard | Requirement | Rationale |
|----------|-------------|-----------|
| No print() | Use loguru or rich.console | Consistent logging |
| Pydantic models | All data classes must be BaseModel | Type safety |
| No subprocess | Use plumbum for execution | Cross-platform |
| Type hints | All functions fully typed (MyPy strict) | Maintainability |
| File-level noqa | No method-level lint suppressions | Cleaner code |

---

## Implementation Phases

### Phase 1: MVP - Git Branch Protection ✅ COMPLETE

**Goal**: Block git commits on protected branches

**Delivered**:
- Daemon with start/stop/status/restart commands
- Shell wrapper for AI tool integration
- Plugin system with git-protect plugin
- Configuration via ~/.safeshell/config.yaml
- 75 unit tests passing

**Learnings Applied**:
1. Health check connections need graceful handling (debug level, not warning)
2. File-level noqa comments preferred over inline
3. contextlib.suppress doesn't work with async await
4. Pydantic field names must not conflict with methods (error → error_message)
5. Use model_dump(mode="json") for YAML serialization

### Phase 2: Approval Workflow with Monitor TUI (Planned)

**Goal**: Risky operations require human approval via terminal UI

**Key Features**:
- Terminal UI (Textual) with mouse support
- Three-pane layout: Debug | History | Approval
- Approve/Deny buttons with optional reason text
- Reason text reported back to AI agent
- Event streaming from daemon to monitor
- Keyboard shortcuts for terminals without mouse support

### Phase 3: CI/CD Hardening (Planned)

**Goal**: Robust test coverage and CI pipeline

**Key Requirements**:
- Integration tests for full command flow
- Coverage thresholds (target: 80%)
- MyPy strict mode passing
- Bandit security checks passing

### Future Phases (Not Scheduled)

- rm-protect plugin (soft delete / trash)
- path-protect plugin (block access to sensitive paths)
- secrets-detect plugin (block commands exposing secrets)
- macOS support
- Windows support
- Packaging (Homebrew, Snap, Chocolatey)
- AI-assisted plugin creation (prompt-agent)
- Enterprise features (centralized policy, RBAC, audit logging)

---

## Open Questions (Deferred from Original Requirements)

These questions from the original requirements document remain open:

1. **Command parsing depth**: How deeply should SafeShell parse compound commands (`cmd1 && cmd2`, pipes)? MVP uses simple parsing.

2. **Watched commands cache**: For performance, should wrapper cache the set of watched executables? MVP evaluates all commands via daemon.

3. **Plugin priority/ordering**: When multiple plugins match, evaluation order? Currently: first-deny-wins.

4. **Windows architecture**: Shell wrapper approach needs adaptation for PowerShell.

5. **Bundled Python for plugins**: How does standalone executable load user Python plugins?

6. **Enterprise architecture**: How to design MVP abstractions to not preclude enterprise features?

---

## Update Protocol

After completing each major phase:
1. Update "Implementation Phases" section with learnings
2. Update technical constraints if validated/changed
3. Add any new coding standards discovered
4. Note architecture changes
5. Move resolved open questions to appropriate sections
6. Update this document's "Last Updated" date

---

## References

- Completed roadmaps: `.roadmap/complete/`
- Active roadmaps: `.roadmap/in-progress/`
- Planned roadmaps: `.roadmap/planning/`
- Coding standards: `.ai/ai-rules.md`
- Architecture context: `.ai/ai-context.md`

---

*Document version: 2.0*
*Last updated: After MVP Phase 1 completion*
