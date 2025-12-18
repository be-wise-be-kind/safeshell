"""
File: src/safeshell/events/bus.py
Purpose: Async event bus for daemon-monitor communication
Exports: EventBus
Depends: asyncio, uuid, loguru
Overview: Provides pub/sub infrastructure for streaming events from daemon to monitors
"""

import asyncio
import uuid
from collections.abc import Awaitable, Callable

from loguru import logger

from safeshell.events.types import Event

# Type alias for event callbacks
EventCallback = Callable[[Event], Awaitable[None]]

# Logging constants
_ID_LOG_PREVIEW_LENGTH = 8


class EventBus:
    """Async event bus for daemon-monitor communication.

    The EventBus allows multiple subscribers to receive events published
    by the daemon. Each subscriber receives events asynchronously through
    a callback function.

    Thread Safety:
        This class is designed for single-threaded async use. All operations
        should be called from the same event loop.

    Example:
        bus = EventBus()

        async def handler(event: Event) -> None:
            print(f"Received: {event.type}")

        sub_id = await bus.subscribe(handler)
        await bus.publish(Event.command_received("ls", "/tmp"))
        await bus.unsubscribe(sub_id)
    """

    def __init__(self) -> None:
        """Initialize the event bus with no subscribers."""
        self._subscribers: dict[str, EventCallback] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, callback: EventCallback) -> str:
        """Subscribe to events with a callback function.

        Args:
            callback: Async function to call when events are published.
                     Signature: async def callback(event: Event) -> None

        Returns:
            Subscription ID that can be used to unsubscribe later.
        """
        sub_id = str(uuid.uuid4())
        async with self._lock:
            self._subscribers[sub_id] = callback
        logger.debug(f"Subscriber {sub_id[:_ID_LOG_PREVIEW_LENGTH]}... registered")
        return sub_id

    async def unsubscribe(self, sub_id: str) -> bool:
        """Unsubscribe from events.

        Args:
            sub_id: Subscription ID returned from subscribe()

        Returns:
            True if subscriber was found and removed, False otherwise.
        """
        async with self._lock:
            if sub_id in self._subscribers:
                del self._subscribers[sub_id]
                logger.debug(f"Subscriber {sub_id[:_ID_LOG_PREVIEW_LENGTH]}... unregistered")
                return True
        logger.warning(f"Subscriber {sub_id[:_ID_LOG_PREVIEW_LENGTH]}... not found for unsubscribe")
        return False

    async def publish(self, event: Event) -> int:
        """Publish an event to all subscribers.

        Events are delivered to subscribers concurrently. If a subscriber's
        callback raises an exception, it is logged but does not affect
        delivery to other subscribers.

        Args:
            event: The event to publish

        Returns:
            Number of subscribers the event was delivered to.
        """
        async with self._lock:
            callbacks = list(self._subscribers.items())

        if not callbacks:
            logger.debug(f"No subscribers for event {event.type}")
            return 0

        logger.debug(f"Publishing {event.type} to {len(callbacks)} subscribers")

        # Deliver to all subscribers concurrently
        results = await asyncio.gather(
            *[self._deliver(sub_id, callback, event) for sub_id, callback in callbacks],
            return_exceptions=True,
        )

        # Count successful deliveries
        return sum(1 for r in results if r is True)

    async def _deliver(self, sub_id: str, callback: EventCallback, event: Event) -> bool:
        """Deliver an event to a single subscriber.

        Args:
            sub_id: Subscriber ID for logging
            callback: The subscriber's callback function
            event: The event to deliver

        Returns:
            True if delivery succeeded, False otherwise.
        """
        try:
            await callback(event)
            return True
        except Exception as e:
            logger.exception(f"Error delivering event to {sub_id[:_ID_LOG_PREVIEW_LENGTH]}...: {e}")
            return False

    @property
    def subscriber_count(self) -> int:
        """Return the current number of subscribers."""
        return len(self._subscribers)

    async def clear(self) -> int:
        """Remove all subscribers.

        Returns:
            Number of subscribers that were removed.
        """
        async with self._lock:
            count = len(self._subscribers)
            self._subscribers.clear()
        logger.debug(f"Cleared {count} subscribers")
        return count

    def get_subscriber_ids(self) -> list[str]:
        """Return list of current subscriber IDs.

        Useful for debugging and testing.
        """
        return list(self._subscribers.keys())
