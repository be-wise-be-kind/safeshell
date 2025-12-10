"""
File: src/safeshell/common/__init__.py
Purpose: Common utilities and shared constants
Exports: SAFESHELL_DIR, ensure_safeshell_dir
Depends: safeshell.common.paths
Overview: Provides common path utilities used across SafeShell modules
"""

from safeshell.common.paths import SAFESHELL_DIR, ensure_safeshell_dir

__all__ = ["SAFESHELL_DIR", "ensure_safeshell_dir"]
