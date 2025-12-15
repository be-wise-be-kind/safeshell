"""Tests for safeshell.rules.cli module."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

# Import the main app to test via the subcommand path
from safeshell.cli import app

runner = CliRunner()


class TestValidateCommand:
    """Tests for validate command."""

    def test_validate_help(self) -> None:
        """Test validate command help."""
        result = runner.invoke(app, ["rules", "validate", "--help"])
        assert result.exit_code == 0
        assert "validate" in result.stdout.lower()

    def test_validate_single_file_not_found(self) -> None:
        """Test validate with nonexistent file."""
        result = runner.invoke(app, ["rules", "validate", "--path", "/nonexistent/rules.yaml"])
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    def test_validate_single_file_valid(self) -> None:
        """Test validate with valid rules file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
rules:
  - name: test-rule
    commands:
      - git
    action: deny
    message: Test message
""")
            rules_path = Path(f.name)

        try:
            result = runner.invoke(app, ["rules", "validate", "--path", str(rules_path)])
            assert result.exit_code == 0
            assert "valid" in result.stdout.lower()
        finally:
            rules_path.unlink()

    def test_validate_single_file_invalid_yaml(self) -> None:
        """Test validate with invalid YAML syntax."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: syntax: [")
            rules_path = Path(f.name)

        try:
            result = runner.invoke(app, ["rules", "validate", "--path", str(rules_path)])
            assert result.exit_code == 1
            assert "invalid" in result.stdout.lower() or "error" in result.stdout.lower()
        finally:
            rules_path.unlink()

    def test_validate_verbose_flag(self) -> None:
        """Test validate with verbose flag."""
        result = runner.invoke(app, ["rules", "validate", "--help"])
        assert result.exit_code == 0
        assert "--verbose" in result.stdout or "-v" in result.stdout

    def test_validate_all_rules_no_global(self) -> None:
        """Test validate all when no global rules exist."""
        with (
            patch("safeshell.rules.cli.GLOBAL_RULES_PATH") as mock_global,
            patch("safeshell.rules.cli._find_repo_rules", return_value=None),
        ):
            mock_global.exists.return_value = False

            result = runner.invoke(app, ["rules", "validate"])
            assert result.exit_code == 0
            # Should report no global rules found
            assert "not found" in result.stdout.lower() or "valid" in result.stdout.lower()


class TestShowRulesTable:
    """Tests for rules table display."""

    def test_validate_verbose_shows_table(self) -> None:
        """Test that verbose mode shows rules table."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
rules:
  - name: test-rule
    commands:
      - git
    action: deny
    message: Test message
""")
            rules_path = Path(f.name)

        try:
            result = runner.invoke(app, ["rules", "validate", "--path", str(rules_path), "--verbose"])
            assert result.exit_code == 0
            # Should show some rule info
            assert "test-rule" in result.stdout or "valid" in result.stdout.lower()
        finally:
            rules_path.unlink()


class TestHelpText:
    """Tests for CLI help text."""

    def test_app_help(self) -> None:
        """Test main rules command help."""
        result = runner.invoke(app, ["rules", "--help"])
        assert result.exit_code == 0
        assert "rules" in result.stdout.lower()

    def test_validate_path_option(self) -> None:
        """Test validate --path option exists."""
        result = runner.invoke(app, ["rules", "validate", "--help"])
        assert result.exit_code == 0
        assert "--path" in result.stdout or "-p" in result.stdout
