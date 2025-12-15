"""
File: src/safeshell/cli.py
Purpose: Main CLI entry point for SafeShell
Exports: app (Typer app)
Depends: typer, rich, safeshell.daemon.cli, safeshell.wrapper.cli
Overview: Provides version, check, status commands and registers daemon/wrapper subcommands
"""

import os
from pathlib import Path

import typer
from rich.panel import Panel
from rich.table import Table

from safeshell.console import console, print_error, print_info, print_success, print_warning
from safeshell.daemon.cli import _daemonize
from safeshell.daemon.cli import app as daemon_app
from safeshell.daemon.lifecycle import DaemonLifecycle
from safeshell.rules.cli import app as rules_app
from safeshell.theme import ICON_ERROR, ICON_INFO, ICON_SUCCESS
from safeshell.wrapper.cli import app as wrapper_app

app = typer.Typer(
    name="safeshell",
    help="Command-line safety layer for AI coding assistants.",
    no_args_is_help=True,
)

# Register subcommands
app.add_typer(daemon_app, name="daemon")
app.add_typer(wrapper_app, name="wrapper")
app.add_typer(rules_app, name="rules")


@app.command()
def version() -> None:
    """Show the SafeShell version.

    Displays the current SafeShell version and brief description.
    """
    console.print(
        Panel.fit(
            "[bold]SafeShell[/bold] v0.1.0\n"
            "Command-line safety layer for AI coding assistants",
            border_style="green",
        )
    )


@app.command()
def check(command: str) -> None:
    """Check if a command would be allowed by SafeShell.

    Evaluates the command against active rules without executing it.
    Useful for testing rules before running commands.

    Examples:
        safeshell check "git commit -m test"
        safeshell check "rm -rf /"
    """
    from safeshell.exceptions import DaemonNotRunningError
    from safeshell.wrapper.client import DaemonClient

    console.print(f"[muted]Checking:[/muted] [command]{command}[/command]")
    console.print()

    if not DaemonLifecycle.is_running():
        print_error("Daemon is not running", "Start it with: safeshell daemon start")
        raise typer.Exit(1)

    client = DaemonClient()
    try:
        response = client.evaluate(
            command=command,
            working_dir=str(Path.cwd()),
            env=dict(os.environ),
        )

        if response.should_execute:
            print_success("Command would be [bold]ALLOWED[/bold]")
        else:
            print_error("Command would be [bold]BLOCKED[/bold]")
            if response.denial_message:
                print_info(response.denial_message)

    except DaemonNotRunningError as e:
        print_error(f"Error connecting to daemon: {e}")
        raise typer.Exit(1) from e


@app.command()
def status() -> None:
    """Show SafeShell daemon status.

    Displays daemon status and socket connection health.
    Use this to verify SafeShell is running correctly.
    """
    table = Table(title="SafeShell Status", show_header=False, box=None)
    table.add_column("Component", style="bold")
    table.add_column("Status")

    if DaemonLifecycle.is_running():
        table.add_row("Daemon", f"[green]{ICON_SUCCESS} Running[/green]")

        # Try to get socket status
        from safeshell.wrapper.client import DaemonClient

        client = DaemonClient()
        if client.ping():
            table.add_row("Socket", f"[green]{ICON_SUCCESS} Connected[/green]")
        else:
            table.add_row("Socket", f"[yellow]{ICON_INFO} Connection issue[/yellow]")
    else:
        table.add_row("Daemon", f"[red]{ICON_ERROR} Not running[/red]")

    console.print(table)

    if not DaemonLifecycle.is_running():
        console.print()
        print_info("Start the daemon with: [command]safeshell daemon start[/command]")


@app.command()
def monitor(
    debug: bool = typer.Option(
        False,
        "--debug",
        "-d",
        help="Show all panes (debug log, command history, approval)",
    ),
) -> None:
    """Launch the SafeShell monitor TUI.

    Opens an interactive terminal interface for monitoring and approving
    commands in real-time.

    By default, shows only the approval pane. Use --debug to show:
    - Debug log: Real-time daemon events
    - Command history: Recent commands and their status
    - Approval pane: Handle pending approval requests

    Keyboard shortcuts:
        a    Approve current request
        d    Deny current request
        r    Reconnect to daemon
        h    Show help panel
        q    Quit

    Examples:
        safeshell monitor           # Clean approval-only view
        safeshell monitor --debug   # Full debug view
    """
    # Check if daemon is running
    if not DaemonLifecycle.is_running():
        print_warning("Daemon is not running")
        if typer.confirm("Start the daemon?", default=True):
            console.print("[muted]Starting daemon...[/muted]")
            _daemonize()
            if DaemonLifecycle.is_running():
                print_success("Daemon started")
            else:
                print_error("Failed to start daemon")
                raise typer.Exit(1)
        else:
            print_info("Monitor requires the daemon to be running")
            print_info("Start it with: [command]safeshell daemon start[/command]")
            raise typer.Exit(1)

    # Suppress loguru output for TUI - redirect to /dev/null instead of stderr
    # This preserves stderr for Textual while silencing our logs
    from loguru import logger

    logger.remove()  # Remove default stderr handler
    logger.add(os.devnull, level="DEBUG")  # Send all logs to /dev/null

    from safeshell.monitor.app import MonitorApp

    monitor_app = MonitorApp(debug_mode=debug)
    monitor_app.run()


@app.command()
def init() -> None:
    """Initialize SafeShell configuration, rules, and shims.

    Creates default configuration and rules files if they don't exist,
    and sets up command shims for interception.

    Creates:
    - ~/.safeshell/config.yaml - Configuration settings
    - ~/.safeshell/rules.yaml - Safety rules
    - ~/.safeshell/shims/ - Command shims

    After running init, add shell integration to your shell config
    and start the daemon.

    Examples:
        safeshell init              # Initialize SafeShell
        safeshell daemon start      # Then start the daemon
    """
    from safeshell.config import CONFIG_PATH, create_default_config
    from safeshell.rules import DEFAULT_RULES_YAML, GLOBAL_RULES_PATH
    from safeshell.shims import (
        get_shell_init_instructions,
        install_init_script,
        refresh_shims,
    )

    config_created = False
    rules_created = False

    # Handle config.yaml
    if CONFIG_PATH.exists():
        print_warning(f"Config already exists: {CONFIG_PATH}")
        if typer.confirm("Overwrite config?"):
            create_default_config()
            config_created = True
    else:
        create_default_config()
        config_created = True

    # Handle rules.yaml
    if GLOBAL_RULES_PATH.exists():
        print_warning(f"Rules already exist: {GLOBAL_RULES_PATH}")
        if typer.confirm("Overwrite rules?"):
            GLOBAL_RULES_PATH.parent.mkdir(parents=True, exist_ok=True)
            GLOBAL_RULES_PATH.write_text(DEFAULT_RULES_YAML)
            rules_created = True
    else:
        GLOBAL_RULES_PATH.parent.mkdir(parents=True, exist_ok=True)
        GLOBAL_RULES_PATH.write_text(DEFAULT_RULES_YAML)
        rules_created = True

    # Set up shims
    console.print("[muted]Setting up shims...[/muted]")
    install_init_script()
    result = refresh_shims()
    shims_created = len(result["created"])

    if not config_created and not rules_created and shims_created == 0:
        print_warning("No changes made")
        raise typer.Exit(0)

    print_success("SafeShell initialized!")
    console.print()

    # Show created files table
    table = Table(title="Created Files", show_header=False, box=None)
    table.add_column("Type", style="bold")
    table.add_column("Path")
    table.add_column("Status")

    config_status = "[green]created[/green]" if config_created else "[muted]unchanged[/muted]"
    rules_status = "[green]created[/green]" if rules_created else "[muted]unchanged[/muted]"

    table.add_row("Config", str(CONFIG_PATH), config_status)
    table.add_row("Rules", str(GLOBAL_RULES_PATH), rules_status)
    if shims_created > 0:
        table.add_row("Shims", f"{shims_created} commands", "[green]created[/green]")

    console.print(table)
    console.print()

    console.print("[bold]Next steps:[/bold]")
    console.print("  1. Review rules: [path]~/.safeshell/rules.yaml[/path]")
    console.print("  2. Add shell integration:")
    console.print(get_shell_init_instructions())
    console.print("  3. Start the daemon: [command]safeshell daemon start[/command]")


@app.command()
def refresh() -> None:
    """Regenerate shims based on rules.yaml commands.

    Reads all commands from global and repo rules, then creates/updates
    symlinks in ~/.safeshell/shims/ for each command that needs interception.

    Stale shims (for commands no longer in rules) are removed.

    Examples:
        safeshell refresh    # Update all shims
    """
    from safeshell.shims import refresh_shims

    console.print("[muted]Refreshing shims...[/muted]")
    result = refresh_shims(working_dir=str(Path.cwd()))

    if result["created"]:
        print_success(f"Created: {', '.join(result['created'])}")
    if result["removed"]:
        print_warning(f"Removed: {', '.join(result['removed'])}")
    if result["unchanged"]:
        console.print(f"[muted]Unchanged: {', '.join(result['unchanged'])}[/muted]")

    total = len(result["created"]) + len(result["unchanged"])
    console.print()
    print_success(f"Done! {total} shim(s) active")


if __name__ == "__main__":
    app()
