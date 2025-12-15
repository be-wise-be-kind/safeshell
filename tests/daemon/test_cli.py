"""Tests for safeshell.daemon.cli module."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from safeshell.daemon.cli import app

runner = CliRunner()


class TestDaemonStart:
    """Tests for daemon start command."""

    def test_start_when_already_running(self) -> None:
        """Test that start exits cleanly if daemon already running."""
        with patch("safeshell.daemon.cli.DaemonLifecycle") as mock_lifecycle:
            mock_lifecycle.is_running.return_value = True

            result = runner.invoke(app, ["start"])
            assert result.exit_code == 0
            assert "already running" in result.stdout.lower()

    def test_start_foreground_flag_recognized(self) -> None:
        """Test that --foreground flag is recognized."""
        result = runner.invoke(app, ["start", "--help"])
        assert result.exit_code == 0
        assert "foreground" in result.stdout.lower()

    def test_start_background_calls_daemonize(self) -> None:
        """Test that start in background mode calls _daemonize."""
        with (
            patch("safeshell.daemon.cli.DaemonLifecycle") as mock_lifecycle,
            patch("safeshell.daemon.cli._daemonize") as mock_daemonize,
        ):
            mock_lifecycle.is_running.return_value = False

            result = runner.invoke(app, ["start"])
            assert result.exit_code == 0
            mock_daemonize.assert_called_once()
            assert "started" in result.stdout.lower()

    def test_start_foreground_runs_daemon(self) -> None:
        """Test that start --foreground runs daemon in foreground."""
        with (
            patch("safeshell.daemon.cli.DaemonLifecycle") as mock_lifecycle,
            patch("safeshell.daemon.cli.asyncio") as mock_asyncio,
        ):
            mock_lifecycle.is_running.return_value = False

            result = runner.invoke(app, ["start", "--foreground"])
            assert result.exit_code == 0
            mock_asyncio.run.assert_called_once()


class TestDaemonStop:
    """Tests for daemon stop command."""

    def test_stop_when_running(self) -> None:
        """Test stop when daemon is running."""
        with patch("safeshell.daemon.cli.DaemonLifecycle") as mock_lifecycle:
            mock_lifecycle.stop_daemon.return_value = True

            result = runner.invoke(app, ["stop"])
            assert result.exit_code == 0
            assert "stopped" in result.stdout.lower()

    def test_stop_when_not_running(self) -> None:
        """Test stop when daemon is not running."""
        with patch("safeshell.daemon.cli.DaemonLifecycle") as mock_lifecycle:
            mock_lifecycle.stop_daemon.return_value = False

            result = runner.invoke(app, ["stop"])
            assert result.exit_code == 0
            assert "not running" in result.stdout.lower()


class TestDaemonStatus:
    """Tests for daemon status command."""

    def test_status_when_running_and_connected(self) -> None:
        """Test status when daemon is running and socket is connected."""
        with (
            patch("safeshell.daemon.cli.DaemonLifecycle") as mock_lifecycle,
            patch("safeshell.wrapper.client.DaemonClient") as mock_client_class,
        ):
            mock_lifecycle.is_running.return_value = True
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_client_class.return_value = mock_client

            result = runner.invoke(app, ["status"])
            assert result.exit_code == 0
            assert "running" in result.stdout.lower()
            assert "connected" in result.stdout.lower()

    def test_status_when_running_but_socket_fails(self) -> None:
        """Test status when daemon is running but socket connection fails."""
        with (
            patch("safeshell.daemon.cli.DaemonLifecycle") as mock_lifecycle,
            patch("safeshell.wrapper.client.DaemonClient") as mock_client_class,
        ):
            mock_lifecycle.is_running.return_value = True
            mock_client = MagicMock()
            mock_client.ping.return_value = False
            mock_client_class.return_value = mock_client

            result = runner.invoke(app, ["status"])
            assert result.exit_code == 0
            assert "running" in result.stdout.lower()
            assert "failed" in result.stdout.lower()

    def test_status_when_not_running(self) -> None:
        """Test status when daemon is not running."""
        with patch("safeshell.daemon.cli.DaemonLifecycle") as mock_lifecycle:
            mock_lifecycle.is_running.return_value = False

            result = runner.invoke(app, ["status"])
            assert result.exit_code == 0
            assert "not running" in result.stdout.lower()


class TestDaemonRestart:
    """Tests for daemon restart command."""

    def test_restart_help(self) -> None:
        """Test restart command help."""
        result = runner.invoke(app, ["restart", "--help"])
        assert result.exit_code == 0
        assert "restart" in result.stdout.lower()

    def test_restart_when_running(self) -> None:
        """Test restart when daemon is running stops and starts."""
        with (
            patch("safeshell.daemon.cli.DaemonLifecycle") as mock_lifecycle,
            patch("safeshell.daemon.cli._daemonize") as mock_daemonize,
            patch("time.sleep") as mock_sleep,
        ):
            mock_lifecycle.is_running.return_value = True
            mock_lifecycle.stop_daemon.return_value = True

            result = runner.invoke(app, ["restart"])
            assert result.exit_code == 0
            mock_lifecycle.stop_daemon.assert_called_once()
            mock_sleep.assert_called_with(0.5)
            mock_daemonize.assert_called_once()

    def test_restart_when_not_running(self) -> None:
        """Test restart when daemon not running just starts."""
        with (
            patch("safeshell.daemon.cli.DaemonLifecycle") as mock_lifecycle,
            patch("safeshell.daemon.cli._daemonize") as mock_daemonize,
        ):
            mock_lifecycle.is_running.return_value = False

            result = runner.invoke(app, ["restart"])
            assert result.exit_code == 0
            mock_lifecycle.stop_daemon.assert_not_called()
            mock_daemonize.assert_called_once()


class TestDaemonLogs:
    """Tests for daemon logs command."""

    def test_logs_when_file_not_found(self) -> None:
        """Test logs command when log file doesn't exist."""
        with patch("safeshell.config.load_config") as mock_load_config:
            mock_config = MagicMock()
            mock_config.get_log_file_path.return_value = Path("/nonexistent/daemon.log")
            mock_load_config.return_value = mock_config

            result = runner.invoke(app, ["logs"])
            assert result.exit_code == 1
            assert "not found" in result.stdout.lower()

    def test_logs_displays_content(self) -> None:
        """Test logs command displays log file content."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            f.write("line 1\nline 2\nline 3\n")
            log_path = Path(f.name)

        try:
            with patch("safeshell.config.load_config") as mock_load_config:
                mock_config = MagicMock()
                mock_config.get_log_file_path.return_value = log_path
                mock_load_config.return_value = mock_config

                result = runner.invoke(app, ["logs", "--lines", "10"])
                assert result.exit_code == 0
                assert "line 1" in result.stdout
                assert "line 2" in result.stdout
        finally:
            log_path.unlink()

    def test_logs_lines_option(self) -> None:
        """Test logs --lines option."""
        result = runner.invoke(app, ["logs", "--help"])
        assert result.exit_code == 0
        assert "--lines" in result.stdout or "-n" in result.stdout

    def test_logs_follow_option(self) -> None:
        """Test logs --follow option."""
        result = runner.invoke(app, ["logs", "--help"])
        assert result.exit_code == 0
        assert "--follow" in result.stdout or "-f" in result.stdout

    def test_logs_follow_with_tail(self) -> None:
        """Test logs --follow uses tail command when available."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            f.write("test log\n")
            log_path = Path(f.name)

        try:
            with (
                patch("safeshell.config.load_config") as mock_load_config,
                patch("shutil.which", return_value="/usr/bin/tail"),
                patch("subprocess.run") as mock_run,
            ):
                mock_config = MagicMock()
                mock_config.get_log_file_path.return_value = log_path
                mock_load_config.return_value = mock_config

                result = runner.invoke(app, ["logs", "-f"])
                assert result.exit_code == 0
                mock_run.assert_called_once()
        finally:
            log_path.unlink()

    def test_logs_follow_fallback_when_no_tail(self) -> None:
        """Test logs --follow uses Python fallback when tail unavailable."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            f.write("test log\n")
            log_path = Path(f.name)

        try:
            with (
                patch("safeshell.config.load_config") as mock_load_config,
                patch("shutil.which", return_value=None),
                patch("safeshell.daemon.cli._follow_log") as mock_follow,
            ):
                mock_config = MagicMock()
                mock_config.get_log_file_path.return_value = log_path
                mock_load_config.return_value = mock_config

                result = runner.invoke(app, ["logs", "-f"])
                assert result.exit_code == 0
                mock_follow.assert_called_once()
        finally:
            log_path.unlink()

    def test_logs_read_error(self) -> None:
        """Test logs handles read error gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "daemon.log"
            log_path.touch()
            # Make file unreadable
            log_path.chmod(0o000)

            try:
                with patch("safeshell.config.load_config") as mock_load_config:
                    mock_config = MagicMock()
                    mock_config.get_log_file_path.return_value = log_path
                    mock_load_config.return_value = mock_config

                    result = runner.invoke(app, ["logs"])
                    assert result.exit_code == 1
                    assert "error" in result.stdout.lower()
            finally:
                # Restore permissions for cleanup
                log_path.chmod(0o644)


class TestHelpText:
    """Tests for CLI help text."""

    def test_app_help(self) -> None:
        """Test main daemon command help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "daemon" in result.stdout.lower()

    def test_start_help(self) -> None:
        """Test start command help."""
        result = runner.invoke(app, ["start", "--help"])
        assert result.exit_code == 0
        assert "start" in result.stdout.lower()

    def test_stop_help(self) -> None:
        """Test stop command help."""
        result = runner.invoke(app, ["stop", "--help"])
        assert result.exit_code == 0
        assert "stop" in result.stdout.lower()

    def test_status_help(self) -> None:
        """Test status command help."""
        result = runner.invoke(app, ["status", "--help"])
        assert result.exit_code == 0
        assert "status" in result.stdout.lower()

    def test_logs_help(self) -> None:
        """Test logs command help."""
        result = runner.invoke(app, ["logs", "--help"])
        assert result.exit_code == 0
        assert "log" in result.stdout.lower()
