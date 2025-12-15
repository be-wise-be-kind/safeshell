"""
File: src/safeshell/theme.py
Purpose: Shared theme configuration for TUI and CLI
Exports: Color constants, CLI_THEME, TUI_COLORS
Depends: rich.theme
Overview: Centralized theme definitions for consistent styling across SafeShell
"""

from rich.theme import Theme

# Color palette - semantic colors for consistent usage
PRIMARY = "#00aa00"  # Green - success, approval, safe
SECONDARY = "#0088ff"  # Blue - info, neutral
DANGER = "#ff0000"  # Red - error, denial, dangerous
WARNING = "#ffaa00"  # Yellow - warning, pending, caution
SUCCESS = PRIMARY

# Additional UI colors
SURFACE = "#2a2a2a"  # Background for elevated elements
TEXT_PRIMARY = "#ffffff"  # Primary text
TEXT_MUTED = "#888888"  # Secondary/muted text
BORDER_DEFAULT = "#444444"  # Default border color

# Semantic icon characters (widely-supported Unicode)
ICON_SUCCESS = "\u2713"  # Check mark
ICON_ERROR = "\u2717"  # X mark
ICON_WARNING = "\u26a0"  # Warning triangle
ICON_INFO = "\u2192"  # Right arrow
ICON_PENDING = "\u23f3"  # Hourglass
ICON_WAITING = "\u2753"  # Question mark

# Rich theme for CLI output
CLI_THEME = Theme(
    {
        "success": f"bold {SUCCESS}",
        "error": f"bold {DANGER}",
        "warning": f"bold {WARNING}",
        "info": f"bold {SECONDARY}",
        "command": "cyan",
        "path": "magenta",
        "muted": "dim white",
        "highlight": "bold white",
    }
)

# TUI color references (for documentation and CSS generation)
TUI_COLORS = {
    "primary": PRIMARY,
    "secondary": SECONDARY,
    "danger": DANGER,
    "warning": WARNING,
    "success": SUCCESS,
    "surface": SURFACE,
    "text-primary": TEXT_PRIMARY,
    "text-muted": TEXT_MUTED,
}
