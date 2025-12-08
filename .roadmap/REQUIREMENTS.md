# SafeShell Requirements Document

**Purpose**: Living requirements document, updated after each major phase with learnings

**Last Updated**: After PR-2 completion (Architecture Pivot Decision)

---

## Executive Summary

SafeShell is a command-line safety layer for AI coding assistants. AI tools are configured to use SafeShell as their shell. SafeShell intercepts all commands, evaluates them against configurable rules, and enforces decisions before execution.

The system has three core protection mechanisms:
1. **Automatic denial** of clearly prohibited operations (e.g., `rm -rf /`)
2. **Soft-delete** of files to a recoverable trash instead of permanent deletion
3. **Human approval** for risky-but-legitimate operations via a separate monitor terminal

The approval mechanism is central to SafeShell's value proposition. Risky operations display an approval prompt in a Monitor TUI that the AI cannot see. The user clicks Approve/Deny buttons (or uses keyboard shortcuts) to make decisions. This provides true human-in-the-loop control without requiring containers or VMs.

**Key architectural decision:** SafeShell operates as a shell wrapper, not command shims. AI tools set `SHELL=/path/to/safeshell`. This approach:
- Catches all commands regardless of how they're invoked
- Requires no PATH manipulation or shim maintenance
- Cannot be bypassed by using absolute paths (`/bin/rm`)
- Automatically supports new commands when rules are added

The system assumes a cooperative (non-adversarial) AI agent and focuses on preventing mistakes rather than containing malicious behavior.

---

## ⚠️ ARCHITECTURE PIVOT: Config-Based Rules

**Decision Date**: After PR-2 completion

**Change**: The Python plugin system is being replaced with YAML configuration files.

**Rationale**:
1. **Simpler**: Adding rules is editing YAML, not writing Python
2. **More flexible**: Bash conditions can check anything (git branch, file paths, etc.)
3. **Repo-level rules**: Easy to support `.safeshell/rules.yaml` per project
4. **Auditable**: All rules visible in config, no code to read

**Impact**:
- `src/safeshell/plugins/` is deprecated
- New `src/safeshell/rules/` module handles rule evaluation
- Rules defined in `~/.safeshell/rules.yaml` (global) and `.safeshell/rules.yaml` (repo)

See `.roadmap/in-progress/approval-workflow/AI_CONTEXT.md` for full architecture details.

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

### Config-Based Rules (NEW)

All policy logic is defined in YAML configuration files, not Python code. This provides:
- Easy rule creation (edit YAML, no Python)
- Global rules (`~/.safeshell/rules.yaml`) for user-wide protections
- Repo rules (`.safeshell/rules.yaml`) for project-specific additions
- Bash conditions for complex logic (git branch detection, path resolution, etc.)

---

## System Architecture

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
│  Daemon (asyncio)           │  ← Long-running
│  - Rule evaluator           │
│  - Event publishing         │
│  - Approval management      │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Rules (YAML config)        │
│  - ~/.safeshell/rules.yaml  │
│  - .safeshell/rules.yaml    │
│  - Bash conditions          │
└─────────────────────────────┘
```

### Rule Evaluation Flow

```
1. Command received (e.g., "git commit -m test")
2. Extract executable ("git")
3. Is "git" in any rule's commands list? No → ALLOW (fast path)
4. For each matching rule:
   a. Check directory pattern (if specified)
   b. Run bash conditions (all must pass)
   c. If all match → apply action (deny/require_approval/redirect)
5. No rules matched → ALLOW
6. Multiple rules matched → most restrictive wins (deny > require_approval > redirect)
```

---

## Rule Configuration

### Rule Schema

```yaml
rules:
  - name: "rule-identifier"           # Unique name for logging
    commands: ["git", "rm"]           # Target executables (fast-path)
    directory: "regex"                # Optional: working directory pattern
    conditions:                       # Optional: bash conditions
      - "bash statement exits 0 if true"
    action: deny | require_approval | redirect
    allow_override: true | false      # For deny: can user approve anyway?
    redirect_to: "command $ARGS"      # For redirect: replacement command
    message: "User-facing message"    # Shown in denial/approval
```

### Available Variables

- `$CMD` - Full command string
- `$ARGS` - Arguments after executable
- `$PWD` - Current working directory

### Example Rules

```yaml
# Block git commit on protected branches
- name: block-commit-protected
  commands: ["git"]
  conditions:
    - "echo '$CMD' | grep -qE '^git\\s+commit'"
    - "git branch --show-current | grep -qE '^(main|master|develop)$'"
  action: deny
  message: "Cannot commit to protected branch. Create a feature branch."

# Redirect rm to trash
- name: redirect-rm-to-trash
  commands: ["rm"]
  action: redirect
  redirect_to: "trash $ARGS"
  message: "Redirecting to trash for safety"

# Block reading SSH keys
- name: block-read-ssh
  commands: ["cat", "less", "head", "tail"]
  conditions:
    - "echo '$CMD' | grep -qE '\\.ssh'"
  action: deny
  message: "Cannot read SSH keys"
```

### Global vs Repo Rules

```
~/.safeshell/rules.yaml     # Global - YOUR protections (loaded first)
.safeshell/rules.yaml       # Repo - project additions (merged, additive only)
```

**Security**: Repo rules can only ADD restrictions, never relax global rules. A malicious repo cannot disable your protections.

---

## System Components

### Component 1: Shell Wrapper ✅ (MVP Complete)

**Implementation**: `src/safeshell/wrapper/shell.py`

SafeShell acts as a shell wrapper. AI tools are configured to use SafeShell as their shell. SafeShell intercepts every command, checks policy with the daemon, and delegates execution to the user's real shell.

### Component 2: Daemon ✅ (MVP Complete)

**Implementation**: `src/safeshell/daemon/`

A background process that:
- Receives evaluation requests from wrapper
- Loads and evaluates rules
- Emits events to connected monitor clients
- Manages pending approvals

### Component 3: Monitor (Phase 2 - In Progress)

A terminal user interface (TUI) for real-time visibility and human approval workflow.

```
┌─────────────────────┬─────────────────────┬─────────────────────┐
│  Debug/Log Pane     │  Command History    │  Approval Prompt    │
│                     │                     │                     │
│  [DEBUG] Rule...    │  ✓ echo hello       │  ⚠️ APPROVAL NEEDED │
│  [INFO] Evaluating  │  ✗ git commit (blk) │                     │
│  [DEBUG] Result...  │  ✓ ls -la           │  git push --force   │
│                     │  ? git push (pend)  │  to origin/main     │
│                     │                     │                     │
│                     │                     │  [Approve] [Deny]   │
│                     │                     │  Reason: ________   │
└─────────────────────┴─────────────────────┴─────────────────────┘
```

### Component 4: Rule System (Replacing Plugins)

**Implementation**: `src/safeshell/rules/`

- `schema.py` - Pydantic models for Rule, RuleSet
- `loader.py` - Load and merge rule files
- `evaluator.py` - Rule matching and bash condition execution

---

## Configuration

### Configuration File Location

Primary: `~/.safeshell/config.yaml`

```yaml
# Behavior when daemon is unreachable
unreachable_behavior: fail_closed  # or fail_open

# Shell to delegate commands to
delegate_shell: /bin/bash

# Log level
log_level: INFO

# Approval settings (Phase 2)
approval:
  timeout_seconds: 300
```

### Rules File Location

Global: `~/.safeshell/rules.yaml`
Per-repo: `.safeshell/rules.yaml`

---

## Implementation Phases

### Phase 1: MVP - Git Branch Protection ✅ COMPLETE

**Goal**: Block git commits on protected branches

**Delivered**:
- Daemon with start/stop/status/restart commands
- Shell wrapper for AI tool integration
- Plugin system with git-protect plugin (being replaced)
- Configuration via ~/.safeshell/config.yaml
- 75 unit tests passing

### Phase 2: Approval Workflow with Monitor TUI (In Progress)

**Progress**: 33% (2/6 PRs complete)

**PR Status**:
- ✅ PR-1: Event System Foundation (merged)
- ✅ PR-2: Daemon Event Publishing (merged)
- 🔴 PR-2.5: Config-Based Rules Architecture ← **NEXT**
- 🔴 PR-3: Monitor TUI Shell
- 🔴 PR-4: Approval Protocol
- 🔴 PR-5: Integration and Polish

**Current Task (PR-2.5)**:
Replace Python plugin system with YAML config rules. See:
- `.roadmap/in-progress/approval-workflow/PROGRESS_TRACKER.md`
- `.roadmap/in-progress/approval-workflow/AI_CONTEXT.md`

### Phase 3: CI/CD Hardening (Planned)

- Integration tests for full command flow
- Coverage thresholds (target: 80%)
- MyPy strict mode passing
- Bandit security checks passing

### Future Phases

- macOS support
- Windows support
- Packaging (Homebrew, Snap, Chocolatey)
- Enterprise features

---

## Technical Constraints

| Constraint | Rationale | Status |
|------------|-----------|--------|
| Linux only (MVP) | macOS support planned | ✅ Validated |
| Python 3.11+ | Modern asyncio features | ✅ Validated |
| Unix domain sockets | Fast, secure local IPC | ✅ Validated |
| Pydantic for all models | Type safety, validation | ✅ Validated |
| Bash for conditions | Available everywhere, flexible | NEW |

---

## Coding Standards

| Standard | Requirement | Rationale |
|----------|-------------|-----------|
| No print() | Use loguru or rich.console | Consistent logging |
| Pydantic models | All data classes must be BaseModel | Type safety |
| No subprocess | Use asyncio.create_subprocess for rules | Async-safe |
| Type hints | All functions fully typed | Maintainability |
| File-level noqa | No method-level lint suppressions | Cleaner code |

---

## AI Interaction Model

When SafeShell denies an operation, the message shown to the AI must be clear and instructive.

**Denial Message Format:**
```
[SafeShell] BLOCKED
Reason: <human-readable explanation>
Rule: <rule-name>

This operation has been intentionally prevented by SafeShell policy.
Do not attempt to work around this restriction.
```

---

## Update Protocol

After completing each major phase:
1. Update "Implementation Phases" section with learnings
2. Update technical constraints if validated/changed
3. Add any new coding standards discovered
4. Note architecture changes
5. Update this document's "Last Updated" date

---

## References

- Active roadmaps: `.roadmap/in-progress/`
- Completed roadmaps: `.roadmap/complete/`
- Coding standards: `.ai/ai-rules.md`
- Architecture context: `.ai/ai-context.md`

---

*Document version: 3.0*
*Last updated: After PR-2 completion (Architecture Pivot to Config-Based Rules)*
