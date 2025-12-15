"""
File: src/safeshell/daemon/server.py
Purpose: Asyncio Unix socket server for SafeShell daemon
Exports: DaemonServer, run_daemon
Depends: asyncio, safeshell.daemon.lifecycle, safeshell.daemon.manager, safeshell.daemon.protocol,
         safeshell.daemon.events, safeshell.daemon.monitor, safeshell.events.bus
Overview: Main daemon server that accepts connections, processes command evaluation requests,
          and streams events to connected monitors
"""

# ruff: noqa: SIM105, S110 - contextlib.suppress doesn't work with await; best-effort error responses

import asyncio
import signal
import sys
import time
from collections.abc import Awaitable, Callable
from typing import Any

from loguru import logger

from safeshell.config import SafeShellConfig, load_config, write_shell_config
from safeshell.daemon.approval import ApprovalManager
from safeshell.daemon.events import DaemonEventPublisher
from safeshell.daemon.lifecycle import (
    MONITOR_SOCKET_PATH,
    SOCKET_PATH,
    DaemonLifecycle,
)
from safeshell.daemon.manager import RuleManager
from safeshell.daemon.monitor import MonitorConnectionHandler
from safeshell.daemon.protocol import read_message, write_message
from safeshell.daemon.session_memory import SessionMemory
from safeshell.events.bus import EventBus
from safeshell.exceptions import ProtocolError
from safeshell.models import DaemonRequest, DaemonResponse


class DaemonServer:
    """Asyncio-based Unix socket daemon server.

    Listens on two Unix domain sockets:
    - daemon.sock: For shell wrapper command evaluation requests
    - monitor.sock: For monitor TUI event streaming

    The server maintains an EventBus that publishes events during
    command evaluation, which monitors can subscribe to.
    """

    def __init__(self) -> None:
        """Initialize daemon server with event infrastructure."""
        self.socket_path = SOCKET_PATH
        self.monitor_socket_path = MONITOR_SOCKET_PATH

        # Load configuration
        self._config = load_config()

        # Event infrastructure
        self._event_bus = EventBus()
        self._event_publisher = DaemonEventPublisher(self._event_bus)
        self._monitor_handler = MonitorConnectionHandler(self._event_bus)

        # Approval manager for handling REQUIRE_APPROVAL decisions
        self._approval_manager = ApprovalManager(
            event_publisher=self._event_publisher,
            default_timeout=self._config.approval_timeout_seconds,
        )

        # Wire monitor handler's approval callbacks to approval manager
        self._monitor_handler.set_approval_callbacks(
            approve_callback=self._approval_manager.approve,
            deny_callback=self._approval_manager.deny,
        )

        # Session memory for "don't ask again" approvals
        self._session_memory = SessionMemory(
            ttl_seconds=self._config.approval_memory_ttl_seconds,
        )

        # Rule manager with event publisher, approval manager, and session memory
        self.rule_manager = RuleManager(
            event_publisher=self._event_publisher,
            approval_manager=self._approval_manager,
            session_memory=self._session_memory,
        )

        # Server state
        self._wrapper_server: asyncio.Server | None = None
        self._monitor_server: asyncio.Server | None = None
        self._shutdown_event: asyncio.Event | None = None

        # Statistics
        self._start_time: float = 0.0
        self._commands_processed: int = 0

    @property
    def event_bus(self) -> EventBus:
        """Return the event bus."""
        return self._event_bus

    @property
    def event_publisher(self) -> DaemonEventPublisher:
        """Return the event publisher."""
        return self._event_publisher

    @property
    def approval_manager(self) -> ApprovalManager:
        """Return the approval manager."""
        return self._approval_manager

    @property
    def uptime_seconds(self) -> float:
        """Return daemon uptime in seconds."""
        if self._start_time == 0.0:
            return 0.0
        return time.monotonic() - self._start_time

    @property
    def commands_processed(self) -> int:
        """Return total commands processed."""
        return self._commands_processed

    @property
    def active_monitor_connections(self) -> int:
        """Return number of active monitor connections."""
        return self._monitor_handler.active_connections

    async def start(self) -> None:
        """Start the daemon server.

        Sets up signal handlers, creates both sockets, and serves forever.
        """
        # Clean up any stale files
        DaemonLifecycle.cleanup_on_start()

        # Write PID file
        DaemonLifecycle.write_pid()

        # Record start time
        self._start_time = time.monotonic()

        # Set up shutdown event
        self._shutdown_event = asyncio.Event()

        # Set up signal handlers for graceful shutdown
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._signal_handler)

        # Create and start wrapper server (command evaluation)
        self._wrapper_server = await asyncio.start_unix_server(
            self._handle_wrapper_client,
            path=str(self.socket_path),
        )
        self.socket_path.chmod(0o600)
        logger.info(f"Wrapper server started on {self.socket_path}")

        # Create and start monitor server (event streaming)
        self._monitor_server = await asyncio.start_unix_server(
            self._monitor_handler.handle_monitor,
            path=str(self.monitor_socket_path),
        )
        self.monitor_socket_path.chmod(0o600)
        logger.info(f"Monitor server started on {self.monitor_socket_path}")

        logger.info("Rule-based evaluation enabled")

        # Publish daemon started event
        await self._event_publisher.daemon_status(
            "started",
            0.0,
            0,
            0,
        )

        # Serve until shutdown
        async with self._wrapper_server, self._monitor_server:
            await self._shutdown_event.wait()

        # Publish shutdown event
        await self._event_publisher.daemon_status(
            "stopping",
            self.uptime_seconds,
            self._commands_processed,
            self.active_monitor_connections,
        )

        logger.info("Daemon shutting down")

    def _signal_handler(self) -> None:
        """Handle shutdown signals."""
        logger.info("Received shutdown signal")
        if self._shutdown_event:
            self._shutdown_event.set()

    async def _handle_wrapper_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle a shell wrapper client connection.

        Reads requests, processes them, and writes responses.
        Handles one request per connection (simple protocol).

        Args:
            reader: Stream reader for client
            writer: Stream writer for client
        """
        peer = writer.get_extra_info("peername")
        logger.debug(f"Wrapper client connected: {peer}")

        try:
            # Read request
            message = await read_message(reader)
            logger.debug(f"Received: {message}")

            # Create callback for sending intermediate messages
            async def send_intermediate(response: DaemonResponse) -> None:
                await write_message(writer, response)
                logger.debug(f"Sent intermediate: {response.model_dump()}")

            # Parse and process request
            response = await self._process_message(message, send_intermediate)

            # Write response
            await write_message(writer, response)
            logger.debug(f"Sent: {response.model_dump()}")

        except ProtocolError as e:
            # "Connection closed" is normal for health checks - don't log as warning
            if "closed" in str(e).lower():
                logger.debug(f"Client disconnected early: {peer}")
            else:
                logger.warning(f"Protocol error from {peer}: {e}")
                error_response = DaemonResponse.error(str(e))
                try:
                    await write_message(writer, error_response)
                except Exception:
                    pass

        except Exception as e:
            logger.exception(f"Error handling client {peer}: {e}")
            error_response = DaemonResponse.error(f"Internal error: {e}")
            try:
                await write_message(writer, error_response)
            except Exception:
                pass

        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except (BrokenPipeError, ConnectionResetError):
                pass  # Client already disconnected
            logger.debug(f"Wrapper client disconnected: {peer}")

    async def _process_message(
        self,
        message: dict[str, Any],
        send_intermediate: Callable[[DaemonResponse], Awaitable[None]] | None = None,
    ) -> DaemonResponse:
        """Process a message and return response.

        Args:
            message: Parsed message dictionary
            send_intermediate: Optional callback to send intermediate responses

        Returns:
            Response to send to client
        """
        try:
            request = DaemonRequest.model_validate(message)

            # Track command evaluation requests
            if request.type.value == "evaluate":
                self._commands_processed += 1

            return await self.rule_manager.process_request(request, send_intermediate)
        except Exception as e:
            logger.error(f"Failed to process message: {e}")
            return DaemonResponse.error(f"Invalid request: {e}")


def configure_logging(config: SafeShellConfig) -> None:
    """Configure loguru logging for daemon.

    Sets up file logging in addition to stderr output.

    Args:
        config: Configuration containing log settings
    """
    # Remove default handler to reconfigure
    logger.remove()

    # Add stderr handler with configured level (includes milliseconds)
    stderr_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    logger.add(
        sys.stderr,
        level=config.log_level,
        format=stderr_format,
    )

    # Add file handler (includes milliseconds)
    log_path = config.get_log_file_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | " + "{name}:{function}:{line} - {message}"
    )
    logger.add(
        log_path,
        level=config.log_level,
        format=file_format,
        rotation="10 MB",
        retention="7 days",
        compression="gz",
    )

    logger.info(f"Logging configured: level={config.log_level}, file={log_path}")


async def run_daemon() -> None:
    """Run the daemon server.

    Entry point for running the daemon in foreground mode.
    """
    # Load config and configure logging before starting server
    config = load_config()
    configure_logging(config)

    # Write shell-readable config for init.bash
    write_shell_config(config)

    server = DaemonServer()
    await server.start()
