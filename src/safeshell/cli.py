"""SafeShell CLI - Command-line safety layer for AI coding assistants."""

import typer
from rich.console import Console

app = typer.Typer(
    name="safeshell",
    help="Command-line safety layer for AI coding assistants.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def version() -> None:
    """Show the SafeShell version."""
    console.print("[bold]SafeShell[/bold] v0.1.0")


@app.command()
def check(command: str) -> None:
    """Check if a command is safe to execute.

    Args:
        command: The shell command to evaluate.
    """
    console.print(f"[yellow]Checking command:[/yellow] {command}")
    # TODO: Implement command evaluation logic
    console.print("[green]Command appears safe.[/green]")


@app.command()
def status() -> None:
    """Show SafeShell daemon status."""
    console.print("[yellow]SafeShell daemon status:[/yellow]")
    console.print("  Status: [red]Not running[/red]")
    console.print("  Plugins: None loaded")


if __name__ == "__main__":
    app()
