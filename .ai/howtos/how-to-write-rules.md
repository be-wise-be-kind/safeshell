File: .ai/howtos/how-to-write-rules.md

Purpose: Guide for writing SafeShell YAML rules

Exports: Rule schema reference, example rules, condition patterns

Depends: rules module documentation

Overview: Step-by-step guide for creating custom SafeShell rules using YAML
    configuration. Covers rule schema, bash conditions, variable usage,
    and best practices for rule design.

# How to: Write SafeShell Rules

**Purpose**: Guide for writing custom SafeShell rules

**Scope**: Rule schema, conditions, and examples

**Overview**: This guide explains how to write YAML-based rules for SafeShell
    to protect against dangerous operations, require approval for risky commands,
    or redirect commands to safer alternatives.

**Dependencies**: SafeShell installed, `safeshell init` run

**Exports**: Rule patterns, condition examples, best practices

**Related**: how-to-use-safeshell-cli.md

**Implementation**: YAML configuration with bash conditions

---

## Overview

SafeShell uses YAML-based rules to evaluate shell commands. Rules are loaded from:
1. **Global rules**: `~/.safeshell/rules.yaml` (your personal protections)
2. **Repo rules**: `.safeshell/rules.yaml` (project-specific, additive only)

Repo rules can only add restrictions, never relax global rules.

---

## Rule Schema

```yaml
rules:
  - name: "unique-rule-identifier"
    commands: ["git", "rm"]           # Executables this rule applies to
    directory: ".*sensitive.*"        # Optional: regex pattern for working dir
    conditions:                       # Bash conditions (all must exit 0)
      - 'echo "$CMD" | grep -qE "pattern"'
    action: deny                      # deny | require_approval | redirect
    redirect_to: "safe-command $ARGS" # Required if action is redirect
    message: "User-facing message"
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Unique identifier for logging |
| `commands` | list[string] | Executables this rule applies to |
| `action` | enum | `deny`, `require_approval`, or `redirect` |
| `message` | string | Message shown to user when rule matches |

### Optional Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `directory` | string | null | Regex pattern for working directory |
| `conditions` | list[string] | [] | Bash conditions (all must pass) |
| `redirect_to` | string | null | Command to redirect to (required for redirect action) |
| `allow_override` | bool | true | Whether repo rules can override |

---

## Available Variables

Use these variables in conditions:

| Variable | Description | Example Value |
|----------|-------------|---------------|
| `$CMD` | Full command string | `git commit -m "test"` |
| `$ARGS` | Arguments after executable | `-m "test"` |
| `$PWD` | Current working directory | `/home/user/project` |

---

## Writing Conditions

Conditions are bash commands that must exit with code 0 for the rule to match.
All conditions must pass for the rule to trigger.

### Pattern Matching with grep

```yaml
# Match command pattern
conditions:
  - 'echo "$CMD" | grep -qE "^git\\s+commit"'

# Match any of several patterns
conditions:
  - 'echo "$CMD" | grep -qE "(--force|-f|--force-with-lease)"'
```

### Git Branch Detection

```yaml
# Block on protected branches
conditions:
  - 'echo "$CMD" | grep -qE "^git\\s+commit"'
  - 'git branch --show-current 2>/dev/null | grep -qE "^(main|master|develop)$"'
```

### File Path Detection

```yaml
# Block deletion of important files
conditions:
  - 'echo "$CMD" | grep -qE "\\.(env|pem|key)$"'
```

### Directory-Based Rules

```yaml
# Only apply in production directories
directory: ".*/production/.*"
conditions:
  - 'echo "$CMD" | grep -qE "^rm\\s+-rf"'
```

---

## Example Rules

### Block Git Commits on Protected Branches

```yaml
- name: block-commit-protected-branch
  commands: ["git"]
  conditions:
    - 'echo "$CMD" | grep -qE "^git\\s+commit"'
    - 'git branch --show-current 2>/dev/null | grep -qE "^(main|master|develop)$"'
  action: deny
  message: "Cannot commit directly to protected branch. Create a feature branch first."
```

### Require Approval for Force Push

```yaml
- name: approve-force-push
  commands: ["git"]
  conditions:
    - 'echo "$CMD" | grep -qE "^git\\s+push.*(--force|-f)"'
  action: require_approval
  message: "Force push requires approval. This is a destructive operation."
```

### Redirect rm to Trash

```yaml
- name: rm-to-trash
  commands: ["rm"]
  conditions:
    - 'echo "$CMD" | grep -qvE "^rm\\s+-rf\\s+/$"'  # Don't redirect rm -rf /
  action: redirect
  redirect_to: "trash-put $ARGS"
  message: "Redirecting rm to trash for safety"
```

### Block Curl to Internal Networks

```yaml
- name: block-internal-curl
  commands: ["curl", "wget"]
  conditions:
    - 'echo "$CMD" | grep -qE "(192\\.168\\.|10\\.|172\\.16\\.)"'
  action: deny
  message: "Cannot access internal network addresses from this context."
```

### Require Approval for Database Operations

```yaml
- name: approve-db-operations
  commands: ["psql", "mysql", "mongo"]
  directory: ".*/production/.*"
  action: require_approval
  message: "Database operations in production require approval."
```

---

## Testing Rules

Test your rules without executing commands:

```bash
# Check if a command would be blocked
safeshell check "git commit -m 'test'"

# Check from a specific directory
cd /path/to/project && safeshell check "rm -rf node_modules"
```

---

## Best Practices

1. **Be specific with patterns**: Use anchors (`^`, `$`) and word boundaries
2. **Test conditions manually**: Run bash conditions in terminal first
3. **Use meaningful names**: Rule names appear in logs
4. **Write clear messages**: Users need to understand why they're blocked
5. **Start restrictive**: It's easier to relax rules than tighten them
6. **Use fast-path filtering**: Always specify `commands` to skip unrelated commands

### Condition Tips

```yaml
# Good: Specific pattern with anchors
conditions:
  - 'echo "$CMD" | grep -qE "^git\\s+commit"'

# Bad: Overly broad pattern
conditions:
  - 'echo "$CMD" | grep -q "commit"'  # Matches "git commit", "svn commit", etc.
```

### Error Handling

Conditions should handle errors gracefully:

```yaml
# Good: Suppress errors, fail gracefully
conditions:
  - 'git branch --show-current 2>/dev/null | grep -qE "^main$"'

# Bad: Will fail noisily outside git repos
conditions:
  - 'git branch --show-current | grep -qE "^main$"'
```

---

## Rule Evaluation Flow

1. Command received (e.g., `git commit -m test`)
2. Extract executable (`git`)
3. **Fast-path**: If executable not in any rule's `commands` list, ALLOW
4. For each matching rule:
   - Check directory pattern (if specified)
   - Run bash conditions (all must pass, 100ms timeout per condition)
   - If all match, apply action
5. **Aggregate**: Most restrictive decision wins (DENY > REQUIRE_APPROVAL > REDIRECT > ALLOW)

---

## Troubleshooting

### Rule Not Matching

1. Verify the command is in the `commands` list
2. Test conditions manually: `echo "your command" | grep -qE "pattern" && echo "match"`
3. Check for escaping issues in regex patterns

### Conditions Timing Out

Conditions have a 100ms timeout by default. If a condition is slow:
- Use simpler patterns
- Avoid network calls in conditions
- Use cached/local data when possible

### Repo Rules Being Ignored

Repo rules are only loaded if `.safeshell/rules.yaml` exists in the current
directory or a parent directory.

---

## File Locations

| File | Purpose |
|------|---------|
| `~/.safeshell/rules.yaml` | Global rules (apply everywhere) |
| `.safeshell/rules.yaml` | Repo-specific rules (additive) |

---

## Overriding Default Rules

Default rules are built into SafeShell, but you can override or disable them in your
global `~/.safeshell/rules.yaml` file using the `overrides` section.

**Note**: For security, repo rules (`.safeshell/rules.yaml`) cannot override default
or global rules - only the user's global config can do this.

### Override Schema

```yaml
overrides:
  - name: "rule-name-to-override"
    disabled: true                   # Remove this rule entirely
    action: require_approval         # Or change the action
    message: "Custom message"        # Or change the message
    context: human_only              # Or change the context
    allow_override: false            # Or change allow_override
```

### Disable a Default Rule

```yaml
# ~/.safeshell/rules.yaml
rules: []

overrides:
  - name: approve-force-push
    disabled: true  # I know what I'm doing with force push
```

### Change Action from Deny to Approval

```yaml
# ~/.safeshell/rules.yaml
rules: []

overrides:
  - name: deny-rm-rf-star
    action: require_approval
    message: "Are you sure you want to rm -rf *?"
```

### Change Context

```yaml
# ~/.safeshell/rules.yaml
rules: []

overrides:
  - name: approve-pip-install
    context: human_only  # Only apply to human terminals, not AI
```

### Viewing Available Default Rules

To see which default rules you can override:

```bash
# List all loaded rules
safeshell rules validate -v
```

---

## Verification Checklist

Before deploying rules:
- [ ] Rules have unique names
- [ ] Commands list is accurate
- [ ] Conditions tested manually
- [ ] Messages are user-friendly
- [ ] Tested with `safeshell check`
