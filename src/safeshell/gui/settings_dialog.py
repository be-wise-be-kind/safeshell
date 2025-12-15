"""
File: src/safeshell/gui/settings_dialog.py
Purpose: Settings dialog for GUI preferences
Exports: SettingsDialog
Depends: PyQt6.QtWidgets, safeshell.gui.settings
Overview: Dialog for toggling debug mode, notifications, and other preferences
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QVBoxLayout,
)

from safeshell.gui.settings import GuiSettings


class SettingsDialog(QDialog):
    """Dialog for editing GUI preferences.

    Emits settings_changed signal when OK is clicked and settings differ.
    """

    # Signal emitted when settings are saved
    settings_changed = pyqtSignal()

    def __init__(self, settings: GuiSettings, parent: object = None) -> None:
        """Initialize the settings dialog.

        Args:
            settings: GuiSettings instance to read/write
            parent: Optional parent widget
        """
        super().__init__(parent)  # type: ignore[arg-type]
        self.settings = settings
        self._setup_window()
        self._setup_ui()
        self._load_settings()

    def _setup_window(self) -> None:
        """Configure window properties."""
        self.setWindowTitle("SafeShell - Settings")
        self.setMinimumWidth(350)

    def _setup_ui(self) -> None:
        """Set up the dialog UI components."""
        layout = QVBoxLayout(self)

        # Display group
        display_group = QGroupBox("Display")
        display_layout = QFormLayout(display_group)

        self.debug_checkbox = QCheckBox("Show debug log window")
        self.debug_checkbox.setToolTip("When enabled, a debug window shows real-time daemon events")
        display_layout.addRow(self.debug_checkbox)

        layout.addWidget(display_group)

        # Notifications group
        notif_group = QGroupBox("Notifications")
        notif_layout = QFormLayout(notif_group)

        self.notifications_checkbox = QCheckBox("Show system notifications")
        self.notifications_checkbox.setToolTip(
            "Show desktop notifications when approval is required"
        )
        notif_layout.addRow(self.notifications_checkbox)

        layout.addWidget(notif_group)

        # Spacer
        layout.addStretch()

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._save_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_settings(self) -> None:
        """Load current settings into UI."""
        self.debug_checkbox.setChecked(self.settings.debug_mode)
        self.notifications_checkbox.setChecked(self.settings.show_notifications)

    def _save_and_accept(self) -> None:
        """Save settings and close dialog."""
        changed = False

        # Check and save debug mode
        new_debug = self.debug_checkbox.isChecked()
        if new_debug != self.settings.debug_mode:
            self.settings.debug_mode = new_debug
            changed = True

        # Check and save notifications
        new_notif = self.notifications_checkbox.isChecked()
        if new_notif != self.settings.show_notifications:
            self.settings.show_notifications = new_notif
            changed = True

        self.settings.sync()

        if changed:
            self.settings_changed.emit()

        self.accept()
