"""
File: src/safeshell/console.py
Purpose: Shared console configuration for consistent CLI output
Exports: console, print_success, print_error, print_warning, print_info
Depends: rich.console, safeshell.theme
Overview: Centralized Rich console with theme for consistent CLI formatting
"""

from rich.console import Console
from rich.panel import Panel

from safeshell.theme import CLI_THEME, ICON_ERROR, ICON_INFO, ICON_SUCCESS, ICON_WARNING

# Shared console with CLI theme
console = Console(theme=CLI_THEME)


def print_success(message: str) -> None:
    """Print a success message with checkmark icon.

    Args:
        message: The success message to display
    """
    console.print(f"[success]{ICON_SUCCESS}[/success] {message}")


def print_error(message: str, hint: str | None = None) -> None:
    """Print an error message with X icon and optional hint.

    Args:
        message: The error message to display
        hint: Optional actionable suggestion for resolving the error
    """
    console.print(f"[error]{ICON_ERROR}[/error] {message}")
    if hint:
        console.print(f"[info]{ICON_INFO}[/info] {hint}")


def print_warning(message: str) -> None:
    """Print a warning message with warning icon.

    Args:
        message: The warning message to display
    """
    console.print(f"[warning]{ICON_WARNING}[/warning] {message}")


def print_info(message: str) -> None:
    """Print an informational message with arrow icon.

    Args:
        message: The info message to display
    """
    console.print(f"[info]{ICON_INFO}[/info] {message}")


def print_status_panel(title: str, content: str, success: bool = True) -> None:
    """Print a status panel with colored border.

    Args:
        title: Panel title
        content: Panel content
        success: If True, use green border; otherwise red
    """
    border_style = "green" if success else "red"
    console.print(Panel(content, title=title, border_style=border_style))
