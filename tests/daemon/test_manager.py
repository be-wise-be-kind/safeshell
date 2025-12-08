"""Tests for safeshell.daemon.manager module."""

import tempfile
from pathlib import Path

import pytest

from safeshell.daemon.manager import PluginManager
from safeshell.models import DaemonRequest, Decision, RequestType


@pytest.fixture
def manager() -> PluginManager:
    """Create a PluginManager instance."""
    return PluginManager()


@pytest.fixture
def git_repo_main() -> Path:
    """Create a temporary git repo on main branch."""
    with tempfile.TemporaryDirectory() as tmpdir:
        git_dir = Path(tmpdir) / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("ref: refs/heads/main\n")
        yield Path(tmpdir)


@pytest.fixture
def git_repo_feature() -> Path:
    """Create a temporary git repo on feature branch."""
    with tempfile.TemporaryDirectory() as tmpdir:
        git_dir = Path(tmpdir) / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("ref: refs/heads/feature/test\n")
        yield Path(tmpdir)


class TestPluginManager:
    """Tests for PluginManager initialization."""

    def test_loads_builtin_plugins(self, manager: PluginManager) -> None:
        """Test that built-in plugins are loaded."""
        assert len(manager.plugins) > 0

    def test_git_protect_loaded(self, manager: PluginManager) -> None:
        """Test that git-protect plugin is loaded."""
        plugin_names = [p.name for p in manager.plugins]
        assert "git-protect" in plugin_names


class TestProcessRequest:
    """Tests for PluginManager.process_request()."""

    @pytest.mark.asyncio
    async def test_ping_request(self, manager: PluginManager) -> None:
        """Test handling ping request."""
        request = DaemonRequest(type=RequestType.PING)
        response = await manager.process_request(request)
        assert response.success is True

    @pytest.mark.asyncio
    async def test_status_request(self, manager: PluginManager) -> None:
        """Test handling status request."""
        request = DaemonRequest(type=RequestType.STATUS)
        response = await manager.process_request(request)
        assert response.success is True

    @pytest.mark.asyncio
    async def test_evaluate_missing_command(self, manager: PluginManager) -> None:
        """Test evaluate request without command."""
        request = DaemonRequest(
            type=RequestType.EVALUATE,
            working_dir="/home/user",
        )
        response = await manager.process_request(request)
        assert response.success is False
        assert response.error_message is not None
        assert "command" in response.error_message.lower()

    @pytest.mark.asyncio
    async def test_evaluate_missing_working_dir(self, manager: PluginManager) -> None:
        """Test evaluate request without working_dir."""
        request = DaemonRequest(
            type=RequestType.EVALUATE,
            command="ls",
        )
        response = await manager.process_request(request)
        assert response.success is False
        assert response.error_message is not None
        assert "directory" in response.error_message.lower()


class TestEvaluateCommand:
    """Tests for command evaluation."""

    @pytest.mark.asyncio
    async def test_allowed_command_outside_repo(self, manager: PluginManager) -> None:
        """Test that commands outside git repo are allowed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            request = DaemonRequest(
                type=RequestType.EVALUATE,
                command="ls -la",
                working_dir=tmpdir,
            )
            response = await manager.process_request(request)
            assert response.success is True
            assert response.final_decision == Decision.ALLOW
            assert response.should_execute is True

    @pytest.mark.asyncio
    async def test_git_commit_blocked_on_main(
        self, manager: PluginManager, git_repo_main: Path
    ) -> None:
        """Test git commit is blocked on main branch."""
        request = DaemonRequest(
            type=RequestType.EVALUATE,
            command="git commit -m 'test'",
            working_dir=str(git_repo_main),
        )
        response = await manager.process_request(request)
        assert response.success is True
        assert response.final_decision == Decision.DENY
        assert response.should_execute is False
        assert response.denial_message is not None

    @pytest.mark.asyncio
    async def test_git_commit_allowed_on_feature(
        self, manager: PluginManager, git_repo_feature: Path
    ) -> None:
        """Test git commit is allowed on feature branch."""
        request = DaemonRequest(
            type=RequestType.EVALUATE,
            command="git commit -m 'test'",
            working_dir=str(git_repo_feature),
        )
        response = await manager.process_request(request)
        assert response.success is True
        assert response.final_decision == Decision.ALLOW
        assert response.should_execute is True

    @pytest.mark.asyncio
    async def test_non_git_command_in_repo(
        self, manager: PluginManager, git_repo_main: Path
    ) -> None:
        """Test non-git commands are allowed in git repo."""
        request = DaemonRequest(
            type=RequestType.EVALUATE,
            command="ls -la",
            working_dir=str(git_repo_main),
        )
        response = await manager.process_request(request)
        assert response.success is True
        assert response.final_decision == Decision.ALLOW


class TestDecisionAggregation:
    """Tests for decision aggregation logic."""

    @pytest.mark.asyncio
    async def test_deny_overrides_allow(self, manager: PluginManager) -> None:
        """Test that DENY takes precedence over ALLOW."""
        # The git-protect plugin should DENY, so final should be DENY
        with tempfile.TemporaryDirectory() as tmpdir:
            git_dir = Path(tmpdir) / ".git"
            git_dir.mkdir()
            (git_dir / "HEAD").write_text("ref: refs/heads/main\n")

            request = DaemonRequest(
                type=RequestType.EVALUATE,
                command="git commit -m test",
                working_dir=tmpdir,
            )
            response = await manager.process_request(request)

            # Should have at least one result
            assert len(response.results) >= 1
            # Final decision should be DENY
            assert response.final_decision == Decision.DENY
