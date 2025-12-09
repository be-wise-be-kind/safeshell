# Production Rules Development - Progress Tracker & AI Agent Handoff Document

**Purpose**: Primary AI agent handoff document for Production Rules Development with current progress tracking and implementation guidance

**Scope**: Create a comprehensive set of default rules for common AI coding assistant mistakes, including global rules and per-repository rules

**Overview**: Primary handoff document for AI agents working on the Production Rules Development feature.
    Tracks current implementation progress, provides next action guidance, and coordinates AI agent work across
    multiple pull requests. Contains current status, prerequisite validation, PR dashboard, detailed checklists,
    implementation strategy, success metrics, and AI agent instructions.

**Dependencies**: Phase 4 (Architecture Review) - rules engine must be validated before extensive rule creation

**Exports**: Progress tracking, implementation guidance, AI agent coordination, and feature development roadmap

**Related**: AI_CONTEXT.md for feature overview, PR_BREAKDOWN.md for detailed tasks

**Implementation**: Progress-driven coordination with systematic validation, checklist management, and AI agent handoff procedures

---

## Document Purpose
This is the **PRIMARY HANDOFF DOCUMENT** for AI agents working on the Production Rules Development feature. When starting work on any PR, the AI agent should:
1. **Read this document FIRST** to understand current progress and feature requirements
2. **Check the "Next PR to Implement" section** for what to do
3. **Reference the linked documents** for detailed instructions
4. **Update this document** after completing each PR

## Current Status
**Current PR**: Not Started - Beginning PR1
**Infrastructure State**: Basic rules engine exists, default rules are minimal
**Feature Target**: Comprehensive rule set preventing common AI mistakes

## Required Documents Location
```
.roadmap/planning/phase5-rules/
├── AI_CONTEXT.md          # Overall feature architecture and context
├── PR_BREAKDOWN.md        # Detailed instructions for each PR
└── PROGRESS_TRACKER.md    # THIS FILE - Current progress and handoff notes
```

## Next PR to Implement

### START HERE: PR1 - Global Rules for Destructive Operations

**Quick Summary**:
Create comprehensive global rules preventing destructive file operations, dangerous git commands, and system modifications.

**Pre-flight Checklist**:
- [ ] Read current default rules in src/safeshell/rules/defaults.py
- [ ] Review rules schema in src/safeshell/rules/schema.py
- [ ] Understand condition evaluation in src/safeshell/rules/evaluator.py
- [ ] Test current rules functionality with `safeshell check`

**Prerequisites Complete**:
- [ ] Phase 4 Architecture Review completed
- [ ] Rules engine validated and stable

---

## Overall Progress
**Total Completion**: 0% (0/4 PRs completed)

```
[░░░░░░░░░░] 0% Complete
```

---

## PR Status Dashboard

| PR | Title | Status | Completion | Complexity | Priority | Notes |
|----|-------|--------|------------|------------|----------|-------|
| PR1 | Global Rules - Destructive Operations | 🔴 Not Started | 0% | Medium | P0 | rm, chmod, system files |
| PR2 | Global Rules - Sensitive Data & Git | 🔴 Not Started | 0% | Medium | P0 | .env, SSH, credentials, git push |
| PR3 | Global Rules - AI-Specific Patterns | 🔴 Not Started | 0% | Medium | P0 | Common AI mistakes |
| PR4 | Repository-Local Rules Examples | 🔴 Not Started | 0% | Low | P1 | Demo local rules |

### Status Legend
- 🔴 Not Started
- 🟡 In Progress
- 🟢 Complete
- 🔵 Blocked
- ⚫ Cancelled

---

## PR1: Global Rules - Destructive Operations

### Scope
Create rules preventing destructive file and system operations:
- Block `rm -rf /`, `rm -rf ~`, `rm -rf *` patterns
- Block `chmod 777` and overly permissive permissions
- Block modifications to system directories (/etc, /usr, /bin)
- Block `dd` commands to disk devices
- Require approval for recursive deletes in project directories

### Success Criteria
- [ ] All destructive patterns blocked or require approval
- [ ] Rules tested with `safeshell check` command
- [ ] False positive rate is acceptable (no blocking of safe operations)
- [ ] Documentation updated with new rules

---

## PR2: Global Rules - Sensitive Data & Git

### Scope
Create rules protecting sensitive data and git operations:
- Block reading .env, .env.local, .env.production files
- Block access to ~/.ssh/ directory
- Block reading credentials.json, secrets.yaml, etc.
- Block `git push --force` to main/master
- Block `git reset --hard` without approval
- Require approval for commits to main/master
- Block exposure of API keys and tokens in commands

### Success Criteria
- [ ] Sensitive file patterns comprehensively covered
- [ ] Git safety rules prevent common mistakes
- [ ] Rules work for both AI and human contexts where appropriate
- [ ] Integration with existing context-aware filtering (ai_only/human_only)

---

## PR3: Global Rules - AI-Specific Patterns

### Scope
Create rules for common AI coding assistant mistakes:
- Block commands that could corrupt package managers (npm/pip/poetry)
- Require approval for installing global packages
- Block commands that modify shell configuration (.bashrc, .zshrc)
- Block commands that could expose environment to network
- Require approval for docker commands that mount sensitive volumes
- Block curl/wget piped directly to shell

### Success Criteria
- [ ] Common AI mistake patterns identified and blocked
- [ ] Rules use ai_only filter where appropriate
- [ ] Balance between safety and usability
- [ ] Rules documented with rationale

---

## PR4: Repository-Local Rules Examples

### Scope
Create example repository-local rules demonstrating:
- Project-specific forbidden directories
- Custom approval workflows for deployments
- Branch protection rules specific to repo
- Environment-specific restrictions

Create `.safeshell/rules.yaml` examples for:
- A typical web application project
- A monorepo with multiple services
- A security-sensitive project

### Success Criteria
- [ ] Local rules override/extend global rules correctly
- [ ] Examples are realistic and useful
- [ ] Documentation explains local rules usage
- [ ] Test local rules in safeshell repo itself

---

## Implementation Strategy

### Phase Approach
1. **PR1**: Destructive operations (highest risk, clearest rules)
2. **PR2**: Sensitive data and git (data protection focus)
3. **PR3**: AI-specific patterns (preventive patterns)
4. **PR4**: Local rules examples (demonstrate flexibility)

### Quality Gates
- All rules tested with `safeshell check "<command>"`
- Manual testing with actual AI tool integration
- No false positives for common safe operations
- Rules use appropriate context filters (ai_only/human_only)

## Success Metrics

### Technical Metrics
- [ ] 50+ production rules created
- [ ] All rules have descriptions
- [ ] All rules tested and validated
- [ ] Zero false positives on common operations

### Feature Metrics
- [ ] Common AI mistakes are blocked
- [ ] Sensitive data is protected
- [ ] Destructive operations require approval or are blocked
- [ ] Local rules work correctly

## Update Protocol

After completing each PR:
1. Update the PR status to 🟢 Complete
2. Fill in completion percentage
3. Add any important notes or blockers
4. Update the "Next PR to Implement" section
5. Update overall progress percentage
6. Commit changes to the progress document

## Notes for AI Agents

### Critical Context
- **Rules Location**: Global rules in `~/.safeshell/rules.yaml`, local in `.safeshell/rules.yaml`
- **Default Rules**: Currently defined in `src/safeshell/rules/defaults.py`
- **Context Filters**: Use `ai_only: true` or `human_only: true` for context-specific rules
- **Actions**: allow, deny, require_approval, redirect

### Common Pitfalls to Avoid
- Don't create rules that block normal development workflows
- Don't forget to test rules with actual commands
- Don't create overly broad patterns that cause false positives
- Remember that conditions are bash expressions that must exit 0 to match

### Resources
- Rules guide: .ai/howtos/how-to-write-rules.md
- Rules schema: src/safeshell/rules/schema.py
- Default rules: src/safeshell/rules/defaults.py
- Evaluator: src/safeshell/rules/evaluator.py

## Definition of Done

The feature is considered complete when:
- [ ] 50+ comprehensive global rules exist
- [ ] Rules cover destructive operations, sensitive data, git, AI patterns
- [ ] Local rules examples created and tested
- [ ] All rules documented with descriptions
- [ ] Integration tested with Claude Code
- [ ] No significant false positives
- [ ] Rules guide updated with new examples
