"""Tests for safeshell.wrapper.client module."""

import tempfile
from pathlib import Path

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
