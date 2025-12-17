# How to: Add Condition Types

**Purpose**: Guide for extending SafeShell with new condition types

**Scope**: Creating new condition classes, registration, testing

**Overview**: This guide explains how to add new structured condition types to SafeShell's
    rule engine. New conditions enable rules to match on custom criteria beyond the
    built-in conditions.

**Dependencies**: rules/condition_types.py, pydantic

**Exports**: Condition implementation pattern, testing approach

**Related**: how-to-understand-rule-evaluation.md, how-to-write-rules.md

**Implementation**: Step-by-step with code examples

---

## Available Condition Types

Before creating a new condition, check if an existing one fits your needs:

### Command Conditions

| Type | Purpose | Parameters |
|------|---------|------------|
| `command_matches` | Regex match on full command | `pattern: str` |
| `command_contains` | Substring match | `pattern: str` |
| `command_startswith` | Prefix match | `prefix: str` |

### Git Conditions

| Type | Purpose | Parameters |
|------|---------|------------|
| `git_branch_in` | Branch is in list | `branches: list[str]` |
| `git_branch_matches` | Branch matches regex | `pattern: str` |
| `in_git_repo` | Is in git repository | `value: bool` |

### Path Conditions

| Type | Purpose | Parameters |
|------|---------|------------|
| `path_matches` | Path in command matches glob | `pattern: str` |
| `file_exists` | File exists in working dir | `path: str` |

### Environment Conditions

| Type | Purpose | Parameters |
|------|---------|------------|
| `env_equals` | Env var equals value | `name: str, value: str` |

---

## Condition Class Template

All conditions inherit from `BaseCondition`:

```python
"""
File: src/safeshell/rules/condition_types.py

New condition class template
"""
from pydantic import BaseModel, Field
from safeshell.models import CommandContext


class MyNewCondition(BaseModel):
    """Description of what this condition checks."""

    type: str = Field(default="my_new_condition", frozen=True)

    # Add your parameters here
    param1: str
    param2: int = 10  # Optional with default

    def evaluate(self, context: CommandContext) -> bool:
        """
        Evaluate the condition against the command context.

        Args:
            context: Contains command, args, working_dir, git info, etc.

        Returns:
            True if condition passes, False otherwise
        """
        # Your logic here
        return self.param1 in context.command
```

---

## Step-by-Step Implementation

### Step 1: Define the Condition Class

```python
# In src/safeshell/rules/condition_types.py

class UserInGroup(BaseModel):
    """Check if current user is in a specific Unix group."""

    type: str = Field(default="user_in_group", frozen=True)
    group: str = Field(description="Unix group name to check")

    def evaluate(self, context: CommandContext) -> bool:
        """Check if current user is in the specified group."""
        import grp
        import os

        try:
            group_info = grp.getgrnam(self.group)
            current_user = os.getlogin()
            return current_user in group_info.gr_mem
        except KeyError:
            return False  # Group doesn't exist
```

### Step 2: Register the Condition

Add to the `Condition` type union:

```python
# In src/safeshell/rules/condition_types.py

from typing import Annotated, Union
from pydantic import Discriminator

Condition = Annotated[
    Union[
        CommandMatches,
        CommandContains,
        CommandStartswith,
        GitBranchIn,
        GitBranchMatches,
        InGitRepo,
        PathMatches,
        FileExists,
        EnvEquals,
        UserInGroup,  # Add your new condition here
    ],
    Discriminator("type"),
]
```

### Step 3: Update Rule Schema

The `Rule` model automatically uses the `Condition` union, so no changes needed there.

---

## Testing New Conditions

### Unit Test Pattern

```python
# In tests/rules/test_condition_types.py

import pytest
from safeshell.rules.condition_types import UserInGroup
from safeshell.models import CommandContext


class TestUserInGroup:
    """Tests for UserInGroup condition."""

    def test_user_in_group_matches(self, mocker):
        """Test condition passes when user is in group."""
        # Mock grp module
        mock_group = mocker.MagicMock()
        mock_group.gr_mem = ["testuser"]
        mocker.patch("grp.getgrnam", return_value=mock_group)
        mocker.patch("os.getlogin", return_value="testuser")

        condition = UserInGroup(group="developers")
        context = CommandContext(
            command="make build",
            executable="make",
            args=["build"],
            working_dir="/home/testuser/project",
        )

        assert condition.evaluate(context) is True

    def test_user_not_in_group(self, mocker):
        """Test condition fails when user not in group."""
        mock_group = mocker.MagicMock()
        mock_group.gr_mem = ["otheruser"]
        mocker.patch("grp.getgrnam", return_value=mock_group)
        mocker.patch("os.getlogin", return_value="testuser")

        condition = UserInGroup(group="developers")
        context = CommandContext(
            command="make build",
            executable="make",
            args=["build"],
            working_dir="/home/testuser/project",
        )

        assert condition.evaluate(context) is False

    def test_group_not_exists(self, mocker):
        """Test condition fails gracefully when group doesn't exist."""
        mocker.patch("grp.getgrnam", side_effect=KeyError("Group not found"))

        condition = UserInGroup(group="nonexistent")
        context = CommandContext(
            command="make build",
            executable="make",
            args=["build"],
            working_dir="/home/testuser/project",
        )

        assert condition.evaluate(context) is False
```

### Integration Test

```python
# Test with actual rule evaluation

def test_rule_with_custom_condition(mocker):
    """Test custom condition works in rule evaluation."""
    from safeshell.rules.schema import Rule
    from safeshell.rules.evaluator import RuleEvaluator

    # Mock user group membership
    mock_group = mocker.MagicMock()
    mock_group.gr_mem = ["admin"]
    mocker.patch("grp.getgrnam", return_value=mock_group)
    mocker.patch("os.getlogin", return_value="admin")

    rule = Rule(
        name="admin-only-deploy",
        commands=["deploy"],
        conditions=[
            {"type": "user_in_group", "group": "admin"}
        ],
        action="allow",
    )

    evaluator = RuleEvaluator(rules=[rule])
    context = CommandContext(
        command="deploy production",
        executable="deploy",
        args=["production"],
        working_dir="/app",
    )

    decision = evaluator.evaluate(context)
    assert decision.action == "allow"
```

---

## Performance Considerations

### Compile Regex Once

```python
class MyPatternCondition(BaseModel):
    type: str = Field(default="my_pattern", frozen=True)
    pattern: str

    _compiled_pattern: re.Pattern | None = None

    def model_post_init(self, __context) -> None:
        """Compile pattern after model initialization."""
        object.__setattr__(
            self, "_compiled_pattern", re.compile(self.pattern)
        )

    def evaluate(self, context: CommandContext) -> bool:
        return bool(self._compiled_pattern.match(context.command))
```

### Cache Expensive Operations

```python
class ExpensiveCondition(BaseModel):
    type: str = Field(default="expensive", frozen=True)

    def evaluate(self, context: CommandContext) -> bool:
        # Use context's cached git info instead of calling git
        if context.git_branch is None:
            return False  # Not in git repo

        # Use cached value
        return context.git_branch == "main"
```

### Avoid Disk I/O When Possible

```python
# SLOW - disk access every evaluation
class SlowCondition(BaseModel):
    def evaluate(self, context: CommandContext) -> bool:
        return Path("/some/file").exists()

# FASTER - use context or cache
class FastCondition(BaseModel):
    def evaluate(self, context: CommandContext) -> bool:
        # Only check if really needed
        if "sensitive" not in context.command:
            return True
        return Path("/some/file").exists()
```

---

## Common Patterns

### Boolean Parameter

```python
class InDockerContainer(BaseModel):
    type: str = Field(default="in_docker", frozen=True)
    value: bool = True  # Expected value

    def evaluate(self, context: CommandContext) -> bool:
        is_docker = Path("/.dockerenv").exists()
        return is_docker == self.value
```

### List Parameter

```python
class CommandInList(BaseModel):
    type: str = Field(default="command_in_list", frozen=True)
    commands: list[str]

    def evaluate(self, context: CommandContext) -> bool:
        return context.executable in self.commands
```

### Optional Parameter

```python
class FileMatch(BaseModel):
    type: str = Field(default="file_match", frozen=True)
    pattern: str
    case_sensitive: bool = True  # Optional with default

    def evaluate(self, context: CommandContext) -> bool:
        flags = 0 if self.case_sensitive else re.IGNORECASE
        return bool(re.search(self.pattern, context.command, flags))
```

---

## Checklist for New Conditions

- [ ] Class inherits from `BaseModel`
- [ ] Has `type` field with frozen default
- [ ] Has `evaluate(self, context: CommandContext) -> bool` method
- [ ] Added to `Condition` union in condition_types.py
- [ ] Unit tests cover success and failure cases
- [ ] Integration test with rule evaluation
- [ ] Performance acceptable (<1ms typical)
- [ ] Regex patterns compiled once (if applicable)
- [ ] Expensive operations cached (if applicable)
- [ ] Documentation added to this file
