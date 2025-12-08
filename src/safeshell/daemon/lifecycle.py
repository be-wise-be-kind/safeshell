"""
File: src/safeshell/daemon/lifecycle.py
Purpose: Daemon process lifecycle management
Exports: DaemonLifecycle, SOCKET_PATH, MONITOR_SOCKET_PATH, PID_PATH, SAFESHELL_DIR
Depends: pathlib, os, signal, socket
Overview: Manages daemon start/stop, PID files, and socket cleanup
"""

import contextlib
import os
import signal
import socket
from pathlib import Path

from loguru import logger

# SafeShell directory and file paths
SAFESHELL_DIR = Path.home() / ".safeshell"
SOCKET_PATH = SAFESHELL_DIR / "daemon.sock"
MONITOR_SOCKET_PATH = SAFESHELL_DIR / "monitor.sock"
PID_PATH = SAFESHELL_DIR / "daemon.pid"


class DaemonLifecycle:
    """Manage daemon lifecycle using socket as primary liveness check.

    The daemon socket serves as the authoritative indicator of whether
    the daemon is running. PID file is used for stopping the daemon.
    """

    socket_path: Path = SOCKET_PATH
    pid_path: Path = PID_PATH

    @classmethod
    def ensure_directories(cls) -> None:
        """Ensure SafeShell directories exist."""
        SAFESHELL_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def is_running(cls) -> bool:
        """Check if daemon is running by testing socket connectivity.

        Returns:
            True if daemon is running and accepting connections
        """
        if not cls.socket_path.exists():
            return False

        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(1.0)
            sock.connect(str(cls.socket_path))
            sock.close()
            return True
        except (ConnectionRefusedError, FileNotFoundError, TimeoutError, OSError):
            # Socket exists but daemon is dead - clean up
            cls._cleanup_stale_socket()
            return False

    @classmethod
    def _cleanup_stale_socket(cls) -> None:
        """Remove stale socket file."""
        with contextlib.suppress(FileNotFoundError):
            cls.socket_path.unlink()
            logger.debug(f"Cleaned up stale socket at {cls.socket_path}")

    @classmethod
    def write_pid(cls) -> None:
        """Write current PID to file for stop command."""
        cls.ensure_directories()
        cls.pid_path.write_text(str(os.getpid()))
        logger.debug(f"Wrote PID {os.getpid()} to {cls.pid_path}")

    @classmethod
    def read_pid(cls) -> int | None:
        """Read PID from file.

        Returns:
            PID if file exists and is valid, None otherwise
        """
        if not cls.pid_path.exists():
            return None
        try:
            return int(cls.pid_path.read_text().strip())
        except (ValueError, OSError):
            return None

    @classmethod
    def stop_daemon(cls) -> bool:
        """Stop running daemon via SIGTERM.

        Returns:
            True if daemon was stopped, False if not running
        """
        pid = cls.read_pid()
        if pid is None:
            return False

        try:
            os.kill(pid, signal.SIGTERM)
            logger.info(f"Sent SIGTERM to daemon (PID {pid})")

            # Clean up files
            cls._cleanup_stale_socket()
            with contextlib.suppress(FileNotFoundError):
                cls.pid_path.unlink()

            return True
        except ProcessLookupError:
            logger.warning(f"Daemon PID {pid} not found, cleaning up")
            cls._cleanup_stale_socket()
            with contextlib.suppress(FileNotFoundError):
                cls.pid_path.unlink()
            return False

    @classmethod
    def cleanup_on_start(cls) -> None:
        """Clean up any stale files before starting daemon."""
        cls.ensure_directories()
        if cls.socket_path.exists():
            cls._cleanup_stale_socket()
        if MONITOR_SOCKET_PATH.exists():
            cls._cleanup_stale_monitor_socket()

    @classmethod
    def _cleanup_stale_monitor_socket(cls) -> None:
        """Remove stale monitor socket file."""
        with contextlib.suppress(FileNotFoundError):
            MONITOR_SOCKET_PATH.unlink()
            logger.debug(f"Cleaned up stale monitor socket at {MONITOR_SOCKET_PATH}")
