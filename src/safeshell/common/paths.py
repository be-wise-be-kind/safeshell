"""
File: src/safeshell/common/paths.py
Purpose: Common path constants and utilities
Exports: SAFESHELL_DIR, ensure_safeshell_dir
Depends: pathlib
Overview: Central location for SafeShell directory paths used across modules
"""

from pathlib import Path

# Base directory for SafeShell user data
SAFESHELL_DIR = Path.home() / ".safeshell"


def ensure_safeshell_dir() -> Path:
    """Ensure the SafeShell directory exists.

    Creates ~/.safeshell if it doesn't exist.

    Returns:
        Path to the SafeShell directory
    """
    SAFESHELL_DIR.mkdir(parents=True, exist_ok=True)
    return SAFESHELL_DIR
