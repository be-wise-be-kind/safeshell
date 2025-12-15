"""Tests for safeshell.wrapper.client module."""

import json
import socket
import tempfile
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from safeshell.exceptions import DaemonNotRunningError, DaemonStartError
from safeshell.models import Decision, DaemonResponse
from safeshell.wrapper.client import DaemonClient


class TestDaemonClientConstants:
    """Tests for DaemonClient class constants."""

    def test_max_start_wait(self) -> None:
        """Test MAX_START_WAIT constant."""
        assert DaemonClient.MAX_START_WAIT == 5.0

    def test_poll_interval(self) -> None:
        """Test POLL_INTERVAL constant."""
        assert DaemonClient.POLL_INTERVAL == 0.05

    def test_recv_buffer(self) -> None:
        """Test RECV_BUFFER constant."""
        assert DaemonClient.RECV_BUFFER == 65536

    def test_timeout_multiplier(self) -> None:
        """Test TIMEOUT_MULTIPLIER constant."""
        assert DaemonClient.TIMEOUT_MULTIPLIER == 2.0


class TestDaemonClientInit:
    """Tests for DaemonClient initialization."""

    def test_default_socket_path(self) -> None:
        """Test default socket path is set."""
        client = DaemonClient()
        assert client.socket_path is not None
        assert "daemon.sock" in str(client.socket_path)

    def test_custom_socket_path(self) -> None:
        """Test custom socket path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_path = Path(tmpdir) / "custom.sock"
            client = DaemonClient(socket_path=custom_path)
            assert client.socket_path == custom_path

    def test_config_loaded(self) -> None:
        """Test that config is loaded on initialization."""
        client = DaemonClient()
        assert client._config is not None
        # Should have approval_timeout_seconds from config
        assert hasattr(client._config, "approval_timeout_seconds")


class TestDaemonClientPing:
    """Tests for DaemonClient.ping method."""

    def test_ping_returns_false_when_no_daemon(self) -> None:
        """Test ping returns False when daemon not running."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Use a non-existent socket path
            socket_path = Path(tmpdir) / "nonexistent.sock"
            client = DaemonClient(socket_path=socket_path)
            assert client.ping() is False

    def test_ping_returns_true_when_daemon_responds(self) -> None:
        """Test ping returns True when daemon responds successfully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "daemon.sock"

            # Create mock daemon that responds to ping
            response = DaemonResponse(success=True).model_dump_json() + "\n"

            def handle_client(conn: socket.socket) -> None:
                conn.recv(1024)  # Receive request
                conn.sendall(response.encode())
                conn.close()

            server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server.bind(str(socket_path))
            server.listen(1)

            def accept_connection() -> None:
                conn, _ = server.accept()
                handle_client(conn)

            thread = threading.Thread(target=accept_connection)
            thread.start()

            try:
                client = DaemonClient(socket_path=socket_path)
                assert client.ping() is True
            finally:
                thread.join(timeout=1)
                server.close()


class TestDaemonClientEvaluate:
    """Tests for DaemonClient.evaluate method."""

    def test_evaluate_sends_request_and_receives_response(self) -> None:
        """Test evaluate sends request and receives response."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "daemon.sock"

            # Create mock daemon that responds to evaluate
            response = DaemonResponse(
                success=True,
                final_decision=Decision.ALLOW,
                should_execute=True,
            ).model_dump_json() + "\n"

            def handle_client(conn: socket.socket) -> None:
                conn.recv(4096)  # Receive request
                conn.sendall(response.encode())
                conn.close()

            server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server.bind(str(socket_path))
            server.listen(1)

            def accept_connection() -> None:
                conn, _ = server.accept()
                handle_client(conn)

            thread = threading.Thread(target=accept_connection)
            thread.start()

            try:
                client = DaemonClient(socket_path=socket_path)
                result = client.evaluate(
                    command="git status",
                    working_dir="/tmp",
                    env={"PATH": "/usr/bin"},
                    execution_context="human",
                )
                assert result.success is True
                assert result.should_execute is True
            finally:
                thread.join(timeout=1)
                server.close()

    def test_evaluate_with_ai_context(self) -> None:
        """Test evaluate with AI execution context."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "daemon.sock"

            received_request = []

            response = DaemonResponse(
                success=True,
                final_decision=Decision.ALLOW,
                should_execute=True,
            ).model_dump_json() + "\n"

            def handle_client(conn: socket.socket) -> None:
                data = conn.recv(4096)
                received_request.append(json.loads(data.decode().strip()))
                conn.sendall(response.encode())
                conn.close()

            server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server.bind(str(socket_path))
            server.listen(1)

            def accept_connection() -> None:
                conn, _ = server.accept()
                handle_client(conn)

            thread = threading.Thread(target=accept_connection)
            thread.start()

            try:
                client = DaemonClient(socket_path=socket_path)
                client.evaluate(
                    command="rm -rf /",
                    working_dir="/tmp",
                    execution_context="ai",
                )
                assert received_request[0]["execution_context"] == "ai"
            finally:
                thread.join(timeout=1)
                server.close()


class TestDaemonClientSendRequest:
    """Tests for DaemonClient._send_request method."""

    def test_raises_when_socket_not_exists(self) -> None:
        """Test raises DaemonNotRunningError when socket doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "nonexistent.sock"
            client = DaemonClient(socket_path=socket_path)

            from safeshell.models import DaemonRequest, RequestType

            request = DaemonRequest(type=RequestType.PING)
            with pytest.raises(DaemonNotRunningError):
                client._send_request(request)

    def test_raises_on_connection_refused(self) -> None:
        """Test raises DaemonNotRunningError on connection refused."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "daemon.sock"
            # Create socket file but no listener
            socket_path.touch()

            client = DaemonClient(socket_path=socket_path)

            from safeshell.models import DaemonRequest, RequestType

            request = DaemonRequest(type=RequestType.PING)
            with pytest.raises(DaemonNotRunningError):
                client._send_request(request)


class TestDaemonClientTryConnect:
    """Tests for DaemonClient._try_connect method."""

    def test_returns_false_when_socket_not_exists(self) -> None:
        """Test returns False when socket doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "nonexistent.sock"
            client = DaemonClient(socket_path=socket_path)
            assert client._try_connect() is False

    def test_returns_true_when_connection_succeeds(self) -> None:
        """Test returns True when connection succeeds."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "daemon.sock"

            server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server.bind(str(socket_path))
            server.listen(1)

            try:
                client = DaemonClient(socket_path=socket_path)
                assert client._try_connect() is True
            finally:
                server.close()

    def test_returns_false_on_connection_error(self) -> None:
        """Test returns False on connection error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "daemon.sock"
            socket_path.touch()  # File exists but no server

            client = DaemonClient(socket_path=socket_path)
            assert client._try_connect() is False


class TestDaemonClientEnsureDaemonRunning:
    """Tests for DaemonClient.ensure_daemon_running method."""

    def test_returns_immediately_if_daemon_running(self) -> None:
        """Test returns immediately if daemon is already running."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "daemon.sock"

            server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server.bind(str(socket_path))
            server.listen(1)

            try:
                client = DaemonClient(socket_path=socket_path)
                # Should not raise
                client.ensure_daemon_running()
            finally:
                server.close()

    def test_raises_after_timeout(self) -> None:
        """Test raises DaemonStartError after timeout."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "daemon.sock"

            client = DaemonClient(socket_path=socket_path)
            # Set very short timeout for test
            client.MAX_START_WAIT = 0.1
            client.POLL_INTERVAL = 0.01

            with patch.object(client, "_start_daemon"):
                with pytest.raises(DaemonStartError):
                    client.ensure_daemon_running()


class TestDaemonClientRecvOne:
    """Tests for DaemonClient._recv_one method."""

    def test_receives_single_json_line(self) -> None:
        """Test receives a single JSON line from socket."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"

            message = b'{"test": "data"}\n'

            server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server.bind(str(socket_path))
            server.listen(1)

            def send_message() -> None:
                conn, _ = server.accept()
                conn.sendall(message)
                conn.close()

            thread = threading.Thread(target=send_message)
            thread.start()

            client_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client_sock.connect(str(socket_path))

            try:
                client = DaemonClient(socket_path=socket_path)
                result = client._recv_one(client_sock)
                assert result == b'{"test": "data"}'
            finally:
                client_sock.close()
                thread.join(timeout=1)
                server.close()

    def test_handles_chunked_data(self) -> None:
        """Test handles data arriving in chunks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"

            server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server.bind(str(socket_path))
            server.listen(1)

            def send_chunks() -> None:
                import time

                conn, _ = server.accept()
                conn.sendall(b'{"tes')
                time.sleep(0.01)
                conn.sendall(b't": "data"}\n')
                conn.close()

            thread = threading.Thread(target=send_chunks)
            thread.start()

            client_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client_sock.connect(str(socket_path))

            try:
                client = DaemonClient(socket_path=socket_path)
                result = client._recv_one(client_sock)
                assert result == b'{"test": "data"}'
            finally:
                client_sock.close()
                thread.join(timeout=1)
                server.close()


class TestDaemonClientStartDaemon:
    """Tests for DaemonClient._start_daemon method."""

    def test_start_daemon_uses_plumbum(self) -> None:
        """Test _start_daemon uses plumbum to start daemon."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "daemon.sock"
            client = DaemonClient(socket_path=socket_path)

            mock_cmd = MagicMock()
            mock_local = MagicMock()
            mock_local.__getitem__ = MagicMock(return_value=mock_cmd)

            with patch("plumbum.local", mock_local):
                with patch("plumbum.BG"):
                    # Should call local[sys.executable] to get the python command
                    client._start_daemon()
                    mock_local.__getitem__.assert_called()
