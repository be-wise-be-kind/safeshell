"""Tests for safeshell.hooks.claude_code_hook module."""

import json
import subprocess
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestFindWrapper:
    """Tests for find_wrapper() function."""

    def test_finds_wrapper_in_path(self) -> None:
        """Test finding wrapper in PATH."""
        from safeshell.hooks import claude_code_hook

        with tempfile.TemporaryDirectory() as tmpdir:
            wrapper = Path(tmpdir) / "safeshell-wrapper"
            wrapper.touch()
            wrapper.chmod(0o755)

            with patch.dict("os.environ", {"PATH": tmpdir}):
                result = claude_code_hook.find_wrapper()
                assert result == str(wrapper)

    def test_finds_wrapper_in_local_bin(self) -> None:
        """Test finding wrapper in ~/.local/bin/."""
        from safeshell.hooks import claude_code_hook

        with tempfile.TemporaryDirectory() as tmpdir:
            home_dir = Path(tmpdir)
            local_bin = home_dir / ".local/bin"
            local_bin.mkdir(parents=True)
            wrapper = local_bin / "safeshell-wrapper"
            wrapper.touch()
            wrapper.chmod(0o755)

            with (
                patch.dict("os.environ", {"PATH": "/nonexistent"}, clear=True),
                patch.object(Path, "home", return_value=home_dir),
            ):
                result = claude_code_hook.find_wrapper()
                assert result == str(wrapper)

    def test_returns_none_when_not_found(self) -> None:
        """Test returns None when wrapper not found anywhere."""
        from safeshell.hooks import claude_code_hook

        with tempfile.TemporaryDirectory() as tmpdir:
            # No wrapper anywhere
            home_dir = Path(tmpdir)

            with (
                patch.dict("os.environ", {"PATH": "/nonexistent"}, clear=True),
                patch.object(Path, "home", return_value=home_dir),
            ):
                result = claude_code_hook.find_wrapper()
                assert result is None

    def test_skips_non_executable_files(self) -> None:
        """Test that non-executable files are skipped."""
        from safeshell.hooks import claude_code_hook

        with tempfile.TemporaryDirectory() as tmpdir:
            wrapper = Path(tmpdir) / "safeshell-wrapper"
            wrapper.touch()
            # Not executable
            wrapper.chmod(0o644)

            with (
                patch.dict("os.environ", {"PATH": tmpdir}, clear=True),
                patch.object(Path, "home", return_value=Path(tmpdir)),
            ):
                result = claude_code_hook.find_wrapper()
                assert result is None


class TestCheckCommand:
    """Tests for check_command() function."""

    def test_returns_allowed_when_wrapper_not_found(self) -> None:
        """Test fail-open when wrapper not found."""
        from safeshell.hooks import claude_code_hook

        with patch.object(claude_code_hook, "find_wrapper", return_value=None):
            allowed, message = claude_code_hook.check_command("echo hello")
            assert allowed is True
            assert "not found" in message.lower()

    def test_returns_allowed_when_daemon_not_running(self) -> None:
        """Test fail-open when daemon socket doesn't exist."""
        from safeshell.hooks import claude_code_hook

        with tempfile.TemporaryDirectory() as tmpdir:
            # No socket file exists
            with (
                patch.object(claude_code_hook, "find_wrapper", return_value="/usr/bin/wrapper"),
                patch.dict("os.environ", {"SAFESHELL_SOCKET": f"{tmpdir}/nonexistent.sock"}),
            ):
                allowed, message = claude_code_hook.check_command("echo hello")
                assert allowed is True
                assert "not running" in message.lower()

    def test_returns_allowed_when_command_allowed(self) -> None:
        """Test returns (True, '') when command is allowed."""
        from safeshell.hooks import claude_code_hook

        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "daemon.sock"
            socket_path.touch()

            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stderr = ""

            with (
                patch.object(claude_code_hook, "find_wrapper", return_value="/usr/bin/wrapper"),
                patch.dict("os.environ", {"SAFESHELL_SOCKET": str(socket_path)}),
                patch.object(subprocess, "run", return_value=mock_result),
            ):
                allowed, message = claude_code_hook.check_command("echo hello")
                assert allowed is True
                assert message == ""

    def test_returns_blocked_when_command_denied(self) -> None:
        """Test returns (False, message) when command is blocked."""
        from safeshell.hooks import claude_code_hook

        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "daemon.sock"
            socket_path.touch()

            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stderr = "Command blocked by SafeShell"

            with (
                patch.object(claude_code_hook, "find_wrapper", return_value="/usr/bin/wrapper"),
                patch.dict("os.environ", {"SAFESHELL_SOCKET": str(socket_path)}),
                patch.object(subprocess, "run", return_value=mock_result),
            ):
                allowed, message = claude_code_hook.check_command("rm -rf /")
                assert allowed is False
                assert "blocked" in message.lower()

    def test_sets_check_only_env_var(self) -> None:
        """Test that SAFESHELL_CHECK_ONLY=1 is set."""
        from safeshell.hooks import claude_code_hook

        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "daemon.sock"
            socket_path.touch()

            captured_env = {}

            def capture_run(*args, **kwargs):
                captured_env.update(kwargs.get("env", {}))
                result = MagicMock()
                result.returncode = 0
                result.stderr = ""
                return result

            with (
                patch.object(claude_code_hook, "find_wrapper", return_value="/usr/bin/wrapper"),
                patch.dict("os.environ", {"SAFESHELL_SOCKET": str(socket_path)}),
                patch.object(subprocess, "run", side_effect=capture_run),
            ):
                claude_code_hook.check_command("echo hello")
                assert captured_env.get("SAFESHELL_CHECK_ONLY") == "1"

    def test_sets_ai_context_env_var(self) -> None:
        """Test that SAFESHELL_CONTEXT=ai is set."""
        from safeshell.hooks import claude_code_hook

        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "daemon.sock"
            socket_path.touch()

            captured_env = {}

            def capture_run(*args, **kwargs):
                captured_env.update(kwargs.get("env", {}))
                result = MagicMock()
                result.returncode = 0
                result.stderr = ""
                return result

            with (
                patch.object(claude_code_hook, "find_wrapper", return_value="/usr/bin/wrapper"),
                patch.dict("os.environ", {"SAFESHELL_SOCKET": str(socket_path)}),
                patch.object(subprocess, "run", side_effect=capture_run),
            ):
                claude_code_hook.check_command("echo hello")
                assert captured_env.get("SAFESHELL_CONTEXT") == "ai"

    def test_handles_timeout(self) -> None:
        """Test fail-closed on timeout."""
        from safeshell.hooks import claude_code_hook

        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "daemon.sock"
            socket_path.touch()

            with (
                patch.object(claude_code_hook, "find_wrapper", return_value="/usr/bin/wrapper"),
                patch.dict("os.environ", {"SAFESHELL_SOCKET": str(socket_path)}),
                patch.object(subprocess, "run", side_effect=subprocess.TimeoutExpired("cmd", 600)),
            ):
                allowed, message = claude_code_hook.check_command("slow_command")
                assert allowed is False
                assert "timed out" in message.lower()

    def test_fail_open_on_exception(self) -> None:
        """Test fail-open on generic exception."""
        from safeshell.hooks import claude_code_hook

        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "daemon.sock"
            socket_path.touch()

            with (
                patch.object(claude_code_hook, "find_wrapper", return_value="/usr/bin/wrapper"),
                patch.dict("os.environ", {"SAFESHELL_SOCKET": str(socket_path)}),
                patch.object(subprocess, "run", side_effect=Exception("Something went wrong")),
            ):
                allowed, message = claude_code_hook.check_command("echo hello")
                assert allowed is True
                assert "error" in message.lower()


class TestMain:
    """Tests for main() entry point."""

    def test_returns_zero_for_non_bash_tool(self) -> None:
        """Test returns 0 for non-Bash tools."""
        from safeshell.hooks import claude_code_hook

        input_data = {"tool_name": "Read", "tool_input": {"file_path": "/etc/passwd"}}
        stdin = StringIO(json.dumps(input_data))

        with patch("sys.stdin", stdin):
            result = claude_code_hook.main()
            assert result == 0

    def test_returns_zero_for_empty_command(self) -> None:
        """Test returns 0 for Bash with empty command."""
        from safeshell.hooks import claude_code_hook

        input_data = {"tool_name": "Bash", "tool_input": {"command": ""}}
        stdin = StringIO(json.dumps(input_data))

        with patch("sys.stdin", stdin):
            result = claude_code_hook.main()
            assert result == 0

    def test_returns_zero_when_command_allowed(self) -> None:
        """Test returns 0 when command is allowed."""
        from safeshell.hooks import claude_code_hook

        input_data = {"tool_name": "Bash", "tool_input": {"command": "echo hello"}}
        stdin = StringIO(json.dumps(input_data))

        with (
            patch("sys.stdin", stdin),
            patch.object(claude_code_hook, "check_command", return_value=(True, "")),
        ):
            result = claude_code_hook.main()
            assert result == 0

    def test_returns_two_when_command_blocked(self) -> None:
        """Test returns 2 when command is blocked."""
        from safeshell.hooks import claude_code_hook

        input_data = {"tool_name": "Bash", "tool_input": {"command": "rm -rf /"}}
        stdin = StringIO(json.dumps(input_data))

        with (
            patch("sys.stdin", stdin),
            patch.object(claude_code_hook, "check_command", return_value=(False, "Blocked")),
        ):
            result = claude_code_hook.main()
            assert result == 2

    def test_prints_block_message_to_stderr(self) -> None:
        """Test that block message is printed to stderr."""
        from safeshell.hooks import claude_code_hook

        input_data = {"tool_name": "Bash", "tool_input": {"command": "rm -rf /"}}
        stdin = StringIO(json.dumps(input_data))
        stderr_output = []

        with (
            patch("sys.stdin", stdin),
            patch.object(claude_code_hook, "check_command", return_value=(False, "Custom block message")),
            patch("builtins.print", side_effect=lambda *args, **kwargs: stderr_output.append(args[0])),
        ):
            claude_code_hook.main()
            assert any("Custom block message" in str(msg) for msg in stderr_output)

    def test_fail_open_on_json_decode_error(self) -> None:
        """Test fail-open when JSON parsing fails."""
        from safeshell.hooks import claude_code_hook

        stdin = StringIO("not valid json")

        with patch("sys.stdin", stdin):
            result = claude_code_hook.main()
            assert result == 0

    def test_handles_missing_tool_input(self) -> None:
        """Test handles missing tool_input gracefully."""
        from safeshell.hooks import claude_code_hook

        input_data = {"tool_name": "Bash"}  # Missing tool_input
        stdin = StringIO(json.dumps(input_data))

        with patch("sys.stdin", stdin):
            result = claude_code_hook.main()
            assert result == 0

    def test_handles_missing_command_in_tool_input(self) -> None:
        """Test handles missing command in tool_input."""
        from safeshell.hooks import claude_code_hook

        input_data = {"tool_name": "Bash", "tool_input": {}}  # Missing command
        stdin = StringIO(json.dumps(input_data))

        with patch("sys.stdin", stdin):
            result = claude_code_hook.main()
            assert result == 0


class TestExitCodes:
    """Tests for exit code behavior."""

    def test_exit_zero_allows_command(self) -> None:
        """Test that exit 0 allows command execution in Claude Code."""
        # Exit 0 = allow
        from safeshell.hooks import claude_code_hook

        input_data = {"tool_name": "Bash", "tool_input": {"command": "ls"}}
        stdin = StringIO(json.dumps(input_data))

        with (
            patch("sys.stdin", stdin),
            patch.object(claude_code_hook, "check_command", return_value=(True, "")),
        ):
            result = claude_code_hook.main()
            assert result == 0  # Allow

    def test_exit_two_blocks_command(self) -> None:
        """Test that exit 2 blocks command execution in Claude Code."""
        # Exit 2 = block (per Claude Code hook protocol)
        from safeshell.hooks import claude_code_hook

        input_data = {"tool_name": "Bash", "tool_input": {"command": "rm -rf /"}}
        stdin = StringIO(json.dumps(input_data))

        with (
            patch("sys.stdin", stdin),
            patch.object(claude_code_hook, "check_command", return_value=(False, "Blocked")),
        ):
            result = claude_code_hook.main()
            assert result == 2  # Block
