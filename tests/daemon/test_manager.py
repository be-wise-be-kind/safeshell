"""Tests for safeshell.daemon.manager module."""

# ruff: noqa: S603, S607 - subprocess calls in tests are safe with hardcoded git commands

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from safeshell.daemon.manager import RuleManager
from safeshell.models import DaemonRequest, Decision, RequestType
from safeshell.rules.schema import Rule, RuleAction


@pytest.fixture
def manager() -> RuleManager:
    """Create a RuleManager instance."""
    return RuleManager()


@pytest.fixture
def git_repo_main() -> Path:
    """Create a temporary git repo on main branch."""
    import subprocess

    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize a real git repo
        subprocess.run(
            ["git", "init", "-b", "main"],
            cwd=tmpdir,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=tmpdir,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmpdir,
            capture_output=True,
            check=True,
        )
        yield Path(tmpdir)


@pytest.fixture
def git_repo_feature() -> Path:
    """Create a temporary git repo on feature branch."""
    import subprocess

    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize a real git repo and create feature branch
        subprocess.run(
            ["git", "init", "-b", "feature/test"],
            cwd=tmpdir,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=tmpdir,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmpdir,
            capture_output=True,
            check=True,
        )
        yield Path(tmpdir)


@pytest.fixture
def git_protect_rule() -> Rule:
    """A rule equivalent to the old git-protect plugin."""
    return Rule(
        name="block-commit-protected-branch",
        commands=["git"],
        conditions=[
            'echo "$CMD" | grep -qE "^git\\s+commit"',
            "git branch --show-current 2>/dev/null | grep -qE '^(main|master|develop)$'",
        ],
        action=RuleAction.DENY,
        message="Cannot commit directly to protected branch.",
    )


class TestRuleManager:
    """Tests for RuleManager initialization."""

    def test_rule_count_starts_at_zero(self, manager: RuleManager) -> None:
        """Test that rule_count starts at 0 before any evaluation."""
        assert manager.rule_count == 0


class TestProcessRequest:
    """Tests for RuleManager.process_request()."""

    @pytest.mark.asyncio
    async def test_ping_request(self, manager: RuleManager) -> None:
        """Test handling ping request."""
        request = DaemonRequest(type=RequestType.PING)
        response = await manager.process_request(request)
        assert response.success is True

    @pytest.mark.asyncio
    async def test_status_request(self, manager: RuleManager) -> None:
        """Test handling status request."""
        request = DaemonRequest(type=RequestType.STATUS)
        response = await manager.process_request(request)
        assert response.success is True

    @pytest.mark.asyncio
    async def test_evaluate_missing_command(self, manager: RuleManager) -> None:
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
    async def test_evaluate_missing_working_dir(self, manager: RuleManager) -> None:
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
    async def test_allowed_command_outside_repo(self, manager: RuleManager) -> None:
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
        self,
        manager: RuleManager,
        git_repo_main: Path,
        git_protect_rule: Rule,
    ) -> None:
        """Test git commit is blocked on main branch with rules."""
        # Mock RuleCache.get_rules to return our test rule
        with patch.object(
            manager._rule_cache, "get_rules", return_value=([git_protect_rule], False)
        ):
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
        self,
        manager: RuleManager,
        git_repo_feature: Path,
        git_protect_rule: Rule,
    ) -> None:
        """Test git commit is allowed on feature branch."""
        # Mock RuleCache.get_rules to return our test rule
        with patch.object(
            manager._rule_cache, "get_rules", return_value=([git_protect_rule], False)
        ):
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
        self, manager: RuleManager, git_repo_main: Path, git_protect_rule: Rule
    ) -> None:
        """Test non-git commands are allowed in git repo."""
        with patch.object(
            manager._rule_cache, "get_rules", return_value=([git_protect_rule], False)
        ):
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
    async def test_deny_overrides_allow(self, manager: RuleManager) -> None:
        """Test that DENY takes precedence when multiple rules match."""
        allow_rule = Rule(
            name="allow-git",
            commands=["git"],
            action=RuleAction.ALLOW,
            message="Allow git",
        )
        deny_rule = Rule(
            name="deny-git",
            commands=["git"],
            action=RuleAction.DENY,
            message="Deny git",
        )

        with (
            patch.object(
                manager._rule_cache,
                "get_rules",
                return_value=([allow_rule, deny_rule], False),
            ),
            tempfile.TemporaryDirectory() as tmpdir,
        ):
            request = DaemonRequest(
                type=RequestType.EVALUATE,
                command="git status",
                working_dir=tmpdir,
            )
            response = await manager.process_request(request)

            # Should have at least one result
            assert len(response.results) >= 1
            # Final decision should be DENY (most restrictive wins)
            assert response.final_decision == Decision.DENY
