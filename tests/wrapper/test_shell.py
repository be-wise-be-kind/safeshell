"""Tests for safeshell.wrapper.shell module."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from safeshell.config import SafeShellConfig, UnreachableBehavior
from safeshell.exceptions import DaemonNotRunningError, DaemonStartError
from safeshell.models import DaemonResponse, Decision


class TestMain:
    """Tests for main() entry point."""

    def test_command_invocation_calls_evaluate(self) -> None:
        """Test that -c 'command' invocation calls _evaluate_and_execute."""
        from safeshell.wrapper import shell

        with (
            patch.object(shell, "_evaluate_and_execute", return_value=0) as mock_eval,
            patch.object(sys, "argv", ["wrapper", "-c", "echo hello"]),
        ):
            result = shell.main()
            assert result == 0
            mock_eval.assert_called_once_with("echo hello")

    def test_no_args_calls_passthrough(self) -> None:
        """Test that no args invocation calls _passthrough."""
        from safeshell.wrapper import shell

        with (
            patch.object(shell, "_passthrough") as mock_pass,
            patch.object(sys, "argv", ["wrapper"]),
        ):
            shell.main()
            mock_pass.assert_called_once()

    def test_script_invocation_calls_passthrough(self) -> None:
        """Test that script invocation calls _passthrough."""
        from safeshell.wrapper import shell

        with (
            patch.object(shell, "_passthrough") as mock_pass,
            patch.object(sys, "argv", ["wrapper", "script.sh"]),
        ):
            shell.main()
            mock_pass.assert_called_once()

    def test_single_arg_calls_passthrough(self) -> None:
        """Test that single arg (not -c) calls _passthrough."""
        from safeshell.wrapper import shell

        with (
            patch.object(shell, "_passthrough") as mock_pass,
            patch.object(sys, "argv", ["wrapper", "-i"]),
        ):
            shell.main()
            mock_pass.assert_called_once()


class TestEvaluateAndExecute:
    """Tests for _evaluate_and_execute()."""

    @pytest.fixture
    def mock_config(self) -> SafeShellConfig:
        """Create a mock config."""
        return SafeShellConfig(delegate_shell="/bin/bash")

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock DaemonClient."""
        client = MagicMock()
        client.ensure_daemon_running = MagicMock()
        return client

    def test_executes_allowed_command(self, mock_config: SafeShellConfig) -> None:
        """Test that allowed commands are executed."""
        from safeshell.wrapper import shell

        response = DaemonResponse(
            success=True,
            final_decision=Decision.ALLOW,
            should_execute=True,
        )

        mock_client = MagicMock()
        mock_client.evaluate.return_value = response

        with (
            patch.object(shell, "load_config", return_value=mock_config),
            patch.object(shell, "DaemonClient", return_value=mock_client),
            patch.object(shell, "_execute", return_value=0) as mock_exec,
            patch.dict("os.environ", {}, clear=True),
        ):
            result = shell._evaluate_and_execute("echo hello")
            assert result == 0
            mock_exec.assert_called_once_with("echo hello", "/bin/bash")

    def test_blocks_denied_command(self, mock_config: SafeShellConfig) -> None:
        """Test that denied commands are blocked."""
        from safeshell.wrapper import shell

        response = DaemonResponse(
            success=True,
            final_decision=Decision.DENY,
            should_execute=False,
            denial_message="Command blocked by policy",
        )

        mock_client = MagicMock()
        mock_client.evaluate.return_value = response

        with (
            patch.object(shell, "load_config", return_value=mock_config),
            patch.object(shell, "DaemonClient", return_value=mock_client),
            patch.dict("os.environ", {}, clear=True),
        ):
            result = shell._evaluate_and_execute("rm -rf /")
            assert result == 1

    def test_denied_command_prints_message(self, mock_config: SafeShellConfig) -> None:
        """Test that denial message is printed to stderr."""
        from safeshell.wrapper import shell

        response = DaemonResponse(
            success=True,
            final_decision=Decision.DENY,
            should_execute=False,
            denial_message="Custom denial message",
        )

        mock_client = MagicMock()
        mock_client.evaluate.return_value = response
        stderr_output = []

        def capture_stderr(msg: str) -> None:
            stderr_output.append(msg)

        with (
            patch.object(shell, "load_config", return_value=mock_config),
            patch.object(shell, "DaemonClient", return_value=mock_client),
            patch.object(sys.stderr, "write", side_effect=capture_stderr),
            patch.dict("os.environ", {}, clear=True),
        ):
            shell._evaluate_and_execute("bad command")
            assert any("Custom denial message" in msg for msg in stderr_output)

    def test_default_denial_message_when_none(self, mock_config: SafeShellConfig) -> None:
        """Test default denial message when none provided."""
        from safeshell.wrapper import shell

        response = DaemonResponse(
            success=True,
            final_decision=Decision.DENY,
            should_execute=False,
            denial_message=None,
        )

        mock_client = MagicMock()
        mock_client.evaluate.return_value = response
        stderr_output = []

        def capture_stderr(msg: str) -> None:
            stderr_output.append(msg)

        with (
            patch.object(shell, "load_config", return_value=mock_config),
            patch.object(shell, "DaemonClient", return_value=mock_client),
            patch.object(sys.stderr, "write", side_effect=capture_stderr),
            patch.dict("os.environ", {}, clear=True),
        ):
            shell._evaluate_and_execute("bad command")
            assert any("blocked by policy" in msg for msg in stderr_output)

    def test_check_only_mode_returns_zero_when_allowed(self, mock_config: SafeShellConfig) -> None:
        """Test CHECK_ONLY mode returns 0 for allowed commands."""
        from safeshell.wrapper import shell

        response = DaemonResponse(
            success=True,
            final_decision=Decision.ALLOW,
            should_execute=True,
        )

        mock_client = MagicMock()
        mock_client.evaluate.return_value = response

        with (
            patch.object(shell, "load_config", return_value=mock_config),
            patch.object(shell, "DaemonClient", return_value=mock_client),
            patch.object(shell, "_execute") as mock_exec,
            patch.dict("os.environ", {"SAFESHELL_CHECK_ONLY": "1"}, clear=True),
        ):
            result = shell._evaluate_and_execute("echo hello")
            assert result == 0
            # Should NOT execute in check-only mode
            mock_exec.assert_not_called()

    def test_ai_context_environment_variable(self, mock_config: SafeShellConfig) -> None:
        """Test SAFESHELL_CONTEXT=ai is passed to evaluate."""
        from safeshell.wrapper import shell

        response = DaemonResponse(
            success=True,
            final_decision=Decision.ALLOW,
            should_execute=True,
        )

        mock_client = MagicMock()
        mock_client.evaluate.return_value = response

        with (
            patch.object(shell, "load_config", return_value=mock_config),
            patch.object(shell, "DaemonClient", return_value=mock_client),
            patch.object(shell, "_execute", return_value=0),
            patch.dict("os.environ", {"SAFESHELL_CONTEXT": "ai"}, clear=True),
        ):
            shell._evaluate_and_execute("echo hello")
            call_kwargs = mock_client.evaluate.call_args.kwargs
            assert call_kwargs["execution_context"] == "ai"

    def test_warp_ai_agent_sets_ai_context(self, mock_config: SafeShellConfig) -> None:
        """Test WARP_AI_AGENT=1 sets ai execution context."""
        from safeshell.wrapper import shell

        response = DaemonResponse(
            success=True,
            final_decision=Decision.ALLOW,
            should_execute=True,
        )

        mock_client = MagicMock()
        mock_client.evaluate.return_value = response

        with (
            patch.object(shell, "load_config", return_value=mock_config),
            patch.object(shell, "DaemonClient", return_value=mock_client),
            patch.object(shell, "_execute", return_value=0),
            patch.dict("os.environ", {"WARP_AI_AGENT": "1"}, clear=True),
        ):
            shell._evaluate_and_execute("echo hello")
            call_kwargs = mock_client.evaluate.call_args.kwargs
            assert call_kwargs["execution_context"] == "ai"

    def test_human_context_by_default(self, mock_config: SafeShellConfig) -> None:
        """Test human execution context when no AI env vars set."""
        from safeshell.wrapper import shell

        response = DaemonResponse(
            success=True,
            final_decision=Decision.ALLOW,
            should_execute=True,
        )

        mock_client = MagicMock()
        mock_client.evaluate.return_value = response

        with (
            patch.object(shell, "load_config", return_value=mock_config),
            patch.object(shell, "DaemonClient", return_value=mock_client),
            patch.object(shell, "_execute", return_value=0),
            patch.dict("os.environ", {}, clear=True),
        ):
            shell._evaluate_and_execute("echo hello")
            call_kwargs = mock_client.evaluate.call_args.kwargs
            assert call_kwargs["execution_context"] == "human"


class TestDaemonUnreachable:
    """Tests for daemon unreachable scenarios."""

    @pytest.fixture
    def mock_config_fail_open(self) -> SafeShellConfig:
        """Create config with fail-open behavior."""
        return SafeShellConfig(
            delegate_shell="/bin/bash",
            unreachable_behavior=UnreachableBehavior.FAIL_OPEN,
        )

    @pytest.fixture
    def mock_config_fail_closed(self) -> SafeShellConfig:
        """Create config with fail-closed behavior."""
        return SafeShellConfig(
            delegate_shell="/bin/bash",
            unreachable_behavior=UnreachableBehavior.FAIL_CLOSED,
        )

    def test_fail_open_executes_on_daemon_not_running(
        self, mock_config_fail_open: SafeShellConfig
    ) -> None:
        """Test fail-open executes command when daemon not running."""
        from safeshell.wrapper import shell

        mock_client = MagicMock()
        mock_client.ensure_daemon_running.side_effect = DaemonNotRunningError("Not running")

        with (
            patch.object(shell, "load_config", return_value=mock_config_fail_open),
            patch.object(shell, "DaemonClient", return_value=mock_client),
            patch.object(shell, "_execute", return_value=0) as mock_exec,
            patch.dict("os.environ", {}, clear=True),
        ):
            result = shell._evaluate_and_execute("echo hello")
            assert result == 0
            mock_exec.assert_called_once()

    def test_fail_closed_blocks_on_daemon_not_running(
        self, mock_config_fail_closed: SafeShellConfig
    ) -> None:
        """Test fail-closed blocks command when daemon not running."""
        from safeshell.wrapper import shell

        mock_client = MagicMock()
        mock_client.ensure_daemon_running.side_effect = DaemonNotRunningError("Not running")

        with (
            patch.object(shell, "load_config", return_value=mock_config_fail_closed),
            patch.object(shell, "DaemonClient", return_value=mock_client),
            patch.object(shell, "_execute") as mock_exec,
            patch.dict("os.environ", {}, clear=True),
        ):
            result = shell._evaluate_and_execute("echo hello")
            assert result == 1
            mock_exec.assert_not_called()

    def test_fail_open_on_daemon_start_error(
        self, mock_config_fail_open: SafeShellConfig
    ) -> None:
        """Test fail-open on daemon start error."""
        from safeshell.wrapper import shell

        mock_client = MagicMock()
        mock_client.ensure_daemon_running.side_effect = DaemonStartError("Failed to start")

        with (
            patch.object(shell, "load_config", return_value=mock_config_fail_open),
            patch.object(shell, "DaemonClient", return_value=mock_client),
            patch.object(shell, "_execute", return_value=0) as mock_exec,
            patch.dict("os.environ", {}, clear=True),
        ):
            result = shell._evaluate_and_execute("echo hello")
            assert result == 0
            mock_exec.assert_called_once()

    def test_check_only_mode_returns_zero_on_fail_open(
        self, mock_config_fail_open: SafeShellConfig
    ) -> None:
        """Test check-only mode returns 0 in fail-open scenario."""
        from safeshell.wrapper import shell

        mock_client = MagicMock()
        mock_client.ensure_daemon_running.side_effect = DaemonNotRunningError("Not running")

        with (
            patch.object(shell, "load_config", return_value=mock_config_fail_open),
            patch.object(shell, "DaemonClient", return_value=mock_client),
            patch.object(shell, "_execute") as mock_exec,
            patch.dict("os.environ", {"SAFESHELL_CHECK_ONLY": "1"}, clear=True),
        ):
            result = shell._evaluate_and_execute("echo hello")
            assert result == 0
            # Should not execute in check-only mode
            mock_exec.assert_not_called()


class TestExecute:
    """Tests for _execute() function."""

    def test_returns_exit_code_from_command(self) -> None:
        """Test that exit code from command is returned."""
        from safeshell.wrapper import shell

        with patch("plumbum.local") as mock_local:
            mock_shell = MagicMock()
            mock_local.__getitem__.return_value = mock_shell
            mock_cmd = MagicMock()
            mock_shell.__getitem__.return_value = mock_cmd
            mock_cmd.run.return_value = (0, "output", "")

            result = shell._execute("echo hello", "/bin/bash")
            assert result == 0

    def test_returns_nonzero_exit_code(self) -> None:
        """Test that nonzero exit codes are returned."""
        from safeshell.wrapper import shell

        with patch("plumbum.local") as mock_local:
            mock_shell = MagicMock()
            mock_local.__getitem__.return_value = mock_shell
            mock_cmd = MagicMock()
            mock_shell.__getitem__.return_value = mock_cmd
            mock_cmd.run.return_value = (1, "", "error")

            result = shell._execute("false", "/bin/bash")
            assert result == 1

    def test_writes_stdout(self) -> None:
        """Test that stdout is written."""
        from safeshell.wrapper import shell

        stdout_output = []

        def capture_stdout(msg: str) -> None:
            stdout_output.append(msg)

        with (
            patch("plumbum.local") as mock_local,
            patch.object(sys.stdout, "write", side_effect=capture_stdout),
        ):
            mock_shell = MagicMock()
            mock_local.__getitem__.return_value = mock_shell
            mock_cmd = MagicMock()
            mock_shell.__getitem__.return_value = mock_cmd
            mock_cmd.run.return_value = (0, "hello world", "")

            shell._execute("echo hello", "/bin/bash")
            assert any("hello world" in msg for msg in stdout_output)

    def test_writes_stderr(self) -> None:
        """Test that stderr is written."""
        from safeshell.wrapper import shell

        stderr_output = []

        def capture_stderr(msg: str) -> None:
            stderr_output.append(msg)

        with (
            patch("plumbum.local") as mock_local,
            patch.object(sys.stderr, "write", side_effect=capture_stderr),
        ):
            mock_shell = MagicMock()
            mock_local.__getitem__.return_value = mock_shell
            mock_cmd = MagicMock()
            mock_shell.__getitem__.return_value = mock_cmd
            mock_cmd.run.return_value = (0, "", "error output")

            shell._execute("cmd", "/bin/bash")
            assert any("error output" in msg for msg in stderr_output)

    def test_handles_process_execution_error(self) -> None:
        """Test handling of ProcessExecutionError."""
        from plumbum.commands.processes import ProcessExecutionError

        from safeshell.wrapper import shell

        with patch("plumbum.local") as mock_local:
            mock_shell = MagicMock()
            mock_local.__getitem__.return_value = mock_shell
            mock_cmd = MagicMock()
            mock_shell.__getitem__.return_value = mock_cmd
            mock_cmd.run.side_effect = ProcessExecutionError([], 127, "", "")

            result = shell._execute("nonexistent", "/bin/bash")
            assert result == 127

    def test_handles_generic_exception(self) -> None:
        """Test handling of generic exceptions."""
        from safeshell.wrapper import shell

        with patch("plumbum.local") as mock_local:
            mock_shell = MagicMock()
            mock_local.__getitem__.return_value = mock_shell
            mock_cmd = MagicMock()
            mock_shell.__getitem__.return_value = mock_cmd
            mock_cmd.run.side_effect = Exception("Something went wrong")

            result = shell._execute("cmd", "/bin/bash")
            assert result == 1


class TestPassthrough:
    """Tests for _passthrough() function."""

    def test_calls_execv_with_delegate_shell(self) -> None:
        """Test that os.execv is called with delegate shell."""
        from safeshell.wrapper import shell

        # Create a mock config that bypasses validation
        mock_config = MagicMock()
        mock_config.delegate_shell = "/bin/zsh"

        with (
            patch.object(shell, "load_config", return_value=mock_config),
            patch("os.execv") as mock_execv,
            patch.object(sys, "argv", ["wrapper", "-i"]),
        ):
            try:
                shell._passthrough()
            except SystemExit:
                pass  # Expected since os.execv is mocked

            mock_execv.assert_called_once_with("/bin/zsh", ["/bin/zsh", "-i"])

    def test_passes_all_args_to_shell(self) -> None:
        """Test that all args are passed to delegate shell."""
        from safeshell.wrapper import shell

        mock_config = MagicMock()
        mock_config.delegate_shell = "/bin/bash"

        with (
            patch.object(shell, "load_config", return_value=mock_config),
            patch("os.execv") as mock_execv,
            patch.object(sys, "argv", ["wrapper", "script.sh", "arg1", "arg2"]),
        ):
            try:
                shell._passthrough()
            except SystemExit:
                pass

            mock_execv.assert_called_once_with(
                "/bin/bash", ["/bin/bash", "script.sh", "arg1", "arg2"]
            )
