"""
File: src/safeshell/cli.py
Purpose: Main CLI entry point for SafeShell
Exports: app (Typer app)
Depends: typer, rich, safeshell.daemon.cli, safeshell.wrapper.cli
Overview: Provides version, check, status commands and registers daemon/wrapper subcommands
"""

import os

import typer
from rich.console import Console

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
            working_dir=os.getcwd(),
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
def init() -> None:
    """Initialize SafeShell configuration."""
    from safeshell.config import CONFIG_PATH, create_default_config

    if CONFIG_PATH.exists():
        console.print(f"[yellow]Config already exists at:[/yellow] {CONFIG_PATH}")
        if not typer.confirm("Overwrite?"):
            raise typer.Exit(0)

    config = create_default_config()
    console.print("[green]SafeShell initialized![/green]")
    console.print()
    console.print(f"  Config: {CONFIG_PATH}")
    console.print(f"  Shell:  {config.delegate_shell}")
    console.print()
    console.print("Next steps:")
    console.print("  1. Start the daemon: safeshell daemon start")
    console.print("  2. Configure your AI tool: safeshell wrapper install")


if __name__ == "__main__":
    app()
