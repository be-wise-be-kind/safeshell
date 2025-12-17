# How to: Debug Rules

**Purpose**: Step-by-step guide for testing and debugging SafeShell rules

**Scope**: Rule testing, condition debugging, performance troubleshooting

**Overview**: This guide covers techniques for testing rules before deploying, debugging rule
    matching issues, and troubleshooting performance problems. Essential for rule authors
    who need to validate their rules work as intended.

**Dependencies**: safeshell CLI, daemon running

**Exports**: Debugging techniques, testing workflows, troubleshooting procedures

**Related**: how-to-write-rules.md, how-to-understand-rule-evaluation.md

**Implementation**: Practical debugging workflows with examples

---

## Using safeshell check

The `safeshell check` command is your primary tool for testing rules.

### Basic Usage

```bash
# Check if a command would be allowed
safeshell check "rm -rf /tmp/test"

# Output shows:
# - Decision (ALLOW, DENY, REQUIRE_APPROVAL)
# - Matching rule (if any)
# - Reason for decision
```

### Testing Different Contexts

```bash
# Test as AI context
SAFESHELL_CONTEXT=ai safeshell check "git push --force"

# Test as human context
SAFESHELL_CONTEXT=human safeshell check "git push --force"
```

### Testing in Specific Directories

```bash
# Test directory-specific rules
cd /path/to/project
safeshell check "git checkout main"
```

---

## Enabling Debug Logging

### Daemon Logs

```bash
# View daemon logs
safeshell daemon logs

# Or check log file directly
cat ~/.safeshell/logs/daemon.log
```

### Enable Verbose Mode

```bash
# Start daemon with debug logging
safeshell daemon start --debug

# Check logs for detailed evaluation trace
safeshell daemon logs -f
```

---

## Inspecting Loaded Rules

### List All Loaded Rules

```bash
# Show rules status
safeshell status

# This displays:
# - Number of loaded rules
# - Rule sources (default, global, repo)
# - Any loading errors
```

### Validate Rule Files

```bash
# Validate rule syntax
safeshell rules validate

# Check specific rule file
safeshell rules validate --file ~/.safeshell/rules.yaml
```

---

## Testing Individual Conditions

### Understanding Condition Evaluation

Rules use structured Python conditions. To test them:

1. **Identify the condition type** from rule definition
2. **Create test scenario** that should match/not match
3. **Use safeshell check** to verify behavior

### Example: Testing GitBranchIn Condition

```yaml
# Rule to test
- name: protect-main-branch
  commands: ["git"]
  conditions:
    - type: git_branch_in
      branches: ["main", "master"]
  action: require_approval
```

```bash
# Test on main branch
cd /repo/on/main
safeshell check "git push"
# Should: REQUIRE_APPROVAL

# Test on feature branch
cd /repo/on/feature
safeshell check "git push"
# Should: ALLOW
```

### Example: Testing CommandContains Condition

```yaml
# Rule to test
- name: block-force-flag
  conditions:
    - type: command_contains
      pattern: "--force"
  action: deny
```

```bash
safeshell check "git push --force"
# Should: DENY

safeshell check "git push"
# Should: ALLOW
```

---

## Common Issues

### Regex Escaping Problems

**Problem**: Rule doesn't match expected commands

**Cause**: Special regex characters not escaped

```yaml
# WRONG - . matches any character
- type: command_matches
  pattern: "rm .env"

# CORRECT - escape the dot
- type: command_matches
  pattern: "rm \\.env"
```

**Debug**: Test pattern in Python
```python
import re
pattern = r"rm \.env"
re.match(pattern, "rm .env")  # Should match
re.match(pattern, "rm xenv")  # Should NOT match
```

### Directory Pattern Issues

**Problem**: Rule applies in wrong directories

**Cause**: Glob pattern too broad or too narrow

```yaml
# Too broad - matches anywhere
directory: "**/*"

# Better - specific project type
directory: "**/node_modules/**"
```

**Debug**: Check current directory matching
```bash
# Verify directory detection
pwd
safeshell check "npm install"
```

### Condition Timeout Issues

**Problem**: Rule evaluation slow or timing out

**Cause**: Expensive condition evaluation

**Debug**:
```bash
# Enable timing in logs
safeshell daemon start --debug

# Look for slow conditions
grep "condition.*ms" ~/.safeshell/logs/daemon.log
```

**Fix**: Optimize conditions or use fast-path
```yaml
# Add commands field for fast-path optimization
commands: ["npm", "yarn"]  # Only evaluate for these commands
```

---

## Performance Debugging

### Identifying Slow Rules

```bash
# Enable profiling
safeshell perf benchmark

# This shows:
# - Average evaluation time
# - Slowest rules
# - Condition timing
```

### Common Performance Issues

1. **No commands field**: Rule evaluated for ALL commands
2. **Complex regex**: Use simple patterns when possible
3. **Many conditions**: Conditions are AND'd; first failure exits early

### Optimization Strategies

```yaml
# SLOW - no fast-path
- name: slow-rule
  conditions:
    - type: command_matches
      pattern: ".*dangerous.*"
  action: deny

# FAST - fast-path via commands
- name: fast-rule
  commands: ["rm", "mv", "cp"]
  conditions:
    - type: command_matches
      pattern: ".*dangerous.*"
  action: deny
```

---

## Rule Loading Order

Rules load in this order (later rules can override):

1. **Default rules** - Built into SafeShell
2. **Global rules** - `~/.safeshell/rules.yaml`
3. **Repo rules** - `.safeshell/rules.yaml` in working directory

### Debugging Load Order

```bash
# Check which rules are active
safeshell status --verbose

# Shows source file for each rule
```

### Override Behavior

- Repo rules can only ADD restrictions
- Repo rules CANNOT make global rules more permissive
- This prevents malicious repos from disabling protections

---

## Testing Workflow

### Before Deploying New Rules

1. **Write rule** in test file
2. **Validate syntax**: `safeshell rules validate --file test-rules.yaml`
3. **Test with check**: Test various commands
4. **Test contexts**: Test AI and human contexts
5. **Test directories**: Test in relevant directories
6. **Deploy**: Copy to `~/.safeshell/rules.yaml`
7. **Restart daemon**: `safeshell daemon restart`
8. **Verify**: Run checks again

### Example Test Session

```bash
# Create test rule
cat > /tmp/test-rule.yaml << 'EOF'
- name: test-block-docker-rm
  commands: ["docker"]
  conditions:
    - type: command_contains
      pattern: "rm"
  action: require_approval
  message: "Docker remove requires approval"
EOF

# Validate
safeshell rules validate --file /tmp/test-rule.yaml

# Test scenarios
safeshell check "docker rm container"      # Should: REQUIRE_APPROVAL
safeshell check "docker ps"                 # Should: ALLOW
safeshell check "docker rmi image"          # Should: REQUIRE_APPROVAL (has "rm")

# Deploy if tests pass
cp /tmp/test-rule.yaml ~/.safeshell/rules.yaml
safeshell daemon restart
```

---

## Quick Debugging Checklist

- [ ] Is the daemon running? (`safeshell status`)
- [ ] Are rules loaded? (`safeshell status`)
- [ ] Is rule syntax valid? (`safeshell rules validate`)
- [ ] Does `safeshell check` show expected result?
- [ ] Is the context correct (AI vs human)?
- [ ] Is the directory correct for directory-scoped rules?
- [ ] Are regex patterns properly escaped?
- [ ] Is the commands field set for fast-path?
