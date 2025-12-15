"""
File: src/safeshell/gui/tray.py
Purpose: System tray icon and menu for SafeShell
Exports: SafeShellTray
Depends: PyQt6.QtWidgets, PyQt6.QtGui
Overview: Provides system tray icon with status indication and context menu
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

if TYPE_CHECKING:
    from safeshell.gui.app import SafeShellGuiApp


class TrayStatus:
    """Enum-like class for tray icon status."""

    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    PENDING = "pending"


class SafeShellTray(QSystemTrayIcon):
    """System tray icon for SafeShell.

    Shows connection status and provides menu for:
    - Toggling debug log window
    - Opening settings
    - Reconnecting to daemon
    - Quitting the application
    """

    def __init__(self, app: SafeShellGuiApp) -> None:
        """Initialize the system tray icon.

        Args:
            app: Reference to the main application
        """
        super().__init__()
        self.app = app
        self._status = TrayStatus.DISCONNECTED
        self._pending_count = 0

        self._setup_icons()
        self._setup_menu()
        self._update_icon()

    def _setup_icons(self) -> None:
        """Set up icons for different states.

        Uses Qt's built-in style icons which are more reliable across platforms.
        """
        from PyQt6.QtGui import QIcon
        from PyQt6.QtWidgets import QStyle

        # Get the application style for standard icons
        style = self.app.qt_app.style()

        # Use Qt standard pixmap icons (more reliable than theme icons)
        if style:
            self._icons = {
                TrayStatus.DISCONNECTED: style.standardIcon(
                    QStyle.StandardPixmap.SP_MessageBoxCritical
                ),
                TrayStatus.CONNECTED: style.standardIcon(
                    QStyle.StandardPixmap.SP_DialogApplyButton
                ),
                TrayStatus.PENDING: style.standardIcon(QStyle.StandardPixmap.SP_MessageBoxWarning),
            }
        else:
            # Fallback to empty icons
            self._icons = {
                TrayStatus.DISCONNECTED: QIcon(),
                TrayStatus.CONNECTED: QIcon(),
                TrayStatus.PENDING: QIcon(),
            }

    def _setup_menu(self) -> None:
        """Set up the context menu."""
        self.menu = QMenu()

        # Debug log toggle
        self.debug_action = QAction("Show Debug Log", self.menu)
        self.debug_action.setCheckable(True)
        self.debug_action.triggered.connect(self._on_toggle_debug)
        self.menu.addAction(self.debug_action)

        self.menu.addSeparator()

        # Settings
        self.settings_action = QAction("Settings...", self.menu)
        self.settings_action.triggered.connect(self._on_settings)
        self.menu.addAction(self.settings_action)

        # Reconnect
        self.reconnect_action = QAction("Reconnect", self.menu)
        self.reconnect_action.triggered.connect(self._on_reconnect)
        self.menu.addAction(self.reconnect_action)

        self.menu.addSeparator()

        # Quit
        self.quit_action = QAction("Quit", self.menu)
        self.quit_action.triggered.connect(self._on_quit)
        self.menu.addAction(self.quit_action)

        self.setContextMenu(self.menu)

        # Connect tray activation (click/double-click)
        self.activated.connect(self._on_activated)

    def _update_icon(self) -> None:
        """Update icon and tooltip based on current status."""
        icon = self._icons.get(self._status, self._icons[TrayStatus.DISCONNECTED])
        self.setIcon(icon)

        if self._status == TrayStatus.DISCONNECTED:
            tooltip = "SafeShell - Disconnected"
        elif self._status == TrayStatus.PENDING:
            tooltip = f"SafeShell - {self._pending_count} pending approval(s)"
        else:
            tooltip = "SafeShell - Connected"

        self.setToolTip(tooltip)

    def set_status(self, status: str, pending_count: int = 0) -> None:
        """Update the tray status.

        Args:
            status: One of TrayStatus values
            pending_count: Number of pending approvals (for PENDING status)
        """
        self._status = status
        self._pending_count = pending_count
        self._update_icon()

    def set_connected(self, connected: bool) -> None:
        """Set connected/disconnected status.

        Args:
            connected: Whether connected to daemon
        """
        if connected:
            self.set_status(TrayStatus.CONNECTED)
        else:
            self.set_status(TrayStatus.DISCONNECTED)

    def set_pending(self, count: int) -> None:
        """Set pending approval count.

        Args:
            count: Number of pending approvals
        """
        if count > 0:
            self.set_status(TrayStatus.PENDING, count)
        else:
            self.set_status(TrayStatus.CONNECTED)

    def set_debug_checked(self, checked: bool) -> None:
        """Update the debug menu item checked state.

        Args:
            checked: Whether debug mode is enabled
        """
        self.debug_action.setChecked(checked)

    def show_notification(self, title: str, message: str) -> None:
        """Show a system notification.

        Args:
            title: Notification title
            message: Notification body text
        """
        if self.supportsMessages():
            self.showMessage(title, message, QSystemTrayIcon.MessageIcon.Warning, 5000)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon activation (click)."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Single click - could show/hide main window
            pass
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            # Double click - toggle debug window
            self._on_toggle_debug()

    def _on_toggle_debug(self) -> None:
        """Handle debug log toggle."""
        self.app.toggle_debug_window()

    def _on_settings(self) -> None:
        """Handle settings menu action."""
        self.app.show_settings()

    def _on_reconnect(self) -> None:
        """Handle reconnect menu action."""
        self.app.reconnect()

    def _on_quit(self) -> None:
        """Handle quit menu action."""
        self.app.quit()
