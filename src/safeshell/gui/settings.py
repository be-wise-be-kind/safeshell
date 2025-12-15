"""
File: src/safeshell/gui/settings.py
Purpose: Settings persistence for GUI using QSettings
Exports: GuiSettings
Depends: PyQt6.QtCore
Overview: Wraps QSettings for storing GUI preferences like debug mode, window geometry
"""

from PyQt6.QtCore import QSettings


class GuiSettings:
    """Wrapper around QSettings for GUI preferences.

    Settings are stored in:
    - Linux: ~/.config/SafeShell/GUI.conf
    - macOS: ~/Library/Preferences/com.safeshell.GUI.plist
    - Windows: Registry under HKEY_CURRENT_USER/Software/SafeShell/GUI
    """

    def __init__(self) -> None:
        """Initialize settings with SafeShell/GUI scope."""
        self._settings = QSettings("SafeShell", "GUI")

    @property
    def debug_mode(self) -> bool:
        """Whether debug mode is enabled (shows debug log window)."""
        value = self._settings.value("debug_mode", False)
        # QSettings may return string "true"/"false" on some platforms
        if isinstance(value, str):
            return value.lower() == "true"
        return bool(value)

    @debug_mode.setter
    def debug_mode(self, value: bool) -> None:
        """Set debug mode preference."""
        self._settings.setValue("debug_mode", value)

    @property
    def show_notifications(self) -> bool:
        """Whether to show system notifications for new approvals."""
        value = self._settings.value("show_notifications", True)
        if isinstance(value, str):
            return value.lower() == "true"
        return bool(value)

    @show_notifications.setter
    def show_notifications(self, value: bool) -> None:
        """Set notification preference."""
        self._settings.setValue("show_notifications", value)

    @property
    def main_window_geometry(self) -> bytes | None:
        """Saved geometry for the main/debug window."""
        value = self._settings.value("main_window_geometry")
        if isinstance(value, bytes):
            return value
        return None

    @main_window_geometry.setter
    def main_window_geometry(self, value: bytes) -> None:
        """Save main window geometry."""
        self._settings.setValue("main_window_geometry", value)

    def sync(self) -> None:
        """Force settings to be written to storage."""
        self._settings.sync()
