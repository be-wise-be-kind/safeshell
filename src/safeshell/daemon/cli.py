"""
File: src/safeshell/daemon/cli.py
Purpose: CLI commands for daemon management
Exports: app (Typer app)
Depends: typer, rich, asyncio, safeshell.daemon
Overview: Provides start, stop, status commands for daemon management
"""

# ruff: noqa: SIM115 - open() for daemonization must stay open for process lifetime
# ruff: noqa: PTH123 - Must use open() for daemon stdio redirect (pathlib doesn't work here)

import asyncio
import os
import sys

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from safeshell.console import console, print_error, print_info, print_success, print_warning
from safeshell.daemon.lifecycle import DaemonLifecycle
from safeshell.daemon.server import run_daemon
from safeshell.theme import ICON_ERROR, ICON_SUCCESS

app = typer.Typer(name="daemon", help="Manage the SafeShell daemon")


@app.command()
def start(
    foreground: bool = typer.Option(
        False, "--foreground", "-f", help="Run in foreground (don't daemonize)"
    ),
) -> None:
    """Start the SafeShell daemon.

    The daemon runs in the background and processes command approval
    requests from the shell wrapper. You must start the daemon before
    using SafeShell-wrapped shells.

    Examples:
        safeshell daemon start              # Start in background
        safeshell daemon start --foreground # Run in foreground for debugging
    """
    if DaemonLifecycle.is_running():
        print_warning("Daemon is already running")
        raise typer.Exit(0)

    if foreground:
        print_success("Starting daemon in foreground...")
        print_info("Press Ctrl+C to stop")
        asyncio.run(run_daemon())
    else:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Starting daemon...", total=None)
            _daemonize()

        print_success("Daemon started")


@app.command()
def stop() -> None:
    """Stop the SafeShell daemon.

    Sends a stop signal to the running daemon process.
    Safe to run even if daemon is not running.

    Examples:
        safeshell daemon stop
    """
    if DaemonLifecycle.stop_daemon():
        print_success("Daemon stopped")
    else:
        print_warning("Daemon was not running")


@app.command()
def status() -> None:
    """Show daemon status.

    Displays whether the daemon is running and if the socket
    connection is working.

    Examples:
        safeshell daemon status
    """
    table = Table(title="Daemon Status", show_header=False, box=None)
    table.add_column("Component", style="bold")
    table.add_column("Status")

    if DaemonLifecycle.is_running():
        table.add_row("Process", f"[green]{ICON_SUCCESS} Running[/green]")

        # Try to get more info via ping
        from safeshell.wrapper.client import DaemonClient

        client = DaemonClient()
        if client.ping():
            table.add_row("Socket", f"[green]{ICON_SUCCESS} Connected[/green]")
        else:
            table.add_row("Socket", f"[yellow]{ICON_ERROR} Connection failed[/yellow]")
    else:
        table.add_row("Process", f"[red]{ICON_ERROR} Not running[/red]")

    console.print(table)

    if not DaemonLifecycle.is_running():
        console.print()
        print_info("Start the daemon with: [command]safeshell daemon start[/command]")


@app.command()
def restart() -> None:
    """Restart the SafeShell daemon.

    Stops the daemon if running, then starts a new instance.
    Useful after configuration changes.

    Examples:
        safeshell daemon restart
    """
    if DaemonLifecycle.is_running():
        console.print("[muted]Stopping daemon...[/muted]")
        DaemonLifecycle.stop_daemon()

        # Wait a moment for clean shutdown
        import time

        time.sleep(0.5)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("Starting daemon...", total=None)
        _daemonize()

    print_success("Daemon restarted")


@app.command()
def logs(
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output (like tail -f)"),
    lines: int = typer.Option(50, "--lines", "-n", help="Number of lines to show"),
) -> None:
    """View daemon log file.

    Shows the daemon log from ~/.safeshell/daemon.log.
    Use --follow to continuously watch for new log entries.

    Examples:
        safeshell daemon logs            # Show last 50 lines
        safeshell daemon logs -n 100     # Show last 100 lines
        safeshell daemon logs -f         # Follow log output
    """
    from safeshell.config import load_config

    config = load_config()
    log_path = config.get_log_file_path()

    if not log_path.exists():
        print_error(
            f"Log file not found: {log_path}",
            "The daemon may not have been started yet",
        )
        raise typer.Exit(1)

    if follow:
        # Use subprocess to run tail -f for following
        import shutil
        import subprocess

        console.print(f"[muted]Following {log_path} (Ctrl+C to stop)[/muted]")

        # Find tail in PATH - all inputs are trusted (config path and int lines)
        tail_path = shutil.which("tail")
        if tail_path:
            import contextlib

            with contextlib.suppress(KeyboardInterrupt):
                # S603: inputs are trusted - log_path from config, lines is int
                subprocess.run(  # noqa: S603
                    [tail_path, "-f", "-n", str(lines), str(log_path)],
                    check=True,
                )
        else:
            # tail not available, fall back to manual following
            print_warning("'tail' command not available, using Python fallback")
            _follow_log(log_path, lines)
    else:
        # Read and display last N lines
        try:
            content = log_path.read_text()
            all_lines = content.strip().split("\n")
            display_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            for line in display_lines:
                console.print(line)
        except Exception as e:
            print_error(f"Error reading log file: {e}")
            raise typer.Exit(1) from e


def _follow_log(log_path: "os.PathLike[str]", initial_lines: int) -> None:
    """Follow a log file using Python (fallback when tail is unavailable).

    Args:
        log_path: Path to the log file
        initial_lines: Number of initial lines to display
    """
    import time

    # Show initial lines
    with open(log_path) as f:
        lines = f.readlines()
        for line in lines[-initial_lines:]:
            console.print(line.rstrip())

        # Follow new content
        try:
            while True:
                line = f.readline()
                if line:
                    console.print(line.rstrip())
                else:
                    time.sleep(0.1)
        except KeyboardInterrupt:
            pass


def _daemonize() -> None:
    """Fork and run daemon in background.

    Uses double-fork pattern for proper daemonization.
    """
    # First fork
    try:
        pid = os.fork()
        if pid > 0:
            # Parent - wait briefly for child to start
            import time

            time.sleep(0.5)
            return
    except OSError as e:
        print_error(f"Fork failed: {e}")
        raise typer.Exit(1) from e

    # Child - create new session
    os.setsid()

    # Second fork - prevent acquiring controlling terminal
    try:
        pid = os.fork()
        if pid > 0:
            # First child exits
            os._exit(0)
    except OSError as e:
        print_error(f"Second fork failed: {e}")
        os._exit(1)

    # Grandchild - the actual daemon
    # Redirect standard file descriptors
    # Note: These must remain open for daemon lifetime, context managers not appropriate
    sys.stdin = open(os.devnull)
    sys.stdout = open(os.devnull, "w")
    sys.stderr = open(os.devnull, "w")

    # IMPORTANT: Reconfigure loguru to use the new stderr (which is /dev/null)
    # Loguru captures the original stderr at import time, so we must reconfigure it
    from loguru import logger

    logger.remove()  # Remove default handler pointing to original stderr
    logger.add(sys.stderr, level="DEBUG")  # Add new handler to /dev/null stderr

    # Run the daemon
    asyncio.run(run_daemon())
