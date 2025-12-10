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
        Binding("q", "quit", "Quit", priority=True),
        Binding("a", "approve", "Approve", priority=True),
        Binding("d", "deny", "Deny", priority=True),
        Binding("r", "reconnect", "Reconnect", priority=True),
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

    def _process_event(self, message: dict[str, Any]) -> None:
        """Process an event message from the daemon.

        Args:
            message: Event message
        """
        approval_pane = self.query_one("#approval-pane", ApprovalPane)

        # Get optional panes (only exist in debug mode)
        history_pane = None
        if self._debug_mode:
            history_pane = self.query_one("#history-pane", HistoryPane)

        msg_type = message.get("type")

        if msg_type == "event":
            event_data = message.get("event", {})
            event_type = event_data.get("type")
            data = event_data.get("data", {})

            if event_type == EventType.COMMAND_RECEIVED.value:
                command = data.get("command", "unknown")
                working_dir = data.get("working_dir", "")
                self._log_debug(f"Command received: {command}", "info")
                self._log_debug(f"  Working dir: {working_dir}", "debug")

                # Add to history (debug mode only)
                if history_pane:
                    history_pane.add_command(
                        CommandHistoryItem(
                            command=command,
                            timestamp=datetime.now(),
                            status="pending",
                        )
                    )

            elif event_type == EventType.EVALUATION_STARTED.value:
                plugin_count = data.get("plugin_count", 0)
                self._log_debug(f"Evaluating with {plugin_count} rules...", "debug")

            elif event_type == EventType.EVALUATION_COMPLETED.value:
                command = data.get("command", "unknown")
                decision = data.get("decision", "unknown")
                reason = data.get("reason")
                plugin_name = data.get("plugin_name")

                if decision == "allow":
                    self._log_debug(f"ALLOWED: {command}", "success")
                    if history_pane:
                        history_pane.update_command(command, "allowed", decision)
                elif decision == "deny":
                    self._log_debug(f"BLOCKED: {command}", "error")
                    if reason:
                        self._log_debug(f"  Reason: {reason}", "warning")
                    if plugin_name:
                        self._log_debug(f"  Rule: {plugin_name}", "debug")
                    if history_pane:
                        history_pane.update_command(command, "blocked", decision, reason)
                elif decision == "require_approval":
                    self._log_debug(f"APPROVAL REQUIRED: {command}", "warning")
                    if history_pane:
                        history_pane.update_command(command, "waiting", decision, reason)

            elif event_type == EventType.APPROVAL_NEEDED.value:
                approval_id = data.get("approval_id", "")
                command = data.get("command", "")
                reason = data.get("reason", "")
                plugin_name = data.get("plugin_name", "")

                self._log_debug(f"Approval needed: {command}", "warning")
                self._log_debug(f"  ID: {approval_id[:12]}...", "debug")
                self._log_debug(f"  Reason: {reason}", "info")

                approval_pane.add_pending_approval(
                    {
                        "approval_id": approval_id,
                        "command": command,
                        "reason": reason,
                        "plugin_name": plugin_name,
                    }
                )

                if history_pane:
                    history_pane.update_command(
                        command, "waiting", "require_approval", reason, approval_id
                    )

            elif event_type == EventType.APPROVAL_RESOLVED.value:
                approval_id = data.get("approval_id", "")
                approved = data.get("approved", False)
                reason = data.get("reason")

                if approved:
                    self._log_debug(f"Approved: {approval_id[:12]}...", "success")
                else:
                    self._log_debug(f"Denied: {approval_id[:12]}...", "error")
                    if reason:
                        self._log_debug(f"  Reason: {reason}", "info")

                approval_pane.remove_pending_approval(approval_id)

            elif event_type == EventType.DAEMON_STATUS.value:
                status = data.get("status", "unknown")
                self._log_debug(f"Daemon status: {status}", "info")

        elif msg_type == "response":
            # Response to a command we sent
            success = message.get("success", False)
            msg = message.get("message") or message.get("error")
            if success:
                self._log_debug(f"Response: {msg}", "success")
            else:
                self._log_debug(f"Error: {msg}", "error")

    async def on_approval_pane_approval_action(self, event: ApprovalPane.ApprovalAction) -> None:
        """Handle approval/denial from the approval pane.

        Args:
            event: The approval action event
        """
        if event.approved:
            remember_msg = " (remember)" if event.remember else ""
            self._log_debug(f"Approving{remember_msg} {event.approval_id[:12]}...", "info")
            success = await self._client.approve(event.approval_id, remember=event.remember)
            if not success:
                self._log_debug("Failed to send approval", "error")
        else:
            reason_msg = f" (reason: {event.reason})" if event.reason else ""
            self._log_debug(f"Denying {event.approval_id[:12]}...{reason_msg}", "info")
            success = await self._client.deny(event.approval_id, event.reason)
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

    async def action_reconnect(self) -> None:
        """Attempt to reconnect to the daemon."""
        self._log_debug("Attempting to reconnect...", "info")

        await self._client.disconnect()
        await self._connect_to_daemon()

    async def on_unmount(self) -> None:
        """Handle unmount event - disconnect from daemon."""
        await self._client.disconnect()
