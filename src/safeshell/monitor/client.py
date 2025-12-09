"""
File: src/safeshell/monitor/client.py
Purpose: Async client for connecting to daemon's monitor socket
Exports: MonitorClient
Depends: asyncio, safeshell.daemon.lifecycle, safeshell.daemon.protocol
Overview: Handles connection to monitor socket and event streaming
"""

# ruff: noqa: SIM105, S110 - contextlib.suppress doesn't work with await; best-effort error handling

import asyncio
from collections.abc import Callable
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field

from safeshell.daemon.lifecycle import MONITOR_SOCKET_PATH
from safeshell.daemon.monitor import MonitorCommand, MonitorCommandType
from safeshell.daemon.protocol import decode_message, encode_message


class MonitorClientMessage(BaseModel):
    """Message to send to daemon."""

    type: str = Field(description="Message type")


class MonitorClient:
    """Async client for connecting to the daemon's monitor socket.

    Connects to the monitor socket and receives event stream.
    Also supports sending commands (approve/deny) back to the daemon.
    """

    def __init__(self) -> None:
        """Initialize the monitor client."""
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._connected = False
        self._event_callbacks: list[Callable[[dict[str, Any]], None]] = []
        self._receive_task: asyncio.Task[None] | None = None

    @property
    def connected(self) -> bool:
        """Return whether the client is connected."""
        return self._connected

    def add_event_callback(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """Add a callback to be called when events are received.

        Args:
            callback: Function to call with event data
        """
        self._event_callbacks.append(callback)

    def remove_event_callback(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """Remove an event callback.

        Args:
            callback: Function to remove
        """
        if callback in self._event_callbacks:
            self._event_callbacks.remove(callback)

    async def connect(self) -> bool:
        """Connect to the daemon's monitor socket.

        Returns:
            True if connected successfully
        """
        if self._connected:
            return True

        socket_path = str(MONITOR_SOCKET_PATH)
        try:
            self._reader, self._writer = await asyncio.open_unix_connection(socket_path)
            self._connected = True
            logger.info(f"Connected to monitor socket: {socket_path}")

            # Read welcome message
            if self._reader:
                line = await self._reader.readline()
                if line:
                    welcome = decode_message(line.strip())
                    logger.debug(f"Welcome message: {welcome}")

            return True

        except (ConnectionRefusedError, FileNotFoundError) as e:
            logger.warning(f"Failed to connect to monitor socket: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from the daemon."""
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None

        if self._writer:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except Exception:
                pass

        self._reader = None
        self._writer = None
        self._connected = False
        logger.info("Disconnected from monitor socket")

    async def start_receiving(self) -> None:
        """Start receiving events in background task."""
        if self._receive_task is not None:
            return
        self._receive_task = asyncio.create_task(self._receive_loop())

    async def _receive_loop(self) -> None:
        """Receive events from the daemon and dispatch to callbacks."""
        if not self._reader:
            return

        while self._connected:
            try:
                line = await self._reader.readline()
                if not line:
                    logger.warning("Monitor connection closed by daemon")
                    self._connected = False
                    break

                message = decode_message(line.strip())

                # Dispatch to callbacks
                for callback in self._event_callbacks:
                    try:
                        callback(message)
                    except Exception as e:
                        logger.error(f"Error in event callback: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error receiving from monitor socket: {e}")
                self._connected = False
                break

    async def ping(self) -> bool:
        """Send ping to daemon.

        Returns:
            True if daemon responded
        """
        if not self._connected or not self._writer or not self._reader:
            return False

        try:
            command = MonitorCommand(type=MonitorCommandType.PING)
            self._writer.write(encode_message(command))
            await self._writer.drain()

            line = await asyncio.wait_for(self._reader.readline(), timeout=5.0)
            if line:
                response = decode_message(line.strip())
                success: bool = response.get("success", False)
                return success
            return False

        except Exception as e:
            logger.error(f"Ping failed: {e}")
            return False

    async def approve(self, approval_id: str) -> bool:
        """Approve a pending command.

        Args:
            approval_id: ID of the approval to approve

        Returns:
            True if approved successfully
        """
        if not self._connected or not self._writer:
            return False

        try:
            command = MonitorCommand(
                type=MonitorCommandType.APPROVE,
                approval_id=approval_id,
            )
            self._writer.write(encode_message(command))
            await self._writer.drain()
            logger.info(f"Sent approve for {approval_id[:8]}...")
            return True

        except Exception as e:
            logger.error(f"Failed to send approve: {e}")
            return False

    async def deny(self, approval_id: str, reason: str | None = None) -> bool:
        """Deny a pending command.

        Args:
            approval_id: ID of the approval to deny
            reason: Optional reason for denial

        Returns:
            True if denied successfully
        """
        if not self._connected or not self._writer:
            return False

        try:
            command = MonitorCommand(
                type=MonitorCommandType.DENY,
                approval_id=approval_id,
                reason=reason,
            )
            self._writer.write(encode_message(command))
            await self._writer.drain()
            logger.info(f"Sent deny for {approval_id[:8]}...")
            return True

        except Exception as e:
            logger.error(f"Failed to send deny: {e}")
            return False
