"""Tests for safeshell.daemon.events module."""

import pytest

from safeshell.daemon.events import DaemonEventPublisher
from safeshell.events.bus import EventBus
from safeshell.events.types import Event, EventType
from safeshell.models import Decision


class TestDaemonEventPublisher:
    """Tests for DaemonEventPublisher class."""

    @pytest.fixture
    def bus(self) -> EventBus:
        """Create an EventBus instance."""
        return EventBus()

    @pytest.fixture
    def publisher(self, bus: EventBus) -> DaemonEventPublisher:
        """Create a DaemonEventPublisher instance."""
        return DaemonEventPublisher(bus)

    @pytest.mark.asyncio
    async def test_bus_property(self, bus: EventBus, publisher: DaemonEventPublisher) -> None:
        """Test that bus property returns the underlying EventBus."""
        assert publisher.bus is bus

    @pytest.mark.asyncio
    async def test_command_received(self, publisher: DaemonEventPublisher) -> None:
        """Test publishing command_received event."""
        received_events: list[Event] = []

        async def handler(event: Event) -> None:
            received_events.append(event)

        await publisher.bus.subscribe(handler)
        count = await publisher.command_received("ls -la", "/home/user")

        assert count == 1
        assert len(received_events) == 1
        assert received_events[0].type == EventType.COMMAND_RECEIVED
        assert received_events[0].data["command"] == "ls -la"
        assert received_events[0].data["working_dir"] == "/home/user"

    @pytest.mark.asyncio
    async def test_evaluation_started(self, publisher: DaemonEventPublisher) -> None:
        """Test publishing evaluation_started event."""
        received_events: list[Event] = []

        async def handler(event: Event) -> None:
            received_events.append(event)

        await publisher.bus.subscribe(handler)
        count = await publisher.evaluation_started("git commit -m test", 3)

        assert count == 1
        assert len(received_events) == 1
        assert received_events[0].type == EventType.EVALUATION_STARTED
        assert received_events[0].data["command"] == "git commit -m test"
        assert received_events[0].data["plugin_count"] == 3

    @pytest.mark.asyncio
    async def test_evaluation_completed_allow(self, publisher: DaemonEventPublisher) -> None:
        """Test publishing evaluation_completed event with ALLOW."""
        received_events: list[Event] = []

        async def handler(event: Event) -> None:
            received_events.append(event)

        await publisher.bus.subscribe(handler)
        count = await publisher.evaluation_completed("ls", Decision.ALLOW)

        assert count == 1
        assert len(received_events) == 1
        assert received_events[0].type == EventType.EVALUATION_COMPLETED
        assert received_events[0].data["command"] == "ls"
        assert received_events[0].data["decision"] == "allow"
        assert received_events[0].data["plugin_name"] is None

    @pytest.mark.asyncio
    async def test_evaluation_completed_deny(self, publisher: DaemonEventPublisher) -> None:
        """Test publishing evaluation_completed event with DENY."""
        received_events: list[Event] = []

        async def handler(event: Event) -> None:
            received_events.append(event)

        await publisher.bus.subscribe(handler)
        count = await publisher.evaluation_completed(
            "git commit",
            Decision.DENY,
            plugin_name="git-protect",
            reason="Cannot commit to main",
        )

        assert count == 1
        assert len(received_events) == 1
        assert received_events[0].type == EventType.EVALUATION_COMPLETED
        assert received_events[0].data["command"] == "git commit"
        assert received_events[0].data["decision"] == "deny"
        assert received_events[0].data["plugin_name"] == "git-protect"
        assert received_events[0].data["reason"] == "Cannot commit to main"

    @pytest.mark.asyncio
    async def test_approval_needed(self, publisher: DaemonEventPublisher) -> None:
        """Test publishing approval_needed event."""
        received_events: list[Event] = []

        async def handler(event: Event) -> None:
            received_events.append(event)

        await publisher.bus.subscribe(handler)
        count = await publisher.approval_needed(
            approval_id="abc123",
            command="git push --force",
            plugin_name="git-protect",
            reason="Force push requires approval",
            challenge_code="XY789",
        )

        assert count == 1
        assert len(received_events) == 1
        assert received_events[0].type == EventType.APPROVAL_NEEDED
        assert received_events[0].data["approval_id"] == "abc123"
        assert received_events[0].data["command"] == "git push --force"
        assert received_events[0].data["plugin_name"] == "git-protect"
        assert received_events[0].data["reason"] == "Force push requires approval"
        assert received_events[0].data["challenge_code"] == "XY789"

    @pytest.mark.asyncio
    async def test_approval_resolved_approved(self, publisher: DaemonEventPublisher) -> None:
        """Test publishing approval_resolved event when approved."""
        received_events: list[Event] = []

        async def handler(event: Event) -> None:
            received_events.append(event)

        await publisher.bus.subscribe(handler)
        count = await publisher.approval_resolved("abc123", approved=True)

        assert count == 1
        assert len(received_events) == 1
        assert received_events[0].type == EventType.APPROVAL_RESOLVED
        assert received_events[0].data["approval_id"] == "abc123"
        assert received_events[0].data["approved"] is True
        assert received_events[0].data["reason"] is None

    @pytest.mark.asyncio
    async def test_approval_resolved_denied(self, publisher: DaemonEventPublisher) -> None:
        """Test publishing approval_resolved event when denied."""
        received_events: list[Event] = []

        async def handler(event: Event) -> None:
            received_events.append(event)

        await publisher.bus.subscribe(handler)
        count = await publisher.approval_resolved("abc123", approved=False, reason="Too risky")

        assert count == 1
        assert len(received_events) == 1
        assert received_events[0].type == EventType.APPROVAL_RESOLVED
        assert received_events[0].data["approval_id"] == "abc123"
        assert received_events[0].data["approved"] is False
        assert received_events[0].data["reason"] == "Too risky"

    @pytest.mark.asyncio
    async def test_daemon_status(self, publisher: DaemonEventPublisher) -> None:
        """Test publishing daemon_status event."""
        received_events: list[Event] = []

        async def handler(event: Event) -> None:
            received_events.append(event)

        await publisher.bus.subscribe(handler)
        count = await publisher.daemon_status(
            status="running",
            uptime_seconds=123.5,
            commands_processed=42,
            active_connections=2,
        )

        assert count == 1
        assert len(received_events) == 1
        assert received_events[0].type == EventType.DAEMON_STATUS
        assert received_events[0].data["status"] == "running"
        assert received_events[0].data["uptime_seconds"] == 123.5
        assert received_events[0].data["commands_processed"] == 42
        assert received_events[0].data["active_connections"] == 2

    @pytest.mark.asyncio
    async def test_no_subscribers(self, publisher: DaemonEventPublisher) -> None:
        """Test publishing with no subscribers returns 0."""
        count = await publisher.command_received("ls", "/home/user")
        assert count == 0


class TestEventPublisherWithManager:
    """Tests for PluginManager with event publisher integration."""

    @pytest.mark.asyncio
    async def test_evaluate_emits_events(self) -> None:
        """Test that command evaluation emits events."""
        import tempfile

        from safeshell.daemon.manager import PluginManager
        from safeshell.models import DaemonRequest, RequestType

        bus = EventBus()
        publisher = DaemonEventPublisher(bus)
        manager = PluginManager(event_publisher=publisher)

        received_events: list[Event] = []

        async def handler(event: Event) -> None:
            received_events.append(event)

        await bus.subscribe(handler)

        # Evaluate a command
        with tempfile.TemporaryDirectory() as tmpdir:
            request = DaemonRequest(
                type=RequestType.EVALUATE,
                command="ls -la",
                working_dir=tmpdir,
            )
            await manager.process_request(request)

        # Should have received command_received, evaluation_started, evaluation_completed
        event_types = [e.type for e in received_events]
        assert EventType.COMMAND_RECEIVED in event_types
        assert EventType.EVALUATION_STARTED in event_types
        assert EventType.EVALUATION_COMPLETED in event_types

    @pytest.mark.asyncio
    async def test_evaluate_without_publisher(self) -> None:
        """Test that evaluation works without event publisher."""
        import tempfile

        from safeshell.daemon.manager import PluginManager
        from safeshell.models import DaemonRequest, Decision, RequestType

        manager = PluginManager()  # No publisher

        with tempfile.TemporaryDirectory() as tmpdir:
            request = DaemonRequest(
                type=RequestType.EVALUATE,
                command="ls -la",
                working_dir=tmpdir,
            )
            response = await manager.process_request(request)

        assert response.success is True
        assert response.final_decision == Decision.ALLOW
