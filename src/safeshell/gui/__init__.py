"""
File: src/safeshell/gui/__init__.py
Purpose: PyQt6 GUI module for SafeShell system tray application
Exports: run_gui
Depends: safeshell.gui.app
Overview: Provides a system tray application with popup windows for command approval
"""

from safeshell.gui.app import run_gui

__all__ = ["run_gui"]
