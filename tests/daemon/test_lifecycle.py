"""Tests for safeshell.daemon.lifecycle module."""

import os
import signal
import socket
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from safeshell.daemon.lifecycle import DaemonLifecycle


class TestEnsureDirectories:
    """Tests for ensure_directories method."""

    def test_creates_directory_if_not_exists(self) -> None:
        """Test that ensure_directories creates the directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "safeshell"
            assert not test_dir.exists()

            with patch.object(DaemonLifecycle, "socket_path", test_dir / "daemon.sock"):
                with patch("safeshell.daemon.lifecycle.SAFESHELL_DIR", test_dir):
                    DaemonLifecycle.ensure_directories()

            assert test_dir.exists()

    def test_does_not_error_if_exists(self) -> None:
        """Test that ensure_directories works if directory already exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir)
            assert test_dir.exists()

            with patch("safeshell.daemon.lifecycle.SAFESHELL_DIR", test_dir):
                # Should not raise
                DaemonLifecycle.ensure_directories()


class TestIsRunning:
    """Tests for is_running method."""

    def test_returns_false_if_socket_not_exists(self) -> None:
        """Test returns False when socket file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_socket = Path(tmpdir) / "nonexistent.sock"

            with patch.object(DaemonLifecycle, "socket_path", test_socket):
                assert DaemonLifecycle.is_running() is False

    def test_returns_true_if_socket_connects(self) -> None:
        """Test returns True when socket connects successfully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_socket = Path(tmpdir) / "daemon.sock"

            # Create a listening socket
            server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server_sock.bind(str(test_socket))
            server_sock.listen(1)

            try:
                with patch.object(DaemonLifecycle, "socket_path", test_socket):
                    assert DaemonLifecycle.is_running() is True
            finally:
                server_sock.close()

    def test_returns_false_and_cleans_up_stale_socket(self) -> None:
        """Test returns False and cleans up stale socket when connection refused."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_socket = Path(tmpdir) / "stale.sock"
            # Create a socket file without a listening server
            test_socket.touch()

            with patch.object(DaemonLifecycle, "socket_path", test_socket):
                result = DaemonLifecycle.is_running()
                assert result is False
                # Stale socket should be cleaned up
                assert not test_socket.exists()


class TestCleanupStaleSocket:
    """Tests for _cleanup_stale_socket method."""

    def test_removes_existing_socket(self) -> None:
        """Test that stale socket file is removed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_socket = Path(tmpdir) / "stale.sock"
            test_socket.touch()

            with patch.object(DaemonLifecycle, "socket_path", test_socket):
                DaemonLifecycle._cleanup_stale_socket()

            assert not test_socket.exists()

    def test_handles_nonexistent_socket(self) -> None:
        """Test handles case where socket doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_socket = Path(tmpdir) / "nonexistent.sock"

            with patch.object(DaemonLifecycle, "socket_path", test_socket):
                # Should not raise
                DaemonLifecycle._cleanup_stale_socket()


class TestWritePid:
    """Tests for write_pid method."""

    def test_writes_current_pid(self) -> None:
        """Test that current PID is written to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_pid = Path(tmpdir) / "daemon.pid"

            with (
                patch.object(DaemonLifecycle, "pid_path", test_pid),
                patch("safeshell.daemon.lifecycle.SAFESHELL_DIR", Path(tmpdir)),
            ):
                DaemonLifecycle.write_pid()

            assert test_pid.exists()
            assert test_pid.read_text().strip() == str(os.getpid())


class TestReadPid:
    """Tests for read_pid method."""

    def test_returns_pid_from_file(self) -> None:
        """Test returns PID when file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_pid = Path(tmpdir) / "daemon.pid"
            test_pid.write_text("12345")

            with patch.object(DaemonLifecycle, "pid_path", test_pid):
                assert DaemonLifecycle.read_pid() == 12345

    def test_returns_none_if_file_not_exists(self) -> None:
        """Test returns None when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_pid = Path(tmpdir) / "nonexistent.pid"

            with patch.object(DaemonLifecycle, "pid_path", test_pid):
                assert DaemonLifecycle.read_pid() is None

    def test_returns_none_if_invalid_content(self) -> None:
        """Test returns None when file contains invalid content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_pid = Path(tmpdir) / "daemon.pid"
            test_pid.write_text("not a number")

            with patch.object(DaemonLifecycle, "pid_path", test_pid):
                assert DaemonLifecycle.read_pid() is None


class TestStopDaemon:
    """Tests for stop_daemon method."""

    def test_returns_false_if_no_pid_file(self) -> None:
        """Test returns False when PID file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_pid = Path(tmpdir) / "nonexistent.pid"

            with patch.object(DaemonLifecycle, "pid_path", test_pid):
                assert DaemonLifecycle.stop_daemon() is False

    def test_sends_sigterm_to_running_process(self) -> None:
        """Test sends SIGTERM to running daemon."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_pid = Path(tmpdir) / "daemon.pid"
            test_socket = Path(tmpdir) / "daemon.sock"
            test_pid.write_text("12345")

            with (
                patch.object(DaemonLifecycle, "pid_path", test_pid),
                patch.object(DaemonLifecycle, "socket_path", test_socket),
                patch("os.kill") as mock_kill,
            ):
                result = DaemonLifecycle.stop_daemon()

                assert result is True
                mock_kill.assert_called_once_with(12345, signal.SIGTERM)

    def test_returns_false_if_process_not_found(self) -> None:
        """Test returns False when process doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_pid = Path(tmpdir) / "daemon.pid"
            test_socket = Path(tmpdir) / "daemon.sock"
            test_pid.write_text("99999")
            test_socket.touch()

            with (
                patch.object(DaemonLifecycle, "pid_path", test_pid),
                patch.object(DaemonLifecycle, "socket_path", test_socket),
                patch("os.kill", side_effect=ProcessLookupError),
            ):
                result = DaemonLifecycle.stop_daemon()

                assert result is False
                # Should clean up files
                assert not test_pid.exists()
                assert not test_socket.exists()

    def test_cleans_up_pid_and_socket_after_stop(self) -> None:
        """Test cleans up PID file and socket after successful stop."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_pid = Path(tmpdir) / "daemon.pid"
            test_socket = Path(tmpdir) / "daemon.sock"
            test_pid.write_text("12345")
            test_socket.touch()

            with (
                patch.object(DaemonLifecycle, "pid_path", test_pid),
                patch.object(DaemonLifecycle, "socket_path", test_socket),
                patch("os.kill"),
            ):
                DaemonLifecycle.stop_daemon()

                assert not test_pid.exists()
                assert not test_socket.exists()


class TestCleanupOnStart:
    """Tests for cleanup_on_start method."""

    def test_cleans_up_stale_sockets(self) -> None:
        """Test cleans up stale socket files on start."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_socket = Path(tmpdir) / "daemon.sock"
            test_monitor = Path(tmpdir) / "monitor.sock"
            test_socket.touch()
            test_monitor.touch()

            with (
                patch.object(DaemonLifecycle, "socket_path", test_socket),
                patch("safeshell.daemon.lifecycle.SAFESHELL_DIR", Path(tmpdir)),
                patch("safeshell.daemon.lifecycle.MONITOR_SOCKET_PATH", test_monitor),
            ):
                DaemonLifecycle.cleanup_on_start()

            assert not test_socket.exists()
            assert not test_monitor.exists()

    def test_handles_no_stale_files(self) -> None:
        """Test handles case where no stale files exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_socket = Path(tmpdir) / "daemon.sock"
            test_monitor = Path(tmpdir) / "monitor.sock"

            with (
                patch.object(DaemonLifecycle, "socket_path", test_socket),
                patch("safeshell.daemon.lifecycle.SAFESHELL_DIR", Path(tmpdir)),
                patch("safeshell.daemon.lifecycle.MONITOR_SOCKET_PATH", test_monitor),
            ):
                # Should not raise
                DaemonLifecycle.cleanup_on_start()


class TestCleanupStaleMonitorSocket:
    """Tests for _cleanup_stale_monitor_socket method."""

    def test_removes_existing_monitor_socket(self) -> None:
        """Test that stale monitor socket file is removed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_monitor = Path(tmpdir) / "monitor.sock"
            test_monitor.touch()

            with patch("safeshell.daemon.lifecycle.MONITOR_SOCKET_PATH", test_monitor):
                DaemonLifecycle._cleanup_stale_monitor_socket()

            assert not test_monitor.exists()

    def test_handles_nonexistent_monitor_socket(self) -> None:
        """Test handles case where monitor socket doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_monitor = Path(tmpdir) / "nonexistent.sock"

            with patch("safeshell.daemon.lifecycle.MONITOR_SOCKET_PATH", test_monitor):
                # Should not raise
                DaemonLifecycle._cleanup_stale_monitor_socket()
