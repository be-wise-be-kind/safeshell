"""
File: src/safeshell/cli.py
Purpose: Main CLI entry point for SafeShell
Exports: app (Typer app)
Depends: typer, rich, safeshell.daemon.cli, safeshell.wrapper.cli
Overview: Provides version, check, status commands and registers daemon/wrapper subcommands
"""

import os
import sys
from pathlib import Path

import typer
from rich.console import Console

from safeshell.daemon.cli import _daemonize
from safeshell.daemon.cli import app as daemon_app
from safeshell.daemon.lifecycle import DaemonLifecycle
from safeshell.wrapper.cli import app as wrapper_app

app = typer.Typer(
    name="safeshell",
    help="Command-line safety layer for AI coding assistants.",
    no_args_is_help=True,
)
console = Console()

# Register subcommands
app.add_typer(daemon_app, name="daemon")
app.add_typer(wrapper_app, name="wrapper")


@app.command()
def version() -> None:
    """Show the SafeShell version."""
    console.print("[bold]SafeShell[/bold] v0.1.0")


@app.command()
def check(command: str) -> None:
    """Check if a command would be allowed by SafeShell.

    Args:
        command: The shell command to evaluate.
    """
    from safeshell.exceptions import DaemonNotRunningError
    from safeshell.wrapper.client import DaemonClient

    console.print(f"[yellow]Checking command:[/yellow] {command}")

    if not DaemonLifecycle.is_running():
        console.print("[red]Daemon is not running.[/red]")
        console.print("Start it with: safeshell daemon start")
        raise typer.Exit(1)

    client = DaemonClient()
    try:
        response = client.evaluate(
            command=command,
            working_dir=str(Path.cwd()),
            env=dict(os.environ),
        )

        if response.should_execute:
            console.print("[green]Command would be ALLOWED[/green]")
        else:
            console.print("[red]Command would be BLOCKED[/red]")
            if response.denial_message:
                console.print(response.denial_message)

    except DaemonNotRunningError as e:
        console.print(f"[red]Error connecting to daemon:[/red] {e}")
        raise typer.Exit(1) from e


@app.command()
def status() -> None:
    """Show SafeShell daemon status and loaded plugins."""
    console.print("[bold]SafeShell Status[/bold]")
    console.print()

    if DaemonLifecycle.is_running():
        console.print("  Daemon: [green]Running[/green]")

        # Try to get plugin info
        from safeshell.wrapper.client import DaemonClient

        client = DaemonClient()
        if client.ping():
            console.print("  Socket: [green]Connected[/green]")
        else:
            console.print("  Socket: [yellow]Connection issue[/yellow]")
    else:
        console.print("  Daemon: [red]Not running[/red]")
        console.print()
        console.print("Start with: safeshell daemon start")


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

    By default, shows only the approval pane for a clean interface.
    Use --debug to show all three panes:
    - Debug log: Real-time daemon events
    - Command history: Recent commands and their status
    - Approval pane: Handle pending approval requests

    Keyboard shortcuts:
    - q: Quit
    - a: Approve current request
    - d: Deny current request
    - r: Reconnect to daemon
    """
    # Check if daemon is running
    if not DaemonLifecycle.is_running():
        console.print("[yellow]Daemon is not running.[/yellow]")
        if typer.confirm("Start the daemon?", default=True):
            console.print("Starting daemon...")
            _daemonize()
            if DaemonLifecycle.is_running():
                console.print("[green]Daemon started.[/green]")
            else:
                console.print("[red]Failed to start daemon.[/red]")
                raise typer.Exit(1)
        else:
            console.print("Monitor requires the daemon to be running.")
            console.print("Start it with: safeshell daemon start")
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
    """Initialize SafeShell configuration, rules, and shims."""
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
        console.print(f"[yellow]Config already exists at:[/yellow] {CONFIG_PATH}")
        if typer.confirm("Overwrite config?"):
            create_default_config()
            config_created = True
    else:
        create_default_config()
        config_created = True

    # Handle rules.yaml
    if GLOBAL_RULES_PATH.exists():
        console.print(f"[yellow]Rules already exist at:[/yellow] {GLOBAL_RULES_PATH}")
        if typer.confirm("Overwrite rules?"):
            GLOBAL_RULES_PATH.parent.mkdir(parents=True, exist_ok=True)
            GLOBAL_RULES_PATH.write_text(DEFAULT_RULES_YAML)
            rules_created = True
    else:
        GLOBAL_RULES_PATH.parent.mkdir(parents=True, exist_ok=True)
        GLOBAL_RULES_PATH.write_text(DEFAULT_RULES_YAML)
        rules_created = True

    # Set up shims
    console.print("[dim]Setting up shims...[/dim]")
    install_init_script()
    result = refresh_shims()
    shims_created = len(result["created"])

    if not config_created and not rules_created and shims_created == 0:
        console.print("[yellow]No changes made.[/yellow]")
        raise typer.Exit(0)

    console.print("[green]SafeShell initialized![/green]")
    console.print()
    config_status = " [green](created)[/green]" if config_created else ""
    rules_status = " [green](created)[/green]" if rules_created else ""
    console.print(f"  Config: {CONFIG_PATH}{config_status}")
    console.print(f"  Rules:  {GLOBAL_RULES_PATH}{rules_status}")
    if shims_created > 0:
        console.print(f"  Shims:  {shims_created} command shims created")
    console.print()
    console.print("Next steps:")
    console.print("  1. Review rules: ~/.safeshell/rules.yaml")
    console.print("  2. [bold]Add shell integration:[/bold]")
    console.print(get_shell_init_instructions())
    console.print("  3. Start the daemon: safeshell daemon start")


@app.command()
def refresh() -> None:
    """Regenerate shims based on rules.yaml commands.

    Reads all commands from global and repo rules, then creates/updates
    symlinks in ~/.safeshell/shims/ for each command that needs interception.

    Stale shims (for commands no longer in rules) are removed.
    """
    from safeshell.shims import refresh_shims

    console.print("[dim]Refreshing shims...[/dim]")
    result = refresh_shims(working_dir=str(Path.cwd()))

    if result["created"]:
        console.print(f"[green]Created:[/green] {', '.join(result['created'])}")
    if result["removed"]:
        console.print(f"[yellow]Removed:[/yellow] {', '.join(result['removed'])}")
    if result["unchanged"]:
        console.print(f"[dim]Unchanged:[/dim] {', '.join(result['unchanged'])}")

    total = len(result["created"]) + len(result["unchanged"])
    console.print()
    console.print(f"[green]Done![/green] {total} shim(s) active.")


if __name__ == "__main__":
    app()
