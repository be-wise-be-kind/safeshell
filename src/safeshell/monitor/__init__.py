"""
File: src/safeshell/monitor/__init__.py
Purpose: Monitor TUI module for SafeShell
Exports: MonitorApp, MonitorClient
Depends: textual
Overview: Textual-based terminal UI for monitoring SafeShell daemon and handling approvals
"""

from safeshell.monitor.app import MonitorApp
from safeshell.monitor.client import MonitorClient

__all__ = ["MonitorApp", "MonitorClient"]
