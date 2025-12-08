"""
File: src/safeshell/shims/__init__.py
Purpose: Shim management module for command interception
Exports: ShimManager exports, SHIM_DIR, refresh_shims
Depends: safeshell.shims.manager
Overview: Public API for shim-based command interception system
"""

from safeshell.shims.manager import (
    SHIM_DIR,
    create_shim,
    ensure_shim_directory,
    get_commands_from_rules,
    get_existing_shims,
    get_init_script_path,
    get_shell_init_instructions,
    get_shim_dir,
    get_source_shim_path,
    install_init_script,
    install_shim_script,
    refresh_shims,
    remove_shim,
)

__all__ = [
    "SHIM_DIR",
    "create_shim",
    "ensure_shim_directory",
    "get_commands_from_rules",
    "get_existing_shims",
    "get_init_script_path",
    "get_shell_init_instructions",
    "get_shim_dir",
    "get_source_shim_path",
    "install_init_script",
    "install_shim_script",
    "refresh_shims",
    "remove_shim",
]
