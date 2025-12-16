"""
File: src/safeshell/rules/azure.py
Purpose: Azure CLI rules shipped with SafeShell
Exports: AZURE_RULES_YAML
Depends: None
Overview: Contains Azure CLI rules for protecting cloud resources from AI modifications
"""

AZURE_RULES_YAML = """\
# ==========================================================================
# CATEGORY: AZURE CLI
# Prevent AI agents from modifying Azure resources without approval
# Specific high-risk operations first, then catch-all patterns
# ==========================================================================

rules:
  # REQUIRE_APPROVAL: Resource group deletion (most dangerous - deletes ALL contents)
  - name: approve-az-group-delete
    commands: ["az"]
    conditions:
      - command_matches: "^az\\\\s+group\\\\s+delete"
    action: require_approval
    context: ai_only
    message: "Deleting Azure resource group removes ALL resources inside. Verify this is intended."

  # REQUIRE_APPROVAL: Resource group creation
  - name: approve-az-group-create
    commands: ["az"]
    conditions:
      - command_matches: "^az\\\\s+group\\\\s+create"
    action: require_approval
    context: ai_only
    message: "Creating Azure resource group requires approval."

  # REQUIRE_APPROVAL: Deployment operations (ARM/Bicep templates)
  - name: approve-az-deployment
    commands: ["az"]
    conditions:
      - command_matches: "^az\\\\s+deployment\\\\s+.*\\\\s+(create|delete|cancel)"
    action: require_approval
    context: ai_only
    message: "Azure deployment operations can create/modify multiple resources at once."

  # REQUIRE_APPROVAL: Generic resource mutations
  - name: approve-az-resource-mutate
    commands: ["az"]
    conditions:
      - command_matches: "^az\\\\s+resource\\\\s+(delete|create|update|move)"
    action: require_approval
    context: ai_only
    message: "Azure resource modification requires approval."

  # REQUIRE_APPROVAL: Catch-all for any az ... delete
  - name: approve-az-delete
    commands: ["az"]
    conditions:
      - command_matches: "^az\\\\s+\\\\S+.*\\\\s+delete(\\\\s|$)"
    action: require_approval
    context: ai_only
    message: "Azure resource deletion requires approval."

  # REQUIRE_APPROVAL: Catch-all for any az ... create
  - name: approve-az-create
    commands: ["az"]
    conditions:
      - command_matches: "^az\\\\s+\\\\S+.*\\\\s+create(\\\\s|$)"
    action: require_approval
    context: ai_only
    message: "Azure resource creation requires approval."

  # REQUIRE_APPROVAL: Catch-all for any az ... update
  - name: approve-az-update
    commands: ["az"]
    conditions:
      - command_matches: "^az\\\\s+\\\\S+.*\\\\s+update(\\\\s|$)"
    action: require_approval
    context: ai_only
    message: "Azure resource update requires approval."

  # REQUIRE_APPROVAL: Catch-all for any az ... set (config changes)
  - name: approve-az-set
    commands: ["az"]
    conditions:
      - command_matches: "^az\\\\s+\\\\S+.*\\\\s+set(\\\\s|$)"
    action: require_approval
    context: ai_only
    message: "Azure resource configuration change requires approval."

  # REQUIRE_APPROVAL: Catch-all for any az ... set-policy (IAM/access changes)
  - name: approve-az-set-policy
    commands: ["az"]
    conditions:
      - command_matches: "^az\\\\s+\\\\S+.*\\\\s+set-policy(\\\\s|$)"
    action: require_approval
    context: ai_only
    message: "Azure policy change requires approval. This modifies access permissions."

  # REQUIRE_APPROVAL: Catch-all for any az ... add
  - name: approve-az-add
    commands: ["az"]
    conditions:
      - command_matches: "^az\\\\s+\\\\S+.*\\\\s+add(\\\\s|$)"
    action: require_approval
    context: ai_only
    message: "Azure resource addition requires approval."

  # REQUIRE_APPROVAL: Catch-all for any az ... remove
  - name: approve-az-remove
    commands: ["az"]
    conditions:
      - command_matches: "^az\\\\s+\\\\S+.*\\\\s+remove(\\\\s|$)"
    action: require_approval
    context: ai_only
    message: "Azure resource removal requires approval."

  # REQUIRE_APPROVAL: Catch-all for any az ... start/stop/restart (VM operations)
  - name: approve-az-vm-power
    commands: ["az"]
    conditions:
      - command_matches: "^az\\\\s+\\\\S+.*\\\\s+(start|stop|restart|deallocate)(\\\\s|$)"
    action: require_approval
    context: ai_only
    message: "Azure VM power operation requires approval."

  # REQUIRE_APPROVAL: Catch-all for any az ... import
  - name: approve-az-import
    commands: ["az"]
    conditions:
      - command_matches: "^az\\\\s+\\\\S+.*\\\\s+import(\\\\s|$)"
    action: require_approval
    context: ai_only
    message: "Azure import operation requires approval."

  # REQUIRE_APPROVAL: Catch-all for any az ... purge (permanent deletion)
  - name: approve-az-purge
    commands: ["az"]
    conditions:
      - command_matches: "^az\\\\s+\\\\S+.*\\\\s+purge(\\\\s|$)"
    action: require_approval
    context: ai_only
    message: "Azure purge operation permanently deletes resources. This cannot be undone."
"""
