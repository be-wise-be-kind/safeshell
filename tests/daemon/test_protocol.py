"""Tests for safeshell.daemon.protocol module."""

import pytest

from safeshell.daemon.protocol import (
    decode_message,
    encode_message,
    sync_decode_message,
    sync_encode_message,
)
from safeshell.exceptions import ProtocolError
from safeshell.models import DaemonRequest, DaemonResponse, Decision, RequestType


class TestEncodeMessage:
    """Tests for encode_message function."""

    def test_encode_request(self) -> None:
        """Test encoding a DaemonRequest."""
        request = DaemonRequest(
            type=RequestType.EVALUATE,
            command="git status",
            working_dir="/tmp",
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

    def test_sync_encode_same_as_encode(self) -> None:
        """Test sync_encode_message produces same output."""
        request = DaemonRequest(type=RequestType.PING)
        assert encode_message(request) == sync_encode_message(request)


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

    def test_sync_decode_same_as_decode(self) -> None:
        """Test sync_decode_message produces same output."""
        data = b'{"key": "value"}'
        assert decode_message(data) == sync_decode_message(data)


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
