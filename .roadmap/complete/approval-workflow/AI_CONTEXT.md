# Approval Workflow with Monitor TUI - AI Context

**Purpose**: AI agent context document for implementing the approval workflow feature

**Scope**: Human approval for risky operations via terminal UI with mouse support

**Overview**: Extends SafeShell with human-in-the-loop approval for REQUIRE_APPROVAL decisions. Introduces a Monitor TUI (terminal user interface) built with Textual that displays real-time events, command history, and approval prompts. Supports mouse interaction for approve/deny actions.

**Dependencies**: Python 3.11+, textual, existing daemon infrastructure from MVP

**Exports**: safeshell monitor command, approval protocol, event streaming

**Related**: PR_BREAKDOWN.md for implementation tasks, PROGRESS_TRACKER.md for current status

**Implementation**: Event-driven architecture with config-based rules

---

## ⚠️ ARCHITECTURE PIVOT #1: Config-Based Rules

**Status: COMPLETE (PR-2.5 merged)**

The Python plugin system was replaced with YAML configuration. See rules section below.

---

## ⚠️ ARCHITECTURE PIVOT #2: Shim-Based Interception

**Status: POC COMPLETE, needs productionization (PR-3.5)**

### The Problem

The original SHELL wrapper approach (`SHELL=/path/to/safeshell-wrapper`) only works when:
- AI tools explicitly invoke `$SHELL -c "command"`
- Programs respect the SHELL environment variable

It does NOT work for:
- Humans typing commands directly in terminals
- AI tools that execute commands without using SHELL
- Scripts that call binaries directly

### The Solution: Shims + Shell Function Overrides

**Like pyenv/rbenv**, SafeShell now uses:

1. **Command Shims** - Lightweight scripts in `~/.safeshell/shims/` that intercept external commands
2. **Shell Function Overrides** - Functions that override dangerous builtins (cd, source, eval)
3. **Shell Init Script** - Sourced in .bashrc to set up PATH and functions

### How It Works

```
User types: git commit -m "test"
                │
                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Bash looks up "git" in PATH                                     │
│  PATH = ~/.safeshell/shims:/usr/bin:/bin:...                    │
│                                                                  │
│  Finds: ~/.safeshell/shims/git (symlink to safeshell-shim)      │
└─────────────────────────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────────┐
│  safeshell-shim executes:                                        │
│  1. Check if daemon socket exists (fail-open if not)            │
│  2. SAFESHELL_CHECK_ONLY=1 safeshell-wrapper -c "git commit..." │
│  3. If allowed → exec /usr/bin/git commit -m "test"             │
│  4. If blocked → show message, exit 1                           │
└─────────────────────────────────────────────────────────────────┘
```

### Builtin Overrides

Shell builtins (cd, source, eval) can't be shimmed via PATH. Instead, we define functions:

```bash
cd() {
    if __safeshell_check "cd $target"; then
        builtin cd "$@"
    else
        return 1
    fi
}
```

### Shell Init Script

Users add to `.bashrc`:
```bash
eval "$(safeshell init -)"
# Or: source ~/.safeshell/init.bash
```

This sets up:
1. PATH with shims directory first
2. Function overrides for cd, source, eval
3. Fail-open behavior when daemon not running

### Shim Refresh

When rules.yaml changes, shims need updating:
```bash
safeshell refresh
```

This reads all `commands:` from rules and creates/updates shims.

### Key Files (POC location → Production location)

| POC | Production | Purpose |
|-----|------------|---------|
| `src/safeshell/shims/safeshell-shim` | `~/.safeshell/shims/safeshell-shim` | Universal shim script |
| `src/safeshell/shims/init.bash` | `~/.safeshell/init.bash` | Shell init script |
| N/A | `src/safeshell/shims/manager.py` | Shim management module |

### Limitations

1. **Shell builtins require function overrides** - Can't shim `echo`, `cd`, etc. via PATH
2. **One-time .bashrc setup required** - User must add init line
3. **Shim refresh after rule changes** - Not automatic (like pyenv rehash)

## Config-Based Rules Architecture

### Why This Change?

The original plugin system required:
- Python class per rule type
- Knowledge of our plugin API
- Complex module loading for repo-level rules

The new config system provides:
- YAML files for all rules
- Bash conditions for complex logic
- Global + repo-level configuration
- No Python knowledge required for new rules

### Rule Schema

```yaml
# ~/.safeshell/rules.yaml (global) or .safeshell/rules.yaml (repo)
rules:
  - name: "rule-identifier"           # Unique name for logging/debugging
    commands: ["git", "rm"]           # Target executables (fast-path filter)
    directory: "regex"                # Optional: working directory pattern
    conditions:                       # Optional: bash conditions (all must pass)
      - "bash statement that exits 0 if true"
      - "another condition"
    action: deny | require_approval | redirect
    allow_override: true | false      # For deny: can user approve anyway?
    redirect_to: "command $ARGS"      # For redirect: replacement command
    message: "User-facing message"    # Shown in denial/approval prompt
```

### Available Variables in Conditions

When evaluating conditions, these variables are available:
- `$CMD` - Full command string (e.g., "git commit -m test")
- `$ARGS` - Arguments after executable (e.g., "commit -m test")
- `$PWD` - Current working directory
- `$SAFESHELL_RULE` - Name of current rule being evaluated

### Rule Evaluation Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Command Received                              │
│                 e.g., "git commit -m test"                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 1: Extract executable                                      │
│  "git commit -m test" → executable = "git"                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 2: Fast-path check                                         │
│  Is "git" in ANY rule's commands list?                           │
│  NO → ALLOW immediately (most commands take this path)           │
└─────────────────────────────────────────────────────────────────┘
                              │ YES
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 3: For each rule where executable matches:                 │
│                                                                  │
│  a. Check directory pattern (if specified)                       │
│     - Regex match against $PWD                                   │
│     - No match → skip this rule                                  │
│                                                                  │
│  b. Run bash conditions (if specified)                           │
│     - Each condition run via: bash -c "condition"                │
│     - ALL must exit 0 for rule to match                          │
│     - Any exits non-zero → skip this rule                        │
│                                                                  │
│  c. Rule matches! Record the action.                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 4: Determine final action                                  │
│                                                                  │
│  No rules matched → ALLOW                                        │
│  One rule matched → use its action                               │
│  Multiple matched → most restrictive wins:                       │
│                     deny > require_approval > redirect > allow   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 5: Execute action                                          │
│                                                                  │
│  ALLOW → wrapper executes command                                │
│  DENY → wrapper shows denial message, exits 1                    │
│  REQUIRE_APPROVAL → daemon waits for monitor approval            │
│  REDIRECT → wrapper executes redirect_to instead                 │
└─────────────────────────────────────────────────────────────────┘
```

### Global vs Repo Rules

```
~/.safeshell/rules.yaml          # Global - YOUR protections
     │
     │  loaded first
     ▼
.safeshell/rules.yaml            # Repo - project-specific additions
     │
     │  merged (additive only)
     ▼
Combined rule set                # Repo rules can ADD restrictions
                                 # Repo rules CANNOT relax global rules
```

**Security Model**: Repo rules are additive only. A malicious cloned repo cannot disable your global protections.

### Example Rules

#### 1. Block git commit on protected branches
```yaml
- name: block-commit-protected-branch
  commands: ["git"]
  conditions:
    - "echo '$CMD' | grep -qE '^git\\s+commit'"
    - "git branch --show-current | grep -qE '^(main|master|develop)$'"
  action: deny
  message: "Cannot commit directly to protected branch. Create a feature branch first."
```

#### 2. Require approval for force push
```yaml
- name: require-approval-force-push
  commands: ["git"]
  conditions:
    - "echo '$CMD' | grep -qE '^git\\s+push.*(--force|-f)'"
    - "git branch --show-current | grep -qE '^(main|master|develop)$'"
  action: require_approval
  message: "Force push to protected branch requires approval"
```

#### 3. Redirect rm to trash
```yaml
- name: redirect-rm-to-trash
  commands: ["rm"]
  action: redirect
  redirect_to: "trash $ARGS"
  message: "Redirecting deletion to trash for safety"
```

#### 4. Block reading SSH keys
```yaml
- name: block-read-ssh-keys
  commands: ["cat", "less", "head", "tail", "more", "bat"]
  conditions:
    - "echo '$CMD' | grep -qE '\\.ssh'"
  action: deny
  message: "Cannot read SSH keys"
```

#### 5. Block rm outside project (using path resolution)
```yaml
- name: block-rm-outside-project
  commands: ["rm"]
  conditions:
    - "for f in $ARGS; do realpath \"$f\" 2>/dev/null | grep -qv \"^$PWD\" && exit 0; done; exit 1"
  action: require_approval
  message: "Deleting files outside project requires approval"
```

#### 6. Block curl | bash patterns
```yaml
- name: block-curl-pipe-bash
  commands: ["curl", "wget"]
  conditions:
    - "echo '$CMD' | grep -qE '\\|.*(ba)?sh'"
  action: deny
  message: "Cannot pipe downloads directly to shell"
```

### Implementation Details

#### File Structure
```
src/safeshell/rules/
├── __init__.py          # Exports
├── schema.py            # Pydantic models for Rule, RuleSet
├── evaluator.py         # RuleEvaluator class
└── loader.py            # Load and merge rule files

src/safeshell/
└── default-rules.yaml   # Shipped default rules
```

#### Pydantic Models (schema.py)
```python
from enum import Enum
from pydantic import BaseModel, Field

class RuleAction(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    REDIRECT = "redirect"

class Rule(BaseModel):
    name: str
    commands: list[str]
    directory: str | None = None
    conditions: list[str] = Field(default_factory=list)
    action: RuleAction
    allow_override: bool = True
    redirect_to: str | None = None
    message: str

class RuleSet(BaseModel):
    rules: list[Rule] = Field(default_factory=list)
```

#### Rule Evaluator (evaluator.py)
```python
class RuleEvaluator:
    def __init__(self, rules: list[Rule], event_publisher=None):
        self.rules = rules
        self._event_publisher = event_publisher
        # Build command -> rules index for fast lookup
        self._command_index: dict[str, list[Rule]] = {}
        for rule in rules:
            for cmd in rule.commands:
                self._command_index.setdefault(cmd, []).append(rule)

    async def evaluate(self, command: str, working_dir: str) -> EvaluationResult:
        # Extract executable
        executable = command.split()[0] if command else ""

        # Fast path: no rules for this executable
        if executable not in self._command_index:
            return EvaluationResult(decision=Decision.ALLOW, ...)

        # Check each matching rule
        matching_rules = []
        for rule in self._command_index[executable]:
            if await self._rule_matches(rule, command, working_dir):
                matching_rules.append(rule)

        # Return most restrictive
        return self._aggregate_results(matching_rules)

    async def _rule_matches(self, rule: Rule, cmd: str, pwd: str) -> bool:
        # Check directory pattern
        if rule.directory and not re.match(rule.directory, pwd):
            return False

        # Check bash conditions
        for condition in rule.conditions:
            if not await self._check_condition(condition, cmd, pwd):
                return False

        return True

    async def _check_condition(self, condition: str, cmd: str, pwd: str) -> bool:
        # Run bash condition with variables
        env = {
            "CMD": cmd,
            "ARGS": " ".join(cmd.split()[1:]),
            "PWD": pwd,
        }
        proc = await asyncio.create_subprocess_shell(
            f"bash -c {shlex.quote(condition)}",
            env={**os.environ, **env},
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        return proc.returncode == 0
```

#### Rule Loader (loader.py)
```python
def load_rules(working_dir: str) -> list[Rule]:
    """Load and merge global + repo rules."""
    rules = []

    # Load global rules
    global_path = Path.home() / ".safeshell" / "rules.yaml"
    if global_path.exists():
        rules.extend(_load_rule_file(global_path))

    # Load default rules (shipped with SafeShell)
    default_path = Path(__file__).parent.parent / "default-rules.yaml"
    if default_path.exists():
        rules.extend(_load_rule_file(default_path))

    # Load repo rules (additive only)
    repo_path = Path(working_dir) / ".safeshell" / "rules.yaml"
    if repo_path.exists():
        rules.extend(_load_rule_file(repo_path))

    return rules
```

---

## Monitor TUI (PR-3, after config rules)

### Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  Monitor TUI (safeshell monitor)                                │
├─────────────────────┬─────────────────────┬─────────────────────┤
│  Debug/Log Pane     │  Command History    │  Approval Prompt    │
│                     │                     │                     │
│  [DEBUG] Plugin...  │  ✓ echo hello       │  ⚠️ APPROVAL NEEDED │
│  [INFO] Evaluating  │  ✗ git commit (blk) │                     │
│  [DEBUG] Result...  │  ✓ ls -la           │  git push --force   │
│                     │  ? git push (pend)  │  to origin/main     │
│                     │                     │                     │
│                     │                     │  [Approve] [Deny]   │
│                     │                     │                     │
│                     │                     │  Reason: ________   │
└─────────────────────┴─────────────────────┴─────────────────────┘
```

### Technology: Textual

[Textual](https://textual.textualize.io/) provides:
- Full mouse support
- Rich widget library
- CSS-like styling
- Async-first design

### Communication Flow

```
Wrapper                  Daemon                     Monitor TUI
   │                        │                           │
   │──evaluate(cmd)────────>│                           │
   │                        │──event: cmd_received─────>│
   │                        │                           │
   │                        │ [rule returns REQUIRE_APPROVAL]
   │                        │                           │
   │                        │──event: approval_needed──>│
   │                        │                           │
   │   [wrapper blocks,     │         [user clicks      │
   │    waiting for         │          Approve/Deny]    │
   │    approval]           │                           │
   │                        │<──approve(id, reason?)────│
   │                        │                           │
   │<──response(approved)───│──event: approval_resolved>│
   │                        │                           │
```

---

## Project Background

The MVP established the daemon/wrapper architecture for blocking dangerous commands. However, some operations are risky but not outright forbidden - they require human judgment:

- Force push to protected branches (might be intentional)
- Deleting important files (might be cleanup)
- Running privileged commands (might be necessary)

The approval workflow adds a third decision type: `REQUIRE_APPROVAL`, which pauses execution until a human approves or denies in the Monitor TUI.

---

## Success Metrics

### Phase 2 Complete When:

1. Config-based rules replace Python plugins
2. Global + repo rules work correctly
3. `safeshell monitor` launches TUI successfully
4. TUI displays three panes with correct layout
5. Real-time log streaming works in debug pane
6. Command history updates live
7. Approval prompt appears for REQUIRE_APPROVAL
8. Approve button allows command to execute
9. Deny button blocks with optional reason
10. Reason text appears in wrapper's denial message
11. Timeout properly blocks after configurable period

---

## Technical Constraints

- Textual requires Python 3.8+ (we have 3.11+)
- Terminal must support 256 colors (most modern terminals do)
- Mouse support requires terminal emulator support (most do)
- Single monitor can approve at a time (MVP constraint)
- Bash conditions require bash to be available

---

## AI Agent Guidance

### When Implementing Config Rules (PR-2.5)

1. Start with schema.py - define Pydantic models
2. Implement loader.py - load and merge rule files
3. Implement evaluator.py - rule matching and condition execution
4. Update daemon/manager.py to use RuleEvaluator
5. Create default-rules.yaml with git-protect equivalent
6. Write comprehensive tests for each component
7. Remove old plugin code after tests pass

### When Implementing Monitor TUI (PR-3)

1. Start with single-file prototype, then split
2. Use Textual's reactive pattern for state
3. Connect to daemon socket for events
4. Handle reconnection gracefully

### Testing Bash Conditions

```python
# Test that conditions work as expected
async def test_git_branch_condition():
    evaluator = RuleEvaluator([...])
    # In a git repo on main branch
    result = await evaluator._check_condition(
        "git branch --show-current | grep -qE '^main$'",
        "git commit -m test",
        "/path/to/repo"
    )
    assert result is True
```

---

## Future Enhancements (Phase 3+)

- Approval history/audit log
- Multiple designated approvers
- Remote approval (not just local terminal)
- Approval rules (auto-approve certain patterns)
- Integration with git-protect for force-push approval
