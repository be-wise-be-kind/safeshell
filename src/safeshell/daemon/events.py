"""
File: src/safeshell/daemon/events.py
Purpose: Daemon event publisher for monitor communication
Exports: DaemonEventPublisher
Depends: safeshell.events.bus, safeshell.events.types, safeshell.models
Overview: Wraps EventBus with convenience methods for publishing daemon events
"""

from loguru import logger

from safeshell.events.bus import EventBus
from safeshell.events.types import Event
from safeshell.models import Decision


class DaemonEventPublisher:
    """Publishes daemon events to connected monitors.

    Provides typed convenience methods for publishing events, wrapping
    the underlying EventBus. This class is used by the daemon to emit
    events that monitors can subscribe to.

    Example:
        bus = EventBus()
        publisher = DaemonEventPublisher(bus)
        await publisher.command_received("ls -la", "/home/user")
    """

    def __init__(self, bus: EventBus) -> None:
        """Initialize the event publisher.

        Args:
            bus: The EventBus to publish events to
        """
        self._bus = bus

    @property
    def bus(self) -> EventBus:
        """Return the underlying EventBus."""
        return self._bus

    async def command_received(
        self, command: str, working_dir: str, client_pid: int | None = None
    ) -> int:
        """Publish a command received event.

        Args:
            command: The raw command string
            working_dir: Working directory for the command
            client_pid: PID of the calling shell process

        Returns:
            Number of subscribers that received the event
        """
        event = Event.command_received(command, working_dir, client_pid)
        logger.debug(f"Publishing command_received: {command} (pid={client_pid})")
        return await self._bus.publish(event)

    async def evaluation_started(self, command: str, plugin_count: int) -> int:
        """Publish an evaluation started event.

        Args:
            command: The command being evaluated
            plugin_count: Number of plugins that will evaluate

        Returns:
            Number of subscribers that received the event
        """
        event = Event.evaluation_started(command, plugin_count)
        logger.debug(f"Publishing evaluation_started: {command} ({plugin_count} plugins)")
        return await self._bus.publish(event)

    async def evaluation_completed(
        self,
        command: str,
        decision: Decision,
        plugin_name: str | None = None,
        reason: str | None = None,
    ) -> int:
        """Publish an evaluation completed event.

        Args:
            command: The command that was evaluated
            decision: Final decision for the command
            plugin_name: Plugin that made the decision (if denied)
            reason: Reason for the decision

        Returns:
            Number of subscribers that received the event
        """
        event = Event.evaluation_completed(command, decision, plugin_name, reason)
        logger.debug(f"Publishing evaluation_completed: {command} -> {decision.value}")
        return await self._bus.publish(event)

    async def approval_needed(
        self,
        approval_id: str,
        command: str,
        plugin_name: str,
        reason: str,
        working_dir: str | None = None,
        client_pid: int | None = None,
        challenge_code: str | None = None,
    ) -> int:
        """Publish an approval needed event.

        Args:
            approval_id: Unique identifier for this approval request
            command: The command awaiting approval
            plugin_name: Plugin that requires approval
            reason: Why approval is needed
            working_dir: Working directory for the command
            client_pid: PID of the calling shell process
            challenge_code: Optional challenge code for verification

        Returns:
            Number of subscribers that received the event
        """
        event = Event.approval_needed(
            approval_id, command, plugin_name, reason, working_dir, client_pid, challenge_code
        )
        logger.info(f"Publishing approval_needed: {command} (id={approval_id[:8]}...)")
        return await self._bus.publish(event)

    async def approval_resolved(
        self,
        approval_id: str,
        approved: bool,
        reason: str | None = None,
        working_dir: str | None = None,
        client_pid: int | None = None,
    ) -> int:
        """Publish an approval resolved event.

        Args:
            approval_id: The approval request that was resolved
            approved: Whether the request was approved
            reason: Reason for denial (if denied)
            working_dir: Working directory for the command
            client_pid: PID of the calling shell process

        Returns:
            Number of subscribers that received the event
        """
        event = Event.approval_resolved(approval_id, approved, reason, working_dir, client_pid)
        status = "approved" if approved else "denied"
        logger.info(f"Publishing approval_resolved: {approval_id[:8]}... -> {status}")
        return await self._bus.publish(event)

    async def daemon_status(
        self,
        status: str,
        uptime_seconds: float,
        commands_processed: int,
        active_connections: int,
    ) -> int:
        """Publish a daemon status event.

        Args:
            status: Current daemon status
            uptime_seconds: Daemon uptime in seconds
            commands_processed: Total commands processed
            active_connections: Number of active connections

        Returns:
            Number of subscribers that received the event
        """
        event = Event.daemon_status(status, uptime_seconds, commands_processed, active_connections)
        logger.debug(f"Publishing daemon_status: {status}")
        return await self._bus.publish(event)
