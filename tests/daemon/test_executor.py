"""Tests for daemon executor module."""

import os
import tempfile
from pathlib import Path

import pytest

from safeshell.daemon.executor import ExecutionResult, execute_command


class TestExecutionResult:
    """Tests for ExecutionResult dataclass."""

    def test_execution_result_fields(self) -> None:
        """Test ExecutionResult has expected fields."""
        result = ExecutionResult(
            exit_code=0,
            stdout="hello\n",
            stderr="",
            execution_time_ms=5.0,
        )
        assert result.exit_code == 0
        assert result.stdout == "hello\n"
        assert result.stderr == ""
        assert result.execution_time_ms == 5.0


class TestExecuteCommand:
    """Tests for execute_command function."""

    @pytest.mark.asyncio
    async def test_simple_command_success(self, tmp_path: Path) -> None:
        """Test executing a simple command that succeeds."""
        result = await execute_command("echo hello", working_dir=str(tmp_path))
        assert result.exit_code == 0
        assert result.stdout.strip() == "hello"
        assert result.stderr == ""
        assert result.execution_time_ms > 0

    @pytest.mark.asyncio
    async def test_command_with_args(self, tmp_path: Path) -> None:
        """Test executing a command with arguments."""
        result = await execute_command("echo -n test", working_dir=str(tmp_path))
        assert result.exit_code == 0
        assert result.stdout == "test"

    @pytest.mark.asyncio
    async def test_command_failure(self, tmp_path: Path) -> None:
        """Test executing a command that fails."""
        result = await execute_command("exit 42", working_dir=str(tmp_path))
        assert result.exit_code == 42
        assert result.execution_time_ms > 0

    @pytest.mark.asyncio
    async def test_command_with_stderr(self, tmp_path: Path) -> None:
        """Test executing a command that writes to stderr."""
        result = await execute_command("echo error >&2", working_dir=str(tmp_path))
        assert result.exit_code == 0
        assert result.stderr.strip() == "error"

    @pytest.mark.asyncio
    async def test_command_with_working_dir(self) -> None:
        """Test executing a command in a specific working directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = await execute_command("pwd", working_dir=tmpdir)
            assert result.exit_code == 0
            # Resolve symlinks for comparison (macOS /tmp -> /private/tmp)
            assert os.path.realpath(result.stdout.strip()) == os.path.realpath(tmpdir)

    @pytest.mark.asyncio
    async def test_command_with_env(self, tmp_path: Path) -> None:
        """Test executing a command with custom environment."""
        result = await execute_command(
            "echo $MY_VAR",
            working_dir=str(tmp_path),
            env={"MY_VAR": "custom_value"},
        )
        assert result.exit_code == 0
        assert result.stdout.strip() == "custom_value"

    @pytest.mark.asyncio
    async def test_command_inherits_path(self, tmp_path: Path) -> None:
        """Test that command inherits PATH from environment."""
        # echo is a shell builtin, but ls should be found in PATH
        result = await execute_command("which ls", working_dir=str(tmp_path))
        assert result.exit_code == 0
        assert "/ls" in result.stdout

    @pytest.mark.asyncio
    async def test_invalid_working_dir(self) -> None:
        """Test executing a command in non-existent directory."""
        result = await execute_command("echo test", working_dir="/nonexistent/path")
        assert result.exit_code == 127  # Execution error
        assert "Execution error" in result.stderr

    @pytest.mark.asyncio
    async def test_multiline_output(self, tmp_path: Path) -> None:
        """Test executing a command with multiline output."""
        # Use printf instead of echo -e for portable multiline output
        result = await execute_command(
            "printf 'line1\\nline2\\nline3\\n'", working_dir=str(tmp_path)
        )
        assert result.exit_code == 0
        lines = result.stdout.strip().split("\n")
        assert len(lines) == 3
        assert lines[0] == "line1"
        assert lines[1] == "line2"
        assert lines[2] == "line3"

    @pytest.mark.asyncio
    async def test_command_not_found(self, tmp_path: Path) -> None:
        """Test executing a command that doesn't exist."""
        result = await execute_command("nonexistent_command_xyz", working_dir=str(tmp_path))
        assert result.exit_code != 0
        # Shell returns 127 for command not found
        assert result.exit_code == 127

    @pytest.mark.asyncio
    async def test_timing_measurement(self, tmp_path: Path) -> None:
        """Test that execution time is measured."""
        # Sleep for a small amount to verify timing works
        result = await execute_command("sleep 0.1", working_dir=str(tmp_path))
        assert result.exit_code == 0
        # Should be at least 100ms
        assert result.execution_time_ms >= 90  # Allow some tolerance

    @pytest.mark.asyncio
    async def test_shell_features(self, tmp_path: Path) -> None:
        """Test that shell features work (pipes, redirects, etc.)."""
        result = await execute_command("echo hello | tr 'h' 'H'", working_dir=str(tmp_path))
        assert result.exit_code == 0
        assert result.stdout.strip() == "Hello"

    @pytest.mark.asyncio
    async def test_command_with_quotes(self, tmp_path: Path) -> None:
        """Test executing a command with quoted arguments."""
        result = await execute_command('echo "hello world"', working_dir=str(tmp_path))
        assert result.exit_code == 0
        assert result.stdout.strip() == "hello world"
