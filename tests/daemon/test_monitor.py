"""Tests for safeshell.daemon.monitor module."""

import pytest

from safeshell.daemon.monitor import (
    MonitorCommand,
    MonitorCommandType,
    MonitorConnectionHandler,
    MonitorResponse,
)
from safeshell.events.bus import EventBus


class TestMonitorCommandType:
    """Tests for MonitorCommandType enum."""

    def test_command_types(self) -> None:
        """Test that all expected command types exist."""
        assert MonitorCommandType.SUBSCRIBE.value == "subscribe"
        assert MonitorCommandType.UNSUBSCRIBE.value == "unsubscribe"
        assert MonitorCommandType.APPROVE.value == "approve"
        assert MonitorCommandType.DENY.value == "deny"
        assert MonitorCommandType.PING.value == "ping"


class TestMonitorCommand:
    """Tests for MonitorCommand model."""

    def test_ping_command(self) -> None:
        """Test creating a ping command."""
        cmd = MonitorCommand(type=MonitorCommandType.PING)
        assert cmd.type == MonitorCommandType.PING
        assert cmd.approval_id is None
        assert cmd.reason is None

    def test_approve_command(self) -> None:
        """Test creating an approve command."""
        cmd = MonitorCommand(
            type=MonitorCommandType.APPROVE,
            approval_id="abc123",
        )
        assert cmd.type == MonitorCommandType.APPROVE
        assert cmd.approval_id == "abc123"

    def test_deny_command_with_reason(self) -> None:
        """Test creating a deny command with reason."""
        cmd = MonitorCommand(
            type=MonitorCommandType.DENY,
            approval_id="abc123",
            reason="Too risky",
        )
        assert cmd.type == MonitorCommandType.DENY
        assert cmd.approval_id == "abc123"
        assert cmd.reason == "Too risky"

    def test_serialization(self) -> None:
        """Test command serialization."""
        cmd = MonitorCommand(
            type=MonitorCommandType.DENY,
            approval_id="xyz789",
            reason="Not allowed",
        )
        data = cmd.model_dump()
        assert data["type"] == "deny"
        assert data["approval_id"] == "xyz789"
        assert data["reason"] == "Not allowed"

    def test_deserialization(self) -> None:
        """Test command deserialization."""
        data = {"type": "approve", "approval_id": "test123"}
        cmd = MonitorCommand.model_validate(data)
        assert cmd.type == MonitorCommandType.APPROVE
        assert cmd.approval_id == "test123"


class TestMonitorResponse:
    """Tests for MonitorResponse model."""

    def test_ok_response(self) -> None:
        """Test creating an OK response."""
        resp = MonitorResponse.ok("Success")
        assert resp.success is True
        assert resp.message == "Success"
        assert resp.error is None

    def test_ok_response_no_message(self) -> None:
        """Test creating an OK response without message."""
        resp = MonitorResponse.ok()
        assert resp.success is True
        assert resp.message is None
        assert resp.error is None

    def test_error_response(self) -> None:
        """Test creating an error response."""
        resp = MonitorResponse.err("Something went wrong")
        assert resp.success is False
        assert resp.message is None
        assert resp.error == "Something went wrong"

    def test_serialization(self) -> None:
        """Test response serialization."""
        resp = MonitorResponse(success=True, message="Connected")
        data = resp.model_dump()
        assert data["success"] is True
        assert data["message"] == "Connected"
        assert data["error"] is None


class TestMonitorConnectionHandler:
    """Tests for MonitorConnectionHandler class."""

    @pytest.fixture
    def bus(self) -> EventBus:
        """Create an EventBus instance."""
        return EventBus()

    @pytest.fixture
    def handler(self, bus: EventBus) -> MonitorConnectionHandler:
        """Create a MonitorConnectionHandler instance."""
        return MonitorConnectionHandler(bus)

    def test_initial_state(self, handler: MonitorConnectionHandler) -> None:
        """Test initial handler state."""
        assert handler.active_connections == 0

    @pytest.mark.asyncio
    async def test_process_ping_command(self, handler: MonitorConnectionHandler) -> None:
        """Test processing a ping command."""
        response = await handler._process_command({"type": "ping"})
        assert response.success is True
        assert response.message == "pong"

    @pytest.mark.asyncio
    async def test_process_approve_missing_id(self, handler: MonitorConnectionHandler) -> None:
        """Test approve command without approval_id."""
        response = await handler._process_command({"type": "approve"})
        assert response.success is False
        assert "approval_id" in response.error.lower()

    @pytest.mark.asyncio
    async def test_process_deny_missing_id(self, handler: MonitorConnectionHandler) -> None:
        """Test deny command without approval_id."""
        response = await handler._process_command({"type": "deny"})
        assert response.success is False
        assert "approval_id" in response.error.lower()

    @pytest.mark.asyncio
    async def test_process_invalid_command(self, handler: MonitorConnectionHandler) -> None:
        """Test processing an invalid command."""
        response = await handler._process_command({"type": "invalid"})
        assert response.success is False
        assert response.error is not None

    @pytest.mark.asyncio
    async def test_approve_without_callback(self, handler: MonitorConnectionHandler) -> None:
        """Test approve when no callback is set."""
        response = await handler._process_command(
            {
                "type": "approve",
                "approval_id": "test123",
            }
        )
        assert response.success is False
        assert "not configured" in response.error.lower()

    @pytest.mark.asyncio
    async def test_deny_without_callback(self, handler: MonitorConnectionHandler) -> None:
        """Test deny when no callback is set."""
        response = await handler._process_command(
            {
                "type": "deny",
                "approval_id": "test123",
            }
        )
        assert response.success is False
        assert "not configured" in response.error.lower()

    @pytest.mark.asyncio
    async def test_approve_with_callback(self, handler: MonitorConnectionHandler) -> None:
        """Test approve with callback set."""
        approved_ids: list[tuple[str, bool]] = []

        async def approve_callback(approval_id: str, remember: bool = False) -> None:
            approved_ids.append((approval_id, remember))

        async def deny_callback(
            approval_id: str, reason: str | None, remember: bool = False
        ) -> None:
            pass

        handler.set_approval_callbacks(approve_callback, deny_callback)

        response = await handler._process_command(
            {
                "type": "approve",
                "approval_id": "test123",
            }
        )
        assert response.success is True
        assert ("test123", False) in approved_ids

    @pytest.mark.asyncio
    async def test_deny_with_callback(self, handler: MonitorConnectionHandler) -> None:
        """Test deny with callback set."""
        denied: list[tuple[str, str | None, bool]] = []

        async def approve_callback(approval_id: str, remember: bool = False) -> None:
            pass

        async def deny_callback(
            approval_id: str, reason: str | None, remember: bool = False
        ) -> None:
            denied.append((approval_id, reason, remember))

        handler.set_approval_callbacks(approve_callback, deny_callback)

        response = await handler._process_command(
            {
                "type": "deny",
                "approval_id": "test123",
                "reason": "Too risky",
            }
        )
        assert response.success is True
        assert ("test123", "Too risky", False) in denied

    @pytest.mark.asyncio
    async def test_approve_with_remember_flag(self, handler: MonitorConnectionHandler) -> None:
        """Test approve with remember flag."""
        approved_ids: list[tuple[str, bool]] = []

        async def approve_callback(approval_id: str, remember: bool = False) -> None:
            approved_ids.append((approval_id, remember))

        async def deny_callback(
            approval_id: str, reason: str | None, remember: bool = False
        ) -> None:
            pass

        handler.set_approval_callbacks(approve_callback, deny_callback)

        response = await handler._process_command(
            {
                "type": "approve",
                "approval_id": "remember-test",
                "remember": True,
            }
        )
        assert response.success is True
        assert ("remember-test", True) in approved_ids

    @pytest.mark.asyncio
    async def test_deny_with_remember_flag(self, handler: MonitorConnectionHandler) -> None:
        """Test deny with remember flag."""
        denied: list[tuple[str, str | None, bool]] = []

        async def approve_callback(approval_id: str, remember: bool = False) -> None:
            pass

        async def deny_callback(
            approval_id: str, reason: str | None, remember: bool = False
        ) -> None:
            denied.append((approval_id, reason, remember))

        handler.set_approval_callbacks(approve_callback, deny_callback)

        response = await handler._process_command(
            {
                "type": "deny",
                "approval_id": "deny-remember",
                "reason": "Security risk",
                "remember": True,
            }
        )
        assert response.success is True
        assert ("deny-remember", "Security risk", True) in denied

