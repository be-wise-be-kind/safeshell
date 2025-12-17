"""
File: src/safeshell/gui/main_window.py
Purpose: Event log viewer window
Exports: MainWindow
Depends: PyQt6.QtWidgets, PyQt6.QtCore, PyQt6.QtGui
Overview: Window showing real-time event log from the SafeShell daemon
"""

import subprocess
from datetime import datetime
from pathlib import Path
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

    def _get_terminal_color(self, working_dir: str | None) -> str:
        """Get a consistent color for a given working directory."""
        if not working_dir:
            return TERMINAL_COLORS[0]
        # Hash the full path to get consistent color per directory
        return TERMINAL_COLORS[hash(working_dir) % len(TERMINAL_COLORS)]

    def _get_dir_name(self, working_dir: str | None) -> str:
        """Extract just the final directory name from a path."""
        if not working_dir:
            return ""
        return Path(working_dir).name

    def add_event(self, event: dict[str, Any]) -> None:
        """Add an event to the log display."""
        # Handle nested event structure from daemon
        if event.get("type") == "event" and "event" in event:
            event = event["event"]

        event_type = event.get("type", "")

        # Skip non-event messages (e.g., MonitorResponse with "success" field)
        if not event_type or event_type not in EVENT_COLORS:
            return

        # Skip verbose events unless verbose mode is enabled
        # command_received is verbose by default - only show approval-related events
        verbose_events = {"evaluation_started", "evaluation_completed", "command_received"}
        if event_type in verbose_events and not self.verbose_checkbox.isChecked():
            return

        timestamp_str = event.get("timestamp", "")
        data = event.get("data", {})

        # Parse timestamp (with milliseconds), convert UTC to local time
        try:
            if timestamp_str:
                dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                # Convert to local time for display
                local_dt = dt.astimezone()
                time_display = local_dt.strftime("%H:%M:%S.%f")[:-3]
            else:
                time_display = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        except (ValueError, TypeError):
            time_display = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        color = EVENT_COLORS.get(event_type, "#FFFFFF")

        # Extract terminal source info (PID and working directory)
        client_pid = data.get("client_pid")
        working_dir = data.get("working_dir")

        # Build the log line prefix with terminal source (color based on directory)
        if working_dir:
            terminal_color = self._get_terminal_color(working_dir)
            dir_name = self._get_dir_name(working_dir)
            source_prefix = f"[{client_pid}][{dir_name}] " if client_pid else f"[{dir_name}] "
            # Append source prefix with its own color first
            self._append_colored_text(source_prefix, terminal_color)
        elif client_pid is not None:
            # Fallback: just show PID if no working dir
            self._append_colored_text(f"[{client_pid}] ", TERMINAL_COLORS[0])

        # Format log line with timestamp and event details
        log_line = f"[{time_display}] {event_type.upper()}"
        if data:
            details = []
            if "command" in data:
                details.append(f"cmd={data['command']}")
            if "approved" in data:
                details.append("APPROVED" if data["approved"] else "DENIED")
            if "decision" in data:
                details.append(f"decision={data['decision']}")
            if "plugin_name" in data:
                details.append(f"rule={data['plugin_name']}")
            if "reason" in data and data["reason"]:
                reason = data["reason"]
                if len(reason) > 50:
                    reason = reason[:47] + "..."
                details.append(f"reason={reason}")
            if details:
                log_line += " | " + " | ".join(details)

        self._append_colored_text(log_line + "\n", color)

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
