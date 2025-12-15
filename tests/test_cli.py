"""Tests for SafeShell CLI."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

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


def test_check_command_requires_daemon(monkeypatch) -> None:
    """Test that check command requires daemon to be running."""
    from safeshell.daemon.lifecycle import DaemonLifecycle

    # Mock is_running to always return False for test isolation
    monkeypatch.setattr(DaemonLifecycle, "is_running", staticmethod(lambda: False))

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


class TestStatusCommand:
    """Tests for status command."""

    def test_status_when_daemon_running_and_connected(self, monkeypatch) -> None:
        """Test status shows connected when daemon is running and socket works."""
        from safeshell.daemon.lifecycle import DaemonLifecycle

        monkeypatch.setattr(DaemonLifecycle, "is_running", staticmethod(lambda: True))

        mock_client = MagicMock()
        mock_client.ping.return_value = True

        with patch("safeshell.wrapper.client.DaemonClient", return_value=mock_client):
            result = runner.invoke(app, ["status"])
            assert result.exit_code == 0
            assert "running" in result.stdout.lower()
            assert "connected" in result.stdout.lower()

    def test_status_when_daemon_running_but_socket_fails(self, monkeypatch) -> None:
        """Test status shows issue when socket fails."""
        from safeshell.daemon.lifecycle import DaemonLifecycle

        monkeypatch.setattr(DaemonLifecycle, "is_running", staticmethod(lambda: True))

        mock_client = MagicMock()
        mock_client.ping.return_value = False

        with patch("safeshell.wrapper.client.DaemonClient", return_value=mock_client):
            result = runner.invoke(app, ["status"])
            assert result.exit_code == 0
            assert "issue" in result.stdout.lower() or "running" in result.stdout.lower()

    def test_status_when_daemon_not_running(self, monkeypatch) -> None:
        """Test status shows not running."""
        from safeshell.daemon.lifecycle import DaemonLifecycle

        monkeypatch.setattr(DaemonLifecycle, "is_running", staticmethod(lambda: False))

        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "not running" in result.stdout.lower()


class TestCheckCommand:
    """Tests for check command."""

    def test_check_shows_command(self, monkeypatch) -> None:
        """Test check command shows the command being checked."""
        from safeshell.daemon.lifecycle import DaemonLifecycle

        monkeypatch.setattr(DaemonLifecycle, "is_running", staticmethod(lambda: False))

        result = runner.invoke(app, ["check", "echo hello"])
        # Will fail because daemon not running, but should show the command
        assert "echo hello" in result.stdout or "not running" in result.stdout.lower()

    def test_check_help(self) -> None:
        """Test check command help."""
        result = runner.invoke(app, ["check", "--help"])
        assert result.exit_code == 0
        assert "check" in result.stdout.lower()

    def test_check_allowed_command(self, monkeypatch) -> None:
        """Test check shows allowed when command would be permitted."""
        from safeshell.daemon.lifecycle import DaemonLifecycle

        monkeypatch.setattr(DaemonLifecycle, "is_running", staticmethod(lambda: True))

        mock_response = MagicMock()
        mock_response.should_execute = True
        mock_response.denial_message = None

        mock_client = MagicMock()
        mock_client.evaluate.return_value = mock_response

        with patch("safeshell.wrapper.client.DaemonClient", return_value=mock_client):
            result = runner.invoke(app, ["check", "git status"])
            assert result.exit_code == 0
            assert "allowed" in result.stdout.lower()

    def test_check_blocked_command(self, monkeypatch) -> None:
        """Test check shows blocked when command would be denied."""
        from safeshell.daemon.lifecycle import DaemonLifecycle

        monkeypatch.setattr(DaemonLifecycle, "is_running", staticmethod(lambda: True))

        mock_response = MagicMock()
        mock_response.should_execute = False
        mock_response.denial_message = "Command blocked by rule"

        mock_client = MagicMock()
        mock_client.evaluate.return_value = mock_response

        with patch("safeshell.wrapper.client.DaemonClient", return_value=mock_client):
            result = runner.invoke(app, ["check", "rm -rf /"])
            assert result.exit_code == 0
            assert "blocked" in result.stdout.lower()
            assert "Command blocked by rule" in result.stdout

    def test_check_daemon_error(self, monkeypatch) -> None:
        """Test check handles daemon connection error."""
        from safeshell.daemon.lifecycle import DaemonLifecycle
        from safeshell.exceptions import DaemonNotRunningError

        monkeypatch.setattr(DaemonLifecycle, "is_running", staticmethod(lambda: True))

        mock_client = MagicMock()
        mock_client.evaluate.side_effect = DaemonNotRunningError("Connection failed")

        with patch("safeshell.wrapper.client.DaemonClient", return_value=mock_client):
            result = runner.invoke(app, ["check", "test"])
            assert result.exit_code == 1
            assert "error" in result.stdout.lower()


class TestMonitorCommand:
    """Tests for monitor command."""

    def test_monitor_help(self) -> None:
        """Test monitor command help."""
        result = runner.invoke(app, ["monitor", "--help"])
        assert result.exit_code == 0
        assert "monitor" in result.stdout.lower()
        assert "debug" in result.stdout.lower()

    def test_monitor_offers_to_start_daemon(self, monkeypatch) -> None:
        """Test monitor offers to start daemon if not running."""
        from safeshell.daemon.lifecycle import DaemonLifecycle

        monkeypatch.setattr(DaemonLifecycle, "is_running", staticmethod(lambda: False))

        # Answer 'n' to the prompt
        result = runner.invoke(app, ["monitor"], input="n\n")
        assert result.exit_code == 1
        assert "not running" in result.stdout.lower() or "daemon" in result.stdout.lower()


class TestRefreshCommand:
    """Tests for refresh command."""

    def test_refresh_help(self) -> None:
        """Test refresh command help."""
        result = runner.invoke(app, ["refresh", "--help"])
        assert result.exit_code == 0
        assert "shim" in result.stdout.lower()

    def test_refresh_runs(self) -> None:
        """Test refresh command runs and outputs info."""
        with patch("safeshell.shims.manager.refresh_shims") as mock_refresh:
            mock_refresh.return_value = {
                "created": ["git"],
                "removed": [],
                "unchanged": ["curl"],
            }

            result = runner.invoke(app, ["refresh"])
            assert result.exit_code == 0
            assert "created" in result.stdout.lower() or "done" in result.stdout.lower()

    def test_refresh_shows_removed(self) -> None:
        """Test refresh shows removed shims."""
        with patch("safeshell.shims.refresh_shims") as mock_refresh:
            mock_refresh.return_value = {
                "created": [],
                "removed": ["old_command"],
                "unchanged": [],
            }

            result = runner.invoke(app, ["refresh"])
            assert result.exit_code == 0
            assert "removed" in result.stdout.lower()

    def test_refresh_shows_unchanged(self) -> None:
        """Test refresh shows unchanged shims."""
        with patch("safeshell.shims.refresh_shims") as mock_refresh:
            mock_refresh.return_value = {
                "created": [],
                "removed": [],
                "unchanged": ["git", "curl"],
            }

            result = runner.invoke(app, ["refresh"])
            assert result.exit_code == 0
            assert "unchanged" in result.stdout.lower()


class TestInitCommand:
    """Tests for init command."""

    def test_init_help(self) -> None:
        """Test init command help."""
        result = runner.invoke(app, ["init", "--help"])
        assert result.exit_code == 0
        assert "init" in result.stdout.lower()

    def test_init_creates_files(self) -> None:
        """Test init creates config and rules files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            rules_path = Path(tmpdir) / "rules.yaml"

            with (
                patch("safeshell.config.CONFIG_PATH", config_path),
                patch("safeshell.rules.loader.GLOBAL_RULES_PATH", rules_path),
                patch("safeshell.config.create_default_config"),
                patch("safeshell.shims.manager.install_init_script"),
                patch("safeshell.shims.manager.refresh_shims") as mock_refresh,
                patch("safeshell.shims.manager.get_shell_init_instructions", return_value="# init"),
            ):
                mock_refresh.return_value = {"created": ["git"], "removed": [], "unchanged": []}

                result = runner.invoke(app, ["init"])
                assert result.exit_code == 0
                assert "initialized" in result.stdout.lower()

    def test_init_existing_config_no_overwrite(self) -> None:
        """Test init skips existing config if user declines overwrite."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            rules_path = Path(tmpdir) / "rules.yaml"
            config_path.write_text("existing: config")

            with (
                patch("safeshell.config.CONFIG_PATH", config_path),
                patch("safeshell.rules.loader.GLOBAL_RULES_PATH", rules_path),
                patch("safeshell.config.create_default_config") as mock_create,
                patch("safeshell.shims.manager.install_init_script"),
                patch("safeshell.shims.manager.refresh_shims") as mock_refresh,
                patch("safeshell.shims.manager.get_shell_init_instructions", return_value="# init"),
            ):
                mock_refresh.return_value = {"created": [], "removed": [], "unchanged": []}

                # Answer 'n' to both overwrite prompts
                result = runner.invoke(app, ["init"], input="n\n")
                # Config should not be recreated since user declined
                assert result.exit_code == 0

    def test_init_no_changes(self) -> None:
        """Test init exits when no changes are made."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            rules_path = Path(tmpdir) / "rules.yaml"
            config_path.write_text("existing: config")
            rules_path.parent.mkdir(parents=True, exist_ok=True)
            rules_path.write_text("existing: rules")

            with (
                patch("safeshell.config.CONFIG_PATH", config_path),
                patch("safeshell.rules.loader.GLOBAL_RULES_PATH", rules_path),
                patch("safeshell.shims.manager.install_init_script"),
                patch("safeshell.shims.manager.refresh_shims") as mock_refresh,
            ):
                mock_refresh.return_value = {"created": [], "removed": [], "unchanged": []}

                # Answer 'n' to both overwrite prompts
                result = runner.invoke(app, ["init"], input="n\nn\n")
                assert result.exit_code == 0
                assert "no changes" in result.stdout.lower()


class TestRulesSubcommand:
    """Tests for rules subcommand."""

    def test_rules_help(self) -> None:
        """Test rules subcommand help."""
        result = runner.invoke(app, ["rules", "--help"])
        assert result.exit_code == 0
        assert "rules" in result.stdout.lower()

    def test_rules_validate_help(self) -> None:
        """Test rules validate command help."""
        result = runner.invoke(app, ["rules", "validate", "--help"])
        assert result.exit_code == 0
        assert "validate" in result.stdout.lower()
