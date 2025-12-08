"""
File: src/safeshell/rules/defaults.py
Purpose: Default rules shipped with SafeShell
Exports: DEFAULT_RULES_YAML
Depends: None
Overview: Contains the default rules that are created by 'safeshell init'
"""

DEFAULT_RULES_YAML = """\
# SafeShell Rules Configuration
# See https://github.com/safeshell/safeshell for documentation
#
# Rule Schema:
#   name: Unique identifier for logging
#   commands: List of executables this rule applies to (fast-path filter)
#   conditions: Bash conditions (all must exit 0 for rule to match)
#   action: deny | require_approval | redirect
#   message: User-facing message
#
# Available variables in conditions:
#   $CMD - Full command string
#   $ARGS - Arguments after executable
#   $PWD - Current working directory

rules:
  # Block commits on protected branches
  - name: block-commit-protected-branch
    commands: ["git"]
    conditions:
      - 'echo "$CMD" | grep -qE "^git\\s+commit"'
      - "git branch --show-current 2>/dev/null | grep -qE '^(main|master|develop)$'"
    action: deny
    message: "Cannot commit directly to protected branch. Create a feature branch first."

  # Require approval for force push to protected branches
  - name: approve-force-push-protected-branch
    commands: ["git"]
    conditions:
      - 'echo "$CMD" | grep -qE "^git\\s+push.*(--force|-f|--force-with-lease)"'
      - "git branch --show-current 2>/dev/null | grep -qE '^(main|master|develop)$'"
    action: require_approval
    message: "Force push to protected branch requires approval. This is a destructive operation."
"""
