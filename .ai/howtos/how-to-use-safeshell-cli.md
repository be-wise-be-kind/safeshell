File: .ai/howtos/how-to-use-safeshell-cli.md

Purpose: Step-by-step guide for using the safeshell CLI

Exports: CLI navigation patterns, command discovery, common workflows

Depends: AGENTS.md (for command reference)

Overview: Practical guide for using the safeshell command-line interface to perform
    operational tasks. Covers the help system, navigation patterns, global options,
    and common workflows. Use this for "usage efforts" rather than development efforts.

# How to: Use the SafeShell CLI

**Purpose**: Guide for using the safeshell command-line interface

**Scope**: All safeshell CLI commands

**Overview**: This guide explains how to navigate and use the safeshell CLI for operational tasks.
    Use this guide when you need to perform operations (check status, evaluate commands, etc.)
    rather than develop code.

**Dependencies**: safeshell CLI installed

**Exports**: CLI navigation patterns, common workflows, tips

**Related**: AGENTS.md for command reference

**Implementation**: Step-by-step navigation with examples

---

## Overview

The `safeshell` CLI is the primary tool for interacting with SafeShell.
Use this guide when you need to perform operations, not develop code.

---

## Navigation Pattern

The CLI uses a simple command structure:

### Root Help

```bash
safeshell --help
```

Shows all available commands:
- `version` - Show the SafeShell version
- `init` - Initialize SafeShell configuration and rules
- `check` - Check if a command is safe to execute
- `status` - Show SafeShell daemon status

### Command Help

```bash
safeshell <command> --help
```

Examples:
```bash
safeshell check --help
safeshell status --help
```

Shows arguments, options, and detailed usage.

---

## Available Commands

### version

Show the SafeShell version:

```bash
safeshell version
```

Output:
```
SafeShell v0.1.0
```

### init

Initialize SafeShell configuration and rules:

```bash
safeshell init
```

This creates:
- `~/.safeshell/config.yaml` - SafeShell configuration
- `~/.safeshell/rules.yaml` - Default rules for git protection

Run this once after installation to set up SafeShell. If files already exist,
you'll be prompted before overwriting.

### check

Check if a command is safe to execute:

```bash
safeshell check "rm -rf /tmp/test"
safeshell check "git push --force"
safeshell check "cat ~/.ssh/id_rsa"
```

This evaluates the command against loaded rules without executing it.

### status

Show the daemon status and loaded rules:

```bash
safeshell status
```

Output shows:
- Daemon running state
- Number of loaded rules
- Configuration path

---

## Common Workflows

### Initial Setup

```bash
safeshell init                      # Create config and rules files
safeshell status                    # Verify daemon is running
```

### Check System Status

```bash
safeshell status                    # Show daemon and rules status
safeshell version                   # Show version
```

### Evaluate Commands

```bash
# Check if a command would be blocked
safeshell check "rm -rf /"

# Check a git operation
safeshell check "git push --force origin main"

# Check file access
safeshell check "cat /etc/passwd"
```

---

## Tips

- Use `--help` on any command for detailed usage
- The `check` command evaluates but does not execute
- Run `status` to verify the daemon is running before testing

---

## Verification Checklist

Before running a command:
- [ ] Identified the correct command
- [ ] Reviewed command `--help` for required arguments
- [ ] Daemon is running (check with `status`)
