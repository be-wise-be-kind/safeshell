"""
File: src/safeshell/exceptions.py
Purpose: Custom exception hierarchy for SafeShell
Exports: SafeShellError, DaemonError, DaemonNotRunningError, PluginError, ProtocolError,
         ConfigError, RuleLoadError
Depends: None
Overview: Defines the exception classes used throughout SafeShell for error handling
"""


class SafeShellError(Exception):
    """Base exception for all SafeShell errors."""


class DaemonError(SafeShellError):
    """Errors related to daemon operations."""


class DaemonNotRunningError(DaemonError):
    """Daemon is not running or unreachable."""


class DaemonStartError(DaemonError):
    """Failed to start the daemon."""


class PluginError(SafeShellError):
    """Errors related to plugin operations."""


class PluginLoadError(PluginError):
    """Failed to load a plugin."""


class ProtocolError(SafeShellError):
    """Errors in message protocol between wrapper and daemon."""


class ConfigError(SafeShellError):
    """Errors related to configuration loading or validation."""


class RuleLoadError(SafeShellError):
    """Errors related to rule file loading or validation."""
