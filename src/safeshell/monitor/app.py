"""
File: src/safeshell/monitor/app.py
Purpose: Main Textual application for the SafeShell Monitor TUI
Exports: MonitorApp
Depends: textual, safeshell.monitor.client, safeshell.monitor.widgets
Overview: Three-pane TUI for monitoring daemon events and handling approval requests
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Footer, Header, Static

from safeshell.events.types import EventType
from safeshell.monitor.client import MonitorClient
from safeshell.monitor.widgets import ApprovalPane, CommandHistoryItem, DebugPane, HistoryPane

# UI constants
_ID_DISPLAY_LENGTH = 12


class MonitorApp(App[None]):
    """SafeShell Monitor TUI Application.

    Provides a three-pane interface for:
    - Debug log: Shows daemon events in real-time (debug mode only)
    - Command history: Shows recent commands and their status (debug mode only)
    - Approval pane: Handles pending approval requests

    By default, only shows the approval pane for a cleaner UI.
    Use --debug flag to show all panes.
    """

    TITLE = "SafeShell Monitor"
    CSS_PATH = Path(__file__).parent / "styles.css"

    BINDINGS = [
        Binding("ctrl+q", "quit", "^Q:Quit", priority=True),
        Binding("1", "approve", "1:Approve", priority=True),
        Binding("2", "approve_timed", "2:Approve 5m", priority=True),
        Binding("3", "deny", "3:Deny", priority=True),
        Binding("4", "deny_timed", "4:Deny 5m", priority=True),
        Binding("ctrl+r", "reconnect", "^R:Reconnect", priority=True),
    ]

    def __init__(self, debug_mode: bool = False) -> None:
        """Initialize the monitor app.

        Args:
            debug_mode: If True, show all three panes (debug, history, approval).
                       If False, show only the approval pane.
        """
        super().__init__()
        self._client = MonitorClient()
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5
        self._debug_mode = debug_mode

    def compose(self) -> ComposeResult:
        """Compose the application layout."""
        yield Header()
        yield Static("Connecting...", id="status-bar")
        if self._debug_mode:
            yield Vertical(
                DebugPane(id="debug-pane"),
                HistoryPane(id="history-pane"),
                ApprovalPane(id="approval-pane"),
                id="main-container",
            )
        else:
            yield Vertical(
                ApprovalPane(id="approval-pane"),
                id="main-container",
            )
        yield Footer()

    async def on_mount(self) -> None:
        """Handle mount event - connect to daemon."""
        await self._connect_to_daemon()

    async def _connect_to_daemon(self) -> None:
        """Connect to the daemon's monitor socket."""
        status_bar = self.query_one("#status-bar", Static)

        status_bar.update("[yellow]Connecting to daemon...[/yellow]")
        self._log_debug("Attempting to connect to daemon...", "info")

        connected = await self._client.connect()

        if connected:
            self._reconnect_attempts = 0
            status_bar.update("[green]Connected[/green] to SafeShell daemon")
            status_bar.add_class("status-connected")
            status_bar.remove_class("status-disconnected")
            self._log_debug("Connected to daemon", "success")

            # Set up event callback
            self._client.add_event_callback(self._handle_event)

            # Start receiving events
            await self._client.start_receiving()
        else:
            status_bar.update("[red]Disconnected[/red] - Press 'r' to reconnect")
            status_bar.add_class("status-disconnected")
            status_bar.remove_class("status-connected")
            self._log_debug("Failed to connect to daemon", "error")
            self._log_debug("Is the daemon running? (safeshell daemon start)", "info")

    def _log_debug(self, message: str, level: str = "info") -> None:
        """Log a message to the debug pane if in debug mode.

        Args:
            message: Message to log
            level: Log level (info, warning, error, debug, success)
        """
        if self._debug_mode:
            debug_pane = self.query_one("#debug-pane", DebugPane)
            debug_pane.add_log(message, level)

    def _handle_event(self, message: dict[str, Any]) -> None:
        """Handle an event from the daemon.

        Args:
            message: Event message from daemon
        """
        # Schedule in Textual's event loop (call_later works from async tasks)
        self.call_later(self._process_event, message)

    def _handle_command_received(
        self, data: dict[str, Any], history_pane: HistoryPane | None
    ) -> None:
        """Handle COMMAND_RECEIVED event."""
        command = data.get("command", "unknown")
        working_dir = data.get("working_dir", "")
        self._log_debug(f"Command received: {command}", "info")
        self._log_debug(f"  Working dir: {working_dir}", "debug")

        if history_pane:
            history_pane.add_command(
                CommandHistoryItem(command=command, timestamp=datetime.now(), status="pending")
            )

    def _log_decision_allow(
        self, command: str, decision: str, history_pane: HistoryPane | None
    ) -> None:
        """Log and update history for allowed command."""
        self._log_debug(f"ALLOWED: {command}", "success")
        if history_pane:
            history_pane.update_command(command, "allowed", decision)

    def _log_decision_deny(
        self,
        command: str,
        decision: str,
        reason: str | None,
        plugin_name: str | None,
        history_pane: HistoryPane | None,
    ) -> None:
        """Log and update history for denied command."""
        self._log_debug(f"BLOCKED: {command}", "error")
        if reason:
            self._log_debug(f"  Reason: {reason}", "warning")
        if plugin_name:
            self._log_debug(f"  Rule: {plugin_name}", "debug")
        if history_pane:
            history_pane.update_command(command, "blocked", decision, reason)

    def _log_decision_approval(
        self, command: str, decision: str, reason: str | None, history_pane: HistoryPane | None
    ) -> None:
        """Log and update history for command requiring approval."""
        self._log_debug(f"APPROVAL REQUIRED: {command}", "warning")
        if history_pane:
            history_pane.update_command(command, "waiting", decision, reason)

    def _handle_evaluation_completed(
        self, data: dict[str, Any], history_pane: HistoryPane | None
    ) -> None:
        """Handle EVALUATION_COMPLETED event."""
        command = data.get("command", "unknown")
        decision = data.get("decision", "unknown")
        reason = data.get("reason")
        plugin_name = data.get("plugin_name")

        if decision == "allow":
            self._log_decision_allow(command, decision, history_pane)
        elif decision == "deny":
            self._log_decision_deny(command, decision, reason, plugin_name, history_pane)
        elif decision == "require_approval":
            self._log_decision_approval(command, decision, reason, history_pane)

    def _handle_approval_needed(
        self,
        data: dict[str, Any],
        approval_pane: ApprovalPane,
        history_pane: HistoryPane | None,
    ) -> None:
        """Handle APPROVAL_NEEDED event."""
        approval_id = data.get("approval_id", "")
        command = data.get("command", "")
        reason = data.get("reason", "")
        plugin_name = data.get("plugin_name", "")
        working_dir = data.get("working_dir", "")

        self._log_debug(f"Approval needed: {command}", "warning")
        self._log_debug(f"  ID: {approval_id[:_ID_DISPLAY_LENGTH]}...", "debug")
        self._log_debug(f"  Reason: {reason}", "info")
        if working_dir:
            self._log_debug(f"  Dir: {working_dir}", "debug")

        approval_pane.add_pending_approval(
            {
                "approval_id": approval_id,
                "command": command,
                "reason": reason,
                "plugin_name": plugin_name,
                "working_dir": working_dir,
            }
        )

        if history_pane:
            history_pane.update_command(command, "waiting", "require_approval", reason, approval_id)

    def _handle_approval_resolved(self, data: dict[str, Any], approval_pane: ApprovalPane) -> None:
        """Handle APPROVAL_RESOLVED event."""
        approval_id = data.get("approval_id", "")
        approved = data.get("approved", False)
        reason = data.get("reason")

        if approved:
            self._log_debug(f"Approved: {approval_id[:_ID_DISPLAY_LENGTH]}...", "success")
        else:
            self._log_debug(f"Denied: {approval_id[:_ID_DISPLAY_LENGTH]}...", "error")
            if reason:
                self._log_debug(f"  Reason: {reason}", "info")

        approval_pane.remove_pending_approval(approval_id)

    def _handle_evaluation_started(self, data: dict[str, Any]) -> None:
        """Handle EVALUATION_STARTED event."""
        plugin_count = data.get("plugin_count", 0)
        self._log_debug(f"Evaluating with {plugin_count} rules...", "debug")

    def _handle_daemon_status(self, data: dict[str, Any]) -> None:
        """Handle DAEMON_STATUS event."""
        status = data.get("status", "unknown")
        self._log_debug(f"Daemon status: {status}", "info")

    def _process_daemon_event(
        self,
        event_data: dict[str, Any],
        approval_pane: ApprovalPane,
        history_pane: HistoryPane | None,
    ) -> None:
        """Process a daemon event."""
        event_type = event_data.get("type")
        data = event_data.get("data", {})

        if event_type == EventType.COMMAND_RECEIVED.value:
            self._handle_command_received(data, history_pane)
            return
        if event_type == EventType.EVALUATION_STARTED.value:
            self._handle_evaluation_started(data)
            return
        if event_type == EventType.EVALUATION_COMPLETED.value:
            self._handle_evaluation_completed(data, history_pane)
            return
        if event_type == EventType.APPROVAL_NEEDED.value:
            self._handle_approval_needed(data, approval_pane, history_pane)
            return
        if event_type == EventType.APPROVAL_RESOLVED.value:
            self._handle_approval_resolved(data, approval_pane)
            return
        if event_type == EventType.DAEMON_STATUS.value:
            self._handle_daemon_status(data)

    def _process_event(self, message: dict[str, Any]) -> None:
        """Process an event message from the daemon.

        Args:
            message: Event message
        """
        approval_pane = self.query_one("#approval-pane", ApprovalPane)
        history_pane = self.query_one("#history-pane", HistoryPane) if self._debug_mode else None

        msg_type = message.get("type")

        if msg_type == "event":
            self._process_daemon_event(message.get("event", {}), approval_pane, history_pane)
        elif msg_type == "response":
            success = message.get("success", False)
            msg = message.get("message") or message.get("error")
            level = "success" if success else "error"
            prefix = "Response" if success else "Error"
            self._log_debug(f"{prefix}: {msg}", level)

    async def on_approval_pane_approval_action(self, event: ApprovalPane.ApprovalAction) -> None:
        """Handle approval/denial from the approval pane.

        Args:
            event: The approval action event
        """
        if event.approved:
            remember_msg = " (remember)" if event.remember else ""
            self._log_debug(
                f"Approving{remember_msg} {event.approval_id[:_ID_DISPLAY_LENGTH]}...", "info"
            )
            success = await self._client.approve(event.approval_id, remember=event.remember)
            if not success:
                self._log_debug("Failed to send approval", "error")
        else:
            remember_msg = " (remember)" if event.remember else ""
            reason_msg = f" (reason: {event.reason})" if event.reason else ""
            msg = f"Denying{remember_msg} {event.approval_id[:_ID_DISPLAY_LENGTH]}...{reason_msg}"
            self._log_debug(msg, "info")
            success = await self._client.deny(
                event.approval_id, event.reason, remember=event.remember
            )
            if not success:
                self._log_debug("Failed to send denial", "error")

    async def action_quit(self) -> None:
        """Quit the application."""
        self.exit()

    def action_approve(self) -> None:
        """Approve the current pending approval via keyboard."""
        approval_pane = self.query_one("#approval-pane", ApprovalPane)
        approval_pane.approve_current()

    def action_deny(self) -> None:
        """Deny the current pending approval via keyboard."""
        approval_pane = self.query_one("#approval-pane", ApprovalPane)
        approval_pane.deny_current()

    def action_approve_timed(self) -> None:
        """Approve the current pending approval for 5 minutes."""
        approval_pane = self.query_one("#approval-pane", ApprovalPane)
        approval_pane.approve_current_timed()

    def action_deny_timed(self) -> None:
        """Deny the current pending approval for 5 minutes."""
        approval_pane = self.query_one("#approval-pane", ApprovalPane)
        approval_pane.deny_current_timed()

    async def action_reconnect(self) -> None:
        """Attempt to reconnect to the daemon."""
        self._log_debug("Attempting to reconnect...", "info")

        await self._client.disconnect()
        await self._connect_to_daemon()

    async def on_unmount(self) -> None:
        """Handle unmount event - disconnect from daemon."""
        await self._client.disconnect()
