"""
File: src/safeshell/rules/cache.py
Purpose: Rule caching with file modification time invalidation
Exports: RuleCache, CachedRuleSet
Depends: safeshell.rules.loader, safeshell.rules.schema, pathlib, time, dataclasses
Overview: Caches loaded rules and invalidates when source files change
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from safeshell.rules.loader import GLOBAL_RULES_PATH, _find_repo_rules, _load_rule_file

if TYPE_CHECKING:
    from safeshell.rules.schema import Rule


@dataclass
class CachedRuleSet:
    """Cached rules with their source file modification times.

    Tracks the rules loaded from global and repo rule files along with
    their modification times at load time for cache invalidation.
    """

    rules: list[Rule]
    file_mtimes: dict[Path, float] = field(default_factory=dict)  # path -> mtime at load
    loaded_at: float = field(default_factory=time.time)


class RuleCache:
    """Cache for loaded rules with file-based invalidation.

    Tracks modification times of source rule files (global and repo)
    and invalidates cache when files change. This eliminates the overhead
    of parsing YAML and validating with Pydantic on every request.

    Thread Safety:
        This class is not thread-safe. It's designed for use within
        a single async event loop (the daemon's asyncio loop).
    """

    def __init__(self) -> None:
        """Initialize an empty rule cache."""
        # Cache keyed by working directory (determines which repo rules apply)
        self._cache: dict[str, CachedRuleSet] = {}
        self._hits: int = 0
        self._misses: int = 0

    def get_rules(self, working_dir: str | Path) -> tuple[list[Rule], bool]:
        """Get rules for working directory, using cache if valid.

        Checks if cached rules exist and are still valid (source files
        haven't been modified). If valid, returns cached rules. Otherwise,
        loads fresh rules and updates the cache.

        Args:
            working_dir: Working directory for repo rule discovery

        Returns:
            Tuple of (rules list, was_cache_hit)
        """
        working_dir_str = str(Path(working_dir).resolve())

        # Check if we have a valid cache entry
        if working_dir_str in self._cache:
            cached = self._cache[working_dir_str]
            if self._is_cache_valid(cached, working_dir_str):
                self._hits += 1
                logger.debug(f"Rule cache hit for {working_dir_str}")
                return cached.rules, True

        # Cache miss or invalid - load fresh rules
        self._misses += 1
        logger.debug(f"Rule cache miss for {working_dir_str}")

        rules, file_mtimes = self._load_rules_with_mtimes(working_dir_str)
        self._cache[working_dir_str] = CachedRuleSet(
            rules=rules,
            file_mtimes=file_mtimes,
            loaded_at=time.time(),
        )
        return rules, False

    def invalidate(self, working_dir: str | Path | None = None) -> None:
        """Invalidate cache for specific directory or all.

        Args:
            working_dir: If provided, invalidate only this directory's cache.
                        If None, invalidate entire cache.
        """
        if working_dir is None:
            count = len(self._cache)
            self._cache.clear()
            logger.debug(f"Invalidated entire rule cache ({count} entries)")
        else:
            working_dir_str = str(Path(working_dir).resolve())
            if working_dir_str in self._cache:
                del self._cache[working_dir_str]
                logger.debug(f"Invalidated rule cache for {working_dir_str}")

    @property
    def stats(self) -> dict[str, int]:
        """Get cache statistics.

        Returns:
            Dict with hits, misses, and cached_entries counts
        """
        return {
            "hits": self._hits,
            "misses": self._misses,
            "cached_entries": len(self._cache),
        }

    def _is_cache_valid(self, cached: CachedRuleSet, working_dir: str) -> bool:
        """Check if cached rules are still valid by comparing mtimes.

        A cache entry is valid if:
        1. All tracked files still have the same mtime
        2. No new rule files have appeared (checked via repo discovery)
        3. No tracked files have been deleted

        Args:
            cached: The cached rule set to validate
            working_dir: Working directory for repo rule discovery

        Returns:
            True if cache is still valid, False if it should be refreshed
        """
        # Check if tracked files still have same mtimes
        for file_path, cached_mtime in cached.file_mtimes.items():
            if not file_path.exists():
                # File was deleted - invalidate
                logger.debug(f"Rule file deleted: {file_path}")
                return False

            current_mtime = file_path.stat().st_mtime
            if current_mtime != cached_mtime:
                # File was modified - invalidate
                logger.debug(f"Rule file modified: {file_path}")
                return False

        # Check if new repo rules file appeared
        current_files = self._discover_rule_files(working_dir)
        cached_files = set(cached.file_mtimes.keys())

        if current_files != cached_files:
            # File set changed (new file appeared or tracked file disappeared)
            logger.debug(f"Rule files changed: {cached_files} -> {current_files}")
            return False

        return True

    def _discover_rule_files(self, working_dir: str) -> set[Path]:
        """Discover all rule files that would be loaded for a working directory.

        Args:
            working_dir: Working directory for repo rule discovery

        Returns:
            Set of paths to rule files that exist
        """
        files: set[Path] = set()

        # Global rules
        if GLOBAL_RULES_PATH.exists():
            files.add(GLOBAL_RULES_PATH)

        # Repo rules
        repo_path = _find_repo_rules(Path(working_dir))
        if repo_path:
            files.add(repo_path)

        return files

    def _load_rules_with_mtimes(
        self, working_dir: str
    ) -> tuple[list[Rule], dict[Path, float]]:
        """Load rules and track source file modification times.

        Args:
            working_dir: Working directory for repo rule discovery

        Returns:
            Tuple of (loaded rules, dict of file path -> mtime)
        """
        rules: list[Rule] = []
        file_mtimes: dict[Path, float] = {}

        # Load global rules
        if GLOBAL_RULES_PATH.exists():
            global_rules = _load_rule_file(GLOBAL_RULES_PATH)
            rules.extend(global_rules)
            file_mtimes[GLOBAL_RULES_PATH] = GLOBAL_RULES_PATH.stat().st_mtime
            logger.debug(f"Loaded {len(global_rules)} global rules")

        # Load repo rules
        repo_path = _find_repo_rules(Path(working_dir))
        if repo_path:
            repo_rules = _load_rule_file(repo_path)
            rules.extend(repo_rules)
            file_mtimes[repo_path] = repo_path.stat().st_mtime
            logger.debug(f"Loaded {len(repo_rules)} repo rules from {repo_path}")

        logger.info(f"Loaded {len(rules)} total rules")
        return rules, file_mtimes
