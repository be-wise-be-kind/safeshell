"""Tests for safeshell.daemon.protocol module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from safeshell.daemon.protocol import (
    decode_message,
    encode_message,
    read_message,
    write_message,
)
from safeshell.exceptions import ProtocolError
from safeshell.models import DaemonRequest, DaemonResponse, RequestType


class TestEncodeMessage:
    """Tests for encode_message function."""

    def test_encode_request(self) -> None:
        """Test encoding a DaemonRequest."""
        request = DaemonRequest(
            type=RequestType.EVALUATE,
            command="git status",
            working_dir="/home/user",
        )
        encoded = encode_message(request)

        assert isinstance(encoded, bytes)
        assert encoded.endswith(b"\n")
        assert b"evaluate" in encoded
        assert b"git status" in encoded

    def test_encode_response(self) -> None:
        """Test encoding a DaemonResponse."""
        response = DaemonResponse.allow()
        encoded = encode_message(response)

        assert isinstance(encoded, bytes)
        assert encoded.endswith(b"\n")
        assert b"allow" in encoded


class TestDecodeMessage:
    """Tests for decode_message function."""

    def test_decode_valid_json(self) -> None:
        """Test decoding valid JSON."""
        data = b'{"type": "ping"}'
        result = decode_message(data)
        assert result == {"type": "ping"}

    def test_decode_complex_json(self) -> None:
        """Test decoding complex JSON."""
        data = b'{"type": "evaluate", "command": "ls", "env": {"USER": "test"}}'
        result = decode_message(data)
        assert result["type"] == "evaluate"
        assert result["command"] == "ls"
        assert result["env"]["USER"] == "test"

    def test_decode_invalid_json(self) -> None:
        """Test decoding invalid JSON raises ProtocolError."""
        with pytest.raises(ProtocolError):
            decode_message(b"not valid json")

    def test_decode_invalid_utf8(self) -> None:
        """Test decoding invalid UTF-8 raises ProtocolError."""
        with pytest.raises(ProtocolError):
            decode_message(b"\xff\xfe")


class TestRoundTrip:
    """Tests for encode/decode round trips."""

    def test_request_roundtrip(self) -> None:
        """Test encoding then decoding a request."""
        original = DaemonRequest(
            type=RequestType.EVALUATE,
            command="git commit -m test",
            working_dir="/home/user/project",
            env={"PATH": "/usr/bin"},
        )
        encoded = encode_message(original)
        decoded = decode_message(encoded.strip())

        # Validate decoded matches original
        reconstructed = DaemonRequest.model_validate(decoded)
        assert reconstructed.type == original.type
        assert reconstructed.command == original.command
        assert reconstructed.working_dir == original.working_dir
        assert reconstructed.env == original.env

    def test_response_roundtrip(self) -> None:
        """Test encoding then decoding a response."""
        original = DaemonResponse.deny("Not allowed", "test-plugin")
        encoded = encode_message(original)
        decoded = decode_message(encoded.strip())

        reconstructed = DaemonResponse.model_validate(decoded)
        assert reconstructed.success == original.success
        assert reconstructed.final_decision == original.final_decision
        assert reconstructed.should_execute == original.should_execute
        assert reconstructed.denial_message == original.denial_message


class TestReadMessage:
    """Tests for read_message function."""

    @pytest.mark.asyncio
    async def test_read_valid_message(self) -> None:
        """Test reading a valid JSON message."""
        mock_reader = AsyncMock()
        mock_reader.readline = AsyncMock(return_value=b'{"type": "ping"}\n')

        result = await read_message(mock_reader)
        assert result == {"type": "ping"}

    @pytest.mark.asyncio
    async def test_read_empty_line_raises_error(self) -> None:
        """Test reading empty line raises ProtocolError."""
        mock_reader = AsyncMock()
        mock_reader.readline = AsyncMock(return_value=b"")

        with pytest.raises(ProtocolError, match="Connection closed"):
            await read_message(mock_reader)

    @pytest.mark.asyncio
    async def test_read_invalid_json_raises_error(self) -> None:
        """Test reading invalid JSON raises ProtocolError."""
        mock_reader = AsyncMock()
        mock_reader.readline = AsyncMock(return_value=b"not valid json\n")

        with pytest.raises(ProtocolError, match="Failed to decode"):
            await read_message(mock_reader)

    @pytest.mark.asyncio
    async def test_read_incomplete_raises_error(self) -> None:
        """Test incomplete read raises ProtocolError."""
        mock_reader = AsyncMock()
        mock_reader.readline = AsyncMock(
            side_effect=asyncio.IncompleteReadError(partial=b"partial", expected=100)
        )

        with pytest.raises(ProtocolError, match="Incomplete read"):
            await read_message(mock_reader)


class TestWriteMessage:
    """Tests for write_message function."""

    @pytest.mark.asyncio
    async def test_write_message(self) -> None:
        """Test writing a message to stream."""
        mock_writer = MagicMock()
        mock_writer.write = MagicMock()
        mock_writer.drain = AsyncMock()

        response = DaemonResponse.allow()
        await write_message(mock_writer, response)

        mock_writer.write.assert_called_once()
        written_data = mock_writer.write.call_args[0][0]
        assert written_data.endswith(b"\n")
        mock_writer.drain.assert_called_once()

    @pytest.mark.asyncio
    async def test_write_request(self) -> None:
        """Test writing a request to stream."""
        mock_writer = MagicMock()
        mock_writer.write = MagicMock()
        mock_writer.drain = AsyncMock()

        request = DaemonRequest(type=RequestType.PING)
        await write_message(mock_writer, request)

        mock_writer.write.assert_called_once()
        written_data = mock_writer.write.call_args[0][0]
        assert b"ping" in written_data
