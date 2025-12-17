"""
File: src/safeshell/rules/github.py
Purpose: GitHub CLI rules shipped with SafeShell
Exports: GITHUB_RULES_YAML
Depends: None
Overview: Contains GitHub CLI rules for protecting repositories from AI modifications
"""

GITHUB_RULES_YAML = """\
# ==========================================================================
# CATEGORY: GITHUB CLI
# Prevent AI agents from modifying GitHub resources without approval
# Specific high-risk operations first, then catch-all patterns
# ==========================================================================

rules:
  # REQUIRE_APPROVAL: Workflow run operations (user-reported as common issue)
  - name: approve-gh-workflow-run
    commands: ["gh"]
    conditions:
      - command_matches: "^gh\\\\s+workflow\\\\s+run"
    action: require_approval
    context: ai_only
    message: "Triggering GitHub workflow run requires approval."

  - name: approve-gh-run-rerun
    commands: ["gh"]
    conditions:
      - command_matches: "^gh\\\\s+run\\\\s+rerun"
    action: require_approval
    context: ai_only
    message: "Re-running GitHub workflow requires approval."

  - name: approve-gh-run-cancel
    commands: ["gh"]
    conditions:
      - command_matches: "^gh\\\\s+run\\\\s+cancel"
    action: require_approval
    context: ai_only
    message: "Cancelling GitHub workflow run requires approval."

  - name: approve-gh-run-watch
    commands: ["gh"]
    conditions:
      - command_matches: "^gh\\\\s+run\\\\s+watch"
    action: require_approval
    context: ai_only
    message: "Watching GitHub workflow run requires approval (may have side effects)."

  # REQUIRE_APPROVAL: Repository operations (most dangerous)
  - name: approve-gh-repo-delete
    commands: ["gh"]
    conditions:
      - command_matches: "^gh\\\\s+repo\\\\s+delete"
    action: require_approval
    context: ai_only
    message: "Deleting GitHub repository is EXTREMELY dangerous. Verify this is intended."

  - name: approve-gh-repo-create
    commands: ["gh"]
    conditions:
      - command_matches: "^gh\\\\s+repo\\\\s+create"
    action: require_approval
    context: ai_only
    message: "Creating GitHub repository requires approval."

  - name: approve-gh-repo-archive
    commands: ["gh"]
    conditions:
      - command_matches: "^gh\\\\s+repo\\\\s+archive"
    action: require_approval
    context: ai_only
    message: "Archiving GitHub repository requires approval."

  - name: approve-gh-repo-rename
    commands: ["gh"]
    conditions:
      - command_matches: "^gh\\\\s+repo\\\\s+rename"
    action: require_approval
    context: ai_only
    message: "Renaming GitHub repository requires approval."

  - name: approve-gh-repo-edit
    commands: ["gh"]
    conditions:
      - command_matches: "^gh\\\\s+repo\\\\s+edit"
    action: require_approval
    context: ai_only
    message: "Editing GitHub repository settings requires approval."

  # REQUIRE_APPROVAL: Release operations
  - name: approve-gh-release-create
    commands: ["gh"]
    conditions:
      - command_matches: "^gh\\\\s+release\\\\s+create"
    action: require_approval
    context: ai_only
    message: "Creating GitHub release requires approval."

  - name: approve-gh-release-delete
    commands: ["gh"]
    conditions:
      - command_matches: "^gh\\\\s+release\\\\s+delete"
    action: require_approval
    context: ai_only
    message: "Deleting GitHub release requires approval."

  - name: approve-gh-release-edit
    commands: ["gh"]
    conditions:
      - command_matches: "^gh\\\\s+release\\\\s+edit"
    action: require_approval
    context: ai_only
    message: "Editing GitHub release requires approval."

  # REQUIRE_APPROVAL: Deploy key operations
  - name: approve-gh-deploy-key-add
    commands: ["gh"]
    conditions:
      - command_matches: "^gh\\\\s+repo\\\\s+deploy-key\\\\s+add"
    action: require_approval
    context: ai_only
    message: "Adding deploy key grants repository access. Verify this is intended."

  - name: approve-gh-deploy-key-delete
    commands: ["gh"]
    conditions:
      - command_matches: "^gh\\\\s+repo\\\\s+deploy-key\\\\s+delete"
    action: require_approval
    context: ai_only
    message: "Deleting deploy key requires approval."

  # REQUIRE_APPROVAL: Secrets management
  - name: approve-gh-secret-set
    commands: ["gh"]
    conditions:
      - command_matches: "^gh\\\\s+secret\\\\s+set"
    action: require_approval
    context: ai_only
    message: "Setting GitHub secret requires approval."

  - name: approve-gh-secret-delete
    commands: ["gh"]
    conditions:
      - command_matches: "^gh\\\\s+secret\\\\s+delete"
    action: require_approval
    context: ai_only
    message: "Deleting GitHub secret requires approval."

  # REQUIRE_APPROVAL: Variable management
  - name: approve-gh-variable-set
    commands: ["gh"]
    conditions:
      - command_matches: "^gh\\\\s+variable\\\\s+set"
    action: require_approval
    context: ai_only
    message: "Setting GitHub variable requires approval."

  - name: approve-gh-variable-delete
    commands: ["gh"]
    conditions:
      - command_matches: "^gh\\\\s+variable\\\\s+delete"
    action: require_approval
    context: ai_only
    message: "Deleting GitHub variable requires approval."

  # REQUIRE_APPROVAL: Issue operations
  - name: approve-gh-issue-close
    commands: ["gh"]
    conditions:
      - command_matches: "^gh\\\\s+issue\\\\s+close"
    action: require_approval
    context: ai_only
    message: "Closing GitHub issue requires approval."

  - name: approve-gh-issue-delete
    commands: ["gh"]
    conditions:
      - command_matches: "^gh\\\\s+issue\\\\s+delete"
    action: require_approval
    context: ai_only
    message: "Deleting GitHub issue requires approval."

  - name: approve-gh-issue-edit
    commands: ["gh"]
    conditions:
      - command_matches: "^gh\\\\s+issue\\\\s+edit"
    action: require_approval
    context: ai_only
    message: "Editing GitHub issue requires approval."

  - name: approve-gh-issue-transfer
    commands: ["gh"]
    conditions:
      - command_matches: "^gh\\\\s+issue\\\\s+transfer"
    action: require_approval
    context: ai_only
    message: "Transferring GitHub issue requires approval."

  # REQUIRE_APPROVAL: PR operations
  - name: approve-gh-pr-close
    commands: ["gh"]
    conditions:
      - command_matches: "^gh\\\\s+pr\\\\s+close"
    action: require_approval
    context: ai_only
    message: "Closing GitHub PR requires approval."

  - name: approve-gh-pr-merge
    commands: ["gh"]
    conditions:
      - command_matches: "^gh\\\\s+pr\\\\s+merge"
    action: require_approval
    context: ai_only
    message: "Merging GitHub PR requires approval."

  - name: approve-gh-pr-edit
    commands: ["gh"]
    conditions:
      - command_matches: "^gh\\\\s+pr\\\\s+edit"
    action: require_approval
    context: ai_only
    message: "Editing GitHub PR requires approval."

  # REQUIRE_APPROVAL: Catch-all for any gh ... delete
  - name: approve-gh-delete
    commands: ["gh"]
    conditions:
      - command_matches: "^gh\\\\s+\\\\S+.*\\\\s+delete(\\\\s|$)"
    action: require_approval
    context: ai_only
    message: "GitHub delete operation requires approval."

  # REQUIRE_APPROVAL: Catch-all for any gh ... create
  - name: approve-gh-create
    commands: ["gh"]
    conditions:
      - command_matches: "^gh\\\\s+\\\\S+.*\\\\s+create(\\\\s|$)"
    action: require_approval
    context: ai_only
    message: "GitHub create operation requires approval."
"""
