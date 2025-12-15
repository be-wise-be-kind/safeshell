"""
File: src/safeshell/gui/debug_window.py
Purpose: Debug log window showing real-time daemon events
Exports: DebugWindow
Depends: PyQt6.QtWidgets, PyQt6.QtCore, PyQt6.QtGui
Overview: Optional window that displays color-coded, timestamped event log
"""

from datetime import datetime
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

# Event type to color mapping
EVENT_COLORS: dict[str, str] = {
    "command_received": "#64B5F6",  # Light blue
    "evaluation_started": "#90CAF9",  # Lighter blue
    "evaluation_completed": "#81C784",  # Light green
    "approval_needed": "#FFB74D",  # Orange
    "approval_resolved": "#A5D6A7",  # Soft green
    "daemon_status": "#B0BEC5",  # Gray
}


class DebugWindow(QMainWindow):
    """Window displaying real-time event log from the daemon.

    Shows timestamped, color-coded events for debugging purposes.
    Can be toggled via settings or tray menu.
    """

    def __init__(self, parent: object = None) -> None:
        """Initialize the debug window.

        Args:
            parent: Optional parent widget
        """
        super().__init__(parent)  # type: ignore[arg-type]
        self._setup_window()
        self._setup_ui()

    def _setup_window(self) -> None:
        """Configure window properties."""
        self.setWindowTitle("SafeShell Monitor")
        self.setMinimumSize(600, 400)
        self.resize(800, 500)

    def _setup_ui(self) -> None:
        """Set up the window UI components."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Log display
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("monospace", 9))
        self.log_text.setStyleSheet(
            "background-color: #1E1E1E; color: #D4D4D4; padding: 8px;"
        )
        layout.addWidget(self.log_text)

        # Clear button
        clear_btn = QPushButton("Clear Log")
        clear_btn.clicked.connect(self.clear_log)
        clear_btn.setMaximumWidth(100)
        layout.addWidget(clear_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def add_event(self, event: dict[str, Any]) -> None:
        """Add an event to the log display.

        Args:
            event: Event dictionary - may be wrapped in {'type': 'event', 'event': {...}}
        """
        # Handle nested event structure from daemon
        if event.get("type") == "event" and "event" in event:
            event = event["event"]

        event_type = event.get("type", "unknown")
        timestamp_str = event.get("timestamp", "")
        data = event.get("data", {})

        # Parse timestamp or use current time
        try:
            if timestamp_str:
                # Handle ISO format timestamps
                dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                time_display = dt.strftime("%H:%M:%S")
            else:
                time_display = datetime.now().strftime("%H:%M:%S")
        except (ValueError, TypeError):
            time_display = datetime.now().strftime("%H:%M:%S")

        # Get color for this event type
        color = EVENT_COLORS.get(event_type, "#FFFFFF")

        # Format the log line with full details
        log_line = f"[{time_display}] {event_type.upper()}"
        if data:
            # Show all relevant data
            details = []
            if "command" in data:
                details.append(f"cmd={data['command']}")
            if "decision" in data:
                details.append(f"decision={data['decision']}")
            if "approved" in data:
                details.append(f"approved={data['approved']}")
            if "plugin_name" in data:
                details.append(f"rule={data['plugin_name']}")
            if "reason" in data:
                details.append(f"reason={data['reason']}")
            if "approval_id" in data:
                details.append(f"id={data['approval_id'][:8]}...")
            if "working_dir" in data:
                details.append(f"dir={data['working_dir']}")
            if details:
                log_line += " | " + " | ".join(details)

        # Append to log with color
        self._append_colored_text(log_line + "\n", color)

        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        if scrollbar:
            scrollbar.setValue(scrollbar.maximum())

    def _append_colored_text(self, text: str, color: str) -> None:
        """Append colored text to the log.

        Args:
            text: Text to append
            color: Hex color code (e.g., "#FF0000")
        """
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        char_format = QTextCharFormat()
        char_format.setForeground(QColor(color))
        cursor.setCharFormat(char_format)
        cursor.insertText(text)

        self.log_text.setTextCursor(cursor)

    def clear_log(self) -> None:
        """Clear all log entries."""
        self.log_text.clear()

    def add_status_message(self, message: str, color: str = "#B0BEC5") -> None:
        """Add a status message (not an event).

        Args:
            message: Status message to display
            color: Color for the message
        """
        time_display = datetime.now().strftime("%H:%M:%S")
        self._append_colored_text(f"[{time_display}] {message}\n", color)
