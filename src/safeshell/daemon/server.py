"""
File: src/safeshell/daemon/server.py
Purpose: Asyncio Unix socket server for SafeShell daemon
Exports: DaemonServer
Depends: asyncio, safeshell.daemon.lifecycle, safeshell.daemon.manager, safeshell.daemon.protocol
Overview: Main daemon server that accepts connections and processes command evaluation requests
"""

# ruff: noqa: SIM105, S110 - contextlib.suppress doesn't work with await; best-effort error responses

import asyncio
import os
import signal
from typing import Any

from loguru import logger

from safeshell.daemon.lifecycle import SOCKET_PATH, DaemonLifecycle
from safeshell.daemon.manager import PluginManager
from safeshell.daemon.protocol import read_message, write_message
from safeshell.exceptions import ProtocolError
from safeshell.models import DaemonRequest, DaemonResponse


class DaemonServer:
    """Asyncio-based Unix socket daemon server.

    Listens on a Unix domain socket for requests from shell wrappers,
    evaluates commands using the plugin manager, and returns responses.
    """

    def __init__(self) -> None:
        """Initialize daemon server."""
        self.socket_path = SOCKET_PATH
        self.plugin_manager = PluginManager()
        self._server: asyncio.Server | None = None
        self._shutdown_event: asyncio.Event | None = None

    async def start(self) -> None:
        """Start the daemon server.

        Sets up signal handlers, creates the socket, and serves forever.
        """
        # Clean up any stale files
        DaemonLifecycle.cleanup_on_start()

        # Write PID file
        DaemonLifecycle.write_pid()

        # Set up shutdown event
        self._shutdown_event = asyncio.Event()

        # Set up signal handlers for graceful shutdown
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._signal_handler)

        # Create and start server
        self._server = await asyncio.start_unix_server(
            self._handle_client,
            path=str(self.socket_path),
        )

        # Set socket permissions (owner only)
        os.chmod(self.socket_path, 0o600)

        logger.info(f"Daemon started on {self.socket_path}")
        logger.info(f"Loaded {len(self.plugin_manager.plugins)} plugin(s)")

        # Serve until shutdown
        async with self._server:
            await self._shutdown_event.wait()

        logger.info("Daemon shutting down")

    def _signal_handler(self) -> None:
        """Handle shutdown signals."""
        logger.info("Received shutdown signal")
        if self._shutdown_event:
            self._shutdown_event.set()

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle a single client connection.

        Reads requests, processes them, and writes responses.
        Handles one request per connection (simple protocol).

        Args:
            reader: Stream reader for client
            writer: Stream writer for client
        """
        peer = writer.get_extra_info("peername")
        logger.debug(f"Client connected: {peer}")

        try:
            # Read request
            message = await read_message(reader)
            logger.debug(f"Received: {message}")

            # Parse and process request
            response = await self._process_message(message)

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
            logger.debug(f"Client disconnected: {peer}")

    async def _process_message(self, message: dict[str, Any]) -> DaemonResponse:
        """Process a message and return response.

        Args:
            message: Parsed message dictionary

        Returns:
            Response to send to client
        """
        try:
            request = DaemonRequest.model_validate(message)
            return self.plugin_manager.process_request(request)
        except Exception as e:
            logger.error(f"Failed to process message: {e}")
            return DaemonResponse.error(f"Invalid request: {e}")


async def run_daemon() -> None:
    """Run the daemon server.

    Entry point for running the daemon in foreground mode.
    """
    server = DaemonServer()
    await server.start()
