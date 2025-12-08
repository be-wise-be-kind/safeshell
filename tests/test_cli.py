"""Tests for SafeShell CLI."""

from typer.testing import CliRunner

from safeshell.cli import app

runner = CliRunner()


def test_version_command() -> None:
    """Test that version command runs successfully."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "SafeShell" in result.stdout


def test_status_command() -> None:
    """Test that status command runs successfully."""
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    # Output should mention daemon status
    assert "Daemon" in result.stdout or "daemon" in result.stdout.lower()


def test_check_command_requires_daemon() -> None:
    """Test that check command requires daemon to be running."""
    result = runner.invoke(app, ["check", "ls -la"])
    # Should fail because daemon is not running
    assert result.exit_code == 1
    assert "not running" in result.stdout.lower() or "daemon" in result.stdout.lower()


def test_help() -> None:
    """Test that help displays correctly."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "safety layer" in result.stdout.lower()


def test_daemon_subcommand_exists() -> None:
    """Test that daemon subcommand is registered."""
    result = runner.invoke(app, ["daemon", "--help"])
    assert result.exit_code == 0
    assert "start" in result.stdout.lower()
    assert "stop" in result.stdout.lower()
    assert "status" in result.stdout.lower()


def test_wrapper_subcommand_exists() -> None:
    """Test that wrapper subcommand is registered."""
    result = runner.invoke(app, ["wrapper", "--help"])
    assert result.exit_code == 0
    assert "install" in result.stdout.lower()


def test_init_command_exists() -> None:
    """Test that init command is available."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "init" in result.stdout.lower()
