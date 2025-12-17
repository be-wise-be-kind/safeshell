# How to: Understand Rule Evaluation

**Purpose**: Deep dive into how SafeShell evaluates rules

**Scope**: Evaluation flow, condition types, decision aggregation, performance optimization

**Overview**: This guide explains the complete rule evaluation pipeline from command input to
    final decision. Understanding this flow is essential for writing effective rules and
    debugging unexpected behavior.

**Dependencies**: rules/evaluator.py, rules/condition_types.py

**Exports**: Evaluation flow knowledge, optimization strategies

**Related**: how-to-write-rules.md, how-to-debug-rules.md

**Implementation**: Architectural explanation with diagrams and examples

---

## Evaluation Flow Overview

When SafeShell intercepts a command, it follows this evaluation pipeline:

```
Command Input
     │
     ▼
┌─────────────────┐
│ Extract Command │  Parse executable and arguments
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Fast-Path?    │  Is command in any rule's index?
└────────┬────────┘
         │
    NO ──┴── YES
    │        │
    ▼        ▼
 ALLOW   Continue
         │
         ▼
┌─────────────────┐
│ Match Directory │  Does working dir match rule's directory pattern?
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Match Context   │  Is rule for this context (AI/human/all)?
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Eval Conditions │  Do all conditions pass?
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Aggregate     │  Combine all matching rule decisions
└────────┬────────┘
         │
         ▼
   Final Decision
```

---

## Fast-Path Optimization

### What is Fast-Path?

Rules with a `commands` field are indexed. Commands NOT in any rule's index skip evaluation entirely.

```yaml
# This rule is indexed under "git"
- name: git-protection
  commands: ["git"]  # ← Enables fast-path
  action: require_approval
```

### How Fast-Path Works

1. **Daemon startup**: Build index of all commands from rules
2. **Command received**: Check if executable is in index
3. **Not in index**: Immediately return ALLOW (no rule evaluation)
4. **In index**: Continue to full evaluation

### Performance Impact

| Scenario | Evaluation Time |
|----------|-----------------|
| Fast-path (command not in index) | <0.1ms |
| Full evaluation (few rules) | <1ms |
| Full evaluation (many rules) | 1-5ms |

### Best Practice

Always include `commands` field when possible:

```yaml
# SLOW - evaluated for every command
- name: dangerous-pattern
  conditions:
    - type: command_contains
      pattern: "--force"
  action: deny

# FAST - only evaluated for git commands
- name: git-force-protection
  commands: ["git"]
  conditions:
    - type: command_contains
      pattern: "--force"
  action: deny
```

---

## Condition Types

SafeShell uses structured Python conditions (not bash) for performance and security.

### Command Conditions

| Condition | Description | Example |
|-----------|-------------|---------|
| `command_matches` | Regex match on full command | `pattern: "rm.*-rf"` |
| `command_contains` | Substring match | `pattern: "--force"` |
| `command_startswith` | Prefix match | `prefix: "sudo"` |

### Git Conditions

| Condition | Description | Example |
|-----------|-------------|---------|
| `git_branch_in` | Current branch in list | `branches: ["main", "master"]` |
| `git_branch_matches` | Branch matches pattern | `pattern: "release-.*"` |
| `in_git_repo` | Is working dir a git repo | `value: true` |

### Path Conditions

| Condition | Description | Example |
|-----------|-------------|---------|
| `path_matches` | Path in command matches glob | `pattern: "*.env"` |
| `file_exists` | File exists in working dir | `path: ".env"` |

### Environment Conditions

| Condition | Description | Example |
|-----------|-------------|---------|
| `env_equals` | Environment variable equals value | `name: "CI", value: "true"` |

### Example Rule with Multiple Conditions

```yaml
- name: protect-env-on-main
  commands: ["cat", "less", "head", "tail"]
  conditions:
    - type: git_branch_in
      branches: ["main", "master"]
    - type: path_matches
      pattern: "*.env*"
  action: deny
  message: "Cannot read .env files on main branch"
```

All conditions must pass (AND logic). First failing condition short-circuits.

---

## Decision Aggregation

When multiple rules match a command, SafeShell aggregates their decisions.

### Decision Precedence

```
DENY > REQUIRE_APPROVAL > REDIRECT > ALLOW
```

The **most restrictive** decision wins:

| Rule 1 Decision | Rule 2 Decision | Final Decision |
|-----------------|-----------------|----------------|
| ALLOW | ALLOW | ALLOW |
| ALLOW | REQUIRE_APPROVAL | REQUIRE_APPROVAL |
| REQUIRE_APPROVAL | DENY | DENY |
| REDIRECT | DENY | DENY |

### Example: Conflicting Rules

```yaml
# Rule 1: General git protection
- name: git-general
  commands: ["git"]
  action: require_approval

# Rule 2: Strict main branch protection
- name: git-main-deny
  commands: ["git"]
  conditions:
    - type: git_branch_in
      branches: ["main"]
  action: deny
```

On main branch:
- Rule 1 matches → REQUIRE_APPROVAL
- Rule 2 matches → DENY
- **Final**: DENY (most restrictive)

On feature branch:
- Rule 1 matches → REQUIRE_APPROVAL
- Rule 2 doesn't match
- **Final**: REQUIRE_APPROVAL

---

## Context Filtering

Rules can apply to specific contexts:

```yaml
# Only for AI agents
- name: ai-only-rule
  context: ai_only
  action: deny

# Only for humans
- name: human-only-rule
  context: human_only
  action: allow

# For both (default)
- name: all-contexts
  context: all
  action: require_approval
```

### Context Detection

SafeShell detects context via:
1. `SAFESHELL_CONTEXT` environment variable
2. Parent process detection (Claude Code, Cursor, etc.)
3. Default: `human`

---

## Directory Patterns

Rules can be scoped to specific directories:

```yaml
- name: node-modules-protection
  directory: "**/node_modules/**"
  action: deny

- name: project-specific
  directory: "/home/user/projects/myapp/**"
  action: require_approval
```

### Pattern Syntax

- `**` matches any path segment(s)
- `*` matches within a single segment
- Patterns are matched against working directory

### Example Patterns

| Pattern | Matches | Doesn't Match |
|---------|---------|---------------|
| `**/node_modules/**` | `/a/node_modules/b` | `/a/modules/b` |
| `/home/user/projects/*` | `/home/user/projects/foo` | `/home/user/projects/foo/bar` |
| `**/src/**/*.py` | `/a/src/b/c.py` | `/a/src/b/c.js` |

---

## Performance Characteristics

### Target: <1ms Evaluation

SafeShell aims for sub-millisecond evaluation to avoid noticeable delay.

### Optimization Techniques

1. **Command Indexing**: Fast-path for unmatched commands
2. **Compiled Regex**: Patterns compiled once at load time
3. **Short-Circuit Evaluation**: Conditions stop at first failure
4. **Cached Git Context**: Git branch/repo info cached per evaluation
5. **Structured Conditions**: Python classes, not bash subprocess

### What Slows Evaluation

| Issue | Impact | Solution |
|-------|--------|----------|
| No commands field | Evaluated for all commands | Add commands field |
| Complex regex | Slow pattern matching | Simplify pattern |
| Many rules | Linear scan | Reduce rule count |
| Disk I/O conditions | File system access | Use sparingly |

---

## Why Python Conditions (Not Bash)

SafeShell moved from bash conditions to structured Python for:

1. **Security**: No shell injection risk
2. **Performance**: No subprocess spawning (~250ms per call)
3. **Portability**: Works on all platforms
4. **Type Safety**: Pydantic validation catches errors early
5. **Testability**: Unit testable condition classes

### Migration from Bash

```yaml
# OLD (bash) - deprecated
conditions:
  - 'echo "$CMD" | grep -q "dangerous"'

# NEW (structured) - use this
conditions:
  - type: command_contains
    pattern: "dangerous"
```

---

## Quick Reference

### Evaluation Order
1. Extract command executable
2. Fast-path check (command index)
3. Directory matching
4. Context filtering
5. Condition evaluation
6. Decision aggregation

### Decision Precedence
`DENY > REQUIRE_APPROVAL > REDIRECT > ALLOW`

### Performance Tips
- Always use `commands` field
- Keep regex patterns simple
- Use few conditions per rule
- Avoid file system conditions when possible
