"""Tests for safeshell.wrapper.cli module."""

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from safeshell.wrapper.cli import app

runner = CliRunner()


class TestWrapperInstall:
    """Tests for wrapper install command."""

    def test_install_shows_wrapper_path(self) -> None:
        """Test install command shows wrapper path."""
        result = runner.invoke(app, ["install"])
        assert result.exit_code == 0
        assert "wrapper" in result.stdout.lower()

    def test_install_shows_shell(self) -> None:
        """Test install command shows detected shell."""
        result = runner.invoke(app, ["install"])
        assert result.exit_code == 0
        # Should mention shell or bash/zsh
        output_lower = result.stdout.lower()
        assert "shell" in output_lower or "bash" in output_lower or "zsh" in output_lower

    def test_install_shows_claude_code_instructions(self) -> None:
        """Test install command shows Claude Code setup instructions."""
        result = runner.invoke(app, ["install"])
        assert result.exit_code == 0
        assert "claude" in result.stdout.lower()

    def test_install_shows_cursor_instructions(self) -> None:
        """Test install command shows Cursor setup instructions."""
        result = runner.invoke(app, ["install"])
        assert result.exit_code == 0
        assert "cursor" in result.stdout.lower()

    def test_install_shows_daemon_start_instruction(self) -> None:
        """Test install command shows daemon start instruction."""
        result = runner.invoke(app, ["install"])
        assert result.exit_code == 0
        assert "daemon start" in result.stdout.lower()


class TestWrapperPath:
    """Tests for wrapper path command."""

    def test_path_outputs_something(self) -> None:
        """Test path command outputs a path."""
        result = runner.invoke(app, ["path"])
        assert result.exit_code == 0
        assert result.stdout.strip()  # Non-empty output

    def test_path_finds_wrapper_in_venv(self) -> None:
        """Test path finds wrapper in venv bin directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a fake wrapper in the same dir as python
            bin_dir = Path(tmpdir)
            wrapper = bin_dir / "safeshell-wrapper"
            wrapper.touch()
            fake_python = bin_dir / "python"
            fake_python.touch()

            with patch.object(sys, "executable", str(fake_python)):
                # Need to reimport to get updated _get_wrapper_path
                from safeshell.wrapper import cli as wrapper_cli

                result = wrapper_cli._get_wrapper_path()
                assert str(wrapper) == result

    def test_path_fallback_when_not_found(self) -> None:
        """Test path returns fallback when wrapper not found in venv."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # No wrapper exists
            fake_python = Path(tmpdir) / "python"
            fake_python.touch()

            with patch.object(sys, "executable", str(fake_python)):
                from safeshell.wrapper import cli as wrapper_cli

                result = wrapper_cli._get_wrapper_path()
                assert result == "safeshell-wrapper"


class TestHelpText:
    """Tests for CLI help text."""

    def test_app_help(self) -> None:
        """Test main wrapper command help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "wrapper" in result.stdout.lower()

    def test_install_help(self) -> None:
        """Test install command help."""
        result = runner.invoke(app, ["install", "--help"])
        assert result.exit_code == 0
        assert "install" in result.stdout.lower()

    def test_path_help(self) -> None:
        """Test path command help."""
        result = runner.invoke(app, ["path", "--help"])
        assert result.exit_code == 0
        assert "path" in result.stdout.lower()
