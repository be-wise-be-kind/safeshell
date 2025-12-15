"""
File: src/safeshell/wrapper/shell.py
Purpose: Shell wrapper entry point - intercepts commands from AI tools
Exports: main
Depends: os, sys, plumbum, safeshell.wrapper.client, safeshell.config
Overview: The script that AI tools invoke as their shell (SHELL=/path/to/safeshell-wrapper)
"""

# ruff: noqa: S606 - os.execv is intentional for shell passthrough

import os
import sys
from pathlib import Path
from typing import NoReturn

from loguru import logger

from safeshell.config import UnreachableBehavior, load_config
from safeshell.exceptions import DaemonNotRunningError, DaemonStartError
from safeshell.models import ExecutionContext
from safeshell.wrapper.client import DaemonClient


def main() -> int:
    """Main entry point for shell wrapper.

    Handles shell invocations from AI tools:
    - safeshell-wrapper -c "command"  (execute command string)
    - safeshell-wrapper script.sh     (execute script - passthrough)
    - safeshell-wrapper               (interactive - passthrough)

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Configure logging (minimal for wrapper - speed is critical)
    logger.remove()
    logger.add(sys.stderr, level="WARNING")

    # Bypass mode - skip evaluation entirely (used for internal condition checks)
    # This prevents recursive evaluation when daemon runs bash conditions
    if os.environ.get("SAFESHELL_BYPASS") == "1":
        if len(sys.argv) >= 3 and sys.argv[1] == "-c":
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


def _evaluate_and_execute(command: str) -> int:
    """Evaluate command with daemon and execute if allowed.

    Args:
        command: Command string to evaluate

    Returns:
        Exit code from command execution or 1 if denied
    """
    config = load_config()
    client = DaemonClient()

    # Check-only mode for shims - evaluate but don't execute
    check_only = os.environ.get("SAFESHELL_CHECK_ONLY") == "1"

    # Determine execution context (vendor detection centralized here)
    execution_context = _detect_execution_context()

    try:
        # Ensure daemon is running (auto-start if needed)
        client.ensure_daemon_running()

        # Evaluate command
        response = client.evaluate(
            command=command,
            working_dir=str(Path.cwd()),
            env=dict(os.environ),
            execution_context=execution_context,
        )

        if response.should_execute:
            if check_only:
                return 0  # Signal allowed, shim will execute
            return _execute(command, config.delegate_shell)
        # Command denied - print message and exit
        if response.denial_message:
            sys.stderr.write(response.denial_message + "\n")
        else:
            sys.stderr.write("[SafeShell] Command blocked by policy\n")
        return 1

    except (DaemonNotRunningError, DaemonStartError) as e:
        # Handle based on config
        if config.unreachable_behavior == UnreachableBehavior.FAIL_OPEN:
            sys.stderr.write(f"[SafeShell] Warning: Daemon unreachable ({e}), allowing command\n")
            if check_only:
                return 0  # Signal allowed, shim will execute
            return _execute(command, config.delegate_shell)
        # FAIL_CLOSED (default)
        sys.stderr.write(f"[SafeShell] Error: Daemon unreachable ({e})\n")
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
    config = load_config()
    shell = config.delegate_shell

    # Use os.execv to replace process
    os.execv(shell, [shell] + sys.argv[1:])

    # Should never reach here
    sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
