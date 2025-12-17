"""
File: src/safeshell/cli.py
Purpose: Main CLI entry point for SafeShell
Exports: app (Typer app)
Depends: typer, rich, safeshell.daemon.cli, safeshell.wrapper.cli
Overview: Provides version, check, status commands and registers daemon/wrapper subcommands
"""

import contextlib
import os
import signal
import sys
from pathlib import Path

import typer
from rich.console import Console

from safeshell.benchmarks.cli import app as perf_app
from safeshell.common import SAFESHELL_DIR
from safeshell.daemon.cli import _daemonize
from safeshell.daemon.cli import app as daemon_app
from safeshell.daemon.lifecycle import DaemonLifecycle
from safeshell.rules.cli import app as rules_app
from safeshell.wrapper.cli import app as wrapper_app

# GUI PID file for preventing duplicate instances
GUI_PID_PATH = SAFESHELL_DIR / "gui.pid"


def _is_gui_running() -> bool:
    """Check if GUI process is running."""
    if not GUI_PID_PATH.exists():
        return False
    try:
        pid = int(GUI_PID_PATH.read_text().strip())
        # Check if process exists
        os.kill(pid, 0)
        return True
    except (ValueError, OSError, ProcessLookupError):
        # PID file invalid or process not running
        with contextlib.suppress(FileNotFoundError):
            GUI_PID_PATH.unlink()
        return False


def _stop_gui() -> bool:
    """Stop running GUI process."""
    if not GUI_PID_PATH.exists():
        return False
    try:
        pid = int(GUI_PID_PATH.read_text().strip())
        os.kill(pid, signal.SIGTERM)
        with contextlib.suppress(FileNotFoundError):
            GUI_PID_PATH.unlink()
        return True
    except (ValueError, OSError, ProcessLookupError):
        with contextlib.suppress(FileNotFoundError):
            GUI_PID_PATH.unlink()
        return False


app = typer.Typer(
    name="safeshell",
    help="Command-line safety layer for AI coding assistants.",
    no_args_is_help=True,
)
console = Console()

# Register subcommands
app.add_typer(daemon_app, name="daemon")
app.add_typer(wrapper_app, name="wrapper")
app.add_typer(rules_app, name="rules")
app.add_typer(perf_app, name="perf")


@app.command()
def version() -> None:
    """Show the SafeShell version."""
    console.print("[bold]SafeShell[/bold] v0.1.0")


@app.command()
def up() -> None:
    """Start SafeShell (daemon + system tray GUI).

    This is the recommended way to start SafeShell.
    Starts the daemon if not running, then launches the system tray application
    in the background.

    The tray app provides:
    - Popup windows when commands need approval
    - System tray icon showing status
    - Settings and debug log access
    """
    import subprocess
    import time

    # Start daemon if not running
    if not DaemonLifecycle.is_running():
        console.print("Starting daemon...")
        _daemonize()
        time.sleep(0.5)
        if DaemonLifecycle.is_running():
            console.print("[green]Daemon started.[/green]")
        else:
            console.print("[red]Failed to start daemon.[/red]")
            raise typer.Exit(1)
    else:
        console.print("[dim]Daemon already running.[/dim]")

    # Check if GUI is already running
    if _is_gui_running():
        console.print("[dim]GUI already running, bringing to front...[/dim]")
        # Send SIGUSR1 to bring window to front
        try:
            pid = int(GUI_PID_PATH.read_text().strip())
            os.kill(pid, signal.SIGUSR1)
        except (ValueError, OSError, ProcessLookupError):
            pass
        console.print("[green]SafeShell is running.[/green]")
        return

    # Launch GUI in background process (trusted input - our own module)
    console.print("Starting system tray...")
    subprocess.Popen(  # noqa: S603
        [sys.executable, "-m", "safeshell.gui"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,  # Detach from terminal
    )
    console.print("[green]SafeShell is running.[/green]")
    console.print("[dim]Monitor window should appear. Use 'safeshell down' to stop.[/dim]")


@app.command()
def down() -> None:
    """Stop SafeShell (daemon + GUI).

    Stops both the GUI and daemon processes.

    Equivalent to: safeshell daemon stop
    """
    stopped_something = False

    # Stop GUI first
    if _is_gui_running():
        console.print("Stopping GUI...")
        _stop_gui()
        console.print("[green]GUI stopped.[/green]")
        stopped_something = True

    # Stop daemon
    if DaemonLifecycle.is_running():
        pid = DaemonLifecycle.read_pid()
        if pid:
            console.print(f"Stopping daemon (PID {pid})...")
            DaemonLifecycle.stop_daemon()
            console.print("[green]Daemon stopped.[/green]")
            stopped_something = True
        else:
            console.print("[red]Could not determine daemon PID.[/red]")

    if not stopped_something:
        console.print("[yellow]SafeShell is not running.[/yellow]")


@app.command()
def restart() -> None:
    """Restart SafeShell (daemon + GUI).

    Stops both processes, then starts them again.
    Useful for development iteration.
    """
    import subprocess
    import time

    # Stop everything
    stopped_gui = _stop_gui() if _is_gui_running() else False
    stopped_daemon = DaemonLifecycle.stop_daemon() if DaemonLifecycle.is_running() else False

    if stopped_gui or stopped_daemon:
        console.print("Stopping SafeShell...")
        time.sleep(0.5)  # Allow clean shutdown

    # Start daemon
    console.print("Starting daemon...")
    _daemonize()
    time.sleep(0.5)
    if DaemonLifecycle.is_running():
        console.print("[green]Daemon started.[/green]")
    else:
        console.print("[red]Failed to start daemon.[/red]")
        raise typer.Exit(1)

    # Start GUI in background
    console.print("Starting system tray...")
    subprocess.Popen(  # noqa: S603
        [sys.executable, "-m", "safeshell.gui"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    console.print("[green]SafeShell restarted.[/green]")


@app.command()
def check(command: str) -> None:
    """Check if a command would be allowed by SafeShell.

    Args:
        command: The shell command to evaluate.
    """
    from safeshell.exceptions import DaemonNotRunningError
    from safeshell.models import ExecutionContext
    from safeshell.wrapper.client import DaemonClient

    console.print(f"[yellow]Checking command:[/yellow] {command}")

    if not DaemonLifecycle.is_running():
        console.print("[red]Daemon is not running.[/red]")
        console.print("Start it with: safeshell daemon start")
        raise typer.Exit(1)

    # Determine execution context from environment
    is_ai_context = os.environ.get("SAFESHELL_CONTEXT") == "ai"
    exec_ctx = ExecutionContext.AI if is_ai_context else ExecutionContext.HUMAN

    client = DaemonClient()
    try:
        response = client.evaluate(
            command=command,
            working_dir=str(Path.cwd()),
            env=dict(os.environ),
            execution_context=exec_ctx,
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
def tray() -> None:
    """Launch the SafeShell system tray application.

    Runs in the background and shows popup windows when
    command approval is required.

    Features:
    - System tray icon with status indicator
    - Automatic popup windows for approvals
    - Optional debug log window (toggle in settings or tray menu)
    - Settings persistence

    This is an alternative to the terminal-based 'safeshell monitor' command.
    Both can run simultaneously.
    """
    import time

    # Check if daemon is running
    if not DaemonLifecycle.is_running():
        console.print("[yellow]Daemon is not running.[/yellow]")
        if typer.confirm("Start the daemon?", default=True):
            console.print("Starting daemon...")
            _daemonize()
            # Wait briefly for daemon to start
            time.sleep(0.5)
            if DaemonLifecycle.is_running():
                console.print("[green]Daemon started.[/green]")
            else:
                console.print("[red]Failed to start daemon.[/red]")
                raise typer.Exit(1)
        else:
            console.print("Tray app requires the daemon to be running.")
            console.print("Start it with: safeshell daemon start")
            raise typer.Exit(1)

    # Suppress loguru output for GUI
    from loguru import logger

    logger.remove()
    logger.add(os.devnull, level="DEBUG")

    # Import and run GUI
    from safeshell.gui import run_gui

    console.print("[dim]Starting SafeShell system tray...[/dim]")
    run_gui()


@app.command()
def init() -> None:
    """Initialize SafeShell configuration, rules, and shims."""
    from safeshell.config import CONFIG_PATH, create_default_config
    from safeshell.rules import GLOBAL_RULES_PATH, get_builtin_rules_yaml
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
            GLOBAL_RULES_PATH.write_text(get_builtin_rules_yaml())
            rules_created = True
    else:
        GLOBAL_RULES_PATH.parent.mkdir(parents=True, exist_ok=True)
        GLOBAL_RULES_PATH.write_text(get_builtin_rules_yaml())
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
