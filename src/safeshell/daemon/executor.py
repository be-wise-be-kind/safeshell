"""
File: src/safeshell/daemon/executor.py
Purpose: Execute shell commands from within the daemon process
Exports: ExecutionResult, execute_command
Depends: subprocess, time, dataclasses
Overview: Provides command execution with output capture for daemon-based execution
"""

# ruff: noqa: S602 - subprocess with shell=True is intentional for shell command execution

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass


@dataclass
class ExecutionResult:
    """Result of command execution."""

    exit_code: int
    stdout: str
    stderr: str
    execution_time_ms: float


def execute_command(
    command: str,
    working_dir: str,
    env: dict[str, str] | None = None,
) -> ExecutionResult:
    """Execute a shell command and capture output.

    Args:
        command: The command string to execute
        working_dir: Directory to execute command in
        env: Optional environment variables (merged with current env)

    Returns:
        ExecutionResult with exit code, stdout, stderr, and timing
    """
    import os

    # Build environment - start with current env and overlay provided vars
    exec_env = os.environ.copy()
    if env:
        exec_env.update(env)

    start_time = time.perf_counter()

    try:
        result = subprocess.run(  # nosec B602 - shell=True is intentional for shell command execution
            command,
            shell=True,
            cwd=working_dir,
            env=exec_env,
            capture_output=True,
            text=True,
        )
        exit_code = result.returncode
        stdout = result.stdout
        stderr = result.stderr
    except Exception as e:
        # Handle execution errors (e.g., working_dir doesn't exist)
        exit_code = 127  # Command not found / execution error
        stdout = ""
        stderr = f"Execution error: {e}"

    end_time = time.perf_counter()
    execution_time_ms = (end_time - start_time) * 1000

    return ExecutionResult(
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        execution_time_ms=execution_time_ms,
    )
