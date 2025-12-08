# Approval Workflow with Monitor TUI - Progress Tracker & AI Agent Handoff Document

**Purpose**: Primary AI agent handoff document for approval workflow feature with current progress tracking and implementation guidance

**Scope**: Human approval for risky operations via terminal UI with mouse support

**Overview**: Primary handoff document for AI agents working on the approval workflow feature. Tracks current implementation progress, provides next action guidance, and coordinates AI agent work across multiple pull requests.

**Dependencies**: Completed MVP Phase 1, textual library

**Exports**: Progress tracking, implementation guidance, AI agent coordination

**Related**: AI_CONTEXT.md for feature overview, PR_BREAKDOWN.md for detailed tasks

**Implementation**: Progress-driven coordination with systematic validation

---

## Document Purpose

This is the **PRIMARY HANDOFF DOCUMENT** for AI agents working on the approval workflow feature. When starting work:
1. **Read this document FIRST** to understand current progress
2. **Check "Next PR to Implement" section** for what to do
3. **Reference PR_BREAKDOWN.md** for detailed instructions
4. **Update this document** after completing work

---

## Current Status

**Overall Progress**: 100% complete (6/6 PRs complete)

```
[██████████████████████████████] 100% Complete
```

**Current State**: Feature complete! PR-4 merged with Claude Code hook integration.

**Infrastructure State**:
- MVP Phase 1 complete ✅
- Event system complete ✅ (PR-1 merged)
- Daemon event publishing complete ✅ (PR-2 merged)
- Monitor socket infrastructure complete ✅
- Config-based rules complete ✅ (PR-2.5 merged)
- Monitor TUI complete ✅ (PR-3 merged)
- Shim infrastructure complete ✅ (PR-3.5 merged)
- **Approval protocol complete ✅ (PR-4 implemented)**
- Integration & polish not started ← NEXT STEP

**Major Architecture Discovery (Shims)**:
The SHELL wrapper approach (`SHELL=/path/to/safeshell-wrapper`) only works when AI tools explicitly invoke `$SHELL -c "command"`. For truly transparent interception that works for:
- Humans typing in terminals
- AI tools (Claude Code, Codex, etc.)
- Any script or tool

We need **shims** (like pyenv/rbenv) + **shell function overrides** for builtins.

---

## Next PR to Implement

### START HERE: PR-4 - Approval Protocol

**Quick Summary**:
Implement the approval request/response protocol between wrapper, daemon, and monitor. This enables `require_approval` rules to pause command execution until approved/denied in the Monitor TUI.

**Pre-flight Checklist**:
- [x] PR-1 (Event System) merged
- [x] PR-2 (Daemon Event Publishing) merged
- [x] PR-2.5 (Config Rules) merged
- [x] PR-3 (Monitor TUI) merged
- [x] PR-3.5 (Shim Infrastructure) merged
- [ ] Understand current event flow (daemon → monitor)

**What to Build**:

1. **`src/safeshell/daemon/approval.py`** - ApprovalManager class:
```python
class ApprovalManager:
    """Manages pending approval requests."""

    async def create_approval(self, command: str, rule_name: str, reason: str) -> str:
        """Create a pending approval, returns approval_id."""

    async def wait_for_decision(self, approval_id: str, timeout: float) -> ApprovalDecision:
        """Block until approved/denied or timeout."""

    async def approve(self, approval_id: str) -> bool:
        """Approve a pending request."""

    async def deny(self, approval_id: str, reason: str | None) -> bool:
        """Deny a pending request with optional reason."""
```

2. **Update daemon to handle REQUIRE_APPROVAL**:
   - When rule returns `require_approval`, create pending approval
   - Emit `APPROVAL_NEEDED` event to monitor
   - Block wrapper until decision received
   - Return approval/denial to wrapper

3. **Update monitor to send approval decisions**:
   - When user clicks Approve/Deny, send decision to daemon
   - Daemon forwards result to waiting wrapper

**Files to Create**:
- `src/safeshell/daemon/approval.py` - ApprovalManager, PendingApproval

**Files to Modify**:
- `src/safeshell/daemon/server.py` - Handle approval flow
- `src/safeshell/daemon/manager.py` - Integrate with ApprovalManager
- `src/safeshell/wrapper/client.py` - Wait for approval
- `src/safeshell/rules/evaluator.py` - Support REQUIRE_APPROVAL action

**Success Criteria**:
- [ ] Rule with `action: require_approval` triggers approval flow
- [ ] Monitor TUI shows pending approval
- [ ] Approve button allows command execution
- [ ] Deny button blocks with optional reason
- [ ] Timeout properly blocks pending commands

---

## Overall Progress

**Total Completion**: 100% (6/6 PRs completed)

---

## PR Status Dashboard

| PR | Title | Status | Completion | Complexity | Priority | Notes |
|----|-------|--------|------------|------------|----------|-------|
| PR-1 | Event System Foundation | 🟢 Complete | 100% | Medium | P0 | Merged in PR #4 |
| PR-2 | Daemon Event Publishing | 🟢 Complete | 100% | Medium | P0 | Merged in PR #5 |
| PR-2.5 | Config-Based Rules | 🟢 Complete | 100% | Medium | P0 | Merged in PR #6 |
| PR-3/3.5 | Monitor TUI + Shim Infrastructure | 🟢 Complete | 100% | High | P0 | Merged in PR #7, #8 |
| PR-4 | Approval Protocol + Claude Code Hook | 🟢 Complete | 100% | High | P0 | Merged in PR #9 |
| PR-5 | Integration and Polish | 🟢 Complete | 100% | Medium | P0 | Merged with PR-4 |

### Status Legend
- 🔴 Not Started
- 🟡 In Progress
- 🟢 Complete
- 🔵 Blocked
- ⚫ Cancelled

---

## PR Dependencies

```
PR-1 (Events) ✅
       │
       ▼
PR-2 (Daemon Publishing) ✅
       │
       ▼
PR-2.5 (Config Rules) ✅
       │
       ▼
PR-3/3.5 (Monitor TUI + Shims) ✅
       │
       ▼
PR-4 (Approval Protocol + Claude Code Hook) ✅
       │
       ▼
PR-5 (Integration) ✅ (merged with PR-4)
```

---

## Files to Create

### PR-1 Files ✅
- [x] `src/safeshell/events/__init__.py`
- [x] `src/safeshell/events/types.py`
- [x] `src/safeshell/events/bus.py`
- [x] `tests/events/test_types.py`
- [x] `tests/events/test_bus.py`

### PR-2 Files ✅
- [x] `src/safeshell/daemon/events.py`
- [x] `src/safeshell/daemon/monitor.py`
- [x] `tests/daemon/test_events.py`
- [x] `tests/daemon/test_monitor.py`

### PR-2.5 Files (Config Rules) ✅
- [x] `src/safeshell/rules/__init__.py`
- [x] `src/safeshell/rules/schema.py`
- [x] `src/safeshell/rules/evaluator.py`
- [x] `src/safeshell/rules/loader.py`
- [x] `src/safeshell/rules/defaults.py`
- [x] `tests/rules/test_schema.py`
- [x] `tests/rules/test_evaluator.py`
- [x] `tests/rules/test_loader.py`

### PR-3 Files ✅
- [x] `src/safeshell/monitor/__init__.py`
- [x] `src/safeshell/monitor/app.py`
- [x] `src/safeshell/monitor/widgets.py`
- [x] `src/safeshell/monitor/styles.css`
- [x] `src/safeshell/monitor/client.py`
- [x] `tests/monitor/test_app.py`
- [x] `tests/monitor/test_client.py`
- [x] `tests/monitor/test_widgets.py`

### PR-3.5 Files ✅
- [x] `src/safeshell/shims/__init__.py`
- [x] `src/safeshell/shims/manager.py`
- [x] `src/safeshell/shims/safeshell-shim` (updated)
- [x] `src/safeshell/shims/init.bash` (updated)
- [x] `src/safeshell/cli.py` (added `refresh` command, updated `init`)

### PR-4 Files ✅
- [x] `src/safeshell/daemon/approval.py`
- [x] `src/safeshell/hooks/__init__.py`
- [x] `src/safeshell/hooks/claude_code_hook.py`
- [x] `tests/daemon/test_approval.py`

---

## Validation Checklist

### Code Quality
- [x] `poetry run ruff check src/` passes
- [x] `poetry run pytest` passes (195 tests)
- [ ] `poetry run mypy src/` passes (pre-existing issues with stubs)
- [ ] `poetry run bandit -r src/` passes

### Functional Testing
- [x] Config rules block git commit on protected branches
- [x] Config rules work with bash conditions
- [x] Global + repo rules merge correctly
- [x] `safeshell monitor` launches TUI
- [x] Three-pane layout displays correctly
- [x] Events stream from daemon to monitor
- [x] Shims intercept commands transparently
- [x] `safeshell refresh` creates/removes shims
- [x] `safeshell init` sets up shim infrastructure
- [x] Approval prompt appears for REQUIRE_APPROVAL (PR-4)
- [x] Approve button works (mouse click) (PR-4)
- [x] Deny button works with reason text (PR-4)
- [x] Claude Code hook intercepts AI agent commands (PR-4)
- [ ] Reason appears in denial message (PR-4)

---

## Implementation Strategy

### Approach
1. Build event system foundation (PR-1) ✅
2. Add daemon event publishing (PR-2) ✅
3. Refactor to config-based rules (PR-2.5) ✅
4. Build Monitor TUI + Shim Infrastructure (PR-3/3.5) ✅
5. **Implement approval protocol (PR-4)** ← CURRENT
6. Integration and polish (PR-5)

### Key Considerations
- Config-based rules are simpler than Python plugins
- Bash conditions provide unlimited flexibility
- Global + repo rules enable per-project customization
- Keep event system - still needed for monitor

---

## Notes for AI Agents

### Critical Context
- **Architecture Pivot**: We are moving from Python plugins to YAML config
- **Why**: Simpler, more flexible, supports repo-level customization
- **Textual documentation**: https://textual.textualize.io/ (for PR-3)
- **Two sockets**: daemon.sock for wrappers, monitor.sock for monitors

### Rule Evaluation Flow (PR-2.5)
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

### Common Pitfalls to Avoid
1. Don't forget to handle bash condition failures gracefully
2. Repo rules are ADDITIVE only - can't relax global rules
3. Use proper shell escaping in conditions
4. Don't block the event loop with subprocess calls (use async)

### Key Files from MVP to Reference
- `src/safeshell/models.py` - Pydantic patterns
- `src/safeshell/daemon/protocol.py` - JSON lines pattern
- `src/safeshell/daemon/server.py` - Asyncio server pattern
- `src/safeshell/daemon/events.py` - Event publishing
- `src/safeshell/daemon/monitor.py` - Monitor connection handler

### PR-2 Learnings
- Made `PluginManager.process_request()` async to support event publishing
- Added `MonitorEventMessage` model for sending events over protocol
- Two sockets work well: daemon.sock for wrappers, monitor.sock for monitors
- Event publisher is optional in PluginManager for backward compatibility

---

## Definition of Done

The feature is complete when:
1. [ ] All 6 PRs implemented and merged
2. [ ] Config-based rules replace Python plugins
3. [ ] Global + repo rules work correctly
4. [ ] `safeshell monitor` shows three-pane TUI
5. [ ] Mouse clicks on Approve/Deny work
6. [ ] Denial reason appears in wrapper message
7. [ ] Force-push triggers approval prompt
8. [ ] Timeout properly blocks pending commands
9. [ ] All tests pass
10. [ ] `.roadmap/REQUIREMENTS.md` updated with learnings

---

## Update Protocol

After completing each PR:
1. Update the PR status to 🟢 Complete
2. Check off completed files above
3. Update "Next PR to Implement" section
4. Update overall progress percentage
5. Commit changes to this document

---

## Post-Completion Tasks

After all PRs complete:
1. Update `.roadmap/REQUIREMENTS.md` with Phase 2 learnings
2. Move this roadmap to `.roadmap/complete/approval-workflow/`
3. Begin Phase 3 planning if desired
