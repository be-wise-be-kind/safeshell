"""
File: src/safeshell/daemon/monitor.py
Purpose: Monitor connection handler for event streaming
Exports: MonitorConnectionHandler, MonitorCommand, MonitorCommandType
Depends: asyncio, safeshell.events.bus, safeshell.daemon.protocol
Overview: Handles monitor client connections and streams events to them
"""

# ruff: noqa: SIM105, S110 - contextlib.suppress doesn't work with await; best-effort error handling

import asyncio
from enum import Enum
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field

from safeshell.daemon.protocol import read_message, write_message
from safeshell.events.bus import EventBus
from safeshell.events.types import Event
from safeshell.exceptions import ProtocolError


class MonitorCommandType(str, Enum):
    """Types of commands from monitor to daemon."""

    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    APPROVE = "approve"
    DENY = "deny"
    PING = "ping"


class MonitorCommand(BaseModel):
    """Command from monitor to daemon."""

    type: MonitorCommandType = Field(description="Type of command")
    approval_id: str | None = Field(default=None, description="Approval ID for approve/deny")
    reason: str | None = Field(default=None, description="Reason for denial")


class MonitorResponse(BaseModel):
    """Response from daemon to monitor."""

    success: bool = Field(description="Whether the command succeeded")
    message: str | None = Field(default=None, description="Optional message")
    error: str | None = Field(default=None, description="Error message if failed")

    @classmethod
    def ok(cls, message: str | None = None) -> "MonitorResponse":
        """Create a success response."""
        return cls(success=True, message=message)

    @classmethod
    def err(cls, error: str) -> "MonitorResponse":
        """Create an error response."""
        return cls(success=False, error=error)


class MonitorEventMessage(BaseModel):
    """Event message sent from daemon to monitor."""

    type: str = Field(default="event", description="Message type")
    event: dict[str, Any] = Field(description="The event data")


class MonitorConnectionHandler:
    """Handles monitor client connections for event streaming.

    Each monitor connects over a Unix socket and receives a stream of
    events from the daemon. Monitors can also send commands back
    (e.g., approve/deny) which are processed by this handler.

    The handler manages the subscription lifecycle, automatically
    unsubscribing when the connection closes.
    """

    def __init__(self, bus: EventBus) -> None:
        """Initialize the monitor connection handler.

        Args:
            bus: The EventBus to subscribe to for events
        """
        self._bus = bus
        self._active_connections: int = 0
        self._approve_callback: Any = None
        self._deny_callback: Any = None

    @property
    def active_connections(self) -> int:
        """Return number of active monitor connections."""
        return self._active_connections

    def set_approval_callbacks(
        self,
        approve_callback: Any,
        deny_callback: Any,
    ) -> None:
        """Set callbacks for approval/denial actions.

        Args:
            approve_callback: Called when monitor approves (approval_id)
            deny_callback: Called when monitor denies (approval_id, reason)
        """
        self._approve_callback = approve_callback
        self._deny_callback = deny_callback

    async def handle_monitor(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle a monitor client connection.

        Subscribes to events and streams them to the client. Also listens
        for commands from the monitor (approve/deny) and processes them.

        Args:
            reader: Stream reader for monitor client
            writer: Stream writer for monitor client
        """
        peer = writer.get_extra_info("peername")
        logger.info(f"Monitor connected: {peer}")
        self._active_connections += 1

        sub_id: str | None = None

        try:
            # Create callback to send events to this monitor
            async def send_event(event: Event) -> None:
                await self._send_event(writer, event)

            # Subscribe to events
            sub_id = await self._bus.subscribe(send_event)
            logger.debug(f"Monitor {peer} subscribed with ID {sub_id[:8]}...")

            # Send welcome message
            welcome = MonitorResponse.ok("Connected to SafeShell daemon")
            await write_message(writer, welcome)

            # Handle commands from monitor until disconnection
            await self._handle_commands(reader, writer)

        except ProtocolError as e:
            if "closed" not in str(e).lower():
                logger.warning(f"Protocol error from monitor {peer}: {e}")

        except Exception as e:
            logger.exception(f"Error handling monitor {peer}: {e}")

        finally:
            # Clean up subscription
            if sub_id:
                await self._bus.unsubscribe(sub_id)
                logger.debug(f"Monitor {peer} unsubscribed ({sub_id[:8]}...)")

            # Close connection
            try:
                writer.close()
                await writer.wait_closed()
            except (BrokenPipeError, ConnectionResetError):
                pass

            self._active_connections -= 1
            logger.info(f"Monitor disconnected: {peer}")

    async def _send_event(self, writer: asyncio.StreamWriter, event: Event) -> None:
        """Send an event to a monitor client.

        Args:
            writer: Stream writer for the client
            event: Event to send
        """
        try:
            # Serialize event with JSON-compatible datetime
            event_msg = MonitorEventMessage(event=event.model_dump(mode="json"))
            await write_message(writer, event_msg)
        except (BrokenPipeError, ConnectionResetError):
            # Connection closed, will be handled by main loop
            raise
        except Exception as e:
            logger.error(f"Failed to send event: {e}")

    async def _handle_commands(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle commands from a monitor client.

        Reads commands in a loop until connection closes.

        Args:
            reader: Stream reader for the client
            writer: Stream writer for the client
        """
        while True:
            try:
                message = await read_message(reader)
                response = await self._process_command(message)
                await write_message(writer, response)
            except ProtocolError:
                # Connection closed
                raise
            except Exception as e:
                logger.error(f"Error processing monitor command: {e}")
                error_response = MonitorResponse.err(str(e))
                try:
                    await write_message(writer, error_response)
                except Exception:
                    pass

    async def _process_command(self, message: dict[str, Any]) -> MonitorResponse:
        """Process a command from a monitor client.

        Args:
            message: Parsed command message

        Returns:
            Response to send to client
        """
        try:
            command = MonitorCommand.model_validate(message)
        except Exception as e:
            return MonitorResponse.err(f"Invalid command: {e}")

        if command.type == MonitorCommandType.PING:
            return MonitorResponse.ok("pong")

        if command.type == MonitorCommandType.APPROVE:
            if not command.approval_id:
                return MonitorResponse.err("approval_id required")
            return await self._handle_approve(command.approval_id)

        if command.type == MonitorCommandType.DENY:
            if not command.approval_id:
                return MonitorResponse.err("approval_id required")
            return await self._handle_deny(command.approval_id, command.reason)

        return MonitorResponse.err(f"Unknown command type: {command.type}")

    async def _handle_approve(self, approval_id: str) -> MonitorResponse:
        """Handle an approve command.

        Args:
            approval_id: ID of approval to approve

        Returns:
            Response indicating success or failure
        """
        if not self._approve_callback:
            return MonitorResponse.err("Approval system not configured")

        try:
            await self._approve_callback(approval_id)
            return MonitorResponse.ok(f"Approved {approval_id[:8]}...")
        except Exception as e:
            return MonitorResponse.err(f"Failed to approve: {e}")

    async def _handle_deny(self, approval_id: str, reason: str | None) -> MonitorResponse:
        """Handle a deny command.

        Args:
            approval_id: ID of approval to deny
            reason: Optional reason for denial

        Returns:
            Response indicating success or failure
        """
        if not self._deny_callback:
            return MonitorResponse.err("Approval system not configured")

        try:
            await self._deny_callback(approval_id, reason)
            return MonitorResponse.ok(f"Denied {approval_id[:8]}...")
        except Exception as e:
            return MonitorResponse.err(f"Failed to deny: {e}")
