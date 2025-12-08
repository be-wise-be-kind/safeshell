"""Tests for safeshell.models module."""

import tempfile
from pathlib import Path

from safeshell.models import (
    CommandContext,
    DaemonRequest,
    DaemonResponse,
    Decision,
    EvaluationResult,
    RequestType,
)


class TestDecision:
    """Tests for Decision enum."""

    def test_decision_values(self) -> None:
        """Test that Decision has expected values."""
        assert Decision.ALLOW.value == "allow"
        assert Decision.DENY.value == "deny"
        assert Decision.REQUIRE_APPROVAL.value == "require_approval"

    def test_decision_is_string(self) -> None:
        """Test that Decision values are strings."""
        assert isinstance(Decision.ALLOW.value, str)
        assert Decision.ALLOW == "allow"


class TestCommandContext:
    """Tests for CommandContext model."""

    def test_basic_creation(self) -> None:
        """Test basic CommandContext creation."""
        ctx = CommandContext(
            raw_command="ls -la",
            parsed_args=["ls", "-la"],
            working_dir="/home/user",
        )
        assert ctx.raw_command == "ls -la"
        assert ctx.parsed_args == ["ls", "-la"]
        assert ctx.working_dir == "/home/user"
        assert ctx.git_repo_root is None
        assert ctx.git_branch is None

    def test_executable_property(self) -> None:
        """Test executable property returns first arg."""
        ctx = CommandContext(
            raw_command="git commit -m test",
            parsed_args=["git", "commit", "-m", "test"],
            working_dir="/home/user",
        )
        assert ctx.executable == "git"

    def test_executable_empty(self) -> None:
        """Test executable property with empty args."""
        ctx = CommandContext(
            raw_command="",
            parsed_args=[],
            working_dir="/home/user",
        )
        assert ctx.executable is None

    def test_args_property(self) -> None:
        """Test args property returns args after executable."""
        ctx = CommandContext(
            raw_command="git commit -m test",
            parsed_args=["git", "commit", "-m", "test"],
            working_dir="/home/user",
        )
        assert ctx.args == ["commit", "-m", "test"]

    def test_from_command_simple(self) -> None:
        """Test from_command with simple command."""
        ctx = CommandContext.from_command("ls -la", "/home/user")
        assert ctx.raw_command == "ls -la"
        assert ctx.parsed_args == ["ls", "-la"]
        assert ctx.working_dir == "/home/user"

    def test_from_command_with_quotes(self) -> None:
        """Test from_command with quoted arguments."""
        ctx = CommandContext.from_command('echo "hello world"', "/home/user")
        assert ctx.parsed_args == ["echo", "hello world"]

    def test_from_command_git_detection(self) -> None:
        """Test from_command detects git repo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a git repo
            git_dir = Path(tmpdir) / ".git"
            git_dir.mkdir()
            head_file = git_dir / "HEAD"
            head_file.write_text("ref: refs/heads/main\n")

            ctx = CommandContext.from_command("git status", tmpdir)
            assert ctx.git_repo_root == tmpdir
            assert ctx.git_branch == "main"

    def test_from_command_no_git(self) -> None:
        """Test from_command in non-git directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = CommandContext.from_command("ls", tmpdir)
            assert ctx.git_repo_root is None
            assert ctx.git_branch is None


class TestEvaluationResult:
    """Tests for EvaluationResult model."""

    def test_allow_result(self) -> None:
        """Test creating an ALLOW result."""
        result = EvaluationResult(
            decision=Decision.ALLOW,
            plugin_name="test-plugin",
            reason="Command is safe",
        )
        assert result.decision == Decision.ALLOW
        assert result.plugin_name == "test-plugin"
        assert result.reason == "Command is safe"
        assert result.challenge_code is None

    def test_deny_result(self) -> None:
        """Test creating a DENY result."""
        result = EvaluationResult(
            decision=Decision.DENY,
            plugin_name="git-protect",
            reason="Cannot commit to main",
        )
        assert result.decision == Decision.DENY


class TestDaemonRequest:
    """Tests for DaemonRequest model."""

    def test_evaluate_request(self) -> None:
        """Test creating an evaluate request."""
        request = DaemonRequest(
            type=RequestType.EVALUATE,
            command="git commit -m test",
            working_dir="/home/user/project",
            env={"USER": "testuser"},
        )
        assert request.type == RequestType.EVALUATE
        assert request.command == "git commit -m test"
        assert request.working_dir == "/home/user/project"
        assert request.env["USER"] == "testuser"

    def test_ping_request(self) -> None:
        """Test creating a ping request."""
        request = DaemonRequest(type=RequestType.PING)
        assert request.type == RequestType.PING
        assert request.command is None

    def test_serialization(self) -> None:
        """Test request serialization to JSON."""
        request = DaemonRequest(
            type=RequestType.EVALUATE,
            command="ls",
            working_dir="/home/user",
        )
        json_str = request.model_dump_json()
        assert "evaluate" in json_str
        assert "ls" in json_str


class TestDaemonResponse:
    """Tests for DaemonResponse model."""

    def test_allow_response(self) -> None:
        """Test DaemonResponse.allow() factory."""
        response = DaemonResponse.allow()
        assert response.success is True
        assert response.final_decision == Decision.ALLOW
        assert response.should_execute is True
        assert response.denial_message is None

    def test_deny_response(self) -> None:
        """Test DaemonResponse.deny() factory."""
        response = DaemonResponse.deny("Not allowed", "test-plugin")
        assert response.success is True
        assert response.final_decision == Decision.DENY
        assert response.should_execute is False
        assert response.denial_message is not None
        assert "Not allowed" in response.denial_message
        assert "test-plugin" in response.denial_message

    def test_error_response(self) -> None:
        """Test DaemonResponse.error() factory."""
        response = DaemonResponse.error("Something went wrong")
        assert response.success is False
        assert response.should_execute is False
        assert response.error_message == "Something went wrong"
