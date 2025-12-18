"""
File: src/safeshell/wrapper/shell.py
Purpose: Shell wrapper entry point - intercepts commands from AI tools
Exports: main
Depends: os, sys, plumbum, safeshell.wrapper.client, safeshell.config
Overview: The script that AI tools invoke as their shell (SHELL=/path/to/safeshell-wrapper)
"""

# ruff: noqa: S606 - os.execv is intentional for shell passthrough

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

if TYPE_CHECKING:
    from safeshell.config import SafeShellConfig
    from safeshell.models import ExecutionContext


def main() -> int:
    """Main entry point for shell wrapper.

    Handles shell invocations from AI tools:
    - safeshell-wrapper -c "command"  (execute command string)
    - safeshell-wrapper script.sh     (execute script - passthrough)
    - safeshell-wrapper               (interactive - passthrough)

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Lazy import logger - only configure if we actually use it
    from loguru import logger

    logger.remove()
    logger.add(sys.stderr, level="WARNING")

    # Bypass mode - skip evaluation entirely (used for internal condition checks)
    # This prevents recursive evaluation when daemon runs bash conditions
    if os.environ.get("SAFESHELL_BYPASS") == "1":
        if len(sys.argv) >= 3 and sys.argv[1] == "-c":
            from safeshell.config import load_config

            config = load_config()
            return _execute(sys.argv[2], config.delegate_shell)
        return _passthrough()

    # Handle -c "command" invocation (primary use case)
    if len(sys.argv) >= 3 and sys.argv[1] == "-c":
        command = sys.argv[2]
        return _evaluate_and_execute(command)

    # All other invocations: passthrough to real shell
    return _passthrough()


def _detect_execution_context() -> ExecutionContext:
    """Detect if running in AI context.

    Vendor-specific detection is centralized here.
    Add new AI tool detection in this function only.

    Returns:
        ExecutionContext.AI if in AI-controlled context, ExecutionContext.HUMAN otherwise
    """
    from safeshell.models import ExecutionContext

    # Claude Code sets SAFESHELL_CONTEXT=ai
    if os.environ.get("SAFESHELL_CONTEXT") == "ai":
        return ExecutionContext.AI
    # Warp AI agent mode
    if os.environ.get("WARP_AI_AGENT") == "1":
        return ExecutionContext.AI
    # Add other AI tool detections here:
    # if os.environ.get("CURSOR_AI"):
    #     return ExecutionContext.AI
    return ExecutionContext.HUMAN


def _handle_denied_command(denial_message: str | None) -> int:
    """Handle a denied command by printing the message and returning exit code."""
    msg = denial_message or "[SafeShell] Command blocked by policy"
    sys.stderr.write(msg + "\n")
    return 1


def _execute_or_signal(command: str, shell: str, check_only: bool) -> int:
    """Execute command or signal allowed (for check-only mode)."""
    if check_only:
        return 0  # Signal allowed, shim will execute
    return _execute(command, shell)


def _evaluate_and_execute(command: str) -> int:
    """Evaluate command with daemon and execute if allowed.

    Args:
        command: Command string to evaluate

    Returns:
        Exit code from command execution or 1 if denied
    """
    from safeshell.config import load_config
    from safeshell.exceptions import DaemonNotRunningError, DaemonStartError
    from safeshell.wrapper.client import DaemonClient

    config = load_config()
    client = DaemonClient()
    check_only = os.environ.get("SAFESHELL_CHECK_ONLY") == "1"
    execution_context = _detect_execution_context()

    try:
        client.ensure_daemon_running()
        response = client.evaluate(
            command=command,
            working_dir=str(Path.cwd()),
            env=dict(os.environ),
            execution_context=execution_context,
        )

        if response.should_execute:
            return _execute_or_signal(command, config.delegate_shell, check_only)
        return _handle_denied_command(response.denial_message)

    except (DaemonNotRunningError, DaemonStartError) as e:
        return _handle_daemon_unreachable(e, config, command, check_only)


def _handle_daemon_unreachable(
    error: Exception,
    config: SafeShellConfig,
    command: str,
    check_only: bool,
) -> int:
    """Handle daemon unreachable based on config."""
    from safeshell.config import UnreachableBehavior

    if config.unreachable_behavior == UnreachableBehavior.FAIL_OPEN:
        sys.stderr.write(f"[SafeShell] Warning: Daemon unreachable ({error}), allowing command\n")
        return _execute_or_signal(command, config.delegate_shell, check_only)

    # FAIL_CLOSED (default)
    sys.stderr.write(f"[SafeShell] Error: Daemon unreachable ({error})\n")
    sys.stderr.write("[SafeShell] Command blocked (fail-closed mode)\n")
    return 1


def _execute(command: str, shell: str) -> int:
    """Execute command using the delegate shell.

    Args:
        command: Command to execute
        shell: Path to real shell (e.g., /bin/bash)

    Returns:
        Exit code from command
    """
    from plumbum import local
    from plumbum.commands.processes import ProcessExecutionError

    try:
        real_shell = local[shell]
        retcode_raw, stdout, stderr = real_shell["-c", command].run(retcode=None)

        # Write output to stdout/stderr
        if stdout:
            sys.stdout.write(stdout)
        if stderr:
            sys.stderr.write(stderr)

        # Ensure we return an int (plumbum returns Any)
        retcode: int = int(retcode_raw) if retcode_raw is not None else 0
        return retcode

    except ProcessExecutionError as e:
        sys.stderr.write(str(e) + "\n")
        return e.retcode if e.retcode else 1
    except Exception as e:
        sys.stderr.write(f"[SafeShell] Execution error: {e}\n")
        return 1


def _passthrough() -> NoReturn:
    """Pass through to real shell for non -c invocations.

    Replaces current process with real shell.
    """
    from safeshell.config import load_config

    config = load_config()
    shell = config.delegate_shell

    # Use os.execv to replace process
    os.execv(shell, [shell] + sys.argv[1:])

    # Should never reach here
    sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
