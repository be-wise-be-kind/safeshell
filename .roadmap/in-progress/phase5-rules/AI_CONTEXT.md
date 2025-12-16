# Production Rules Development - AI Context

**Purpose**: AI agent context document for implementing Production Rules Development

**Scope**: Comprehensive rule set preventing common AI coding assistant mistakes

**Overview**: Comprehensive context document for AI agents working on the Production Rules Development feature.
    This document provides architectural context, design decisions, and implementation guidance for
    creating a robust set of default rules that protect users from common AI mistakes.

**Dependencies**: Phase 4 (Architecture Review) - rules engine must be validated

**Exports**: Context for rule design, patterns, and implementation guidance

**Related**: PR_BREAKDOWN.md for implementation tasks, PROGRESS_TRACKER.md for current status

**Implementation**: Incremental rule development with testing and validation

---

## Overview

SafeShell needs a comprehensive set of production rules that:
1. Prevent destructive operations (rm -rf /, chmod 777, etc.)
2. Protect sensitive data (.env files, SSH keys, credentials)
3. Enforce git safety (no force push to main, no hard reset)
4. Block common AI coding assistant mistakes
5. Allow customization through local repository rules

## Project Background

### Current State
- Basic rules engine exists and is functional
- Default rules are minimal (demo-level)
- Rules schema supports patterns, conditions, actions
- Context-aware filtering (ai_only/human_only) is implemented
- Local rules (.safeshell/rules.yaml) can override global rules

### Target State
- 50+ comprehensive global rules
- Coverage of all major risk categories
- Example local rules for different project types
- Documentation with rationale for each rule
- Integration tested with Claude Code

### Rule System Capabilities
The rules engine supports:
- **Pattern matching**: Simple glob/substring matching
- **Bash conditions**: Complex matching via bash expressions
- **Actions**: allow, deny, require_approval, redirect
- **Context filters**: ai_only, human_only
- **Priorities**: Local rules take precedence over global

## Feature Vision

### Rule Categories

1. **Destructive Operations**
   - Recursive deletes (rm -rf)
   - Permission changes (chmod 777)
   - System directory modifications
   - Disk operations (dd, mkfs)

2. **Sensitive Data Protection**
   - Environment files (.env, .env.local)
   - SSH keys (~/.ssh/)
   - Credential files (credentials.json, secrets.yaml)
   - API keys and tokens in commands

3. **Git Safety**
   - Force push prevention
   - Hard reset protection
   - Main/master branch protection
   - Clean with force protection

4. **AI-Specific Patterns**
   - Global package installation
   - Shell configuration modification
   - Curl/wget piped to bash
   - Privileged docker operations
   - Sudo commands from AI

5. **Local/Repository Rules**
   - Project-specific protections
   - Deployment workflows
   - Custom approval requirements

### Design Principles

1. **Fail Safe**: Dangerous operations should be blocked by default
2. **Minimal Friction**: Safe operations should pass without interruption
3. **Context Awareness**: Use ai_only for AI-specific restrictions
4. **Clear Communication**: Every denial should explain why
5. **Customizable**: Users can add/override rules per repository

## Current Application Context

### Rules Engine Architecture
```
~/.safeshell/rules.yaml (Global)
         ↓
.safeshell/rules.yaml (Local - overrides global)
         ↓
    Rules Loader
         ↓
    Rules Evaluator
         ↓
    Action (allow/deny/require_approval)
```

### Rule Schema
```yaml
rules:
  - name: rule-name           # Required: unique identifier
    description: "Why"        # Required: explanation
    pattern: "simple match"   # Optional: substring match
    conditions:               # Optional: bash expressions
      - "bash expression 1"   # All must exit 0 to match
      - "bash expression 2"
    action: deny              # Required: allow|deny|require_approval|redirect
    ai_only: true            # Optional: only apply to AI tools
    human_only: true         # Optional: only apply to humans
```

### Environment Variables in Conditions
Available in bash conditions:
- `$SAFESHELL_COMMAND` - The full command being evaluated
- `$SAFESHELL_CWD` - Current working directory
- `$SAFESHELL_CONTEXT` - "ai" or "human"

### Key Files
- `src/safeshell/rules/schema.py` - Rule schema definitions
- `src/safeshell/rules/loader.py` - Loads rules from YAML
- `src/safeshell/rules/evaluator.py` - Evaluates rules against commands
- `src/safeshell/rules/defaults.py` - Default rules (currently minimal)

## Target Architecture

### Rule Organization

**Global Rules** (`~/.safeshell/rules.yaml`):
```yaml
# Categories organized by severity
rules:
  # CRITICAL: Always block
  - name: block-rm-rf-root
    ...

  # HIGH: Block for AI, require approval for humans
  - name: block-env-access
    ai_only: true
    ...

  # MEDIUM: Require approval
  - name: approve-force-push
    ...
```

**Local Rules** (`.safeshell/rules.yaml`):
```yaml
# Project-specific overrides
rules:
  - name: project-specific-rule
    ...
```

### Rule Precedence
1. Local rules evaluated first
2. If no match, global rules evaluated
3. First matching rule wins
4. No match = allow (implicit)

## Key Decisions Made

### Decision: Comprehensive Default Rules
**Choice**: Include 50+ rules covering common scenarios
**Rationale**: Users get immediate protection without configuration
**Trade-off**: More rules = more maintenance, potential for false positives

### Decision: ai_only for Most Restrictive Rules
**Choice**: Many rules only apply when context is "ai"
**Rationale**: Humans can make informed decisions; AI cannot
**Trade-off**: Different experience for AI vs human operators

### Decision: require_approval over deny Where Possible
**Choice**: Prefer approval workflow over outright denial
**Rationale**: Allows legitimate use cases with human oversight
**Trade-off**: More interruptions, but fewer blocked workflows

### Decision: Bash Conditions for Complex Matching
**Choice**: Use bash expressions for complex pattern matching
**Rationale**: Flexible, powerful, familiar to developers
**Trade-off**: Potential for slow evaluation, harder to debug

### Decision: Local Rules Override Global
**Choice**: Per-repository rules take precedence
**Rationale**: Projects can customize for their needs
**Trade-off**: Users could accidentally disable important protections

## Integration Points

### With Existing Features
- **Context Detection**: Uses ai_only/human_only filters
- **Approval Workflow**: Integrates with require_approval action
- **Monitor TUI**: Displays rule matches and actions
- **CLI**: `safeshell check` for testing rules

### With Claude Code
- Hook intercepts commands before execution
- Rules evaluated for each command
- Denials block execution with explanation
- Approvals pause for human decision

## Success Metrics

### Rule Coverage
- Destructive operations: 100% of common patterns
- Sensitive data: 90%+ of common file patterns
- Git safety: All dangerous operations
- AI patterns: Common mistakes identified and blocked

### Quality Metrics
- False positive rate: < 1%
- Rule evaluation time: < 1ms per rule
- User override rate: Tracked for improvement

### User Experience
- Clear denial messages
- Obvious approval requests
- Easy local customization

## Technical Constraints

### Condition Evaluation
- Conditions run as bash subprocesses
- Default timeout: 100ms per condition
- All conditions must exit 0 to match
- Slow conditions can impact command latency

### Pattern Matching
- Simple substring matching for `pattern` field
- Use conditions for regex or complex matching
- Order matters: first match wins

### YAML Parsing
- Must be valid YAML
- Special characters need quoting
- Regex in conditions needs escaping

## AI Agent Guidance

### When Writing Rules

1. **Start with the threat model**: What are we protecting against?
2. **Use specific patterns**: Avoid overly broad matches
3. **Test thoroughly**: Use `safeshell check` for each rule
4. **Document rationale**: Every rule needs a clear description
5. **Consider context**: Use ai_only/human_only appropriately

### When Testing Rules

```bash
# Test a specific command
safeshell check "rm -rf /"

# Test with context
SAFESHELL_CONTEXT=ai safeshell check "cat .env"

# Test in project directory
cd /path/to/project
safeshell check "rm database.sqlite"
```

### Common Patterns

**Substring Match (Simple)**:
```yaml
- name: block-pattern
  pattern: "rm -rf"
  action: deny
```

**Regex Match (Complex)**:
```yaml
- name: block-pattern
  conditions:
    - "echo $SAFESHELL_COMMAND | grep -qE 'rm.*-rf.*\\/'"
  action: deny
```

**Multiple Conditions (AND)**:
```yaml
- name: block-on-main
  conditions:
    - "echo $SAFESHELL_COMMAND | grep -q 'git commit'"
    - "git rev-parse --abbrev-ref HEAD | grep -qE '^(main|master)$'"
  action: deny
```

**Context-Aware**:
```yaml
- name: ai-only-block
  pattern: "dangerous command"
  action: deny
  ai_only: true
```

## Risk Mitigation

### Risk: False Positives
**Mitigation**:
- Test rules extensively before deployment
- Use specific patterns over broad ones
- Provide clear override mechanisms
- Track and fix reported false positives

### Risk: Performance Impact
**Mitigation**:
- Keep conditions simple and fast
- Limit condition timeout to 100ms
- Profile rule evaluation regularly
- Optimize hot paths

### Risk: User Frustration
**Mitigation**:
- Prefer require_approval over deny
- Provide clear explanations
- Make local overrides easy
- Document common customizations

### Risk: Security Bypass
**Mitigation**:
- Test rules with various bypass attempts
- Consider edge cases and encoding
- Regular security review of rules
- Community feedback on gaps

## Future Enhancements

### After Initial Release
- Rule effectiveness monitoring
- Community-contributed rules
- Rule suggestion system
- Automatic rule updates

### Long-term Vision
- Machine learning for rule suggestions
- Integration with other AI tools
- Cross-platform rule compatibility
- Enterprise rule management
