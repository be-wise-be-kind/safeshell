"""
File: src/safeshell/monitor/widgets.py
Purpose: Custom Textual widgets for the Monitor TUI
Exports: DebugPane, HistoryPane, ApprovalPane, HelpPanel, CommandHistoryItem
Depends: textual, datetime, safeshell.events.types
Overview: Provides the three-pane layout widgets for monitoring SafeShell daemon activity
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.message import Message
from textual.widgets import Button, Input, RichLog, Static


class CommandHistoryItem(BaseModel):
    """Represents a command in the history."""

    command: str = Field(description="The command string")
    timestamp: datetime = Field(description="When the command was received")
    status: str = Field(default="pending", description="Status: pending, allowed, blocked, waiting")
    decision: str | None = Field(default=None, description="The decision made")
    reason: str | None = Field(default=None, description="Reason for decision")
    approval_id: str | None = Field(default=None, description="Approval ID if waiting")


class HelpPanel(Static):
    """Help panel showing keyboard shortcuts and usage instructions.

    Toggle visibility with 'h' or '?' key.
    """

    def compose(self) -> ComposeResult:
        """Compose the help panel content."""
        yield Static("SafeShell Monitor Help", classes="help-title")

        # Keyboard shortcuts section
        yield Static("Keyboard Shortcuts", classes="help-section-title")
        yield Vertical(
            Static("[yellow]a[/yellow]  Approve current command", classes="help-shortcut"),
            Static("[yellow]d[/yellow]  Deny current command", classes="help-shortcut"),
            Static("[yellow]r[/yellow]  Reconnect to daemon", classes="help-shortcut"),
            Static("[yellow]h[/yellow]  Toggle this help panel", classes="help-shortcut"),
            Static("[yellow]q[/yellow]  Quit monitor", classes="help-shortcut"),
            classes="help-section",
        )

        # Approval workflow section
        yield Static("Approval Workflow", classes="help-section-title")
        yield Vertical(
            Static(
                "When a command requires approval, it will\n"
                "appear in the approval pane. You can:",
                classes="help-description",
            ),
            Static(""),
            Static(
                "[green]Approve[/green] - Allow command to run",
                classes="help-shortcut",
            ),
            Static(
                "[green]Yes, Remember[/green] - Allow and remember\n"
                "  for this session",
                classes="help-shortcut",
            ),
            Static(
                "[red]Deny[/red] - Block command execution",
                classes="help-shortcut",
            ),
            Static(
                "[red]No, Remember[/red] - Block and remember\n"
                "  for this session",
                classes="help-shortcut",
            ),
            classes="help-section",
        )

        # Status icons section
        yield Static("Status Icons", classes="help-section-title")
        yield Vertical(
            Static("[green]\u2713[/green]  Command allowed", classes="help-shortcut"),
            Static("[red]\u2717[/red]  Command blocked", classes="help-shortcut"),
            Static("[yellow]\u23f3[/yellow]  Awaiting approval", classes="help-shortcut"),
            classes="help-section",
        )

        # Tips section
        yield Static(
            "Tip: Use --debug flag to show event log\n"
            "and command history panes.\n\n"
            "Press [yellow]h[/yellow] to close this panel.",
            classes="help-tip",
        )


class DebugPane(Static):
    """Debug log pane showing daemon events.

    Displays color-coded log entries from the daemon event stream.
    Shows command received, evaluation, and approval events.
    """

    DEFAULT_CSS = """
    DebugPane {
        height: 100%;
    }

    DebugPane > RichLog {
        height: 100%;
    }

    DebugPane .pane-title {
        text-style: bold;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the debug pane."""
        yield Static("Debug Log", classes="pane-title")
        yield RichLog(id="debug-log", highlight=True, markup=True, wrap=True)

    def add_log(self, message: str, level: str = "info") -> None:
        """Add a log message to the pane.

        Args:
            message: Log message to display
            level: Log level (info, warning, error, debug, success)
        """
        log_widget = self.query_one("#debug-log", RichLog)

        color_map = {
            "info": "white",
            "warning": "yellow",
            "error": "red",
            "debug": "dim white",
            "success": "green",
        }
        color = color_map.get(level, "white")

        timestamp = datetime.now().strftime("%H:%M:%S")
        log_widget.write(f"[dim]{timestamp}[/dim] [{color}]{message}[/{color}]")


class HistoryPane(Static):
    """Command history pane showing recent commands and their status.

    Displays commands with status icons:
    - Pending (hourglass)
    - Allowed (checkmark)
    - Blocked (x)
    - Waiting approval (hourglass)
    """

    DEFAULT_CSS = """
    HistoryPane {
        height: 100%;
    }

    HistoryPane > ScrollableContainer {
        height: 100%;
    }

    HistoryPane .pane-title {
        text-style: bold;
    }

    HistoryPane .history-item {
        margin-bottom: 1;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the history pane."""
        super().__init__(**kwargs)
        self._history: list[CommandHistoryItem] = []

    def compose(self) -> ComposeResult:
        """Compose the history pane."""
        yield Static("Command History", classes="pane-title")
        yield ScrollableContainer(id="history-container")

    def add_command(self, item: CommandHistoryItem) -> None:
        """Add a command to the history.

        Args:
            item: Command history item to add
        """
        self._history.insert(0, item)
        # Keep only last 50 items
        if len(self._history) > 50:
            self._history = self._history[:50]
        self._render_history()

    def update_command(
        self,
        command: str,
        status: str,
        decision: str | None = None,
        reason: str | None = None,
        approval_id: str | None = None,
    ) -> None:
        """Update the status of a command in history.

        Args:
            command: The command to update
            status: New status
            decision: The decision made
            reason: Reason for decision
            approval_id: Approval ID if applicable
        """
        for item in self._history:
            if item.command == command:
                item.status = status
                if decision:
                    item.decision = decision
                if reason:
                    item.reason = reason
                if approval_id:
                    item.approval_id = approval_id
                break
        self._render_history()

    def _render_history(self) -> None:
        """Re-render the history list."""
        container = self.query_one("#history-container", ScrollableContainer)
        container.remove_children()

        # Status icons - using Unicode symbols for consistency
        status_icons = {
            "pending": ("\u23f3", "cmd-pending"),  # Hourglass
            "allowed": ("\u2713", "cmd-allowed"),  # Check mark
            "blocked": ("\u2717", "cmd-blocked"),  # X mark
            "waiting": ("\u23f3", "cmd-waiting"),  # Hourglass
        }

        for item in self._history[:20]:  # Show last 20
            icon, css_class = status_icons.get(item.status, ("?", "cmd-pending"))
            time_str = item.timestamp.strftime("%H:%M:%S")
            cmd_short = item.command[:40] + "..." if len(item.command) > 40 else item.command

            text = f"[{icon}] {time_str} {cmd_short}"
            if item.reason:
                text += f"\n    [dim]{item.reason[:50]}[/dim]"

            container.mount(Static(text, classes=f"history-item {css_class}"))


class ApprovalPane(Static):
    """Approval pane for handling pending approvals.

    Shows pending approval requests with Approve/Deny buttons
    and an optional reason input field for denials.
    Buttons are placed at the bottom for better vertical layout.
    """

    DEFAULT_CSS = """
    ApprovalPane {
        height: 100%;
    }

    ApprovalPane .pane-title {
        text-style: bold;
    }

    ApprovalPane .approval-command {
        padding: 1;
        margin: 1 0;
        max-height: 6;
        overflow: auto;
    }

    ApprovalPane .approval-reason {
        margin: 1 0;
    }

    ApprovalPane #button-row {
        dock: bottom;
        layout: horizontal;
        height: 5;
        width: 100%;
    }

    ApprovalPane Button {
        width: 1fr;
        height: 100%;
        margin: 0 1;
        content-align: center middle;
    }

    ApprovalPane Button:disabled {
        opacity: 0.3;
    }

    ApprovalPane #denial-reason {
        dock: bottom;
        margin: 1 0;
        height: 3;
    }

    ApprovalPane .no-approvals {
        text-style: italic;
    }
    """

    class ApprovalAction(Message):
        """Message sent when an approval action is taken."""

        def __init__(
            self,
            approved: bool,
            approval_id: str,
            reason: str | None = None,
            remember: bool = False,
        ) -> None:
            """Initialize the approval action message.

            Args:
                approved: Whether the command was approved
                approval_id: The approval ID
                reason: Reason for denial (if denied)
                remember: Whether to remember this decision for session
            """
            super().__init__()
            self.approved = approved
            self.approval_id = approval_id
            self.reason = reason
            self.remember = remember

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the approval pane."""
        super().__init__(**kwargs)
        self._pending_approvals: list[dict[str, Any]] = []
        self._current_approval: dict[str, Any] | None = None

    def compose(self) -> ComposeResult:
        """Compose the approval pane."""
        yield Static("Pending Approvals", classes="pane-title")
        yield Static("No pending approvals", id="approval-status", classes="no-approvals")
        yield Static("", id="approval-command", classes="approval-command")
        yield Static("", id="approval-reason", classes="approval-reason")
        yield Static("", id="approval-plugin", classes="approval-plugin")
        yield Input(placeholder="Reason for denial (optional)", id="denial-reason")
        yield Horizontal(
            Button("Approve (a)", id="approve-btn", variant="success"),
            Button("Yes, Remember", id="approve-remember-btn", variant="success"),
            Button("Deny (d)", id="deny-btn", variant="error"),
            Button("No, Remember", id="deny-remember-btn", variant="error"),
            id="button-row",
        )

    def on_mount(self) -> None:
        """Handle mount event - initialize display state."""
        self._update_display()

    def add_pending_approval(self, approval: dict[str, Any]) -> None:
        """Add a pending approval request.

        Args:
            approval: Approval data from the daemon
        """
        self._pending_approvals.append(approval)
        if self._current_approval is None:
            self._current_approval = approval
        self._update_display()

    def remove_pending_approval(self, approval_id: str) -> None:
        """Remove a pending approval.

        Args:
            approval_id: ID of the approval to remove
        """
        self._pending_approvals = [
            a for a in self._pending_approvals if a.get("approval_id") != approval_id
        ]
        if self._current_approval and self._current_approval.get("approval_id") == approval_id:
            self._current_approval = self._pending_approvals[0] if self._pending_approvals else None
        self._update_display()

    def _update_display(self) -> None:
        """Update the display based on current state."""
        status = self.query_one("#approval-status", Static)
        command = self.query_one("#approval-command", Static)
        reason = self.query_one("#approval-reason", Static)
        plugin = self.query_one("#approval-plugin", Static)
        denial_input = self.query_one("#denial-reason", Input)
        approve_btn = self.query_one("#approve-btn", Button)
        approve_remember_btn = self.query_one("#approve-remember-btn", Button)
        deny_btn = self.query_one("#deny-btn", Button)
        deny_remember_btn = self.query_one("#deny-remember-btn", Button)

        if self._current_approval:
            pending_count = len(self._pending_approvals)
            status.update(
                f"[bold yellow]\u26a0 Approval Required[/bold yellow] "
                f"([yellow]{pending_count}[/yellow] pending)"
            )
            cmd_text = self._current_approval.get("command", "Unknown")
            command.update(f"[bold cyan]{cmd_text}[/bold cyan]")
            reason.update(f"Reason: {self._current_approval.get('reason', 'No reason given')}")

            # Show plugin/rule name if available
            plugin_name = self._current_approval.get("plugin_name", "")
            if plugin_name:
                plugin.update(f"Rule: {plugin_name}")
                plugin.display = True
            else:
                plugin.display = False

            denial_input.display = True
            approve_btn.disabled = False
            approve_remember_btn.disabled = False
            deny_btn.disabled = False
            deny_remember_btn.disabled = False
            command.display = True
            reason.display = True
        else:
            status.update("[dim]No pending approvals - waiting for commands...[/dim]")
            command.update("")
            reason.update("")
            plugin.update("")
            plugin.display = False
            denial_input.display = False
            approve_btn.disabled = True
            approve_remember_btn.disabled = True
            deny_btn.disabled = True
            deny_remember_btn.disabled = True
            command.display = False
            reason.display = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if not self._current_approval:
            return

        approval_id = self._current_approval.get("approval_id", "")

        if event.button.id in ("approve-btn", "approve-remember-btn"):
            remember = event.button.id == "approve-remember-btn"
            # Remove from pending immediately to prevent double-click
            self._pending_approvals = [
                a for a in self._pending_approvals if a.get("approval_id") != approval_id
            ]
            self._current_approval = self._pending_approvals[0] if self._pending_approvals else None
            self._update_display()
            self.post_message(self.ApprovalAction(True, approval_id, remember=remember))
        elif event.button.id in ("deny-btn", "deny-remember-btn"):
            remember = event.button.id == "deny-remember-btn"
            denial_input = self.query_one("#denial-reason", Input)
            reason = denial_input.value or None
            # Remove from pending immediately to prevent double-click
            self._pending_approvals = [
                a for a in self._pending_approvals if a.get("approval_id") != approval_id
            ]
            self._current_approval = self._pending_approvals[0] if self._pending_approvals else None
            self._update_display()
            self.post_message(self.ApprovalAction(False, approval_id, reason, remember=remember))
            denial_input.value = ""

    def approve_current(self) -> None:
        """Approve the current pending approval (for keyboard shortcut)."""
        if self._current_approval:
            approval_id = self._current_approval.get("approval_id", "")
            # Remove from pending immediately to prevent double-press
            self._pending_approvals = [
                a for a in self._pending_approvals if a.get("approval_id") != approval_id
            ]
            self._current_approval = self._pending_approvals[0] if self._pending_approvals else None
            self._update_display()
            self.post_message(self.ApprovalAction(True, approval_id))

    def deny_current(self) -> None:
        """Deny the current pending approval (for keyboard shortcut)."""
        if self._current_approval:
            approval_id = self._current_approval.get("approval_id", "")
            denial_input = self.query_one("#denial-reason", Input)
            reason = denial_input.value or None
            # Remove from pending immediately to prevent double-press
            self._pending_approvals = [
                a for a in self._pending_approvals if a.get("approval_id") != approval_id
            ]
            self._current_approval = self._pending_approvals[0] if self._pending_approvals else None
            self._update_display()
            self.post_message(self.ApprovalAction(False, approval_id, reason))
            denial_input.value = ""
