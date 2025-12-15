"""Tests for structured condition types."""

# ruff: noqa: S108 - /tmp paths in tests are fine

import tempfile
from pathlib import Path

import pytest

from safeshell.models import CommandContext, ExecutionContext
from safeshell.rules.condition_types import (
    CommandContains,
    CommandMatches,
    CommandStartswith,
    EnvEquals,
    FileExists,
    GitBranchIn,
    GitBranchMatches,
    InGitRepo,
    PathMatches,
    parse_condition,
)


@pytest.fixture
def git_context() -> CommandContext:
    """Create a context in a git repository."""
    return CommandContext(
        raw_command="git commit -m 'test'",
        parsed_args=["git", "commit", "-m", "test"],
        working_dir="/home/user/project",
        git_repo_root="/home/user/project",
        git_branch="main",
        environment={"HOME": "/home/user", "USER": "user"},
        execution_context=ExecutionContext.HUMAN,
    )


@pytest.fixture
def non_git_context() -> CommandContext:
    """Create a context outside a git repository."""
    return CommandContext(
        raw_command="ls -la",
        parsed_args=["ls", "-la"],
        working_dir="/tmp",
        git_repo_root=None,
        git_branch=None,
        environment={"HOME": "/home/user"},
        execution_context=ExecutionContext.HUMAN,
    )


class TestCommandMatches:
    """Tests for CommandMatches condition."""

    def test_matches_simple_pattern(self, git_context: CommandContext) -> None:
        """Test simple regex match."""
        condition = CommandMatches(command_matches=r"^git\s+commit")
        assert condition.evaluate(git_context) is True

    def test_no_match(self, git_context: CommandContext) -> None:
        """Test regex that doesn't match."""
        condition = CommandMatches(command_matches=r"^git\s+push")
        assert condition.evaluate(git_context) is False

    def test_partial_match(self, git_context: CommandContext) -> None:
        """Test partial match in middle of command."""
        condition = CommandMatches(command_matches=r"commit")
        assert condition.evaluate(git_context) is True

    def test_complex_pattern(self) -> None:
        """Test complex regex pattern."""
        context = CommandContext(
            raw_command="git push --force origin main",
            parsed_args=["git", "push", "--force", "origin", "main"],
            working_dir="/tmp",
            git_repo_root=None,
            git_branch=None,
            environment={},
            execution_context=ExecutionContext.HUMAN,
        )
        condition = CommandMatches(command_matches=r"^git\s+push.*(--force|-f)")
        assert condition.evaluate(context) is True


class TestCommandContains:
    """Tests for CommandContains condition."""

    def test_contains_substring(self, git_context: CommandContext) -> None:
        """Test substring found."""
        condition = CommandContains(command_contains="commit")
        assert condition.evaluate(git_context) is True

    def test_not_contains_substring(self, git_context: CommandContext) -> None:
        """Test substring not found."""
        condition = CommandContains(command_contains="push")
        assert condition.evaluate(git_context) is False

    def test_contains_flag(self) -> None:
        """Test checking for a flag."""
        context = CommandContext(
            raw_command="rm -rf /tmp/test",
            parsed_args=["rm", "-rf", "/tmp/test"],
            working_dir="/tmp",
            git_repo_root=None,
            git_branch=None,
            environment={},
            execution_context=ExecutionContext.HUMAN,
        )
        condition = CommandContains(command_contains="-rf")
        assert condition.evaluate(context) is True


class TestCommandStartswith:
    """Tests for CommandStartswith condition."""

    def test_startswith_match(self, git_context: CommandContext) -> None:
        """Test command starts with prefix."""
        condition = CommandStartswith(command_startswith="git commit")
        assert condition.evaluate(git_context) is True

    def test_startswith_no_match(self, git_context: CommandContext) -> None:
        """Test command doesn't start with prefix."""
        condition = CommandStartswith(command_startswith="git push")
        assert condition.evaluate(git_context) is False


class TestGitBranchIn:
    """Tests for GitBranchIn condition."""

    def test_branch_in_list(self, git_context: CommandContext) -> None:
        """Test branch is in the list."""
        condition = GitBranchIn(git_branch_in=["main", "master", "develop"])
        assert condition.evaluate(git_context) is True

    def test_branch_not_in_list(self, git_context: CommandContext) -> None:
        """Test branch is not in the list."""
        condition = GitBranchIn(git_branch_in=["feature", "bugfix"])
        assert condition.evaluate(git_context) is False

    def test_no_git_branch(self, non_git_context: CommandContext) -> None:
        """Test when not in a git repo."""
        condition = GitBranchIn(git_branch_in=["main"])
        assert condition.evaluate(non_git_context) is False


class TestGitBranchMatches:
    """Tests for GitBranchMatches condition."""

    def test_branch_matches_pattern(self, git_context: CommandContext) -> None:
        """Test branch matches regex."""
        condition = GitBranchMatches(git_branch_matches=r"^main$")
        assert condition.evaluate(git_context) is True

    def test_branch_no_match(self, git_context: CommandContext) -> None:
        """Test branch doesn't match regex."""
        condition = GitBranchMatches(git_branch_matches=r"^feature/")
        assert condition.evaluate(git_context) is False

    def test_no_git_branch(self, non_git_context: CommandContext) -> None:
        """Test when not in a git repo."""
        condition = GitBranchMatches(git_branch_matches=r".*")
        assert condition.evaluate(non_git_context) is False

    def test_prefix_pattern(self) -> None:
        """Test matching branch prefix."""
        context = CommandContext(
            raw_command="git commit",
            parsed_args=["git", "commit"],
            working_dir="/tmp",
            git_repo_root="/tmp",
            git_branch="feature/new-thing",
            environment={},
            execution_context=ExecutionContext.HUMAN,
        )
        condition = GitBranchMatches(git_branch_matches=r"^feature/")
        assert condition.evaluate(context) is True


class TestInGitRepo:
    """Tests for InGitRepo condition."""

    def test_in_git_repo_true(self, git_context: CommandContext) -> None:
        """Test expecting to be in a git repo."""
        condition = InGitRepo(in_git_repo=True)
        assert condition.evaluate(git_context) is True

    def test_in_git_repo_false(self, git_context: CommandContext) -> None:
        """Test expecting not to be in a git repo."""
        condition = InGitRepo(in_git_repo=False)
        assert condition.evaluate(git_context) is False

    def test_not_in_git_repo_true(self, non_git_context: CommandContext) -> None:
        """Test expecting to be in git repo but not."""
        condition = InGitRepo(in_git_repo=True)
        assert condition.evaluate(non_git_context) is False

    def test_not_in_git_repo_false(self, non_git_context: CommandContext) -> None:
        """Test expecting not to be in git repo and not."""
        condition = InGitRepo(in_git_repo=False)
        assert condition.evaluate(non_git_context) is True


class TestPathMatches:
    """Tests for PathMatches condition."""

    def test_path_matches(self, git_context: CommandContext) -> None:
        """Test path matches pattern."""
        condition = PathMatches(path_matches=r"/home/.*/project")
        assert condition.evaluate(git_context) is True

    def test_path_no_match(self, git_context: CommandContext) -> None:
        """Test path doesn't match pattern."""
        condition = PathMatches(path_matches=r"^/tmp")
        assert condition.evaluate(git_context) is False

    def test_path_exact_match(self, non_git_context: CommandContext) -> None:
        """Test exact path match."""
        condition = PathMatches(path_matches=r"^/tmp$")
        assert condition.evaluate(non_git_context) is True


class TestFileExists:
    """Tests for FileExists condition."""

    def test_file_exists(self) -> None:
        """Test file that exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file
            test_file = Path(tmpdir) / "test.txt"
            test_file.touch()

            context = CommandContext(
                raw_command="cat test.txt",
                parsed_args=["cat", "test.txt"],
                working_dir=tmpdir,
                git_repo_root=None,
                git_branch=None,
                environment={},
                execution_context=ExecutionContext.HUMAN,
            )
            condition = FileExists(file_exists="test.txt")
            assert condition.evaluate(context) is True

    def test_file_not_exists(self) -> None:
        """Test file that doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            context = CommandContext(
                raw_command="cat missing.txt",
                parsed_args=["cat", "missing.txt"],
                working_dir=tmpdir,
                git_repo_root=None,
                git_branch=None,
                environment={},
                execution_context=ExecutionContext.HUMAN,
            )
            condition = FileExists(file_exists="missing.txt")
            assert condition.evaluate(context) is False


class TestEnvEquals:
    """Tests for EnvEquals condition."""

    def test_env_equals(self, git_context: CommandContext) -> None:
        """Test environment variable equals expected value."""
        condition = EnvEquals(env_equals={"variable": "USER", "value": "user"})
        assert condition.evaluate(git_context) is True

    def test_env_not_equals(self, git_context: CommandContext) -> None:
        """Test environment variable doesn't equal expected value."""
        condition = EnvEquals(env_equals={"variable": "USER", "value": "root"})
        assert condition.evaluate(git_context) is False

    def test_env_not_set(self, git_context: CommandContext) -> None:
        """Test environment variable not set."""
        condition = EnvEquals(env_equals={"variable": "NONEXISTENT", "value": "anything"})
        assert condition.evaluate(git_context) is False


class TestParseCondition:
    """Tests for parse_condition function."""

    def test_parse_command_matches(self) -> None:
        """Test parsing command_matches condition."""
        condition = parse_condition({"command_matches": r"^git\s+commit"})
        assert isinstance(condition, CommandMatches)
        assert condition.command_matches == r"^git\s+commit"

    def test_parse_git_branch_in(self) -> None:
        """Test parsing git_branch_in condition."""
        condition = parse_condition({"git_branch_in": ["main", "master"]})
        assert isinstance(condition, GitBranchIn)
        assert condition.git_branch_in == ["main", "master"]

    def test_parse_env_equals(self) -> None:
        """Test parsing env_equals condition."""
        condition = parse_condition({"env_equals": {"variable": "X", "value": "Y"}})
        assert isinstance(condition, EnvEquals)
        assert condition.env_equals == {"variable": "X", "value": "Y"}

    def test_parse_string_raises_error(self) -> None:
        """Test that bash strings raise an error."""
        with pytest.raises(ValueError, match="Bash string conditions are no longer supported"):
            parse_condition('echo "$CMD" | grep -q "commit"')

    def test_parse_unknown_type_raises_error(self) -> None:
        """Test that unknown condition types raise an error."""
        with pytest.raises(ValueError, match="Unknown condition type"):
            parse_condition({"unknown_condition": "value"})

    def test_parse_invalid_type_raises_error(self) -> None:
        """Test that non-dict/non-string raises an error."""
        with pytest.raises(ValueError, match="Condition must be a dict"):
            parse_condition(123)  # type: ignore
