"""
File: src/safeshell/gui/main_window.py
Purpose: Unified main window combining event log and approval handling
Exports: MainWindow
Depends: PyQt6.QtWidgets, PyQt6.QtCore, PyQt6.QtGui
Overview: Single window with event log at top and pending approvals at bottom
"""

from datetime import datetime
from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSplitter,
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


class ApprovalCard(QFrame):
    """A card widget for a single pending approval."""

    approved = pyqtSignal(str, bool)  # approval_id, remember
    denied = pyqtSignal(str, bool)  # approval_id, remember

    def __init__(
        self, approval_id: str, command: str, reason: str, plugin_name: str
    ) -> None:
        super().__init__()
        self.approval_id = approval_id
        self._setup_ui(command, reason, plugin_name)

    def _setup_ui(self, command: str, reason: str, plugin_name: str) -> None:
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setStyleSheet(
            "ApprovalCard { background-color: #2D2D2D; border: 1px solid #FF9800; "
            "border-radius: 8px; padding: 8px; margin: 4px; }"
        )

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Header with rule name
        header = QLabel(f"⚠ Approval Required - {plugin_name}")
        header.setStyleSheet("color: #FF9800; font-weight: bold; font-size: 13px;")
        layout.addWidget(header)

        # Command (monospace, scrollable if long)
        cmd_display = QTextEdit()
        cmd_display.setPlainText(command)
        cmd_display.setReadOnly(True)
        cmd_display.setFont(QFont("monospace", 10))
        cmd_display.setMaximumHeight(60)
        cmd_display.setStyleSheet(
            "background-color: #1E1E1E; color: #FFFFFF; border: none; padding: 4px;"
        )
        layout.addWidget(cmd_display)

        # Reason
        reason_label = QLabel(f"Reason: {reason}")
        reason_label.setWordWrap(True)
        reason_label.setStyleSheet("color: #B0BEC5; font-size: 11px;")
        layout.addWidget(reason_label)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        approve_btn = QPushButton("Approve")
        approve_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; padding: 8px 16px; "
            "border: none; border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background-color: #45A049; }"
        )
        approve_btn.clicked.connect(lambda: self.approved.emit(self.approval_id, False))

        approve_remember_btn = QPushButton("Approve + Remember")
        approve_remember_btn.setStyleSheet(
            "QPushButton { background-color: #388E3C; color: white; padding: 8px 16px; "
            "border: none; border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background-color: #2E7D32; }"
        )
        approve_remember_btn.clicked.connect(
            lambda: self.approved.emit(self.approval_id, True)
        )

        deny_btn = QPushButton("Deny")
        deny_btn.setStyleSheet(
            "QPushButton { background-color: #F44336; color: white; padding: 8px 16px; "
            "border: none; border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background-color: #E53935; }"
        )
        deny_btn.clicked.connect(lambda: self.denied.emit(self.approval_id, False))

        deny_remember_btn = QPushButton("Deny + Remember")
        deny_remember_btn.setStyleSheet(
            "QPushButton { background-color: #D32F2F; color: white; padding: 8px 16px; "
            "border: none; border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background-color: #C62828; }"
        )
        deny_remember_btn.clicked.connect(
            lambda: self.denied.emit(self.approval_id, True)
        )

        btn_layout.addWidget(approve_btn)
        btn_layout.addWidget(approve_remember_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(deny_btn)
        btn_layout.addWidget(deny_remember_btn)

        layout.addLayout(btn_layout)


class MainWindow(QMainWindow):
    """Unified SafeShell monitor window with event log and approvals."""

    # Signals for approval actions
    approval_approved = pyqtSignal(str, bool)  # approval_id, remember
    approval_denied = pyqtSignal(str, bool)  # approval_id, remember

    def __init__(self) -> None:
        super().__init__()
        self.approval_cards: dict[str, ApprovalCard] = {}
        self._setup_window()
        self._setup_ui()

    def _setup_window(self) -> None:
        self.setWindowTitle("SafeShell Monitor")
        self.setMinimumSize(800, 700)
        self.resize(1000, 800)

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)

        # Splitter for resizable sections
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Top: Event log
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        log_layout.setContentsMargins(0, 0, 0, 0)

        log_header = QLabel("Event Log")
        log_header.setStyleSheet("font-weight: bold; font-size: 12px; color: #90CAF9;")
        log_layout.addWidget(log_header)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("monospace", 9))
        self.log_text.setStyleSheet(
            "background-color: #1E1E1E; color: #D4D4D4; padding: 8px; border-radius: 4px;"
        )
        log_layout.addWidget(self.log_text)

        splitter.addWidget(log_widget)

        # Bottom: Approvals section
        approvals_widget = QWidget()
        approvals_layout = QVBoxLayout(approvals_widget)
        approvals_layout.setContentsMargins(0, 0, 0, 0)

        self.approvals_header = QLabel("Pending Approvals")
        self.approvals_header.setStyleSheet(
            "font-weight: bold; font-size: 12px; color: #FF9800;"
        )
        approvals_layout.addWidget(self.approvals_header)

        # Scrollable area for approval cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background-color: transparent; }"
        )

        self.approvals_container = QWidget()
        self.approvals_list_layout = QVBoxLayout(self.approvals_container)
        self.approvals_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.approvals_list_layout.setSpacing(8)

        # Placeholder when no approvals
        self.no_approvals_label = QLabel("No pending approvals")
        self.no_approvals_label.setStyleSheet("color: #666; padding: 20px;")
        self.no_approvals_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.approvals_list_layout.addWidget(self.no_approvals_label)

        scroll.setWidget(self.approvals_container)
        approvals_layout.addWidget(scroll)

        splitter.addWidget(approvals_widget)

        # Set initial sizes (60% log, 40% approvals)
        splitter.setSizes([450, 350])

        layout.addWidget(splitter)

        # Bottom buttons
        btn_layout = QHBoxLayout()
        clear_btn = QPushButton("Clear Log")
        clear_btn.clicked.connect(self.clear_log)
        clear_btn.setMaximumWidth(100)
        btn_layout.addStretch()
        btn_layout.addWidget(clear_btn)
        layout.addLayout(btn_layout)

    def add_event(self, event: dict[str, Any]) -> None:
        """Add an event to the log display."""
        # Handle nested event structure from daemon
        if event.get("type") == "event" and "event" in event:
            event = event["event"]

        event_type = event.get("type", "unknown")
        timestamp_str = event.get("timestamp", "")
        data = event.get("data", {})

        # Parse timestamp
        try:
            if timestamp_str:
                dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                time_display = dt.strftime("%H:%M:%S")
            else:
                time_display = datetime.now().strftime("%H:%M:%S")
        except (ValueError, TypeError):
            time_display = datetime.now().strftime("%H:%M:%S")

        color = EVENT_COLORS.get(event_type, "#FFFFFF")

        # Format log line with details
        log_line = f"[{time_display}] {event_type.upper()}"
        if data:
            details = []
            if "command" in data:
                details.append(f"cmd={data['command']}")
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

    def add_pending_approval(
        self, approval_id: str, command: str, reason: str, plugin_name: str
    ) -> None:
        """Add a pending approval to the approvals section."""
        if approval_id in self.approval_cards:
            return  # Already exists

        # Hide "no approvals" label
        self.no_approvals_label.hide()

        # Create card
        card = ApprovalCard(approval_id, command, reason, plugin_name)
        card.approved.connect(self._on_card_approved)
        card.denied.connect(self._on_card_denied)

        self.approval_cards[approval_id] = card
        self.approvals_list_layout.insertWidget(0, card)  # Add at top

        self._update_approvals_header()

        # Raise window to get attention
        if self.isMinimized():
            self.showNormal()
        self.show()
        self.raise_()
        self.activateWindow()

    def remove_pending_approval(self, approval_id: str) -> None:
        """Remove a pending approval."""
        if approval_id not in self.approval_cards:
            return

        card = self.approval_cards.pop(approval_id)
        self.approvals_list_layout.removeWidget(card)
        card.deleteLater()

        self._update_approvals_header()

        # Show placeholder if no approvals left
        if not self.approval_cards:
            self.no_approvals_label.show()

    def _update_approvals_header(self) -> None:
        count = len(self.approval_cards)
        if count == 0:
            self.approvals_header.setText("Pending Approvals")
        else:
            self.approvals_header.setText(f"Pending Approvals ({count})")

    def _on_card_approved(self, approval_id: str, remember: bool) -> None:
        self.approval_approved.emit(approval_id, remember)

    def _on_card_denied(self, approval_id: str, remember: bool) -> None:
        self.approval_denied.emit(approval_id, remember)
