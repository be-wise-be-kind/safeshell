"""
File: src/safeshell/gui/approval_dialog.py
Purpose: Popup dialog for command approval requests
Exports: ApprovalDialog
Depends: PyQt6.QtWidgets, PyQt6.QtCore
Overview: Modal dialog that appears when a command requires user approval
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QDialog,
    QGridLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

# UI dimension and spacing constants
_MIN_DIALOG_WIDTH = 500
_MIN_DIALOG_HEIGHT = 300
_LAYOUT_SPACING = 12
_BUTTON_SPACING = 8
_COMMAND_MAX_HEIGHT = 100
_MONOSPACE_FONT_SIZE = 10


class ApprovalDialog(QDialog):
    """Dialog for approving or denying a command.

    Emits signals when the user makes a decision:
    - approved(approval_id, remember): User approved the command
    - denied(approval_id, reason, remember): User denied the command
    """

    # Signals emitted when user makes a decision
    approved = pyqtSignal(str, bool)  # approval_id, remember
    denied = pyqtSignal(str, str, bool)  # approval_id, reason, remember

    def __init__(
        self,
        approval_id: str,
        command: str,
        reason: str,
        plugin_name: str,
        parent: object = None,
    ) -> None:
        """Initialize the approval dialog.

        Args:
            approval_id: Unique ID for this approval request
            command: The command awaiting approval
            reason: Why approval is required
            plugin_name: Name of the rule that triggered approval
            parent: Optional parent widget
        """
        super().__init__(parent)  # type: ignore[arg-type]
        self.approval_id = approval_id

        self._setup_window()
        self._setup_ui(command, reason, plugin_name)
        self._setup_shortcuts()

    def _setup_window(self) -> None:
        """Configure window properties."""
        self.setWindowTitle("SafeShell - Approval Required")
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setMinimumWidth(_MIN_DIALOG_WIDTH)
        self.setMinimumHeight(_MIN_DIALOG_HEIGHT)

    def _setup_ui(self, command: str, reason: str, plugin_name: str) -> None:
        """Set up the dialog UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(_LAYOUT_SPACING)

        # Header
        header = QLabel("A command requires your approval:")
        header.setStyleSheet("font-size: 14px; font-weight: bold; color: #E65100;")
        layout.addWidget(header)

        # Command display (read-only, scrollable for long commands)
        cmd_label = QLabel("Command:")
        cmd_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(cmd_label)

        self.cmd_text = QTextEdit()
        self.cmd_text.setPlainText(command)
        self.cmd_text.setReadOnly(True)
        self.cmd_text.setMaximumHeight(_COMMAND_MAX_HEIGHT)
        self.cmd_text.setFont(QFont("monospace", _MONOSPACE_FONT_SIZE))
        self.cmd_text.setStyleSheet(
            "background-color: #2D2D2D; color: #FFFFFF; padding: 8px; border-radius: 4px;"
        )
        layout.addWidget(self.cmd_text)

        # Reason and rule
        reason_label = QLabel(f"<b>Reason:</b> {reason}")
        reason_label.setWordWrap(True)
        layout.addWidget(reason_label)

        plugin_label = QLabel(f"<b>Rule:</b> {plugin_name}")
        layout.addWidget(plugin_label)

        # Spacer
        layout.addSpacing(_LAYOUT_SPACING)

        # Button grid (2x2)
        btn_layout = QGridLayout()
        btn_layout.setSpacing(_BUTTON_SPACING)

        # Approve buttons (green variants)
        self.approve_btn = QPushButton("Approve (A)")
        self.approve_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; padding: 10px 20px; "
            "border: none; border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background-color: #45A049; }"
            "QPushButton:pressed { background-color: #3D8B40; }"
        )

        self.approve_remember_btn = QPushButton("Approve, Remember")
        self.approve_remember_btn.setStyleSheet(
            "QPushButton { background-color: #388E3C; color: white; padding: 10px 20px; "
            "border: none; border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background-color: #2E7D32; }"
            "QPushButton:pressed { background-color: #1B5E20; }"
        )

        # Deny buttons (red variants)
        self.deny_btn = QPushButton("Deny (D)")
        self.deny_btn.setStyleSheet(
            "QPushButton { background-color: #F44336; color: white; padding: 10px 20px; "
            "border: none; border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background-color: #E53935; }"
            "QPushButton:pressed { background-color: #C62828; }"
        )

        self.deny_remember_btn = QPushButton("Deny, Remember")
        self.deny_remember_btn.setStyleSheet(
            "QPushButton { background-color: #D32F2F; color: white; padding: 10px 20px; "
            "border: none; border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background-color: #C62828; }"
            "QPushButton:pressed { background-color: #B71C1C; }"
        )

        btn_layout.addWidget(self.approve_btn, 0, 0)
        btn_layout.addWidget(self.approve_remember_btn, 0, 1)
        btn_layout.addWidget(self.deny_btn, 1, 0)
        btn_layout.addWidget(self.deny_remember_btn, 1, 1)

        layout.addLayout(btn_layout)

        # Connect buttons
        self.approve_btn.clicked.connect(lambda: self._approve(remember=False))
        self.approve_remember_btn.clicked.connect(lambda: self._approve(remember=True))
        self.deny_btn.clicked.connect(lambda: self._deny(remember=False))
        self.deny_remember_btn.clicked.connect(lambda: self._deny(remember=True))

    def _setup_shortcuts(self) -> None:
        """Set up keyboard shortcuts."""
        # A for Approve
        approve_shortcut = QShortcut(QKeySequence("A"), self)
        approve_shortcut.activated.connect(lambda: self._approve(remember=False))

        # D for Deny
        deny_shortcut = QShortcut(QKeySequence("D"), self)
        deny_shortcut.activated.connect(lambda: self._deny(remember=False))

    def _approve(self, remember: bool) -> None:
        """Handle approval action."""
        self.approved.emit(self.approval_id, remember)
        self.accept()

    def _deny(self, remember: bool) -> None:
        """Handle denial action."""
        # For now, no reason input - could add a QLineEdit later
        self.denied.emit(self.approval_id, "", remember)
        self.accept()

    def bring_to_front(self) -> None:
        """Bring this dialog to the front and focus it."""
        self.raise_()
        self.activateWindow()
        self.setFocus()
