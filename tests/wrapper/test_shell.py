"""Tests for the shell wrapper module.

Tests command interception, context detection, and execution flows.
"""

import sys
from unittest.mock import MagicMock

import pytest

from safeshell.models import DaemonResponse, Decision, ExecutionContext


class TestDetectExecutionContext:
    """Tests for _detect_execution_context()."""

    def test_returns_human_by_default(self, monkeypatch: pytest.MonkeyPatch):
        """Returns HUMAN when no AI context is detected."""
        # Clear relevant env vars
        monkeypatch.delenv("SAFESHELL_CONTEXT", raising=False)
        monkeypatch.delenv("WARP_AI_AGENT", raising=False)

        from safeshell.wrapper.shell import _detect_execution_context

        result = _detect_execution_context()
        assert result == ExecutionContext.HUMAN

    def test_returns_ai_when_safeshell_context_set(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """Returns AI when SAFESHELL_CONTEXT=ai."""
        monkeypatch.setenv("SAFESHELL_CONTEXT", "ai")

        from safeshell.wrapper.shell import _detect_execution_context

        result = _detect_execution_context()
        assert result == ExecutionContext.AI

    def test_returns_ai_when_warp_agent_set(self, monkeypatch: pytest.MonkeyPatch):
        """Returns AI when WARP_AI_AGENT=1."""
        monkeypatch.delenv("SAFESHELL_CONTEXT", raising=False)
        monkeypatch.setenv("WARP_AI_AGENT", "1")

        from safeshell.wrapper.shell import _detect_execution_context

        result = _detect_execution_context()
        assert result == ExecutionContext.AI

    def test_safeshell_context_takes_precedence(self, monkeypatch: pytest.MonkeyPatch):
        """SAFESHELL_CONTEXT is checked before WARP_AI_AGENT."""
        monkeypatch.setenv("SAFESHELL_CONTEXT", "ai")
        monkeypatch.setenv("WARP_AI_AGENT", "0")

        from safeshell.wrapper.shell import _detect_execution_context

        result = _detect_execution_context()
        assert result == ExecutionContext.AI


class TestEvaluateAndExecute:
    """Tests for _evaluate_and_execute()."""

    def test_allows_when_daemon_says_yes(self, monkeypatch: pytest.MonkeyPatch):
        """Executes command when daemon allows it."""
        from safeshell.wrapper import shell

        # Mock DaemonClient at the import path
        mock_client = MagicMock()
        mock_client.evaluate.return_value = DaemonResponse(
            success=True,
            final_decision=Decision.ALLOW,
            should_execute=True,
        )

        mock_client_class = MagicMock(return_value=mock_client)
        monkeypatch.setattr(
            "safeshell.wrapper.client.DaemonClient", mock_client_class
        )

        # Mock _execute to avoid actually running commands
        mock_execute = MagicMock(return_value=0)
        monkeypatch.setattr(shell, "_execute", mock_execute)

        result = shell._evaluate_and_execute("echo hello")

        assert result == 0
        mock_execute.assert_called_once()

    def test_denies_when_daemon_says_no(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ):
        """Returns 1 and does not execute when daemon denies."""
        from safeshell.wrapper import shell

        # Mock DaemonClient at the import path
        mock_client = MagicMock()
        mock_client.evaluate.return_value = DaemonResponse(
            success=True,
            final_decision=Decision.DENY,
            should_execute=False,
        )

        mock_client_class = MagicMock(return_value=mock_client)
        monkeypatch.setattr(
            "safeshell.wrapper.client.DaemonClient", mock_client_class
        )

        # Mock _execute - should not be called
        mock_execute = MagicMock()
        monkeypatch.setattr(shell, "_execute", mock_execute)

        result = shell._evaluate_and_execute("rm -rf /")

        assert result == 1
        mock_execute.assert_not_called()

    def test_prints_denial_message(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ):
        """Prints the denial message to stderr when command is blocked."""
        from safeshell.wrapper import shell

        # Mock DaemonClient at the import path
        mock_client = MagicMock()
        mock_client.evaluate.return_value = DaemonResponse(
            success=True,
            final_decision=Decision.DENY,
            should_execute=False,
            denial_message="Command blocked: dangerous operation",
        )

        mock_client_class = MagicMock(return_value=mock_client)
        monkeypatch.setattr(
            "safeshell.wrapper.client.DaemonClient", mock_client_class
        )

        shell._evaluate_and_execute("rm -rf /")

        captured = capsys.readouterr()
        assert "Command blocked: dangerous operation" in captured.err

    def test_fail_open_when_daemon_unreachable(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ):
        """Allows command when daemon is unreachable and fail_open is configured."""
        from safeshell.config import SafeShellConfig, UnreachableBehavior
        from safeshell.exceptions import DaemonNotRunningError
        from safeshell.wrapper import shell

        # Mock config to use FAIL_OPEN at the import path
        mock_config = SafeShellConfig(
            unreachable_behavior=UnreachableBehavior.FAIL_OPEN,
            delegate_shell="/bin/bash",
        )
        monkeypatch.setattr(
            "safeshell.config.load_config", lambda: mock_config
        )

        # Mock DaemonClient to raise DaemonNotRunningError
        mock_client = MagicMock()
        mock_client.ensure_daemon_running.side_effect = DaemonNotRunningError(
            "Daemon not running"
        )

        mock_client_class = MagicMock(return_value=mock_client)
        monkeypatch.setattr(
            "safeshell.wrapper.client.DaemonClient", mock_client_class
        )

        # Mock _execute
        mock_execute = MagicMock(return_value=0)
        monkeypatch.setattr(shell, "_execute", mock_execute)

        result = shell._evaluate_and_execute("echo hello")

        assert result == 0
        mock_execute.assert_called_once()
        captured = capsys.readouterr()
        assert "Warning" in captured.err

    def test_fail_closed_when_configured(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ):
        """Blocks command when daemon is unreachable and fail_closed is configured."""
        from safeshell.config import SafeShellConfig, UnreachableBehavior
        from safeshell.exceptions import DaemonNotRunningError
        from safeshell.wrapper import shell

        # Mock config to use FAIL_CLOSED at the import path
        mock_config = SafeShellConfig(
            unreachable_behavior=UnreachableBehavior.FAIL_CLOSED,
            delegate_shell="/bin/bash",
        )
        monkeypatch.setattr(
            "safeshell.config.load_config", lambda: mock_config
        )

        # Mock DaemonClient to raise DaemonNotRunningError
        mock_client = MagicMock()
        mock_client.ensure_daemon_running.side_effect = DaemonNotRunningError(
            "Daemon not running"
        )

        mock_client_class = MagicMock(return_value=mock_client)
        monkeypatch.setattr(
            "safeshell.wrapper.client.DaemonClient", mock_client_class
        )

        # Mock _execute - should not be called
        mock_execute = MagicMock()
        monkeypatch.setattr(shell, "_execute", mock_execute)

        result = shell._evaluate_and_execute("echo hello")

        assert result == 1
        mock_execute.assert_not_called()
        captured = capsys.readouterr()
        assert "blocked" in captured.err.lower()


class TestExecute:
    """Tests for _execute()."""

    def test_runs_command_and_returns_exit_code(self, monkeypatch: pytest.MonkeyPatch):
        """Runs command and returns exit code."""
        from safeshell.wrapper import shell

        # Mock plumbum.local at the plumbum module level
        mock_shell = MagicMock()
        mock_shell.__getitem__ = MagicMock(return_value=mock_shell)
        mock_shell.run.return_value = (0, "output", "")

        mock_local = MagicMock()
        mock_local.__getitem__ = MagicMock(return_value=mock_shell)

        monkeypatch.setattr("plumbum.local", mock_local)

        result = shell._execute("echo hello", "/bin/bash")

        assert result == 0

    def test_captures_stdout_and_stderr(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ):
        """Captures and writes stdout and stderr."""
        from safeshell.wrapper import shell

        # Mock plumbum.local at the plumbum module level
        mock_shell = MagicMock()
        mock_shell.__getitem__ = MagicMock(return_value=mock_shell)
        mock_shell.run.return_value = (0, "stdout content", "stderr content")

        mock_local = MagicMock()
        mock_local.__getitem__ = MagicMock(return_value=mock_shell)

        monkeypatch.setattr("plumbum.local", mock_local)

        result = shell._execute("some command", "/bin/bash")

        assert result == 0
        captured = capsys.readouterr()
        assert "stdout content" in captured.out
        assert "stderr content" in captured.err

    def test_returns_nonzero_exit_code(self, monkeypatch: pytest.MonkeyPatch):
        """Returns non-zero exit code from failed command."""
        from safeshell.wrapper import shell

        # Mock plumbum.local at the plumbum module level
        mock_shell = MagicMock()
        mock_shell.__getitem__ = MagicMock(return_value=mock_shell)
        mock_shell.run.return_value = (1, "", "error")

        mock_local = MagicMock()
        mock_local.__getitem__ = MagicMock(return_value=mock_shell)

        monkeypatch.setattr("plumbum.local", mock_local)

        result = shell._execute("false", "/bin/bash")

        assert result == 1


class TestMain:
    """Tests for main()."""

    def test_bypass_mode_executes_directly(self, monkeypatch: pytest.MonkeyPatch):
        """In bypass mode, executes command without evaluation."""
        from safeshell.wrapper import shell

        monkeypatch.setenv("SAFESHELL_BYPASS", "1")
        monkeypatch.setattr(sys, "argv", ["safeshell-wrapper", "-c", "echo hello"])

        # Mock _execute
        mock_execute = MagicMock(return_value=0)
        monkeypatch.setattr(shell, "_execute", mock_execute)

        result = shell.main()

        assert result == 0
        mock_execute.assert_called_once_with("echo hello", "/bin/bash")

    def test_c_flag_calls_evaluate_and_execute(self, monkeypatch: pytest.MonkeyPatch):
        """With -c flag, evaluates and executes command."""
        from safeshell.wrapper import shell

        monkeypatch.delenv("SAFESHELL_BYPASS", raising=False)
        monkeypatch.setattr(sys, "argv", ["safeshell-wrapper", "-c", "echo hello"])

        # Mock _evaluate_and_execute
        mock_eval = MagicMock(return_value=0)
        monkeypatch.setattr(shell, "_evaluate_and_execute", mock_eval)

        result = shell.main()

        assert result == 0
        mock_eval.assert_called_once_with("echo hello")

    def test_no_args_calls_passthrough(self, monkeypatch: pytest.MonkeyPatch):
        """With no args, passes through to real shell."""
        from safeshell.wrapper import shell

        monkeypatch.delenv("SAFESHELL_BYPASS", raising=False)
        monkeypatch.setattr(sys, "argv", ["safeshell-wrapper"])

        # Mock _passthrough
        mock_passthrough = MagicMock(side_effect=SystemExit(0))
        monkeypatch.setattr(shell, "_passthrough", mock_passthrough)

        with pytest.raises(SystemExit):
            shell.main()

        mock_passthrough.assert_called_once()

    def test_script_arg_calls_passthrough(self, monkeypatch: pytest.MonkeyPatch):
        """With script argument (not -c), passes through to real shell."""
        from safeshell.wrapper import shell

        monkeypatch.delenv("SAFESHELL_BYPASS", raising=False)
        monkeypatch.setattr(sys, "argv", ["safeshell-wrapper", "script.sh"])

        # Mock _passthrough
        mock_passthrough = MagicMock(side_effect=SystemExit(0))
        monkeypatch.setattr(shell, "_passthrough", mock_passthrough)

        with pytest.raises(SystemExit):
            shell.main()

        mock_passthrough.assert_called_once()
