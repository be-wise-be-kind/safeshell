"""
File: src/safeshell/rules/defaults.py
Purpose: Default rules shipped with SafeShell
Exports: DEFAULT_RULES_YAML
Depends: None
Overview: Contains the default rules that are created by 'safeshell init'
"""

DEFAULT_RULES_YAML = """\
# SafeShell Default Rules Configuration
# Philosophy: Permissive with guardrails
#   - DENY: Only truly catastrophic operations with NO legitimate use case
#   - REQUIRE_APPROVAL: Everything risky - let humans decide
#   - context: ai_only for AI-specific restrictions (trust human judgment)
#
# Rule Schema:
#   name: Unique identifier for logging
#   commands: List of executables this rule applies to (fast-path filter)
#   conditions: Structured conditions (all must pass for rule to match)
#   action: deny | require_approval | redirect
#   context: all | ai_only | human_only (default: all)
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
  # ==========================================================================
  # CATEGORY 1: DESTRUCTIVE OPERATIONS
  # Only rm -rf / and rm -rf * are DENY - everything else is REQUIRE_APPROVAL
  # ==========================================================================

  # DENY: Recursive delete of root filesystem - NO legitimate use case
  - name: deny-rm-rf-root
    commands: ["rm"]
    conditions:
      - command_matches: "rm\\\\s+(-[rf]+\\\\s+)*/"
    action: deny
    message: "BLOCKED: Recursive delete of root filesystem (/) is catastrophic and prohibited."

  # DENY: Recursive delete of everything - almost always a mistake
  - name: deny-rm-rf-star
    commands: ["rm"]
    conditions:
      - command_matches: "rm\\\\s+.*-[rf]*r[rf]*.*\\\\s+\\\\*"
    action: deny
    message: "BLOCKED: 'rm -rf *' is too dangerous. Be explicit about what to delete."

  # REQUIRE_APPROVAL: Parent directory recursive delete (AI only)
  - name: approve-rm-parent-recursive
    commands: ["rm"]
    conditions:
      - command_matches: "rm\\\\s+.*-[rf]*r[rf]*.*\\\\.\\\\."
    action: require_approval
    context: ai_only
    message: "Recursive delete with parent directory (..) requires approval."

  # REQUIRE_APPROVAL: Any recursive force delete (AI only)
  - name: approve-rm-rf-directory
    commands: ["rm"]
    conditions:
      - command_matches: "rm\\\\s+.*-[rf]*r[rf]*"
    action: require_approval
    context: ai_only
    message: "Recursive force delete requires approval. Review target carefully."

  # REQUIRE_APPROVAL: World-writable permissions (AI only)
  - name: approve-chmod-777
    commands: ["chmod"]
    conditions:
      - command_contains: "777"
    action: require_approval
    context: ai_only
    message: "chmod 777 creates world-writable files. Consider 755 for dirs, 644 for files."

  # REQUIRE_APPROVAL: World-writable file permissions (AI only)
  - name: approve-chmod-666
    commands: ["chmod"]
    conditions:
      - command_contains: "666"
    action: require_approval
    context: ai_only
    message: "chmod 666 creates world-writable files. Consider 644 instead."

  # REQUIRE_APPROVAL: Recursive permission changes (AI only)
  - name: approve-chmod-recursive
    commands: ["chmod"]
    conditions:
      - command_matches: "chmod\\\\s+.*-R"
    action: require_approval
    context: ai_only
    message: "Recursive permission change requires approval. Verify target directory."

  # REQUIRE_APPROVAL: Direct disk device writes (AI only)
  - name: approve-dd-to-device
    commands: ["dd"]
    conditions:
      - command_matches: "of=/dev/(sd|hd|nvme|vd|loop)"
    action: require_approval
    context: ai_only
    message: "Direct writes to disk devices require approval. Verify this is correct."

  # ==========================================================================
  # CATEGORY 2: SYSTEM PROTECTION (AI only)
  # ==========================================================================

  # REQUIRE_APPROVAL: Modifications to /etc (AI only)
  - name: approve-modify-etc
    commands: ["rm", "mv", "cp", "chmod", "chown"]
    conditions:
      - command_matches: "\\\\s/etc(/|\\\\s|$)"
    action: require_approval
    context: ai_only
    message: "Modifying /etc requires approval. This affects system configuration."

  # REQUIRE_APPROVAL: Modifications to /usr (AI only)
  - name: approve-modify-usr
    commands: ["rm", "mv", "cp", "chmod", "chown"]
    conditions:
      - command_matches: "\\\\s/usr(/|\\\\s|$)"
    action: require_approval
    context: ai_only
    message: "Modifying /usr requires approval. This affects system programs."

  # REQUIRE_APPROVAL: Modifications to /bin (AI only)
  - name: approve-modify-bin
    commands: ["rm", "mv", "cp", "chmod", "chown"]
    conditions:
      - command_matches: "\\\\s/bin(/|\\\\s|$)"
    action: require_approval
    context: ai_only
    message: "Modifying /bin requires approval. This affects system binaries."

  # REQUIRE_APPROVAL: Modifications to /sbin (AI only)
  - name: approve-modify-sbin
    commands: ["rm", "mv", "cp", "chmod", "chown"]
    conditions:
      - command_matches: "\\\\s/sbin(/|\\\\s|$)"
    action: require_approval
    context: ai_only
    message: "Modifying /sbin requires approval. This affects system administration binaries."

  # REQUIRE_APPROVAL: Filesystem creation (AI only)
  - name: approve-mkfs
    commands: ["mkfs", "mkfs.ext4", "mkfs.xfs", "mkfs.btrfs", "mkfs.fat", "mkfs.ntfs"]
    conditions:
      - command_startswith: "mkfs"
    action: require_approval
    context: ai_only
    message: "Creating filesystems requires approval. This formats the target device."

  # REQUIRE_APPROVAL: Disk partitioning (AI only)
  - name: approve-fdisk
    commands: ["fdisk", "parted", "gdisk", "cfdisk", "sfdisk"]
    conditions:
      - command_matches: "^(fdisk|parted|gdisk|cfdisk|sfdisk)"
    action: require_approval
    context: ai_only
    message: "Disk partitioning requires approval. This modifies partition tables."

  # ==========================================================================
  # CATEGORY 3: GIT SAFETY
  # ==========================================================================

  # REQUIRE_APPROVAL: Force push to protected branches (AI only)
  - name: approve-force-push-protected
    commands: ["git"]
    conditions:
      - command_matches: "^git\\\\s+push.*(--force|-f|--force-with-lease)"
      - git_branch_in: ["main", "master", "develop"]
    action: require_approval
    context: ai_only
    message: "Force push to protected branch requires approval. This rewrites shared history."

  # REQUIRE_APPROVAL: Any force push (AI only)
  - name: approve-force-push
    commands: ["git"]
    conditions:
      - command_matches: "^git\\\\s+push.*(--force|-f|--force-with-lease)"
    action: require_approval
    context: ai_only
    message: "Force push requires approval. This rewrites commit history."

  # REQUIRE_APPROVAL: Commits on protected branches (AI only)
  - name: approve-commit-protected-branch
    commands: ["git"]
    conditions:
      - command_matches: "^git\\\\s+commit"
      - git_branch_in: ["main", "master", "develop"]
    action: require_approval
    context: ai_only
    message: "Committing to protected branch requires approval. Consider using a feature branch."

  # REQUIRE_APPROVAL: Hard reset (AI only)
  - name: approve-git-reset-hard
    commands: ["git"]
    conditions:
      - command_contains: "reset --hard"
    action: require_approval
    context: ai_only
    message: "Hard reset discards uncommitted changes. Make sure you have a backup."

  # REQUIRE_APPROVAL: Git clean with force (AI only)
  - name: approve-git-clean-force
    commands: ["git"]
    conditions:
      - command_matches: "git\\\\s+clean\\\\s+.*-[a-z]*f"
    action: require_approval
    context: ai_only
    message: "Git clean -f removes untracked files permanently. Review before approving."

  # REQUIRE_APPROVAL: Rebase (AI only)
  - name: approve-git-rebase
    commands: ["git"]
    conditions:
      - command_matches: "^git\\\\s+rebase"
    action: require_approval
    context: ai_only
    message: "Rebasing rewrites commit history. Approve only for local branches."

  # REQUIRE_APPROVAL: Amend commits (AI only)
  - name: approve-git-commit-amend
    commands: ["git"]
    conditions:
      - command_contains: "commit --amend"
    action: require_approval
    context: ai_only
    message: "Amending commits can cause issues if already pushed. Verify before approving."

  # ==========================================================================
  # CATEGORY 4: SENSITIVE DATA PROTECTION
  # ==========================================================================

  # REQUIRE_APPROVAL: Reading .env files (AI only)
  - name: approve-read-env-files
    commands: ["cat", "less", "more", "head", "tail", "bat", "batcat"]
    conditions:
      - command_matches: "\\\\.(env|env\\\\.local|env\\\\.production|env\\\\.development)($|\\\\s)"
    action: require_approval
    context: ai_only
    message: "Reading environment files may expose secrets. Confirm this is necessary."

  # REQUIRE_APPROVAL: Reading SSH private keys (AI only)
  - name: approve-read-ssh-keys
    commands: ["cat", "less", "more", "head", "tail"]
    conditions:
      - command_matches: "id_(rsa|ed25519|ecdsa|dsa)($|\\\\s)"
    action: require_approval
    context: ai_only
    message: "Reading SSH private keys requires approval. Use ssh-agent instead if possible."

  # REQUIRE_APPROVAL: Copying SSH keys (AI only)
  - name: approve-copy-ssh-keys
    commands: ["cp", "scp", "rsync"]
    conditions:
      - command_matches: "\\\\.ssh/(id_|authorized_keys|known_hosts)"
    action: require_approval
    context: ai_only
    message: "Copying SSH key files requires approval. This is a security-sensitive operation."

  # REQUIRE_APPROVAL: Reading credential files (AI only)
  - name: approve-read-credentials
    commands: ["cat", "less", "more", "head", "tail"]
    conditions:
      - command_matches: "credentials\\\\.(json|yaml|yml|xml|ini)($|\\\\s)"
    action: require_approval
    context: ai_only
    message: "Reading credential files requires approval."

  # REQUIRE_APPROVAL: Reading AWS credentials (AI only)
  - name: approve-read-aws-credentials
    commands: ["cat", "less", "more", "head", "tail"]
    conditions:
      - command_matches: "\\\\.aws/(credentials|config)($|\\\\s)"
    action: require_approval
    context: ai_only
    message: "Reading AWS credentials requires approval."

  # REQUIRE_APPROVAL: Reading secrets files (AI only)
  - name: approve-read-secrets-yaml
    commands: ["cat", "less", "more", "head", "tail"]
    conditions:
      - command_matches: "(secrets?|secret)\\\\.(json|yaml|yml)($|\\\\s)"
    action: require_approval
    context: ai_only
    message: "Reading secrets files requires approval."

  # REQUIRE_APPROVAL: Sourcing env files (AI only)
  - name: approve-source-env
    commands: ["source", "."]
    conditions:
      - command_matches: "\\\\.(env|secret|credentials)"
    action: require_approval
    context: ai_only
    message: "Sourcing sensitive files may expose secrets. Review the file contents first."

  # ==========================================================================
  # CATEGORY 5: PACKAGE MANAGERS
  # ==========================================================================

  # REQUIRE_APPROVAL: Global npm installs (AI only)
  - name: approve-npm-global
    commands: ["npm"]
    conditions:
      - command_matches: "npm\\\\s+(install|i)\\\\s+.*(-g|--global)"
    action: require_approval
    context: ai_only
    message: "Global npm install affects system-wide packages. Verify this is intentional."

  # REQUIRE_APPROVAL: pip install (AI only)
  - name: approve-pip-system
    commands: ["pip", "pip3"]
    conditions:
      - command_matches: "^pip3?\\\\s+install"
    action: require_approval
    context: ai_only
    message: "pip install may modify system Python. Consider using a virtual environment."

  # REQUIRE_APPROVAL: Deleting global node_modules (AI only)
  - name: approve-rm-global-node-modules
    commands: ["rm"]
    conditions:
      - command_matches: "rm.*(/usr|/opt).*/node_modules"
    action: require_approval
    context: ai_only
    message: "Deleting global node_modules requires approval. This could break system packages."

  # REQUIRE_APPROVAL: Deleting system site-packages (AI only)
  - name: approve-rm-site-packages
    commands: ["rm"]
    conditions:
      - command_matches: "rm.*/usr.*/site-packages"
    action: require_approval
    context: ai_only
    message: "Deleting system site-packages requires approval. This could break Python."

  # REQUIRE_APPROVAL: Yarn global installs (AI only)
  - name: approve-yarn-global
    commands: ["yarn"]
    conditions:
      - command_matches: "yarn\\\\s+global\\\\s+add"
    action: require_approval
    context: ai_only
    message: "Global yarn install affects system-wide packages. Verify this is intentional."

  # ==========================================================================
  # CATEGORY 6: NETWORK SAFETY
  # ==========================================================================

  # REQUIRE_APPROVAL: curl piped to bash (AI only)
  - name: approve-curl-pipe-bash
    commands: ["curl"]
    conditions:
      - command_matches: "curl.*\\\\|\\\\s*(ba)?sh"
    action: require_approval
    context: ai_only
    message: "Piping curl to bash requires approval. Consider downloading and inspecting first."

  # REQUIRE_APPROVAL: wget piped to bash (AI only)
  - name: approve-wget-pipe-bash
    commands: ["wget"]
    conditions:
      - command_matches: "wget.*\\\\|\\\\s*(ba)?sh"
    action: require_approval
    context: ai_only
    message: "Piping wget to bash requires approval. Consider downloading and inspecting first."

  # REQUIRE_APPROVAL: Python HTTP server (AI only)
  - name: approve-python-http-server
    commands: ["python", "python3"]
    conditions:
      - command_contains: "http.server"
    action: require_approval
    context: ai_only
    message: "Starting an HTTP server exposes files. Ensure this is intentional."

  # REQUIRE_APPROVAL: netcat listeners (AI only)
  - name: approve-netcat-listen
    commands: ["nc", "netcat", "ncat"]
    conditions:
      - command_matches: "(nc|netcat|ncat).*-l"
    action: require_approval
    context: ai_only
    message: "netcat listener opens a network port. Verify this is safe."

  # REQUIRE_APPROVAL: ngrok (AI only)
  - name: approve-ngrok
    commands: ["ngrok"]
    conditions:
      - command_startswith: "ngrok"
    action: require_approval
    context: ai_only
    message: "ngrok exposes local services to the internet. Verify this is intentional."

  # ==========================================================================
  # CATEGORY 7: DOCKER SAFETY
  # ==========================================================================

  # REQUIRE_APPROVAL: Privileged containers (AI only)
  - name: approve-docker-privileged
    commands: ["docker"]
    conditions:
      - command_contains: "--privileged"
    action: require_approval
    context: ai_only
    message: "Privileged containers have full host access. Use only when necessary."

  # REQUIRE_APPROVAL: Mounting root filesystem (AI only)
  - name: approve-docker-mount-root
    commands: ["docker"]
    conditions:
      - command_matches: "docker\\\\s+run.*-v\\\\s+/:"
    action: require_approval
    context: ai_only
    message: "Mounting root filesystem in containers requires approval."

  # REQUIRE_APPROVAL: Host network mode (AI only)
  - name: approve-docker-host-network
    commands: ["docker"]
    conditions:
      - command_matches: "--network[=\\\\s]+host"
    action: require_approval
    context: ai_only
    message: "Host network mode bypasses container isolation. Verify this is needed."

  # REQUIRE_APPROVAL: Mounting home directory (AI only)
  - name: approve-docker-mount-home
    commands: ["docker"]
    conditions:
      - command_matches: "docker\\\\s+run.*-v\\\\s+(/home|\\\\$HOME|~)"
    action: require_approval
    context: ai_only
    message: "Mounting home directory in containers may expose sensitive data."

  # REQUIRE_APPROVAL: Mounting /etc (AI only)
  - name: approve-docker-mount-etc
    commands: ["docker"]
    conditions:
      - command_matches: "docker\\\\s+run.*-v\\\\s+/etc"
    action: require_approval
    context: ai_only
    message: "Mounting /etc in containers may expose system configuration."

  # ==========================================================================
  # CATEGORY 8: SHELL & AI PATTERNS
  # ==========================================================================

  # REQUIRE_APPROVAL: Modifying .bashrc (AI only)
  - name: approve-modify-bashrc
    commands: ["vim", "vi", "nano", "emacs", "code", "tee"]
    conditions:
      - command_contains: ".bashrc"
    action: require_approval
    context: ai_only
    message: "Modifying .bashrc affects your shell environment. Review changes carefully."

  # REQUIRE_APPROVAL: Modifying .zshrc (AI only)
  - name: approve-modify-zshrc
    commands: ["vim", "vi", "nano", "emacs", "code", "tee"]
    conditions:
      - command_contains: ".zshrc"
    action: require_approval
    context: ai_only
    message: "Modifying .zshrc affects your shell environment. Review changes carefully."

  # REQUIRE_APPROVAL: sudo rm (AI only)
  - name: approve-sudo-rm
    commands: ["sudo"]
    conditions:
      - command_startswith: "sudo rm"
    action: require_approval
    context: ai_only
    message: "sudo rm requires approval. This runs rm with elevated privileges."

  # REQUIRE_APPROVAL: Any sudo command (AI only)
  - name: approve-sudo
    commands: ["sudo"]
    conditions:
      - command_startswith: "sudo"
    action: require_approval
    context: ai_only
    message: "sudo commands run with elevated privileges. Verify this is necessary."

  # REQUIRE_APPROVAL: eval commands (AI only)
  - name: approve-eval
    commands: ["eval"]
    conditions:
      - command_startswith: "eval"
    action: require_approval
    context: ai_only
    message: "eval can execute arbitrary code. Review the expression carefully."

  # REQUIRE_APPROVAL: killall/pkill (AI only)
  - name: approve-killall
    commands: ["killall", "pkill"]
    conditions:
      - command_matches: "^(killall|pkill)"
    action: require_approval
    context: ai_only
    message: "Killing processes by name may affect multiple processes. Verify targets."
"""
