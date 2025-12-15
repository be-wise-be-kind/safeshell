"""
File: src/safeshell/rules/condition_types.py
Purpose: Pydantic models for structured rule conditions with Python evaluation
Exports: Condition type union and all condition type classes
Depends: pydantic, re, os
Overview: Defines structured conditions that replace bash condition strings for fast evaluation
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, PrivateAttr

if TYPE_CHECKING:
    from safeshell.models import CommandContext


class CommandMatches(BaseModel):
    """Match command against regex pattern.

    Example YAML:
        - command_matches: "^git\\s+commit"
    """

    command_matches: str = Field(description="Regex pattern to match against full command")
    _compiled: re.Pattern[str] | None = PrivateAttr(default=None)

    def evaluate(self, context: CommandContext) -> bool:
        """Check if command matches the regex pattern."""
        if self._compiled is None:
            self._compiled = re.compile(self.command_matches)
        return self._compiled.search(context.raw_command) is not None


class CommandContains(BaseModel):
    """Check if command contains literal substring.

    Example YAML:
        - command_contains: "--force"
    """

    command_contains: str = Field(description="Literal string to search for in command")

    def evaluate(self, context: CommandContext) -> bool:
        """Check if command contains the substring."""
        return self.command_contains in context.raw_command


class CommandStartswith(BaseModel):
    """Check if command starts with prefix.

    Example YAML:
        - command_startswith: "rm -rf"
    """

    command_startswith: str = Field(description="Prefix to match at start of command")

    def evaluate(self, context: CommandContext) -> bool:
        """Check if command starts with the prefix."""
        return context.raw_command.startswith(self.command_startswith)


class GitBranchIn(BaseModel):
    """Check if current git branch is in list.

    Example YAML:
        - git_branch_in: ["main", "master", "develop"]
    """

    git_branch_in: list[str] = Field(description="List of branch names to match")
    _branch_set: set[str] | None = PrivateAttr(default=None)

    def evaluate(self, context: CommandContext) -> bool:
        """Check if current branch is in the list."""
        if context.git_branch is None:
            return False
        if self._branch_set is None:
            self._branch_set = set(self.git_branch_in)
        return context.git_branch in self._branch_set


class GitBranchMatches(BaseModel):
    """Match git branch against regex pattern.

    Example YAML:
        - git_branch_matches: "^release/"
    """

    git_branch_matches: str = Field(description="Regex pattern to match against branch name")
    _compiled: re.Pattern[str] | None = PrivateAttr(default=None)

    def evaluate(self, context: CommandContext) -> bool:
        """Check if branch name matches the regex pattern."""
        if context.git_branch is None:
            return False
        if self._compiled is None:
            self._compiled = re.compile(self.git_branch_matches)
        return self._compiled.search(context.git_branch) is not None


class InGitRepo(BaseModel):
    """Check if working directory is in a git repository.

    Example YAML:
        - in_git_repo: true
        - in_git_repo: false
    """

    in_git_repo: bool = Field(description="Expected value (true = must be in git repo)")

    def evaluate(self, context: CommandContext) -> bool:
        """Check if in git repo matches expected value."""
        is_in_repo = context.git_repo_root is not None
        return is_in_repo == self.in_git_repo


class PathMatches(BaseModel):
    """Match working directory against regex pattern.

    Example YAML:
        - path_matches: "/home/.*/projects"
    """

    path_matches: str = Field(description="Regex pattern to match against working directory")
    _compiled: re.Pattern[str] | None = PrivateAttr(default=None)

    def evaluate(self, context: CommandContext) -> bool:
        """Check if working directory matches the pattern."""
        if self._compiled is None:
            self._compiled = re.compile(self.path_matches)
        return self._compiled.search(context.working_dir) is not None


class FileExists(BaseModel):
    """Check if file exists in working directory.

    Example YAML:
        - file_exists: ".gitignore"
        - file_exists: "package.json"
    """

    file_exists: str = Field(description="Relative path to check for existence")

    def evaluate(self, context: CommandContext) -> bool:
        """Check if the file exists."""
        full_path = Path(context.working_dir) / self.file_exists
        return full_path.exists()


class EnvEquals(BaseModel):
    """Check environment variable value.

    Example YAML:
        - env_equals:
            variable: "SAFESHELL_CONTEXT"
            value: "ai"
    """

    env_equals: dict[str, str] = Field(
        description="Dict with 'variable' and 'value' keys"
    )

    def evaluate(self, context: CommandContext) -> bool:
        """Check if environment variable equals expected value."""
        variable = self.env_equals.get("variable", "")
        value = self.env_equals.get("value", "")
        actual = context.environment.get(variable)
        return actual == value


# Union of all structured condition types
StructuredCondition = (
    CommandMatches
    | CommandContains
    | CommandStartswith
    | GitBranchIn
    | GitBranchMatches
    | InGitRepo
    | PathMatches
    | FileExists
    | EnvEquals
)

# The Condition type - structured only, no bash strings
Condition = StructuredCondition


def parse_condition(data: dict[str, Any] | str) -> Condition:
    """Parse a condition from YAML data.

    Args:
        data: Either a dict with a single key (shorthand syntax) or already parsed

    Returns:
        A structured condition instance

    Raises:
        ValueError: If condition format is invalid
    """
    if isinstance(data, str):
        raise ValueError(
            f"Bash string conditions are no longer supported. "
            f"Use structured conditions instead. Got: {data[:50]}..."
        )

    if not isinstance(data, dict):
        raise ValueError(f"Condition must be a dict, got {type(data)}")

    # Map condition key to class
    condition_classes: dict[str, type[StructuredCondition]] = {
        "command_matches": CommandMatches,
        "command_contains": CommandContains,
        "command_startswith": CommandStartswith,
        "git_branch_in": GitBranchIn,
        "git_branch_matches": GitBranchMatches,
        "in_git_repo": InGitRepo,
        "path_matches": PathMatches,
        "file_exists": FileExists,
        "env_equals": EnvEquals,
    }

    # Find which condition type this is based on key
    for key in data:
        if key in condition_classes:
            return condition_classes[key].model_validate(data)

    raise ValueError(
        f"Unknown condition type. Keys found: {list(data.keys())}. "
        f"Valid types: {list(condition_classes.keys())}"
    )
