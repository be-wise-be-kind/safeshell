"""
File: src/safeshell/shims/manager.py
Purpose: Manage shim symlinks for command interception
Exports: ShimManager, get_shim_dir, SHIM_DIR
Depends: pathlib, shutil, loguru, safeshell.rules.loader, safeshell.daemon.lifecycle
Overview: Creates and manages shim symlinks in ~/.safeshell/shims/ for commands in rules.yaml
"""

import shutil
import stat
from pathlib import Path

from loguru import logger

from safeshell.common import SAFESHELL_DIR
from safeshell.rules.loader import GLOBAL_RULES_PATH, load_rules

# Shim directory location
SHIM_DIR = SAFESHELL_DIR / "shims"

# Name of the universal shim script
SHIM_SCRIPT_NAME = "safeshell-shim"

# Commands that should never be shimmed (shell builtins handled by init.bash)
BUILTIN_COMMANDS = frozenset({"cd", "source", "eval", ".", "export", "alias", "unalias"})


def get_shim_dir() -> Path:
    """Get the path to the shims directory.

    Returns:
        Path to ~/.safeshell/shims/
    """
    return SHIM_DIR


def get_commands_from_rules(working_dir: str | Path | None = None) -> set[str]:
    """Extract unique commands from all loaded rules.

    Args:
        working_dir: Working directory for loading repo-specific rules.
                    If None, only global rules are loaded.

    Returns:
        Set of unique command names from all rules
    """
    commands: set[str] = set()

    # Load rules
    if working_dir:
        rules = load_rules(working_dir)
    else:
        # Load only global rules
        if GLOBAL_RULES_PATH.exists():
            from safeshell.rules.loader import _load_rule_file

            rules = _load_rule_file(GLOBAL_RULES_PATH)
        else:
            rules = []

    for rule in rules:
        for cmd in rule.commands:
            # Skip builtins - they're handled by shell function overrides
            if cmd not in BUILTIN_COMMANDS:
                commands.add(cmd)

    return commands


def get_source_shim_path() -> Path:
    """Get path to the universal shim script in the package.

    Returns:
        Path to the bundled safeshell-shim script
    """
    return Path(__file__).parent / SHIM_SCRIPT_NAME


def ensure_shim_directory() -> None:
    """Create the shims directory if it doesn't exist."""
    SHIM_DIR.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Ensured shim directory exists: {SHIM_DIR}")


def install_shim_script() -> Path:
    """Copy the universal shim script to the shims directory.

    Returns:
        Path to the installed shim script

    Raises:
        FileNotFoundError: If the source shim script is not found
    """
    source = get_source_shim_path()
    if not source.exists():
        raise FileNotFoundError(f"Universal shim script not found: {source}")

    ensure_shim_directory()
    dest = SHIM_DIR / SHIM_SCRIPT_NAME

    # Copy and make executable
    shutil.copy2(source, dest)
    dest.chmod(dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    logger.debug(f"Installed shim script: {dest}")
    return dest


def create_shim(command: str) -> Path:
    """Create a shim symlink for a command.

    Args:
        command: The command name to create a shim for (e.g., "git")

    Returns:
        Path to the created symlink
    """
    shim_link = SHIM_DIR / command

    # Remove existing symlink if it exists
    if shim_link.is_symlink():
        shim_link.unlink()
    elif shim_link.exists():
        # Not a symlink, could be a real file - don't overwrite
        logger.warning(f"Skipping {command}: not a symlink at {shim_link}")
        return shim_link

    # Create relative symlink to the shim script
    shim_link.symlink_to(SHIM_SCRIPT_NAME)
    logger.debug(f"Created shim: {command} -> {SHIM_SCRIPT_NAME}")

    return shim_link


def remove_shim(command: str) -> bool:
    """Remove a shim symlink.

    Args:
        command: The command name whose shim to remove

    Returns:
        True if removed, False if not found or not a symlink
    """
    shim_link = SHIM_DIR / command

    if not shim_link.exists() and not shim_link.is_symlink():
        return False

    if not shim_link.is_symlink():
        logger.warning(f"Not removing {command}: not a symlink")
        return False

    shim_link.unlink()
    logger.debug(f"Removed shim: {command}")
    return True


def get_existing_shims() -> set[str]:
    """Get the set of currently installed shims.

    Returns:
        Set of command names that have shim symlinks
    """
    if not SHIM_DIR.exists():
        return set()

    shims = set()
    for entry in SHIM_DIR.iterdir():
        # Skip the shim script itself and non-symlinks
        if entry.name == SHIM_SCRIPT_NAME:
            continue
        if entry.is_symlink():
            shims.add(entry.name)

    return shims


def refresh_shims(working_dir: str | Path | None = None) -> dict[str, list[str]]:
    """Refresh shims to match current rules.

    This will:
    1. Ensure the shims directory exists
    2. Install/update the universal shim script
    3. Create shims for all commands in rules.yaml
    4. Remove stale shims for commands no longer in rules

    Args:
        working_dir: Working directory for loading repo-specific rules.
                    If None, only global rules are used.

    Returns:
        Dict with "created", "removed", and "unchanged" lists of command names
    """
    result: dict[str, list[str]] = {
        "created": [],
        "removed": [],
        "unchanged": [],
    }

    # Ensure directory and shim script exist
    ensure_shim_directory()
    install_shim_script()

    # Get commands that need shims
    needed_commands = get_commands_from_rules(working_dir)
    existing_shims = get_existing_shims()

    # Create new shims
    to_create = needed_commands - existing_shims
    for cmd in sorted(to_create):
        create_shim(cmd)
        result["created"].append(cmd)

    # Remove stale shims
    to_remove = existing_shims - needed_commands
    for cmd in sorted(to_remove):
        if remove_shim(cmd):
            result["removed"].append(cmd)

    # Track unchanged
    unchanged = needed_commands & existing_shims
    result["unchanged"] = sorted(unchanged)

    logger.info(
        f"Shim refresh: {len(result['created'])} created, "
        f"{len(result['removed'])} removed, "
        f"{len(result['unchanged'])} unchanged"
    )

    return result


def get_init_script_path() -> Path:
    """Get path to the shell init script in the package.

    Returns:
        Path to the bundled init.bash script
    """
    return Path(__file__).parent / "init.bash"


def install_init_script() -> Path:
    """Copy the shell init script to the safeshell directory.

    Returns:
        Path to the installed init script
    """
    source = get_init_script_path()
    if not source.exists():
        raise FileNotFoundError(f"Init script not found: {source}")

    dest = SAFESHELL_DIR / "init.bash"
    shutil.copy2(source, dest)
    logger.debug(f"Installed init script: {dest}")

    return dest


def get_shell_init_instructions() -> str:
    """Get instructions for adding safeshell to shell initialization.

    Returns:
        Multi-line string with setup instructions
    """
    init_path = SAFESHELL_DIR / "init.bash"
    return f"""
To enable SafeShell protection, add this to your shell config:

For ~/.bashrc or ~/.bash_profile:
    source {init_path}

For ~/.zshrc:
    source {init_path}

This will:
  - Add ~/.safeshell/shims to your PATH (for command interception)
  - Override dangerous builtins (cd, source, eval) with safe versions
  - Fail-open if daemon isn't running (normal shell behavior)

After adding, restart your shell or run: source {init_path}
"""
