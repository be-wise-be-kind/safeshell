"""
File: src/safeshell/wrapper/client.py
Purpose: Synchronous Unix socket client for daemon communication
Exports: DaemonClient
Depends: socket, json, safeshell.daemon.lifecycle, safeshell.models, safeshell.exceptions
Overview: Client used by shell wrapper to communicate with the daemon
"""

import json
import socket
import sys
import time
from pathlib import Path

from loguru import logger

from safeshell.config import load_config
from safeshell.daemon.lifecycle import SOCKET_PATH
from safeshell.exceptions import DaemonNotRunningError, DaemonStartError
from safeshell.models import DaemonRequest, DaemonResponse, RequestType


class DaemonClient:
    """Synchronous client for communicating with the SafeShell daemon.

    Used by the shell wrapper to send commands for evaluation
    and receive decisions from the daemon.
    """

    MAX_START_WAIT: float = 5.0  # seconds to wait for daemon startup
    POLL_INTERVAL: float = 0.05  # 50ms between connection attempts
    RECV_BUFFER: int = 65536  # Buffer size for receiving response
    TIMEOUT_MULTIPLIER: float = 2.0  # Socket timeout = approval_timeout * this

    def __init__(self, socket_path: Path | None = None) -> None:
        """Initialize client.

        Args:
            socket_path: Path to daemon socket (defaults to standard location)
        """
        self.socket_path = socket_path or SOCKET_PATH
        # Load config to get approval timeout for socket timeout calculation
        self._config = load_config()

    def evaluate(
        self,
        command: str,
        working_dir: str,
        env: dict[str, str] | None = None,
        execution_context: str = "human",
    ) -> DaemonResponse:
        """Send command for evaluation by daemon.

        Args:
            command: Command string to evaluate
            working_dir: Current working directory
            env: Environment variables
            execution_context: Who is executing - "ai" or "human"

        Returns:
            Response from daemon with evaluation results

        Raises:
            DaemonNotRunningError: If daemon is not running and auto-start fails
        """
        from safeshell.models import ExecutionContext

        exec_ctx = ExecutionContext.AI if execution_context == "ai" else ExecutionContext.HUMAN

        request = DaemonRequest(
            type=RequestType.EVALUATE,
            command=command,
            working_dir=working_dir,
            env=env or {},
            execution_context=exec_ctx,
        )
        return self._send_request(request)

    def ping(self) -> bool:
        """Check if daemon is running and responsive.

        Returns:
            True if daemon responds to ping
        """
        try:
            request = DaemonRequest(type=RequestType.PING)
            response = self._send_request(request)
            return response.success
        except (DaemonNotRunningError, DaemonStartError):
            return False

    def _send_request(self, request: DaemonRequest) -> DaemonResponse:
        """Send a request to the daemon and receive response.

        Args:
            request: Request to send

        Returns:
            Response from daemon

        Raises:
            DaemonNotRunningError: If cannot connect to daemon
        """
        if not self.socket_path.exists():
            raise DaemonNotRunningError(f"Daemon socket not found at {self.socket_path}")

        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                # Timeout based on approval timeout from config (with safety margin)
                socket_timeout = self._config.approval_timeout_seconds * self.TIMEOUT_MULTIPLIER
                sock.settimeout(socket_timeout)
                sock.connect(str(self.socket_path))

                # Send request as JSON line
                message = request.model_dump_json().encode("utf-8") + b"\n"
                sock.sendall(message)

                # Receive response(s) - may include intermediate "waiting" messages
                while True:
                    response_data = self._recv_one(sock)
                    response_dict = json.loads(response_data.decode("utf-8"))
                    response = DaemonResponse.model_validate(response_dict)

                    # Print status messages for intermediate responses
                    if response.is_intermediate and response.status_message:
                        sys.stderr.write(response.status_message + "\n")
                        sys.stderr.flush()
                        continue  # Wait for final response

                    return response

        except ConnectionRefusedError as e:
            raise DaemonNotRunningError("Daemon is not accepting connections") from e
        except TimeoutError as e:
            raise DaemonNotRunningError("Daemon connection timed out") from e
        except FileNotFoundError as e:
            raise DaemonNotRunningError(f"Daemon socket not found: {e}") from e

    def _recv_one(self, sock: socket.socket) -> bytes:
        """Receive one JSON line from socket.

        Args:
            sock: Connected socket

        Returns:
            Received data (one JSON line without trailing newline)
        """
        data = b""
        while True:
            chunk = sock.recv(self.RECV_BUFFER)
            if not chunk:
                break
            data += chunk
            if b"\n" in data:
                # Got complete message - return just the first line
                line, _, _ = data.partition(b"\n")
                return line.strip()
        return data.strip()

    def ensure_daemon_running(self) -> None:
        """Ensure daemon is running, starting it if necessary.

        Attempts to connect to daemon. If connection fails,
        starts daemon and waits for it to become ready.

        Raises:
            DaemonStartError: If daemon fails to start within timeout
        """
        if self._try_connect():
            return

        # Try to start daemon
        self._start_daemon()

        # Wait for daemon to become ready
        start_time = time.monotonic()
        while time.monotonic() - start_time < self.MAX_START_WAIT:
            if self._try_connect():
                return
            time.sleep(self.POLL_INTERVAL)

        raise DaemonStartError(f"Daemon failed to start within {self.MAX_START_WAIT} seconds")

    def _try_connect(self) -> bool:
        """Attempt to connect to daemon socket.

        Returns:
            True if connection successful
        """
        if not self.socket_path.exists():
            return False

        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(1.0)
            sock.connect(str(self.socket_path))
            sock.close()
            return True
        except (ConnectionRefusedError, FileNotFoundError, TimeoutError, OSError):
            return False

    def _start_daemon(self) -> None:
        """Start daemon process in background.

        Uses plumbum for cross-platform process spawning.
        """
        from plumbum import local
        from plumbum.commands.processes import ProcessExecutionError

        logger.debug("Starting daemon in background")

        try:
            # Get the safeshell command
            safeshell = local[sys.executable]["-m", "safeshell.daemon.server"]

            # Run in background using plumbum's BG
            from plumbum import BG

            safeshell & BG

        except ProcessExecutionError as e:
            raise DaemonStartError(f"Failed to start daemon: {e}") from e
