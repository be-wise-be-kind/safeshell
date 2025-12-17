"""
File: src/safeshell/gui/main_window.py
Purpose: Event log viewer window
Exports: MainWindow
Depends: PyQt6.QtWidgets, PyQt6.QtCore, PyQt6.QtGui
Overview: Window showing real-time event log from the SafeShell daemon
"""

import subprocess
from datetime import datetime
from typing import Any

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from safeshell.rules.loader import GLOBAL_RULES_PATH

# Event type to color mapping
EVENT_COLORS: dict[str, str] = {
    "command_received": "#64B5F6",  # Light blue
    "evaluation_started": "#90CAF9",  # Lighter blue
    "evaluation_completed": "#81C784",  # Light green
    "approval_needed": "#FFB74D",  # Orange
    "approval_resolved": "#A5D6A7",  # Soft green
    "daemon_status": "#B0BEC5",  # Gray
}

# Color palette for terminal identification (by PID)
TERMINAL_COLORS: list[str] = [
    "#FF6B6B",  # Red
    "#4ECDC4",  # Teal
    "#FFE66D",  # Yellow
    "#95E1D3",  # Mint
    "#F38181",  # Coral
    "#AA96DA",  # Purple
    "#FCBAD3",  # Pink
    "#A8D8EA",  # Light blue
]


class MainWindow(QMainWindow):
    """SafeShell event log viewer window."""

    # Signals for toolbar actions (handled by app.py)
    edit_rules_clicked = pyqtSignal()
    reload_rules_clicked = pyqtSignal()
    toggle_enabled_clicked = pyqtSignal(bool)  # new_enabled_state

    def __init__(self) -> None:
        super().__init__()
        self._enabled = True  # Track enabled state for UI display
        self._pid_colors: dict[int, str] = {}  # Map PIDs to colors
        self._next_color_index = 0
        self._setup_window()
        self._setup_toolbar()
        self._setup_ui()

    def _setup_window(self) -> None:
        self.setWindowTitle("SafeShell Monitor")
        self.setMinimumSize(400, 200)
        self.resize(800, 600)

    def _setup_toolbar(self) -> None:
        """Set up the toolbar with control buttons."""
        toolbar = QToolBar("Controls")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Enable/Disable toggle button
        self.enable_btn = QPushButton("Enabled")
        self.enable_btn.setCheckable(True)
        self.enable_btn.setChecked(True)
        self._update_enable_button_style(True)
        self.enable_btn.clicked.connect(self._on_enable_toggle)
        toolbar.addWidget(self.enable_btn)

        toolbar.addSeparator()

        # Edit Rules button
        edit_rules_btn = QPushButton("Edit Rules")
        edit_rules_btn.setStyleSheet(
            "QPushButton { padding: 4px 12px; }" "QPushButton:hover { background-color: #555; }"
        )
        edit_rules_btn.clicked.connect(self._on_edit_rules)
        toolbar.addWidget(edit_rules_btn)

        # Reload Rules button
        reload_rules_btn = QPushButton("Reload Rules")
        reload_rules_btn.setStyleSheet(
            "QPushButton { padding: 4px 12px; }" "QPushButton:hover { background-color: #555; }"
        )
        reload_rules_btn.clicked.connect(self._on_reload_rules)
        toolbar.addWidget(reload_rules_btn)

        toolbar.addSeparator()

        # Verbose logging checkbox
        self.verbose_checkbox = QCheckBox("Verbose")
        self.verbose_checkbox.setToolTip("Show evaluation started/completed events")
        self.verbose_checkbox.setChecked(False)
        toolbar.addWidget(self.verbose_checkbox)

    def _update_enable_button_style(self, enabled: bool) -> None:
        """Update the enable button appearance based on state."""
        if enabled:
            self.enable_btn.setText("Enabled")
            self.enable_btn.setStyleSheet(
                "QPushButton { background-color: #4CAF50; color: white; padding: 4px 12px; "
                "font-weight: bold; border-radius: 4px; }"
                "QPushButton:hover { background-color: #45A049; }"
            )
        else:
            self.enable_btn.setText("Disabled")
            self.enable_btn.setStyleSheet(
                "QPushButton { background-color: #F44336; color: white; padding: 4px 12px; "
                "font-weight: bold; border-radius: 4px; }"
                "QPushButton:hover { background-color: #E53935; }"
            )

    def _on_enable_toggle(self) -> None:
        """Handle enable/disable button click."""
        new_state = not self._enabled
        self._enabled = new_state
        self._update_enable_button_style(new_state)
        self.enable_btn.setChecked(new_state)
        self.toggle_enabled_clicked.emit(new_state)

    def set_enabled_state(self, enabled: bool) -> None:
        """Set the enabled state (called from app when daemon confirms)."""
        self._enabled = enabled
        self._update_enable_button_style(enabled)
        self.enable_btn.setChecked(enabled)

    def _on_edit_rules(self) -> None:
        """Open the global rules file in the default editor."""
        try:
            subprocess.Popen(["xdg-open", str(GLOBAL_RULES_PATH)])  # noqa: S603, S607
        except Exception as e:
            self.add_status_message(f"Failed to open rules file: {e}", "#EF5350")

    def _on_reload_rules(self) -> None:
        """Emit signal to reload rules."""
        self.reload_rules_clicked.emit()

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)

        # Header
        log_header = QLabel("Event Log")
        log_header.setStyleSheet("font-weight: bold; font-size: 12px; color: #90CAF9;")
        layout.addWidget(log_header)

        # Event log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("monospace", 9))
        self.log_text.setStyleSheet(
            "background-color: #1E1E1E; color: #D4D4D4; padding: 8px; border-radius: 4px;"
        )
        layout.addWidget(self.log_text)

        # Bottom buttons
        btn_layout = QHBoxLayout()
        clear_log_btn = QPushButton("Clear Log")
        clear_log_btn.clicked.connect(self.clear_log)
        clear_log_btn.setMaximumWidth(100)
        btn_layout.addStretch()
        btn_layout.addWidget(clear_log_btn)
        layout.addLayout(btn_layout)

    def _get_terminal_color(self, pid: int) -> str:
        """Get a consistent color for a terminal PID."""
        if pid not in self._pid_colors:
            self._pid_colors[pid] = TERMINAL_COLORS[self._next_color_index % len(TERMINAL_COLORS)]
            self._next_color_index += 1
        return self._pid_colors[pid]

    def add_event(self, event: dict[str, Any]) -> None:
        """Add an event to the log."""
        event_type = event.get("type", "unknown")
        data = event.get("data", {})

        # Skip verbose events if verbose mode is off
        is_verbose_event = event_type in ("evaluation_started", "evaluation_completed")
        if is_verbose_event and not self.verbose_checkbox.isChecked():
            return

        # Format the event
        timestamp = datetime.now().strftime("%H:%M:%S")
        color = EVENT_COLORS.get(event_type, "#B0BEC5")

        # Get PID for terminal color coding
        pid = data.get("pid")
        terminal_indicator = ""
        if pid:
            terminal_color = self._get_terminal_color(pid)
            terminal_indicator = "[●] "  # Will be colored per-terminal

        # Build message based on event type
        if event_type == "command_received":
            command = data.get("command", "")
            message = f"{terminal_indicator}Command: {command}"
        elif event_type == "evaluation_started":
            command = data.get("command", "")
            message = f"{terminal_indicator}Evaluating: {command}"
        elif event_type == "evaluation_completed":
            decision = data.get("decision", "")
            command = data.get("command", "")
            message = f"{terminal_indicator}{decision.upper()}: {command}"
        elif event_type == "approval_needed":
            command = data.get("command", "")
            reason = data.get("reason", "")
            message = f"{terminal_indicator}⚠ APPROVAL NEEDED: {command}\n    Reason: {reason}"
        elif event_type == "approval_resolved":
            decision = data.get("decision", "")
            command = data.get("command", "")
            message = f"{terminal_indicator}✓ {decision.upper()}: {command}"
        else:
            message = f"{event_type}: {data}"

        # Add to log with color
        self._append_colored_text(f"[{timestamp}] ", "#666666")

        # Add terminal indicator with its color if present
        if pid and terminal_indicator:
            terminal_color = self._get_terminal_color(pid)
            self._append_colored_text("[●] ", terminal_color)
            message = message.replace(f"{terminal_indicator}", "")

        self._append_colored_text(f"{message}\n", color)

    def _append_colored_text(self, text: str, color: str) -> None:
        """Append colored text to the log."""
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        char_format = QTextCharFormat()
        char_format.setForeground(QColor(color))

        cursor.setCharFormat(char_format)
        cursor.insertText(text)
        self.log_text.setTextCursor(cursor)

        # Auto-scroll
        scrollbar = self.log_text.verticalScrollBar()
        if scrollbar:
            scrollbar.setValue(scrollbar.maximum())

    def clear_log(self) -> None:
        self.log_text.clear()

    def add_status_message(self, message: str, color: str = "#B0BEC5") -> None:
        time_display = datetime.now().strftime("%H:%M:%S")
        self._append_colored_text(f"[{time_display}] {message}\n", color)
