"""
File: src/safeshell/rules/aws.py
Purpose: AWS CLI rules shipped with SafeShell
Exports: AWS_RULES_YAML
Depends: None
Overview: Contains AWS CLI rules for protecting cloud resources from AI modifications
"""

AWS_RULES_YAML = """\
# ==========================================================================
# CATEGORY: AWS CLI
# Prevent AI agents from using AWS SSM without approval
# SSM provides remote access to infrastructure (sessions, command execution,
# parameter management) and is inherently sensitive
# ==========================================================================

rules:
  # REQUIRE_APPROVAL: All AWS SSM operations
  - name: approve-aws-ssm
    commands: ["aws"]
    conditions:
      - command_matches: "^aws\\\\s+ssm\\\\s+"
    action: require_approval
    context: ai_only
    message: "AWS SSM provides remote infrastructure access. All SSM operations require approval."
"""
