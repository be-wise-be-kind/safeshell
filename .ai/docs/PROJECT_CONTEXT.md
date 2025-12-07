# SafeShell - Project Context

**Purpose**: Command-line safety layer for AI coding assistants

**Scope**: Intercepts shell commands from AI tools, evaluates them against configurable policies, and enforces decisions before execution

**Overview**: SafeShell provides three core protection mechanisms: automatic denial of prohibited operations,
    soft-delete of files to recoverable trash, and human approval for risky operations via a separate monitor terminal

**Dependencies**: Python 3.11+, Poetry, Typer, Rich (for TUI)

**Exports**: CLI tool (`safeshell`), daemon process, monitor TUI, plugin system

**Related**: See requirements document in `.roadmap/safeshell/.roadmap/` for full specifications

**Implementation**: Shell wrapper architecture - AI tools set SHELL=/path/to/safeshell

---

## Project Purpose

SafeShell exists to prevent AI coding assistants from accidentally:
- Deleting critical files or directories
- Exposing sensitive data (SSH keys, environment variables, credentials)
- Executing destructive git operations (force push, hard reset)
- Modifying system files or permissions inappropriately
- Performing irreversible operations without user awareness

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Coding Tool                           │
│              (Claude Code, Cursor, etc.)                    │
│                                                             │
│              SHELL=/usr/local/bin/safeshell                 │
└──────────────────────────┬──────────────────────────────────┘
                           │ executes command
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      SafeShell                              │
│                                                             │
│  1. Receive full command string                             │
│  2. Parse executable and arguments                          │
│  3. Query daemon: any plugins watching this executable?     │
│  4. If no watchers → execute immediately via real shell     │
│  5. If watchers → evaluate policy via daemon                │
│  6. Based on decision: allow/deny/soft-delete/approval      │
└──────────────────────────┬──────────────────────────────────┘
                           │ if allowed
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              User's Real Shell (bash/zsh/fish)              │
└─────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. Shell Wrapper
- Acts as the shell for AI tools
- Intercepts every command
- Fast path for unwatched commands (< 5ms overhead)
- Delegates to user's real shell after policy evaluation

### 2. Daemon
- Loads and manages plugins
- Routes requests to appropriate plugins
- Maintains trash directory for soft-deleted files
- Emits events to connected monitor clients

### 3. Monitor (TUI)
- Real-time display of command evaluations
- Human approval workflow for risky operations
- Challenge code mechanism (AI cannot see approval codes)
- Built with Rich/Textual for terminal UI

### 4. Plugin System
- All policy logic resides in plugins
- Core is policy-agnostic
- Shipped plugins: rm-protect, path-protect, git-protect, secrets-detect
- User plugins in ~/.safeshell/plugins/

## Development Guidelines

### Code Style
- Python 3.11+ with type hints
- Ruff for linting and formatting
- Thai-lint for code quality (SRP, DRY, complexity)

### Testing
- pytest for test framework
- Tests in tests/ directory
- Integration tests for full command flow

### Build System
- justfile (not Makefile) - consistent with thai-lint project
- Poetry for dependency management
- Docker for distribution

## Key Design Principles

### Cooperative Agent Assumption
The system assumes AI tools are cooperative and will respect policy denials.
When SafeShell blocks an operation, the AI is expected to comply.

### Plugin-Only Policy
The SafeShell core provides only plumbing. ALL policy logic resides in plugins.
Users can disable, configure, or replace any plugin.

### Transparency to Existing Tooling
Users don't need to change their terminal emulator or preferred shell.
SafeShell operates as an intermediary layer.
