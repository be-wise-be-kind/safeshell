# Approval Workflow with Monitor TUI - AI Context

**Purpose**: AI agent context document for implementing the approval workflow feature

**Scope**: Human approval for risky operations via terminal UI with mouse support

**Overview**: Extends SafeShell with human-in-the-loop approval for REQUIRE_APPROVAL decisions. Introduces a Monitor TUI (terminal user interface) built with Textual that displays real-time events, command history, and approval prompts. Supports mouse interaction for approve/deny actions.

**Dependencies**: Python 3.11+, textual, existing daemon/plugin infrastructure from MVP

**Exports**: safeshell monitor command, approval protocol, event streaming

**Related**: PR_BREAKDOWN.md for implementation tasks, PROGRESS_TRACKER.md for current status

**Implementation**: Event-driven architecture with WebSocket-like streaming over Unix socket

---

## Overview

Phase 2 adds human approval for risky operations:

```
┌─────────────────────────────────────────────────────────────────┐
│  Monitor TUI (safeshell monitor)                                │
├─────────────────────┬─────────────────────┬─────────────────────┤
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

## Project Background

The MVP established the daemon/wrapper architecture for blocking dangerous commands. However, some operations are risky but not outright forbidden - they require human judgment:

- Force push to protected branches (might be intentional)
- Deleting important files (might be cleanup)
- Running privileged commands (might be necessary)

The approval workflow adds a third decision type: `REQUIRE_APPROVAL`, which pauses execution until a human approves or denies in the Monitor TUI.

## Feature Vision

1. **Monitor TUI**: Rich terminal interface with three panes
   - Debug pane: Real-time log streaming from daemon
   - History pane: Recent commands with allow/block/pending status
   - Approval pane: Current pending approval with action buttons

2. **Mouse Support**: Textual provides full mouse interaction
   - Click Approve/Deny buttons
   - Optional reason text input for denials
   - Scrollable panes

3. **Event Streaming**: Daemon broadcasts events to connected monitors
   - Command received
   - Evaluation started/completed
   - Approval requested/resolved

4. **Keyboard Support**: Full keyboard navigation
   - Press 'a' to approve, 'd' to deny
   - Tab to navigate between elements
   - Works in terminals without mouse support

## Technology Choice: Textual

[Textual](https://textual.textualize.io/) is a modern Python TUI framework that provides:
- Full mouse support (clicks, scrolling)
- Rich widget library (buttons, inputs, panels)
- CSS-like styling
- Reactive data binding
- Async-first design (matches our asyncio daemon)

Textual is actively maintained and production-ready.

## Target Architecture

### New Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Event System | `src/safeshell/events/` | Event types, bus, streaming |
| Monitor TUI | `src/safeshell/monitor/` | Textual app, widgets, screens |
| Monitor CLI | `src/safeshell/monitor/cli.py` | `safeshell monitor` command |
| Approval Protocol | `src/safeshell/daemon/approval.py` | Pending approvals, timeouts |

### Modified Components

| Component | Changes |
|-----------|---------|
| DaemonServer | Add event publishing, approval waiting |
| PluginManager | Support REQUIRE_APPROVAL decisions |
| DaemonResponse | Add challenge_code, approval_id fields |

### Communication Flow

```
Wrapper                  Daemon                     Monitor TUI
   │                        │                           │
   │──evaluate(cmd)────────>│                           │
   │                        │──event: cmd_received─────>│
   │                        │                           │
   │                        │ [plugin returns REQUIRE_APPROVAL]
   │                        │                           │
   │                        │──event: approval_needed──>│
   │                        │                           │
   │   [wrapper blocks,     │         [user clicks      │
   │    waiting for         │          Approve/Deny]    │
   │    approval]           │                           │
   │                        │<──approve(id, reason?)────│
   │                        │                           │
   │<──response(approved)───│──event: approval_resolved>│
   │                        │                           │
```

### Approval States

```
PENDING ──> APPROVED ──> (command executes)
    │
    └──> DENIED ──> (command blocked with reason)
    │
    └──> TIMEOUT ──> (command blocked, timeout message)
```

## Key Decisions

### TUI Layout

Three-column layout with:
1. **Debug Pane** (left, 30%): Scrolling log view, color-coded by level
2. **History Pane** (center, 35%): Recent commands with status icons
3. **Approval Pane** (right, 35%): Current approval request with actions

### Deny Reason

- Optional text input below Deny button
- If provided, included in denial message to AI agent
- Helps AI understand why and avoid repeating

### Event Protocol

Extend JSON lines protocol with event types:
```json
{"type": "event", "event": "command_received", "data": {...}}
{"type": "event", "event": "approval_needed", "data": {"id": "...", "command": "..."}}
{"type": "request", ...}  // existing request format
{"type": "response", ...}  // existing response format
```

### Multiple Monitors

- Support multiple connected monitors (informational)
- Only first connected monitor can approve/deny (simplicity for MVP)
- Future: designated approver concept

## Integration Points

### With Existing Features

- **Plugin System**: Plugins return REQUIRE_APPROVAL decision
- **Daemon Server**: Add event publisher, approval queue
- **Wrapper**: Handle approval_pending response, wait for resolution
- **CLI**: Add `safeshell monitor` subcommand

### With Textual

```python
from textual.app import App
from textual.widgets import Button, Input, Static, RichLog

class MonitorApp(App):
    CSS = """
    /* Three-column layout */
    """

    def compose(self):
        yield DebugPane()
        yield HistoryPane()
        yield ApprovalPane()

    async def on_button_pressed(self, event):
        if event.button.id == "approve":
            await self.send_approval(approved=True)
        elif event.button.id == "deny":
            reason = self.query_one("#reason-input").value
            await self.send_approval(approved=False, reason=reason)
```

## Success Metrics

### Phase 2 Complete When:

1. `safeshell monitor` launches TUI successfully
2. TUI displays three panes with correct layout
3. Real-time log streaming works in debug pane
4. Command history updates live
5. Approval prompt appears for REQUIRE_APPROVAL
6. Approve button allows command to execute
7. Deny button blocks with optional reason
8. Reason text appears in wrapper's denial message
9. Timeout properly blocks after configurable period

## Technical Constraints

- Textual requires Python 3.8+ (we have 3.11+)
- Terminal must support 256 colors (most modern terminals do)
- Mouse support requires terminal emulator support (most do)
- Single monitor can approve at a time (MVP constraint)

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Monitor disconnects during approval | Timeout with configurable behavior |
| Multiple rapid approvals | Queue with FIFO processing |
| Terminal doesn't support mouse | Keyboard shortcuts (a/d keys) |
| Daemon restart loses pending | Fail-closed (deny pending on restart) |

## AI Agent Guidance

### When Implementing Events

1. Define event types in `src/safeshell/events/types.py`
2. Use Pydantic models for event data
3. Implement EventBus with async publish/subscribe
4. Add event emission points in DaemonServer

### When Implementing Monitor TUI

1. Start with single-file prototype, then split
2. Use Textual's reactive pattern for state
3. Connect to daemon socket for events
4. Handle reconnection gracefully

### When Modifying Plugins

1. Use `_require_approval()` helper method
2. Include clear reason for user
3. Consider if operation is truly approval-worthy

## Future Enhancements (Phase 3+)

- Approval history/audit log
- Multiple designated approvers
- Remote approval (not just local terminal)
- Approval rules (auto-approve certain patterns)
- Integration with git-protect for force-push approval

---

## Note on Requirements

After completing Phase 2, update `.roadmap/REQUIREMENTS.md` with:
- Learnings from TUI implementation
- Any new coding standards discovered
- Architecture changes if any
- Updated technical constraints
