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

**Overall Progress**: 0% complete (Planning phase)

```
[░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 0% Complete
```

**Current State**: Roadmap created, ready for implementation

**Infrastructure State**:
- MVP Phase 1 complete ✅
- Event system not started
- Monitor TUI not started
- Approval protocol not started

---

## Next PR to Implement

### START HERE: PR-1 - Event System Foundation

**Quick Summary**:
Create the event type definitions and event bus infrastructure that will power the daemon-monitor communication.

**Pre-flight Checklist**:
- [ ] MVP Phase 1 merged and working
- [ ] Understand event types needed (see AI_CONTEXT.md)
- [ ] Review existing models.py for patterns

**Prerequisites Complete**: ✅ (MVP complete)

---

## Overall Progress

**Total Completion**: 0% (0/5 PRs completed)

---

## PR Status Dashboard

| PR | Title | Status | Completion | Complexity | Priority | Notes |
|----|-------|--------|------------|------------|----------|-------|
| PR-1 | Event System Foundation | 🔴 Not Started | 0% | Medium | P0 | Start here |
| PR-2 | Daemon Event Publishing | 🔴 Not Started | 0% | Medium | P0 | Depends on PR-1 |
| PR-3 | Monitor TUI Shell | 🔴 Not Started | 0% | High | P0 | Depends on PR-1 |
| PR-4 | Approval Protocol | 🔴 Not Started | 0% | High | P0 | Depends on PR-2, PR-3 |
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
PR-1 (Events) ──┬──> PR-2 (Daemon Publishing)
                │
                └──> PR-3 (Monitor TUI)
                            │
                            ▼
PR-2 + PR-3 ──────> PR-4 (Approval Protocol)
                            │
                            ▼
                    PR-5 (Integration)
```

---

## Files to Create

### PR-1 Files
- [ ] `src/safeshell/events/__init__.py`
- [ ] `src/safeshell/events/types.py`
- [ ] `src/safeshell/events/bus.py`
- [ ] `tests/events/test_types.py`
- [ ] `tests/events/test_bus.py`

### PR-2 Files
- [ ] `src/safeshell/daemon/events.py`
- [ ] `src/safeshell/daemon/monitor.py`

### PR-3 Files
- [ ] `src/safeshell/monitor/__init__.py`
- [ ] `src/safeshell/monitor/app.py`
- [ ] `src/safeshell/monitor/widgets.py`
- [ ] `src/safeshell/monitor/styles.css`
- [ ] `src/safeshell/monitor/cli.py`

### PR-4 Files
- [ ] `src/safeshell/daemon/approval.py`

---

## Validation Checklist

### Code Quality
- [ ] `poetry run ruff check src/` passes
- [ ] `poetry run pytest` passes
- [ ] `poetry run mypy src/` passes
- [ ] `poetry run bandit -r src/` passes

### Functional Testing
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
1. Build event system foundation (PR-1)
2. PR-2 and PR-3 can proceed in parallel after PR-1
3. PR-4 integrates approval logic
4. PR-5 polishes and handles edge cases

### Key Considerations
- Textual is async-first, matches our asyncio daemon
- Mouse support is built into Textual
- Keep TUI simple for MVP, polish later
- Test approval timeout behavior carefully

---

## Notes for AI Agents

### Critical Context
- **Textual documentation**: https://textual.textualize.io/
- **Textual is async**: Matches our asyncio daemon
- **Mouse clicks work**: Textual handles this natively
- **Two sockets**: Keep wrapper socket separate from monitor socket

### Common Pitfalls to Avoid
1. Don't block the event loop in TUI handlers
2. Don't forget to handle monitor disconnection
3. Don't expose sensitive data in events
4. Don't forget timeout handling for approvals

### Key Files from MVP to Reference
- `src/safeshell/models.py` - Pydantic patterns
- `src/safeshell/daemon/protocol.py` - JSON lines pattern
- `src/safeshell/daemon/server.py` - Asyncio server pattern
- `src/safeshell/plugins/base.py` - Plugin helper methods

---

## Definition of Done

The feature is complete when:
1. [ ] All 5 PRs implemented and merged
2. [ ] `safeshell monitor` shows three-pane TUI
3. [ ] Mouse clicks on Approve/Deny work
4. [ ] Denial reason appears in wrapper message
5. [ ] Force-push triggers approval prompt
6. [ ] Timeout properly blocks pending commands
7. [ ] All tests pass
8. [ ] `.roadmap/REQUIREMENTS.md` updated with learnings

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
