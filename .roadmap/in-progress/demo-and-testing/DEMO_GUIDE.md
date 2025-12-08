# SafeShell Demo Guide

**Purpose**: Quick reference for demonstrating SafeShell functionality

**Last Updated**: 2024-12-08

---

## Pre-Demo Setup

### 1. Ensure Claude Code Hook is Installed

```bash
# Check if hook exists
ls -la ~/.claude/hooks/PreToolUse.py

# If not, install it:
mkdir -p ~/.claude/hooks
ln -sf ~/.safeshell/hooks/claude_code_hook.py ~/.claude/hooks/PreToolUse.py
```

**IMPORTANT**: After installing the hook, you must restart Claude Code for it to take effect.

### 2. Ensure Daemon is Running

```bash
safeshell daemon status
# If not running:
safeshell daemon start
```

### 3. Start Monitor TUI (in separate terminal)

```bash
safeshell monitor        # Clean UI - approval pane only
safeshell monitor --debug  # Full UI - debug logs, history, and approval pane
```

---

## Demo Commands

### Allowed Commands (should execute normally)

```bash
echo "Hello from SafeShell!"
ls -la
git status
pwd
```

### Blocked Commands (should be denied)

```bash
# Block echo with "don't allow" phrase
echo "don't allow me"

# Block cd outside project (if rule configured)
cd /tmp

# Block sourcing sensitive files
source .env
```

### Approval-Required Commands (should trigger Monitor TUI)

```bash
# Requires approval - listing forbidden directory
ls test-forbidden-directory

# Requires approval - force push to protected branch
git push --force origin main
```

---

## If Commands Aren't Being Intercepted

### For Human Terminals
Ensure shell integration is loaded:
```bash
source ~/.safeshell/init.bash
# Or add to .bashrc: eval "$(safeshell init -)"
```

### For Claude Code Bash Tool
The PreToolUse hook must be installed and Claude Code restarted:
```bash
# Verify hook exists
ls -la ~/.claude/hooks/PreToolUse.py

# Should show symlink to:
# ~/.safeshell/hooks/claude_code_hook.py
```

If hook is missing, install it:
```bash
mkdir -p ~/.claude/hooks
ln -sf ~/.safeshell/hooks/claude_code_hook.py ~/.claude/hooks/PreToolUse.py
```

**Then restart Claude Code** - hooks are only loaded at startup.

### Workaround (without restart)
Demo via subshell that sources init.bash:
```bash
bash -c 'unset SAFESHELL_LOADED; source ~/.safeshell/init.bash; echo "don'\''t allow me"'
```

---

## Current Test Rules (in ~/.safeshell/rules.yaml)

| Rule Name | Command | Trigger | Action |
|-----------|---------|---------|--------|
| block-commit-protected-branch | git | `git commit` on main/master/develop | deny |
| approve-force-push-protected-branch | git | `git push --force` on main/master/develop | require_approval |
| test-block-echo | echo | Contains "don't allow" | deny |
| test-approval-ls-forbidden | ls | Contains "test-forbidden-dir" | require_approval |
| test-block-cd-outside-project | cd | `cd /` outside project path | deny |
| test-block-source-sensitive | source | `.env`, `.secret`, `.credentials` | deny |

---

## Troubleshooting

### Logs appearing in Monitor TUI
Restart the daemon: `safeshell daemon restart`

### Commands not being blocked
1. Check daemon is running: `safeshell daemon status`
2. Check rules loaded: Look for "Loaded X rules" in daemon startup
3. Verify hook installed (for Claude Code)
4. Verify init.bash sourced (for terminals)

### Approval not appearing in Monitor
1. Ensure monitor is connected (shows "Connected to SafeShell daemon")
2. Check the rule action is `require_approval` not `deny`
