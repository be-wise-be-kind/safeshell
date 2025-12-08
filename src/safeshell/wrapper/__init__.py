"""
File: src/safeshell/wrapper/__init__.py
Purpose: Shell wrapper package exports
Exports: DaemonClient
Depends: safeshell.wrapper.client
Overview: Re-exports wrapper components for convenient imports
"""

from safeshell.wrapper.client import DaemonClient

__all__ = ["DaemonClient"]
