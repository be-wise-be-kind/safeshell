"""
File: src/safeshell/wrapper/client.py
Purpose: Synchronous Unix socket client for daemon communication
Exports: DaemonClient, evaluate_fast
Depends: socket, json (minimal dependencies for fast startup)
Overview: Client used by shell wrapper to communicate with the daemon
"""

from __future__ import annotations

import json
import socket
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

# Fast path imports - absolute minimum for command evaluation
# Heavy imports (pydantic, loguru, config) are deferred to methods that need them

# Socket path constant - avoid importing daemon.lifecycle
_DEFAULT_SOCKET_PATH = Path.home() / ".safeshell" / "daemon.sock"

if TYPE_CHECKING:
    from safeshell.models import DaemonResponse, ExecutionContext


def evaluate_fast(
    command: str,
    working_dir: str,
    socket_path: Path | None = None,
) -> tuple[bool, str | None]:
    """Fast-path command evaluation with minimal imports.

    This function evaluates a command against the daemon using direct
    JSON/socket operations, avoiding heavy pydantic imports. Use this
    for maximum performance when you just need allow/deny.

    Args:
        command: Command string to evaluate
        working_dir: Current working directory
        socket_path: Path to daemon socket (defaults to standard location)

    Returns:
        Tuple of (should_execute, denial_message)
        - should_execute: True if command is allowed
        - denial_message: Message to show if denied, or None

    Raises:
        ConnectionError: If cannot connect to daemon
    """
    sock_path = socket_path or _DEFAULT_SOCKET_PATH
    if not sock_path.exists():
        raise ConnectionError(f"Daemon socket not found at {sock_path}")

    # Build request JSON directly (no pydantic import)
    request = {
        "type": "evaluate",
        "command": command,
        "working_dir": working_dir,
        "env": {},
        "execution_context": "human",
    }

    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(120.0)  # 2 minute default timeout
            sock.connect(str(sock_path))

            # Send request
            message = json.dumps(request).encode("utf-8") + b"\n"
            sock.sendall(message)

            # Receive response - handle intermediate messages
            while True:
                data = _recv_line(sock)
                response = json.loads(data.decode("utf-8"))

                # Check for intermediate "waiting" messages
                if response.get("is_intermediate"):
                    msg = response.get("status_message")
                    if msg:
                        sys.stderr.write(msg + "\n")
                        sys.stderr.flush()
                    continue

                # Final response
                should_execute = response.get("should_execute", True)
                denial_message = response.get("denial_message")
                return (should_execute, denial_message)

    except (ConnectionRefusedError, FileNotFoundError, TimeoutError) as e:
        raise ConnectionError(f"Cannot connect to daemon: {e}") from e


def _recv_line(sock: socket.socket) -> bytes:
    """Receive one JSON line from socket."""
    data = b""
    while True:
        chunk = sock.recv(65536)
        if not chunk:
            break
        data += chunk
        if b"\n" in data:
            line, _, _ = data.partition(b"\n")
            return line.strip()
    return data.strip()


class DaemonClient:
    """Synchronous client for communicating with the SafeShell daemon.

    Used by the shell wrapper to send commands for evaluation
    and receive decisions from the daemon.

    Note: This class uses lazy imports to minimize startup time.
    For maximum performance, use evaluate_fast() instead.
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
        self.socket_path = socket_path or _DEFAULT_SOCKET_PATH
        self._config = None  # Lazy loaded

    def _get_config(self):
        """Lazy load config."""
        if self._config is None:
            from safeshell.config import load_config

            self._config = load_config()
        return self._config

    def evaluate(
        self,
        command: str,
        working_dir: str,
        env: dict[str, str] | None = None,
        execution_context: ExecutionContext | None = None,
    ) -> DaemonResponse:
        """Send command for evaluation by daemon.

        Args:
            command: Command string to evaluate
            working_dir: Current working directory
            env: Environment variables
            execution_context: Who is executing the command

        Returns:
            Response from daemon with evaluation results

        Raises:
            DaemonNotRunningError: If daemon is not running and auto-start fails
        """
        # Lazy import pydantic models
        from safeshell.models import (
            DaemonRequest,
            RequestType,
        )
        from safeshell.models import (
            ExecutionContext as ExecCtx,
        )

        request = DaemonRequest(
            type=RequestType.EVALUATE,
            command=command,
            working_dir=working_dir,
            env=env or {},
            execution_context=execution_context or ExecCtx.HUMAN,
        )
        return self._send_request(request)

    def ping(self) -> bool:
        """Check if daemon is running and responsive.

        Returns:
            True if daemon responds to ping
        """
        from safeshell.exceptions import DaemonNotRunningError, DaemonStartError
        from safeshell.models import DaemonRequest, RequestType

        try:
            request = DaemonRequest(type=RequestType.PING)
            response = self._send_request(request)
            return response.success
        except (DaemonNotRunningError, DaemonStartError):
            return False

    def _send_request(self, request) -> DaemonResponse:
        """Send a request to the daemon and receive response.

        Args:
            request: Request to send

        Returns:
            Response from daemon

        Raises:
            DaemonNotRunningError: If cannot connect to daemon
        """
        from safeshell.exceptions import DaemonNotRunningError
        from safeshell.models import DaemonResponse

        if not self.socket_path.exists():
            raise DaemonNotRunningError(f"Daemon socket not found at {self.socket_path}")

        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                # Timeout based on approval timeout from config (with safety margin)
                config = self._get_config()
                socket_timeout = config.approval_timeout_seconds * self.TIMEOUT_MULTIPLIER
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
        from safeshell.exceptions import DaemonStartError

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
        from plumbum import BG, local
        from plumbum.commands.processes import ProcessExecutionError

        from safeshell.exceptions import DaemonStartError

        try:
            # Get the safeshell command
            safeshell = local[sys.executable]["-m", "safeshell.daemon.server"]

            # Run in background using plumbum's BG
            safeshell & BG

        except ProcessExecutionError as e:
            raise DaemonStartError(f"Failed to start daemon: {e}") from e
