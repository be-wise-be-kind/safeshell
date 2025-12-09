"""Tests for safeshell.events.bus module."""

import asyncio

import pytest

from safeshell.events.bus import EventBus
from safeshell.events.types import Event, EventType
from safeshell.models import Decision


class TestEventBus:
    """Tests for EventBus class."""

    @pytest.mark.asyncio
    async def test_subscribe_returns_id(self) -> None:
        """Test that subscribe returns a subscription ID."""
        bus = EventBus()

        async def handler(event: Event) -> None:
            pass

        sub_id = await bus.subscribe(handler)
        assert isinstance(sub_id, str)
        assert len(sub_id) > 0

    @pytest.mark.asyncio
    async def test_unsubscribe_existing(self) -> None:
        """Test unsubscribing an existing subscriber."""
        bus = EventBus()

        async def handler(event: Event) -> None:
            pass

        sub_id = await bus.subscribe(handler)
        assert bus.subscriber_count == 1

        result = await bus.unsubscribe(sub_id)
        assert result is True
        assert bus.subscriber_count == 0

    @pytest.mark.asyncio
    async def test_unsubscribe_nonexistent(self) -> None:
        """Test unsubscribing a nonexistent subscriber."""
        bus = EventBus()
        result = await bus.unsubscribe("nonexistent-id")
        assert result is False

    @pytest.mark.asyncio
    async def test_publish_to_subscriber(self) -> None:
        """Test that publish delivers event to subscriber."""
        bus = EventBus()
        received_events: list[Event] = []

        async def handler(event: Event) -> None:
            received_events.append(event)

        await bus.subscribe(handler)

        event = Event.command_received("ls", "/home/user")
        delivered = await bus.publish(event)

        assert delivered == 1
        assert len(received_events) == 1
        assert received_events[0].type == EventType.COMMAND_RECEIVED
        assert received_events[0].data["command"] == "ls"

    @pytest.mark.asyncio
    async def test_publish_to_multiple_subscribers(self) -> None:
        """Test that publish delivers to all subscribers."""
        bus = EventBus()
        received_1: list[Event] = []
        received_2: list[Event] = []

        async def handler_1(event: Event) -> None:
            received_1.append(event)

        async def handler_2(event: Event) -> None:
            received_2.append(event)

        await bus.subscribe(handler_1)
        await bus.subscribe(handler_2)

        event = Event.evaluation_completed("ls", Decision.ALLOW)
        delivered = await bus.publish(event)

        assert delivered == 2
        assert len(received_1) == 1
        assert len(received_2) == 1

    @pytest.mark.asyncio
    async def test_publish_no_subscribers(self) -> None:
        """Test publishing with no subscribers."""
        bus = EventBus()
        event = Event.daemon_status("running", 0.0, 0, 0)
        delivered = await bus.publish(event)
        assert delivered == 0

    @pytest.mark.asyncio
    async def test_subscriber_error_does_not_affect_others(self) -> None:
        """Test that one subscriber's error doesn't affect others."""
        bus = EventBus()
        received: list[Event] = []

        async def failing_handler(event: Event) -> None:
            raise ValueError("Handler error")

        async def working_handler(event: Event) -> None:
            received.append(event)

        await bus.subscribe(failing_handler)
        await bus.subscribe(working_handler)

        event = Event.command_received("test", "/home/user")
        delivered = await bus.publish(event)

        # One succeeded, one failed
        assert delivered == 1
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_subscriber_count(self) -> None:
        """Test subscriber_count property."""
        bus = EventBus()
        assert bus.subscriber_count == 0

        async def handler(event: Event) -> None:
            pass

        sub_1 = await bus.subscribe(handler)
        assert bus.subscriber_count == 1

        sub_2 = await bus.subscribe(handler)
        assert bus.subscriber_count == 2

        await bus.unsubscribe(sub_1)
        assert bus.subscriber_count == 1

        await bus.unsubscribe(sub_2)
        assert bus.subscriber_count == 0

    @pytest.mark.asyncio
    async def test_clear(self) -> None:
        """Test clearing all subscribers."""
        bus = EventBus()

        async def handler(event: Event) -> None:
            pass

        await bus.subscribe(handler)
        await bus.subscribe(handler)
        await bus.subscribe(handler)

        assert bus.subscriber_count == 3

        removed = await bus.clear()
        assert removed == 3
        assert bus.subscriber_count == 0

    @pytest.mark.asyncio
    async def test_get_subscriber_ids(self) -> None:
        """Test getting list of subscriber IDs."""
        bus = EventBus()

        async def handler(event: Event) -> None:
            pass

        sub_1 = await bus.subscribe(handler)
        sub_2 = await bus.subscribe(handler)

        ids = bus.get_subscriber_ids()
        assert sub_1 in ids
        assert sub_2 in ids
        assert len(ids) == 2

    @pytest.mark.asyncio
    async def test_concurrent_publish(self) -> None:
        """Test that events are delivered concurrently."""
        bus = EventBus()
        call_times: list[float] = []

        async def slow_handler(event: Event) -> None:
            import time

            start = time.monotonic()
            await asyncio.sleep(0.01)  # 10ms delay
            call_times.append(time.monotonic() - start)

        # Add 3 slow handlers
        await bus.subscribe(slow_handler)
        await bus.subscribe(slow_handler)
        await bus.subscribe(slow_handler)

        import time

        start = time.monotonic()
        event = Event.command_received("test", "/home/user")
        await bus.publish(event)
        total_time = time.monotonic() - start

        # If delivered sequentially, would take ~30ms
        # If concurrent, should take ~10-15ms
        assert total_time < 0.025  # Allow some overhead
        assert len(call_times) == 3

    @pytest.mark.asyncio
    async def test_unsubscribe_during_publish(self) -> None:
        """Test that unsubscribe during publish is handled safely."""
        bus = EventBus()
        received: list[Event] = []

        async def handler(event: Event) -> None:
            received.append(event)

        sub_id = await bus.subscribe(handler)

        # Start publishing in background
        event = Event.command_received("test", "/home/user")

        # This should complete without error even if we unsubscribe
        task = asyncio.create_task(bus.publish(event))
        await bus.unsubscribe(sub_id)
        await task

        # The event may or may not have been delivered depending on timing
        # The important thing is no error occurred

    @pytest.mark.asyncio
    async def test_multiple_event_types(self) -> None:
        """Test handling multiple event types."""
        bus = EventBus()
        received: list[Event] = []

        async def handler(event: Event) -> None:
            received.append(event)

        await bus.subscribe(handler)

        # Publish different event types
        await bus.publish(Event.command_received("ls", "/home/user"))
        await bus.publish(Event.evaluation_started("ls", 2))
        await bus.publish(Event.evaluation_completed("ls", Decision.ALLOW))
        await bus.publish(Event.daemon_status("running", 10.0, 5, 1))

        assert len(received) == 4
        assert received[0].type == EventType.COMMAND_RECEIVED
        assert received[1].type == EventType.EVALUATION_STARTED
        assert received[2].type == EventType.EVALUATION_COMPLETED
        assert received[3].type == EventType.DAEMON_STATUS
