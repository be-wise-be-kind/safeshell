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

**Overall Progress**: 70% complete (4/6 PRs complete + shim architecture POC)

```
[█████████████████████████░░░] 70% Complete
```

**Current State**: Shim architecture POC complete, ready for PR-3.5 (safeshell refresh + TUI fix)

**Infrastructure State**:
- MVP Phase 1 complete ✅
- Event system complete ✅ (PR-1 merged)
- Daemon event publishing complete ✅ (PR-2 merged)
- Monitor socket infrastructure complete ✅
- Config-based rules complete ✅ (PR-2.5 done)
- Monitor TUI complete ✅ (PR-3 done)
- **Shim architecture POC complete ✅ (NEW)**
- `safeshell refresh` command not started ← NEXT STEP
- Approval protocol not started

**Major Architecture Discovery (Shims)**:
The SHELL wrapper approach (`SHELL=/path/to/safeshell-wrapper`) only works when AI tools explicitly invoke `$SHELL -c "command"`. For truly transparent interception that works for:
- Humans typing in terminals
- AI tools (Claude Code, Codex, etc.)
- Any script or tool

We need **shims** (like pyenv/rbenv) + **shell function overrides** for builtins.

---

## Next PR to Implement

### START HERE: PR-3.5 - Shim Infrastructure & TUI Fix

**Quick Summary**:
Productionize the shim-based command interception and fix the Monitor TUI to receive events. This enables truly transparent command interception for all users (humans and AI).

**Pre-flight Checklist**:
- [x] PR-1 (Event System) merged
- [x] PR-2 (Daemon Event Publishing) merged
- [x] PR-2.5 (Config Rules) done
- [x] PR-3 (Monitor TUI) done
- [x] Shim POC working (cd, ls blocked via shims)
- [ ] Read shim architecture section below

**What to Build**:

1. **`safeshell refresh` CLI command** (`src/safeshell/cli.py`):
```python
@app.command()
def refresh() -> None:
    """Regenerate shims based on rules.yaml commands."""
    # 1. Load all rules (global + repo)
    # 2. Extract unique commands from rules
    # 3. Create/update symlinks in ~/.safeshell/shims/
    # 4. Report what was created/updated
```

2. **Shim management module** (`src/safeshell/shims/`):
   - Move POC scripts to proper location
   - Create `manager.py` for shim CRUD operations
   - Support `~/.safeshell/shims/` as production location

3. **Update `safeshell init`**:
   - Create `~/.safeshell/shims/` directory
   - Copy universal shim script
   - Run initial `safeshell refresh`
   - Output shell init instructions

4. **Fix Monitor TUI event display**:
   - Changed `call_from_thread()` to `call_later()` in app.py (done)
   - Verify events flow from shims → daemon → monitor

**Files to Create**:
- `src/safeshell/shims/manager.py` - Shim management functions
- `~/.safeshell/shims/safeshell-shim` - Universal shim (installed by init)

**Files to Modify**:
- `src/safeshell/cli.py` - Add `refresh` command, update `init`
- `src/safeshell/monitor/app.py` - Fix event handling (done: call_later)

**Success Criteria**:
- [ ] `safeshell init` creates shims directory and initial shims
- [ ] `safeshell refresh` regenerates shims from rules.yaml
- [ ] `poetry run ruff check src/` passes
- [ ] `poetry run pytest` passes
- [ ] Shimmed commands are intercepted transparently
- [ ] Monitor TUI displays events from intercepted commands
- [ ] Shell starts cleanly without daemon (fail-open)

---

### THEN: PR-4 - Approval Protocol

**Quick Summary**:
Implement the approval request/response protocol between wrapper, daemon, and monitor.

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

**Total Completion**: 67% (4/6 PRs completed)

---

## PR Status Dashboard

| PR | Title | Status | Completion | Complexity | Priority | Notes |
|----|-------|--------|------------|------------|----------|-------|
| PR-1 | Event System Foundation | 🟢 Complete | 100% | Medium | P0 | Merged in PR #4 |
| PR-2 | Daemon Event Publishing | 🟢 Complete | 100% | Medium | P0 | Merged in PR #5 |
| PR-2.5 | Config-Based Rules | 🟢 Complete | 100% | Medium | P0 | Merged in PR #6 |
| PR-3 | Monitor TUI Shell | 🟡 In Progress | 80% | High | P0 | Code done, needs manual test |
| PR-3.5 | Shim Infrastructure & TUI Fix | 🟡 In Progress | 60% | Medium | P0 | **START HERE** |
| PR-4 | Approval Protocol | 🔴 Not Started | 0% | High | P0 | After PR-3.5 |
| PR-5 | Integration and Polish | 🔴 Not Started | 0% | Medium | P0 | Depends on PR-4 |

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
PR-3 (Monitor TUI) ✅
       │
       ▼
PR-4 (Approval Protocol) ◀── START HERE
       │
       ▼
PR-5 (Integration)
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

### PR-4 Files
- [ ] `src/safeshell/daemon/approval.py`

---

## Validation Checklist

### Code Quality
- [x] `poetry run ruff check src/` passes
- [x] `poetry run pytest` passes (140 tests)
- [ ] `poetry run mypy src/` passes (pre-existing issues with stubs)
- [ ] `poetry run bandit -r src/` passes

### Functional Testing
- [ ] Config rules block git commit on protected branches
- [ ] Config rules work with bash conditions
- [ ] Global + repo rules merge correctly
- [ ] `safeshell monitor` launches TUI
- [ ] Three-pane layout displays correctly
- [ ] Events stream from daemon to monitor
- [ ] Approval prompt appears for REQUIRE_APPROVAL
- [ ] Approve button works (mouse click)
- [ ] Deny button works with reason text
- [ ] Reason appears in denial message

---

## Implementation Strategy

### Approach
1. Build event system foundation (PR-1) ✅
2. Add daemon event publishing (PR-2) ✅
3. **Refactor to config-based rules (PR-2.5)** ← CURRENT
4. Build Monitor TUI (PR-3)
5. Implement approval protocol (PR-4)
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
