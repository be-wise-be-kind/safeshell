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
from collections.abc import Callable
from typing import TextIO

import typer
from rich.console import Console

from safeshell.daemon.lifecycle import DaemonLifecycle
from safeshell.daemon.server import run_daemon

# CLI constants
_DAEMON_STARTUP_DELAY = 0.5  # seconds to wait for daemon to start
_DEFAULT_LOG_LINES = 50
_LOG_POLL_INTERVAL = 0.1  # seconds between log polls

app = typer.Typer(name="daemon", help="Manage the SafeShell daemon")
console = Console()


@app.command()
def start(
    foreground: bool = typer.Option(
        False, "--foreground", "-f", help="Run in foreground (don't daemonize)"
    ),
) -> None:
    """Start the SafeShell daemon."""
    try:
        with DaemonLifecycle.startup_lock():
            if DaemonLifecycle.is_running():
                console.print("[yellow]Daemon is already running[/yellow]")
                raise typer.Exit(0)

            if foreground:
                console.print("[green]Starting daemon in foreground...[/green]")
                console.print("Press Ctrl+C to stop")
                asyncio.run(run_daemon())
            else:
                _daemonize()
                console.print("[green]Daemon started[/green]")
    except RuntimeError as e:
        console.print(f"[yellow]{e}[/yellow]")
        raise typer.Exit(0) from e


@app.command()
def stop() -> None:
    """Stop the SafeShell daemon."""
    if DaemonLifecycle.stop_daemon():
        console.print("[green]Daemon stopped[/green]")
    else:
        console.print("[yellow]Daemon was not running[/yellow]")


@app.command()
def status() -> None:
    """Show daemon status."""
    if DaemonLifecycle.is_running():
        console.print("[green]Daemon is running[/green]")

        # Try to get more info via ping
        from safeshell.wrapper.client import DaemonClient

        client = DaemonClient()
        if client.ping():
            console.print("  Socket: connected")
        else:
            console.print("  [yellow]Socket: connection failed[/yellow]")
    else:
        console.print("[red]Daemon is not running[/red]")


@app.command()
def restart() -> None:
    """Restart the SafeShell daemon."""
    if DaemonLifecycle.is_running():
        console.print("Stopping daemon...")
        DaemonLifecycle.stop_daemon()

        # Wait a moment for clean shutdown
        import time

        time.sleep(_DAEMON_STARTUP_DELAY)

    _daemonize()
    console.print("[green]Daemon restarted[/green]")


@app.command()
def logs(
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output (like tail -f)"),
    lines: int = typer.Option(_DEFAULT_LOG_LINES, "--lines", "-n", help="Number of lines to show"),
) -> None:
    """View daemon log file.

    Shows the daemon log from ~/.safeshell/daemon.log.
    Use --follow to continuously watch for new log entries.
    """
    from safeshell.config import load_config

    config = load_config()
    log_path = config.get_log_file_path()

    if not log_path.exists():
        console.print(f"[yellow]Log file not found:[/yellow] {log_path}")
        console.print("The daemon may not have been started yet.")
        raise typer.Exit(1)

    if follow:
        # Use subprocess to run tail -f for following
        import shutil
        import subprocess

        console.print(f"[dim]Following {log_path} (Ctrl+C to stop)[/dim]")

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
            console.print("[yellow]'tail' command not available, using Python fallback[/yellow]")
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
            console.print(f"[red]Error reading log file:[/red] {e}")
            raise typer.Exit(1) from e


def _tail_file(file: TextIO, sleep_fn: Callable[[float], None]) -> None:
    """Continuously read and print new lines from a file.

    Args:
        file: Open file handle positioned at end of initial content
        sleep_fn: Function to call for sleeping (allows injection for testing)
    """
    try:
        while True:
            line = file.readline()
            if line:
                console.print(line.rstrip())
            else:
                sleep_fn(_LOG_POLL_INTERVAL)
    except KeyboardInterrupt:
        pass


def _follow_log(log_path: "os.PathLike[str]", initial_lines: int) -> None:
    """Follow a log file using Python (fallback when tail is unavailable).

    Args:
        log_path: Path to the log file
        initial_lines: Number of initial lines to display
    """
    import time

    with open(log_path) as f:
        # Show initial lines
        lines = f.readlines()
        for line in lines[-initial_lines:]:
            console.print(line.rstrip())

        # Follow new content
        _tail_file(f, time.sleep)


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

            time.sleep(_DAEMON_STARTUP_DELAY)
            return
    except OSError as e:
        console.print(f"[red]Fork failed: {e}[/red]")
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
        console.print(f"[red]Second fork failed: {e}[/red]")
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
