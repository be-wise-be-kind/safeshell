"""
File: src/safeshell/wrapper/cli.py
Purpose: CLI commands for shell wrapper management
Exports: app (Typer app)
Depends: typer, rich, safeshell.config
Overview: Provides install command with setup instructions for AI tools
"""

import sys

import typer
from rich.console import Console
from rich.panel import Panel

from safeshell.config import SafeShellConfig

app = typer.Typer(name="wrapper", help="Manage the SafeShell shell wrapper")
console = Console()


@app.command()
def install() -> None:
    """Show installation instructions for AI tools."""
    # Detect wrapper path
    wrapper_path = _get_wrapper_path()
    real_shell = SafeShellConfig.detect_default_shell()

    console.print(Panel.fit(
        "[bold blue]SafeShell Wrapper Installation[/bold blue]",
        border_style="blue",
    ))

    console.print()
    console.print(f"[bold]Wrapper location:[/bold] {wrapper_path}")
    console.print(f"[bold]Your shell:[/bold] {real_shell}")
    console.print()

    console.print("[bold yellow]Configure your AI tool:[/bold yellow]")
    console.print()

    # Claude Code
    console.print("[bold]Claude Code:[/bold]")
    console.print(f"  claude config set shell {wrapper_path}")
    console.print()

    # Cursor
    console.print("[bold]Cursor:[/bold]")
    console.print(f"  Settings → Terminal → Shell Path → {wrapper_path}")
    console.print()

    # Generic
    console.print("[bold]Generic (environment variable):[/bold]")
    console.print(f"  export SHELL={wrapper_path}")
    console.print()

    console.print("[bold yellow]Then start the daemon:[/bold yellow]")
    console.print("  safeshell daemon start")
    console.print()

    console.print("[dim]The daemon must be running for SafeShell to evaluate commands.[/dim]")


@app.command()
def path() -> None:
    """Print the wrapper path (for scripting)."""
    console.print(_get_wrapper_path())


def _get_wrapper_path() -> str:
    """Get the path to the safeshell-wrapper executable.

    Returns:
        Path to wrapper, or instruction if not found
    """
    # Try to find safeshell-wrapper in the same location as python
    from pathlib import Path

    # Check if we're in a poetry/venv environment
    python_path = Path(sys.executable)
    bin_dir = python_path.parent

    wrapper_path = bin_dir / "safeshell-wrapper"
    if wrapper_path.exists():
        return str(wrapper_path)

    # Fall back to assuming it's installed globally
    return "safeshell-wrapper"
