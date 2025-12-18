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

# Logging constants
_ID_LOG_PREVIEW_LENGTH = 8


class MonitorCommandType(str, Enum):
    """Types of commands from monitor to daemon."""

    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    APPROVE = "approve"
    DENY = "deny"
    PING = "ping"
    SET_ENABLED = "set_enabled"
    RELOAD_RULES = "reload_rules"
    GET_STATUS = "get_status"


class MonitorCommand(BaseModel):
    """Command from monitor to daemon."""

    type: MonitorCommandType = Field(description="Type of command")
    approval_id: str | None = Field(default=None, description="Approval ID for approve/deny")
    reason: str | None = Field(default=None, description="Reason for denial")
    remember: bool = Field(default=False, description="Remember decision for session")
    enabled: bool | None = Field(default=None, description="Enable/disable protection")


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
        self._set_enabled_callback: Any = None
        self._reload_rules_callback: Any = None
        self._get_status_callback: Any = None

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

    def set_control_callbacks(
        self,
        set_enabled_callback: Any,
        reload_rules_callback: Any,
        get_status_callback: Any,
    ) -> None:
        """Set callbacks for control actions.

        Args:
            set_enabled_callback: Called when monitor sets enabled state (enabled: bool)
            reload_rules_callback: Called when monitor requests rule reload
            get_status_callback: Called when monitor requests status (returns dict)
        """
        self._set_enabled_callback = set_enabled_callback
        self._reload_rules_callback = reload_rules_callback
        self._get_status_callback = get_status_callback

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
            logger.debug(f"Monitor {peer} subscribed with ID {sub_id[:_ID_LOG_PREVIEW_LENGTH]}...")

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
                logger.debug(f"Monitor {peer} unsubscribed ({sub_id[:_ID_LOG_PREVIEW_LENGTH]}...)")

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
            logger.exception(f"Failed to send event: {e}")

    async def _try_send_error(self, writer: asyncio.StreamWriter, error: str) -> None:
        """Try to send an error response, ignoring failures."""
        try:
            await write_message(writer, MonitorResponse.err(error))
        except Exception:
            pass  # Best effort - client may have disconnected

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
                logger.exception(f"Error processing monitor command: {e}")
                await self._try_send_error(writer, str(e))

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
            return await self._handle_approve(command.approval_id, command.remember)

        if command.type == MonitorCommandType.DENY:
            if not command.approval_id:
                return MonitorResponse.err("approval_id required")
            return await self._handle_deny(command.approval_id, command.reason, command.remember)

        if command.type == MonitorCommandType.SET_ENABLED:
            if command.enabled is None:
                return MonitorResponse.err("enabled field required")
            return await self._handle_set_enabled(command.enabled)

        if command.type == MonitorCommandType.RELOAD_RULES:
            return await self._handle_reload_rules()

        if command.type == MonitorCommandType.GET_STATUS:
            return await self._handle_get_status()

        return MonitorResponse.err(f"Unknown command type: {command.type}")

    async def _handle_approve(self, approval_id: str, remember: bool = False) -> MonitorResponse:
        """Handle an approve command.

        Args:
            approval_id: ID of approval to approve
            remember: Whether to remember decision for session

        Returns:
            Response indicating success or failure
        """
        if not self._approve_callback:
            return MonitorResponse.err("Approval system not configured")

        try:
            await self._approve_callback(approval_id, remember=remember)
            action = "Approved (remember)" if remember else "Approved"
            return MonitorResponse.ok(f"{action} {approval_id[:_ID_LOG_PREVIEW_LENGTH]}...")
        except Exception as e:
            return MonitorResponse.err(f"Failed to approve: {e}")

    async def _handle_deny(
        self, approval_id: str, reason: str | None, remember: bool = False
    ) -> MonitorResponse:
        """Handle a deny command.

        Args:
            approval_id: ID of approval to deny
            reason: Optional reason for denial
            remember: Whether to remember decision for session

        Returns:
            Response indicating success or failure
        """
        if not self._deny_callback:
            return MonitorResponse.err("Approval system not configured")

        try:
            await self._deny_callback(approval_id, reason, remember=remember)
            action = "Denied (remember)" if remember else "Denied"
            return MonitorResponse.ok(f"{action} {approval_id[:_ID_LOG_PREVIEW_LENGTH]}...")
        except Exception as e:
            return MonitorResponse.err(f"Failed to deny: {e}")

    async def _handle_set_enabled(self, enabled: bool) -> MonitorResponse:
        """Handle a set_enabled command.

        Args:
            enabled: Whether to enable or disable protection

        Returns:
            Response indicating success or failure
        """
        if not self._set_enabled_callback:
            return MonitorResponse.err("Control system not configured")

        try:
            await self._set_enabled_callback(enabled)
            status = "enabled" if enabled else "disabled"
            return MonitorResponse.ok(f"Protection {status}")
        except Exception as e:
            return MonitorResponse.err(f"Failed to set enabled: {e}")

    async def _handle_reload_rules(self) -> MonitorResponse:
        """Handle a reload_rules command.

        Returns:
            Response indicating success or failure
        """
        if not self._reload_rules_callback:
            return MonitorResponse.err("Control system not configured")

        try:
            await self._reload_rules_callback()
            return MonitorResponse.ok("Rules reloaded")
        except Exception as e:
            return MonitorResponse.err(f"Failed to reload rules: {e}")

    async def _handle_get_status(self) -> MonitorResponse:
        """Handle a get_status command.

        Returns:
            Response with current daemon status
        """
        if not self._get_status_callback:
            return MonitorResponse.err("Control system not configured")

        try:
            status = await self._get_status_callback()
            # Return status info in the message field
            return MonitorResponse.ok(str(status))
        except Exception as e:
            return MonitorResponse.err(f"Failed to get status: {e}")
