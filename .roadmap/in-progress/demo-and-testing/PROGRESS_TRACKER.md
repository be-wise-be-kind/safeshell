# Demo and Cross-Environment Testing - Progress Tracker

**Purpose**: Track progress on ensuring SafeShell works across all environments

**Status**: In Progress

---

## Current Focus

Testing and documenting SafeShell functionality across different execution contexts.

---

## Demo Quick Start

When resuming this roadmap, start with:
1. Read `DEMO_GUIDE.md` for setup and commands
2. Verify hook is configured in `~/.claude/settings.json`
3. If hook missing, add it and **restart Claude Code**
4. Run demo commands as requested

---

## Environment Test Matrix

| Environment | External Commands (git, ls) | Builtins (echo, cd) | Status |
|-------------|----------------------------|---------------------|--------|
| Human terminal (bash) | ✅ shim | ✅ function override | Working |
| Human terminal (zsh) | ❓ | ❓ | Not tested |
| Claude Code Bash tool | ✅ PreToolUse hook | ✅ PreToolUse hook | **Verified Working** |
| WARP terminal | ✅ shim | ✅ function override | **Verified Working** |
| Other AI tools | ❓ | ❓ | Not tested |

---

## Completed Tasks

- [x] Verify builtin rules work (echo, cd, source) - tested via bash subshell
- [x] Identify Claude Code hook configuration (in ~/.claude/settings.json)
- [x] Document hook installation process
- [x] Create DEMO_GUIDE.md with quick reference
- [x] Verify hook works manually (tested with `echo "don't allow me"` - exits 2)
- [x] Confirmed hook is configured in settings.json with correct path
- [x] **Fixed hook format** - hooks array needs objects with `type` and `command` fields
- [x] **Tested with Claude Code** - Both deny and require_approval rules verified working
- [x] **Fixed double-approval bug** - init.bash now detects Claude Code via `$CLAUDECODE` env var and skips shim loading (hook provides protection)

---

## Pending Tasks

- [ ] Test zsh compatibility
- [ ] Document BASH_ENV approach for non-interactive shells
- [ ] Add integration tests for each environment type
- [ ] Research other AI tool integration patterns (Cursor, Aider, etc.)
- [ ] Document tool-specific setup instructions (which tools need hooks vs shims)

---

## Key Learnings

### Tool Pattern Detection

Different AI tools require different protection strategies. Detection happens in `init.bash`:

| Pattern | Detection | Protection | init.bash behavior |
|---------|-----------|------------|-------------------|
| Claude Code | `$CLAUDECODE=1` | PreToolUse hook | Skip shims (hook protects) |
| Warp/Interactive | `$- == *i*` | Shims + builtins | Load full protection |
| Unknown non-interactive | Default | Shims + builtins | Load full protection |

This prevents double-approval issues where both hook AND shims would check the same command.

### Claude Code Integration

1. **PreToolUse Hook**: Claude Code hooks are configured in `~/.claude/settings.json`
2. **Configuration format**: Hooks array needs objects with `type: "command"` and `command: "path"`
3. **Restart required**: Claude Code must be restarted after changing hook configuration
4. **Exit code 2**: Hook returns exit code 2 to block a command
5. **Environment detection**: Claude Code sets `CLAUDECODE=1` which init.bash uses to skip shim loading

**Example settings.json configuration:**
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "/home/user/.safeshell/hooks/claude_code_hook.py"
          }
        ]
      }
    ]
  }
}
```

### Logging Fix (2024-12-08)

The Monitor TUI was showing daemon logs because:
- Loguru captures stderr at import time
- After daemonizing, stderr redirect to /dev/null didn't affect loguru
- **Fix**: Reconfigure loguru in daemon after stderr redirect

```python
# In _daemonize() after redirecting stderr:
from loguru import logger
logger.remove()
logger.add(sys.stderr, level="DEBUG")  # Now points to /dev/null
```

---

## Files Reference

- Hook source: `src/safeshell/hooks/claude_code_hook.py`
- Hook install location: `~/.safeshell/hooks/claude_code_hook.py`
- Hook configuration: `~/.claude/settings.json` (hooks.PreToolUse section)
- Shell init: `~/.safeshell/init.bash`
- Rules config: `~/.safeshell/rules.yaml`
- Shims directory: `~/.safeshell/shims/`
