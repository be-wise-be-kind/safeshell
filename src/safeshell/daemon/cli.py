"""
File: src/safeshell/daemon/cli.py
Purpose: CLI commands for daemon management
Exports: app (Typer app)
Depends: typer, rich, asyncio, safeshell.daemon
Overview: Provides start, stop, status commands for daemon management
"""

# ruff: noqa: SIM115 - open() for daemonization must stay open for process lifetime

import asyncio
import os
import sys

import typer
from rich.console import Console

from safeshell.daemon.lifecycle import DaemonLifecycle
from safeshell.daemon.server import run_daemon

app = typer.Typer(name="daemon", help="Manage the SafeShell daemon")
console = Console()


@app.command()
def start(
    foreground: bool = typer.Option(
        False, "--foreground", "-f", help="Run in foreground (don't daemonize)"
    ),
) -> None:
    """Start the SafeShell daemon."""
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

        time.sleep(0.5)

    _daemonize()
    console.print("[green]Daemon restarted[/green]")


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
