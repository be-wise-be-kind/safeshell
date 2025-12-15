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
#   conditions: Structured conditions (all must pass for rule to match)
#   action: deny | require_approval | redirect
#   message: User-facing message
#
# Condition Types:
#   - command_matches: "regex"      Match command against regex
#   - command_contains: "string"    Check if command contains substring
#   - command_startswith: "prefix"  Check if command starts with prefix
#   - git_branch_in: ["main", ...]  Check if on one of these branches
#   - git_branch_matches: "regex"   Match branch name against regex
#   - in_git_repo: true/false       Check if in a git repository
#   - path_matches: "regex"         Match working directory
#   - file_exists: "path"           Check if file exists
#   - env_equals: {variable, value} Check environment variable

rules:
  # Block commits on protected branches
  - name: block-commit-protected-branch
    commands: ["git"]
    conditions:
      - command_matches: "^git\\\\s+commit"
      - git_branch_in: ["main", "master", "develop"]
    action: deny
    message: "Cannot commit directly to protected branch. Create a feature branch first."

  # Require approval for force push to protected branches
  - name: approve-force-push-protected-branch
    commands: ["git"]
    conditions:
      - command_matches: "^git\\\\s+push.*(--force|-f|--force-with-lease)"
      - git_branch_in: ["main", "master", "develop"]
    action: require_approval
    message: "Force push to protected branch requires approval. This is a destructive operation."
"""
