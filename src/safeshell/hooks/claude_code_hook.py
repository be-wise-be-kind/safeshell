#!/usr/bin/env python3
"""
File: src/safeshell/hooks/claude_code_hook.py
Purpose: Claude Code PreToolUse hook for SafeShell command interception
Exports: main() entry point
Depends: json, subprocess, sys, os
Overview: Intercepts Claude Code Bash commands and validates them with SafeShell daemon

Usage:
    Configure in ~/.claude/settings.json:
    {
      "hooks": {
        "PreToolUse": [
          {
            "matcher": "Bash",
            "hooks": ["/path/to/safeshell/hooks/claude_code_hook.py"]
          }
        ]
      }
    }

Exit codes:
    0 - Allow the command
    2 - Block the command (Claude Code will not execute)
"""

# ruff: noqa: S603, S607 - subprocess calls with known commands are intentional

import json
import os
import subprocess
import sys
from pathlib import Path

# Timeout for approval flow (10 minutes)
_APPROVAL_TIMEOUT_SECONDS = 600


def _is_executable(path: Path) -> bool:
    """Check if path is an executable file."""
    return path.is_file() and os.access(path, os.X_OK)


def _find_in_pyenv_versions() -> str | None:
    """Search pyenv versions for safeshell-wrapper.

    Handles the case where safeshell is installed in a different Python version
    than the currently active one.
    """
    pyenv_versions = Path.home() / ".pyenv/versions"
    if not pyenv_versions.is_dir():
        return None

    for version_dir in pyenv_versions.iterdir():
        if not version_dir.is_dir():
            continue
        wrapper = version_dir / "bin/safeshell-wrapper"
        if _is_executable(wrapper):
            return str(wrapper)

    return None


def _find_via_poetry() -> str | None:
    """Try to find safeshell-wrapper via poetry run (development mode)."""
    project_dir = Path.home() / "Projects/safeshell"
    if not (project_dir / "pyproject.toml").exists():
        return None

    try:
        result = subprocess.run(
            ["poetry", "run", "which", "safeshell-wrapper"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return None


def find_wrapper() -> str | None:
    """Find safeshell-wrapper executable.

    Searches in order:
    1. Current PATH
    2. Common installation locations (~/.local/bin, /usr/local/bin)
    3. pyenv versions directories (handles pyenv version mismatch)
    4. Development mode via poetry run
    """
    # Check PATH first
    for path_dir in os.environ.get("PATH", "").split(os.pathsep):
        wrapper = Path(path_dir) / "safeshell-wrapper"
        if _is_executable(wrapper):
            return str(wrapper)

    # Check common locations
    locations = [
        Path.home() / ".local/bin/safeshell-wrapper",
        Path("/usr/local/bin/safeshell-wrapper"),
    ]

    for loc in locations:
        if _is_executable(loc):
            return str(loc)

    # Check pyenv versions
    pyenv_result = _find_in_pyenv_versions()
    if pyenv_result:
        return pyenv_result

    # Development mode: try poetry run
    return _find_via_poetry()


def check_command(command: str) -> tuple[bool, str]:
    """Check if command is allowed by SafeShell.

    Args:
        command: The command to check

    Returns:
        Tuple of (allowed, message)
    """
    wrapper = find_wrapper()
    if wrapper is None:
        # Fail open if wrapper not found
        return True, "SafeShell wrapper not found, allowing command"

    # Check if daemon socket exists
    socket_path = Path(os.environ.get("SAFESHELL_SOCKET", Path.home() / ".safeshell/daemon.sock"))
    if not socket_path.exists():
        # Daemon not running - fail open
        return True, "SafeShell daemon not running, allowing command"

    try:
        env = os.environ.copy()
        env["SAFESHELL_CHECK_ONLY"] = "1"
        env["SAFESHELL_CONTEXT"] = "ai"  # Mark as AI agent execution

        result = subprocess.run(
            [wrapper, "-c", command],
            env=env,
            capture_output=True,
            text=True,
            timeout=_APPROVAL_TIMEOUT_SECONDS,
        )

        if result.returncode == 0:
            # Pass through stderr (may contain approval message for AI to see)
            return True, result.stderr.strip() if result.stderr else ""
        # Command blocked
        message = result.stderr.strip() if result.stderr else "Command blocked by SafeShell"
        return False, message

    except subprocess.TimeoutExpired:
        return False, "SafeShell approval timed out"
    except Exception as e:
        # Fail open on errors
        return True, f"SafeShell error: {e}"


def main() -> int:
    """Main entry point for the hook."""
    # Read hook input from stdin
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        # If we can't parse input, allow (fail open)
        return 0

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Only intercept Bash commands
    if tool_name != "Bash":
        return 0

    command = tool_input.get("command", "")
    if not command:
        return 0

    # Check with SafeShell
    allowed, message = check_command(command)

    if allowed:
        # Print any approval/status message for Claude to see
        if message:
            print(message, file=sys.stderr)
        return 0
    # Print block message for Claude to see
    if message:
        print(message, file=sys.stderr)
    return 2  # Exit 2 tells Claude Code to block


if __name__ == "__main__":
    sys.exit(main())
