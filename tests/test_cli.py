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
    assert "status" in result.stdout.lower()


def test_check_command() -> None:
    """Test that check command runs with a command argument."""
    result = runner.invoke(app, ["check", "ls -la"])
    assert result.exit_code == 0
    assert "ls -la" in result.stdout


def test_help() -> None:
    """Test that help displays correctly."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "safety layer" in result.stdout.lower()
