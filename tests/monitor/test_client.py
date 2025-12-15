"""
File: tests/monitor/test_client.py
Purpose: Tests for MonitorClient
"""

# ruff: noqa: SIM105 - contextlib.suppress doesn't work with await in test cleanup

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from safeshell.monitor.client import MonitorClient


class TestMonitorClient:
    """Tests for MonitorClient."""

    def test_init(self) -> None:
        """Test client initialization."""
        client = MonitorClient()
        assert not client.connected
        assert client._reader is None
        assert client._writer is None

    def test_add_event_callback(self) -> None:
        """Test adding event callbacks."""
        client = MonitorClient()
        callback = MagicMock()

        client.add_event_callback(callback)
        assert callback in client._event_callbacks

    def test_remove_event_callback(self) -> None:
        """Test removing event callbacks."""
        client = MonitorClient()
        callback = MagicMock()

        client.add_event_callback(callback)
        client.remove_event_callback(callback)
        assert callback not in client._event_callbacks

    def test_remove_nonexistent_callback(self) -> None:
        """Test removing a callback that wasn't added."""
        client = MonitorClient()
        callback = MagicMock()

        # Should not raise
        client.remove_event_callback(callback)

    @pytest.mark.asyncio
    async def test_connect_failure(self) -> None:
        """Test connection failure when daemon not running."""
        client = MonitorClient()

        with patch("safeshell.monitor.client.MONITOR_SOCKET_PATH") as mock_path:
            mock_path.__str__ = MagicMock(return_value="/nonexistent/socket")

            connected = await client.connect()
            assert not connected
            assert not client.connected

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self) -> None:
        """Test disconnect when not connected does nothing."""
        client = MonitorClient()

        # Should not raise
        await client.disconnect()
        assert not client.connected

    @pytest.mark.asyncio
    async def test_ping_when_not_connected(self) -> None:
        """Test ping returns False when not connected."""
        client = MonitorClient()

        result = await client.ping()
        assert not result

    @pytest.mark.asyncio
    async def test_approve_when_not_connected(self) -> None:
        """Test approve returns False when not connected."""
        client = MonitorClient()

        result = await client.approve("test-approval-id")
        assert not result

    @pytest.mark.asyncio
    async def test_deny_when_not_connected(self) -> None:
        """Test deny returns False when not connected."""
        client = MonitorClient()

        result = await client.deny("test-approval-id", "test reason")
        assert not result

    @pytest.mark.asyncio
    async def test_deny_with_remember_when_not_connected(self) -> None:
        """Test deny with remember flag returns False when not connected."""
        client = MonitorClient()

        result = await client.deny("test-approval-id", "test reason", remember=True)
        assert not result

    @pytest.mark.asyncio
    async def test_start_receiving_without_task(self) -> None:
        """Test that start_receiving creates a task."""
        client = MonitorClient()
        client._connected = True
        client._reader = AsyncMock()
        client._reader.readline = AsyncMock(side_effect=asyncio.CancelledError)

        await client.start_receiving()
        assert client._receive_task is not None

        # Clean up
        client._receive_task.cancel()
        try:
            await client._receive_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_event_callback_dispatch(self) -> None:
        """Test that events are dispatched to callbacks."""
        client = MonitorClient()
        client._connected = True

        callback = MagicMock()
        client.add_event_callback(callback)

        # Create mock reader that returns one message then closes
        mock_reader = AsyncMock()
        mock_reader.readline = AsyncMock(
            side_effect=[
                b'{"type": "event", "data": {"test": "value"}}\n',
                b"",  # Connection closed
            ]
        )
        client._reader = mock_reader

        # Run receive loop until it exits
        await client._receive_loop()

        # Callback should have been called
        callback.assert_called_once()
        call_args = callback.call_args[0][0]
        assert call_args["type"] == "event"

    @pytest.mark.asyncio
    async def test_callback_error_handling(self) -> None:
        """Test that callback errors don't stop the receive loop."""
        client = MonitorClient()
        client._connected = True

        # First callback raises, second should still be called
        callback1 = MagicMock(side_effect=Exception("test error"))
        callback2 = MagicMock()
        client.add_event_callback(callback1)
        client.add_event_callback(callback2)

        mock_reader = AsyncMock()
        mock_reader.readline = AsyncMock(
            side_effect=[
                b'{"type": "event"}\n',
                b"",  # Connection closed
            ]
        )
        client._reader = mock_reader

        await client._receive_loop()

        callback1.assert_called_once()
        callback2.assert_called_once()

    @pytest.mark.asyncio
    async def test_approve_writes_to_socket(self) -> None:
        """Test approve writes correctly to socket."""
        client = MonitorClient()
        client._connected = True

        mock_writer = MagicMock()
        mock_writer.write = MagicMock()
        mock_writer.drain = AsyncMock()
        client._writer = mock_writer

        result = await client.approve("test-approval-id")

        assert result is True
        mock_writer.write.assert_called_once()

    @pytest.mark.asyncio
    async def test_deny_writes_to_socket(self) -> None:
        """Test deny writes correctly to socket."""
        client = MonitorClient()
        client._connected = True

        mock_writer = MagicMock()
        mock_writer.write = MagicMock()
        mock_writer.drain = AsyncMock()
        client._writer = mock_writer

        result = await client.deny("test-approval-id", "test reason")

        assert result is True
        mock_writer.write.assert_called_once()

    @pytest.mark.asyncio
    async def test_approve_sends_command_with_remember(self) -> None:
        """Test approve sends correct command with remember flag."""
        client = MonitorClient()
        client._connected = True

        mock_writer = MagicMock()
        mock_writer.write = MagicMock()
        mock_writer.drain = AsyncMock()
        client._writer = mock_writer

        await client.approve("test-id", remember=True)

        written = mock_writer.write.call_args[0][0].decode()
        assert "approve" in written
        assert "test-id" in written
        assert "remember" in written

    @pytest.mark.asyncio
    async def test_deny_sends_command_with_reason(self) -> None:
        """Test deny sends correct command with reason."""
        client = MonitorClient()
        client._connected = True

        mock_writer = MagicMock()
        mock_writer.write = MagicMock()
        mock_writer.drain = AsyncMock()
        client._writer = mock_writer

        await client.deny("test-id", "security risk", remember=False)

        written = mock_writer.write.call_args[0][0].decode()
        assert "deny" in written
        assert "test-id" in written
        assert "security risk" in written

    @pytest.mark.asyncio
    async def test_ping_sends_command(self) -> None:
        """Test ping sends ping command and reads response."""
        client = MonitorClient()
        client._connected = True

        mock_writer = MagicMock()
        mock_writer.write = MagicMock()
        mock_writer.drain = AsyncMock()
        client._writer = mock_writer

        mock_reader = AsyncMock()
        mock_reader.readline = AsyncMock(return_value=b'{"success": true}\n')
        client._reader = mock_reader

        result = await client.ping()

        assert result is True
        mock_writer.write.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_closes_writer(self) -> None:
        """Test disconnect properly closes the writer."""
        client = MonitorClient()
        client._connected = True

        mock_writer = MagicMock()
        mock_writer.close = MagicMock()
        mock_writer.wait_closed = AsyncMock()
        client._writer = mock_writer

        await client.disconnect()

        mock_writer.close.assert_called_once()
        mock_writer.wait_closed.assert_called_once()
        assert client._writer is None
        assert not client.connected

    @pytest.mark.asyncio
    async def test_receive_loop_handles_json_error(self) -> None:
        """Test _receive_loop terminates on invalid JSON."""
        client = MonitorClient()
        client._connected = True

        callback = MagicMock()
        client.add_event_callback(callback)

        mock_reader = AsyncMock()
        mock_reader.readline = AsyncMock(
            side_effect=[
                b"not valid json\n",  # Invalid JSON - causes loop to terminate
            ]
        )
        client._reader = mock_reader

        await client._receive_loop()

        # Loop terminates on JSON error, callback not called
        callback.assert_not_called()
        # Connected should be False after error
        assert not client._connected

    def test_connected_property(self) -> None:
        """Test connected property reflects internal state."""
        client = MonitorClient()
        assert not client.connected

        client._connected = True
        assert client.connected

        client._connected = False
        assert not client.connected
