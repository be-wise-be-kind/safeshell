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

**Overall Progress**: 50% complete (3/6 PRs merged)

```
[██████████████░░░░░░░░░░░░░░] 50% Complete
```

**Current State**: PR-2.5 complete, ready for PR-3 (Monitor TUI Shell)

**Infrastructure State**:
- MVP Phase 1 complete ✅
- Event system complete ✅ (PR-1 merged)
- Daemon event publishing complete ✅ (PR-2 merged)
- Monitor socket infrastructure complete ✅
- **Config-based rules complete ✅ (PR-2.5 done)**
- Monitor TUI not started ← NEXT STEP
- Approval protocol not started

---

## ⚠️ ARCHITECTURE PIVOT - READ THIS FIRST

**Before continuing with PR-3 (Monitor TUI), we are refactoring to a simpler config-based rules system.**

The current Python plugin architecture is being replaced with YAML configuration files. This is a **major simplification** that:
1. Eliminates the need for Python plugins
2. Enables global + repo-level rule configuration
3. Uses bash conditions for complex logic
4. Makes adding new rules trivial (edit YAML, no Python)

**See AI_CONTEXT.md Section "Config-Based Rules Architecture" for full details.**

---

## Next PR to Implement

### START HERE: PR-2.5 - Config-Based Rules Architecture

**Quick Summary**:
Replace the Python plugin system with YAML-based rule configuration. Rules use regex patterns and bash conditions for matching, with actions: deny, require_approval, redirect.

**This is a REFACTOR, not new functionality. The goal is to simplify before adding more features.**

**Pre-flight Checklist**:
- [x] PR-1 (Event System) merged
- [x] PR-2 (Daemon Event Publishing) merged
- [ ] Read AI_CONTEXT.md "Config-Based Rules Architecture" section thoroughly
- [ ] Understand the rule evaluation flow

**What to Build**:

1. **Rule Schema** (`~/.safeshell/rules.yaml` and `.safeshell/rules.yaml`):
```yaml
rules:
  - name: "block-commit-protected"
    commands: ["git"]
    conditions:
      - "echo '$CMD' | grep -qE '^git\\s+commit'"
      - "git branch --show-current | grep -qE '^(main|master|develop)$'"
    action: deny
    message: "Cannot commit to protected branch"
```

2. **Rule Evaluator** (replaces PluginManager):
   - Load global rules from `~/.safeshell/rules.yaml`
   - Load repo rules from `.safeshell/rules.yaml` (additive only)
   - Fast-path: skip if command not in any rule's `commands` list
   - Evaluate conditions via subprocess (bash)
   - Return: ALLOW, DENY, REQUIRE_APPROVAL, or REDIRECT

3. **Migration**:
   - Keep event system (PR-1) - still needed for monitor
   - Keep daemon infrastructure (PR-2) - still needed
   - Remove/deprecate: `src/safeshell/plugins/` directory
   - Update: `PluginManager` → `RuleEvaluator`

**Files to Create**:
- `src/safeshell/rules/__init__.py`
- `src/safeshell/rules/schema.py` - Pydantic models for rules
- `src/safeshell/rules/evaluator.py` - Rule evaluation logic
- `src/safeshell/rules/loader.py` - Load and merge rule files
- `tests/rules/test_schema.py`
- `tests/rules/test_evaluator.py`
- `tests/rules/test_loader.py`

**Files to Modify**:
- `src/safeshell/daemon/manager.py` - Use RuleEvaluator instead of plugins
- `src/safeshell/daemon/server.py` - Update imports

**Files to Remove/Deprecate**:
- `src/safeshell/plugins/base.py` - No longer needed
- `src/safeshell/plugins/git_protect.py` - Replaced by config rules
- `tests/plugins/` - Replace with rules tests

**Default Rules to Include** (equivalent to current git-protect):
```yaml
# ~/.safeshell/default-rules.yaml (shipped with SafeShell)
rules:
  - name: block-commit-protected-branch
    commands: ["git"]
    conditions:
      - "echo '$CMD' | grep -qE '^git\\s+commit'"
      - "git branch --show-current | grep -qE '^(main|master|develop)$'"
    action: deny
    message: "Cannot commit directly to protected branch. Create a feature branch first."

  - name: block-force-push-protected
    commands: ["git"]
    conditions:
      - "echo '$CMD' | grep -qE '^git\\s+push.*(--force|-f)'"
      - "git branch --show-current | grep -qE '^(main|master|develop)$'"
    action: require_approval
    message: "Force push to protected branch requires approval"
```

**Success Criteria**:
- [ ] `poetry run ruff check src/` passes
- [ ] `poetry run pytest` passes
- [ ] Existing git-protect behavior works via config rules
- [ ] Global rules load from `~/.safeshell/rules.yaml`
- [ ] Repo rules load from `.safeshell/rules.yaml`
- [ ] Bash conditions execute correctly
- [ ] Rule evaluation is fast (< 50ms for non-matching commands)

---

## Overall Progress

**Total Completion**: 33% (2/6 PRs completed)

---

## PR Status Dashboard

| PR | Title | Status | Completion | Complexity | Priority | Notes |
|----|-------|--------|------------|------------|----------|-------|
| PR-1 | Event System Foundation | 🟢 Complete | 100% | Medium | P0 | Merged in PR #4 |
| PR-2 | Daemon Event Publishing | 🟢 Complete | 100% | Medium | P0 | Merged in PR #5 |
| PR-2.5 | Config-Based Rules | 🟢 Complete | 100% | Medium | P0 | Done |
| PR-3 | Monitor TUI Shell | 🔴 Not Started | 0% | High | P0 | **START HERE** |
| PR-4 | Approval Protocol | 🔴 Not Started | 0% | High | P0 | Depends on PR-2.5, PR-3 |
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
PR-3 (Monitor TUI) ◀── START HERE
       │
       ▼
PR-4 (Approval Protocol)
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
