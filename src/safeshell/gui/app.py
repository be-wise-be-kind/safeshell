"""
File: src/safeshell/gui/app.py
Purpose: Main PyQt6 application with qasync integration
Exports: SafeShellGuiApp, run_gui
Depends: PyQt6, qasync, safeshell.monitor.client, safeshell.gui.*
Overview: Coordinates system tray, approval dialogs, and daemon communication
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import signal
import sys
from typing import Any

import qasync
from loguru import logger
from PyQt6.QtCore import QByteArray, QObject, QTimer, pyqtSlot
from PyQt6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

from safeshell.common import SAFESHELL_DIR
from safeshell.events.types import EventType
from safeshell.gui.main_window import MainWindow
from safeshell.gui.settings import GuiSettings
from safeshell.gui.tray import SafeShellTray, TrayStatus
from safeshell.monitor.client import MonitorClient

# GUI PID file path
GUI_PID_PATH = SAFESHELL_DIR / "gui.pid"


class SafeShellGuiApp(QObject):
    """Main GUI application coordinating all components.

    Integrates asyncio event loop with Qt using qasync.
    Manages:
    - MonitorClient for daemon communication
    - Main window with event log and approvals
    - System tray icon (optional, may not work on all systems)
    """

    def __init__(self, qt_app: QApplication) -> None:
        """Initialize the GUI application.

        Args:
            qt_app: The QApplication instance
        """
        super().__init__()
        self.qt_app = qt_app
        self.settings = GuiSettings()

        # Write PID file for single instance management
        self._write_pid_file()

        # Set up signal handler for SIGUSR1 (raise window)
        signal.signal(signal.SIGUSR1, self._handle_sigusr1)

        # Daemon communication
        self.client = MonitorClient()
        self.client.add_event_callback(self._on_event_received)

        # Main window (unified event log + approvals)
        self.main_window = MainWindow()
        self.main_window.approval_approved.connect(self._on_approval_approved)
        self.main_window.approval_denied.connect(self._on_approval_denied)

        # Restore window geometry if saved
        geometry = self.settings.main_window_geometry
        if geometry:
            self.main_window.restoreGeometry(QByteArray(geometry))

        self.main_window.show()

        # System tray (may not be visible on all systems like GNOME/Wayland)
        self.tray = SafeShellTray(self)
        self.tray.show()

    def _write_pid_file(self) -> None:
        """Write current PID to file for single instance management."""
        SAFESHELL_DIR.mkdir(parents=True, exist_ok=True)
        GUI_PID_PATH.write_text(str(os.getpid()))
        logger.debug(f"Wrote GUI PID {os.getpid()} to {GUI_PID_PATH}")

    def _handle_sigusr1(self, signum: int, frame: object) -> None:
        """Handle SIGUSR1 signal by scheduling window raise on Qt thread."""
        # Schedule on Qt event loop since we're in a signal handler
        QTimer.singleShot(0, self._raise_window)

    def _raise_window(self) -> None:
        """Bring main window to front."""
        if self.main_window.isMinimized():
            self.main_window.showNormal()
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()

    async def start(self) -> None:
        """Start the application and connect to daemon."""
        logger.info("Starting SafeShell GUI...")

        connected = await self.client.connect()
        self.tray.set_connected(connected)

        if connected:
            await self.client.start_receiving()
            logger.info("Connected to daemon, receiving events")
            self.main_window.add_status_message("Connected to daemon", "#81C784")
        else:
            logger.warning("Failed to connect to daemon")
            self.main_window.add_status_message(
                "Failed to connect to daemon", "#EF5350"
            )
            self.tray.show_notification(
                "SafeShell",
                "Could not connect to daemon. Is it running?",
            )

    async def stop(self) -> None:
        """Stop the application and disconnect."""
        logger.info("Stopping SafeShell GUI...")
        await self.client.disconnect()

        # Save window geometry
        geometry = self.main_window.saveGeometry()
        self.settings.main_window_geometry = bytes(geometry.data())
        self.settings.sync()

        # Clean up PID file
        with contextlib.suppress(FileNotFoundError):
            GUI_PID_PATH.unlink()

        self.main_window.close()

    def _on_event_received(self, message: dict[str, Any]) -> None:
        """Handle event from daemon (called from asyncio context).

        Uses QTimer.singleShot to safely schedule UI updates on Qt thread.
        Since qasync runs both asyncio and Qt on the same thread, this is
        safe and ensures the UI update happens on the next event loop iteration.
        """
        # Schedule UI update on next Qt event loop iteration
        QTimer.singleShot(0, lambda: self._process_event(message))

    @pyqtSlot(dict)
    def _process_event(self, message: dict[str, Any]) -> None:
        """Process event on the main Qt thread.

        Args:
            message: Event message dictionary - may be wrapped in {'type': 'event', 'event': {...}}
        """
        # Handle nested event structure from daemon
        if message.get("type") == "event" and "event" in message:
            message = message["event"]

        event_type = message.get("type", "")
        data = message.get("data", {})

        # Log to main window
        self.main_window.add_event(message)

        # Handle specific event types
        if event_type == EventType.APPROVAL_NEEDED.value:
            self._handle_approval_needed(data)
        elif event_type == EventType.APPROVAL_RESOLVED.value:
            self._handle_approval_resolved(data)

        # Update tray pending count
        self._update_pending_count()

    def _handle_approval_needed(self, data: dict[str, Any]) -> None:
        """Handle APPROVAL_NEEDED event by adding to main window."""
        approval_id = data.get("approval_id", "")
        command = data.get("command", "")
        reason = data.get("reason", "")
        plugin_name = data.get("plugin_name", "")

        if not approval_id:
            logger.warning("Received approval_needed without approval_id")
            return

        # Add to main window's approval section
        self.main_window.add_pending_approval(approval_id, command, reason, plugin_name)

        # Show system notification if enabled
        if self.settings.show_notifications:
            cmd_preview = command[:50] + "..." if len(command) > 50 else command
            self.tray.show_notification(
                "Approval Required",
                f"Command: {cmd_preview}",
            )

    def _handle_approval_resolved(self, data: dict[str, Any]) -> None:
        """Handle APPROVAL_RESOLVED event by removing from main window."""
        approval_id = data.get("approval_id", "")
        self.main_window.remove_pending_approval(approval_id)

    def _on_approval_approved(self, approval_id: str, remember: bool) -> None:
        """Handle approval from main window."""
        asyncio.ensure_future(self.client.approve(approval_id, remember=remember))

    def _on_approval_denied(self, approval_id: str, remember: bool) -> None:
        """Handle denial from main window."""
        asyncio.ensure_future(self.client.deny(approval_id, remember=remember))

    def _update_pending_count(self) -> None:
        """Update tray icon based on pending approval count."""
        count = len(self.main_window.approval_cards)
        self.tray.set_pending(count)

    def toggle_debug_window(self) -> None:
        """Toggle main window visibility."""
        if self.main_window.isVisible():
            self.main_window.hide()
        else:
            self.main_window.show()
            self.main_window.raise_()

    def show_settings(self) -> None:
        """Show the settings dialog (placeholder for future use)."""
        pass  # Settings dialog removed for simplicity

    def reconnect(self) -> None:
        """Reconnect to daemon."""

        async def do_reconnect() -> None:
            await self.client.disconnect()
            self.main_window.add_status_message("Reconnecting...", "#FFB74D")
            self.tray.set_status(TrayStatus.DISCONNECTED)
            await self.start()

        asyncio.ensure_future(do_reconnect())

    def quit(self) -> None:
        """Quit the application."""

        async def do_quit() -> None:
            await self.stop()
            self.qt_app.quit()

        asyncio.ensure_future(do_quit())


def run_gui() -> None:
    """Run the SafeShell GUI application.

    This is the main entry point for the GUI.
    Sets up Qt application with qasync for asyncio integration.
    """
    # Create Qt application first (required before using any Qt widgets)
    qt_app = QApplication(sys.argv)
    qt_app.setQuitOnLastWindowClosed(False)  # Keep running when windows close
    qt_app.setApplicationName("SafeShell")
    qt_app.setOrganizationName("SafeShell")

    # Check if system tray is available (must be after QApplication creation)
    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(
            None,
            "SafeShell",
            "System tray is not available on this system.\n"
            "The GUI requires system tray support.",
        )
        sys.exit(1)

    # Set up qasync event loop
    loop = qasync.QEventLoop(qt_app)
    asyncio.set_event_loop(loop)

    # Create and start our application
    gui_app = SafeShellGuiApp(qt_app)

    # Run the event loop
    with loop:
        loop.run_until_complete(gui_app.start())
        print("SafeShell GUI is running. Look for the tray icon.")
        print("Press Ctrl+C to quit, or right-click the tray icon → Quit")
        loop.run_forever()
