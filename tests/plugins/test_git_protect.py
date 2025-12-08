"""Tests for safeshell.plugins.git_protect module."""

import tempfile
from pathlib import Path

import pytest

from safeshell.models import CommandContext, Decision
from safeshell.plugins.git_protect import GitProtectPlugin


@pytest.fixture
def plugin() -> GitProtectPlugin:
    """Create a GitProtectPlugin instance."""
    return GitProtectPlugin()


@pytest.fixture
def git_repo_main() -> Path:
    """Create a temporary git repo on main branch."""
    with tempfile.TemporaryDirectory() as tmpdir:
        git_dir = Path(tmpdir) / ".git"
        git_dir.mkdir()
        head_file = git_dir / "HEAD"
        head_file.write_text("ref: refs/heads/main\n")
        yield Path(tmpdir)


@pytest.fixture
def git_repo_feature() -> Path:
    """Create a temporary git repo on feature branch."""
    with tempfile.TemporaryDirectory() as tmpdir:
        git_dir = Path(tmpdir) / ".git"
        git_dir.mkdir()
        head_file = git_dir / "HEAD"
        head_file.write_text("ref: refs/heads/feature/test\n")
        yield Path(tmpdir)


class TestGitProtectPlugin:
    """Tests for GitProtectPlugin."""

    def test_name(self, plugin: GitProtectPlugin) -> None:
        """Test plugin name."""
        assert plugin.name == "git-protect"

    def test_description(self, plugin: GitProtectPlugin) -> None:
        """Test plugin description."""
        assert "protect" in plugin.description.lower()

    def test_protected_branches(self, plugin: GitProtectPlugin) -> None:
        """Test protected branches include main and master."""
        assert "main" in plugin.PROTECTED_BRANCHES
        assert "master" in plugin.PROTECTED_BRANCHES
        assert "develop" in plugin.PROTECTED_BRANCHES


class TestGitProtectMatches:
    """Tests for GitProtectPlugin.matches()."""

    def test_matches_git_command_in_repo(
        self, plugin: GitProtectPlugin, git_repo_main: Path
    ) -> None:
        """Test matches returns True for git commands in git repo."""
        ctx = CommandContext.from_command("git status", str(git_repo_main))
        assert plugin.matches(ctx) is True

    def test_no_match_non_git_command(self, plugin: GitProtectPlugin, git_repo_main: Path) -> None:
        """Test matches returns False for non-git commands."""
        ctx = CommandContext.from_command("ls -la", str(git_repo_main))
        assert plugin.matches(ctx) is False

    def test_no_match_outside_repo(self, plugin: GitProtectPlugin) -> None:
        """Test matches returns False outside git repo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = CommandContext.from_command("git status", tmpdir)
            assert plugin.matches(ctx) is False

    def test_no_match_empty_command(self, plugin: GitProtectPlugin, git_repo_main: Path) -> None:
        """Test matches returns False for empty command."""
        ctx = CommandContext(
            raw_command="",
            parsed_args=[],
            working_dir=str(git_repo_main),
            git_repo_root=str(git_repo_main),
            git_branch="main",
        )
        assert plugin.matches(ctx) is False


class TestGitProtectCommit:
    """Tests for git commit evaluation."""

    def test_commit_blocked_on_main(self, plugin: GitProtectPlugin, git_repo_main: Path) -> None:
        """Test git commit is blocked on main branch."""
        ctx = CommandContext.from_command("git commit -m 'test'", str(git_repo_main))
        result = plugin.evaluate(ctx)
        assert result.decision == Decision.DENY
        assert "main" in result.reason

    def test_commit_blocked_on_master(self, plugin: GitProtectPlugin) -> None:
        """Test git commit is blocked on master branch."""
        with tempfile.TemporaryDirectory() as tmpdir:
            git_dir = Path(tmpdir) / ".git"
            git_dir.mkdir()
            (git_dir / "HEAD").write_text("ref: refs/heads/master\n")

            ctx = CommandContext.from_command("git commit -m 'test'", tmpdir)
            result = plugin.evaluate(ctx)
            assert result.decision == Decision.DENY
            assert "master" in result.reason

    def test_commit_allowed_on_feature(
        self, plugin: GitProtectPlugin, git_repo_feature: Path
    ) -> None:
        """Test git commit is allowed on feature branch."""
        ctx = CommandContext.from_command("git commit -m 'test'", str(git_repo_feature))
        result = plugin.evaluate(ctx)
        assert result.decision == Decision.ALLOW


class TestGitProtectPush:
    """Tests for git push evaluation."""

    def test_force_push_blocked_on_main(
        self, plugin: GitProtectPlugin, git_repo_main: Path
    ) -> None:
        """Test force push is blocked on main branch."""
        ctx = CommandContext.from_command("git push --force origin main", str(git_repo_main))
        result = plugin.evaluate(ctx)
        assert result.decision == Decision.DENY
        assert "force" in result.reason.lower()

    def test_force_push_with_f_flag(self, plugin: GitProtectPlugin, git_repo_main: Path) -> None:
        """Test force push with -f flag is blocked."""
        ctx = CommandContext.from_command("git push -f origin main", str(git_repo_main))
        result = plugin.evaluate(ctx)
        assert result.decision == Decision.DENY

    def test_regular_push_allowed(self, plugin: GitProtectPlugin, git_repo_main: Path) -> None:
        """Test regular push is allowed."""
        ctx = CommandContext.from_command("git push origin main", str(git_repo_main))
        result = plugin.evaluate(ctx)
        assert result.decision == Decision.ALLOW

    def test_force_push_allowed_on_feature(
        self, plugin: GitProtectPlugin, git_repo_feature: Path
    ) -> None:
        """Test force push is allowed on feature branch."""
        ctx = CommandContext.from_command("git push --force", str(git_repo_feature))
        result = plugin.evaluate(ctx)
        assert result.decision == Decision.ALLOW


class TestGitProtectOtherCommands:
    """Tests for other git commands."""

    def test_git_status_allowed(self, plugin: GitProtectPlugin, git_repo_main: Path) -> None:
        """Test git status is allowed."""
        ctx = CommandContext.from_command("git status", str(git_repo_main))
        result = plugin.evaluate(ctx)
        assert result.decision == Decision.ALLOW

    def test_git_log_allowed(self, plugin: GitProtectPlugin, git_repo_main: Path) -> None:
        """Test git log is allowed."""
        ctx = CommandContext.from_command("git log --oneline", str(git_repo_main))
        result = plugin.evaluate(ctx)
        assert result.decision == Decision.ALLOW

    def test_git_add_allowed(self, plugin: GitProtectPlugin, git_repo_main: Path) -> None:
        """Test git add is allowed."""
        ctx = CommandContext.from_command("git add .", str(git_repo_main))
        result = plugin.evaluate(ctx)
        assert result.decision == Decision.ALLOW

    def test_git_no_subcommand(self, plugin: GitProtectPlugin, git_repo_main: Path) -> None:
        """Test bare git command is allowed."""
        ctx = CommandContext.from_command("git", str(git_repo_main))
        result = plugin.evaluate(ctx)
        assert result.decision == Decision.ALLOW
