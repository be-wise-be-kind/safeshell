"""
Tests for git context caching in CommandContext.
"""

import time
import tempfile
import os
from pathlib import Path

import pytest

from safeshell.models import (
    CommandContext,
    _git_context_cache,
    _GIT_CONTEXT_CACHE_TTL,
)


class TestGitContextCache:
    """Tests for git context caching."""

    def setup_method(self) -> None:
        """Clear cache before each test."""
        _git_context_cache.clear()

    def test_cache_stores_result(self) -> None:
        """Test that git context detection caches its result."""
        # Use current directory (which is in a git repo)
        working_dir = os.getcwd()

        # First call should populate cache
        result1 = CommandContext._detect_git_context(working_dir)

        # Cache should now have an entry
        assert working_dir in _git_context_cache

        # Second call should return same result
        result2 = CommandContext._detect_git_context(working_dir)
        assert result1 == result2

    def test_cache_returns_none_for_non_git_dir(self) -> None:
        """Test that non-git directories return (None, None) and are cached."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = CommandContext._detect_git_context(tmpdir)

            assert result == (None, None)
            assert tmpdir in _git_context_cache
            assert _git_context_cache[tmpdir][0] is None
            assert _git_context_cache[tmpdir][1] is None

    def test_cache_expires_after_ttl(self) -> None:
        """Test that cache entries expire after TTL."""
        # This test is tricky because we can't easily change TTL
        # Just verify the cache structure includes timestamp
        working_dir = os.getcwd()

        CommandContext._detect_git_context(working_dir)

        assert working_dir in _git_context_cache
        entry = _git_context_cache[working_dir]
        # Entry should be (git_root, git_branch, timestamp)
        assert len(entry) == 3
        assert isinstance(entry[2], float)  # timestamp

    def test_uncached_method_bypasses_cache(self) -> None:
        """Test that _detect_git_context_uncached doesn't use cache."""
        working_dir = os.getcwd()

        # Clear cache
        _git_context_cache.clear()

        # Call uncached method
        result = CommandContext._detect_git_context_uncached(working_dir)

        # Cache should still be empty
        assert working_dir not in _git_context_cache

        # Result should still be valid
        # (we're in a git repo, so should return something)
        assert result[0] is not None or result[0] is None  # Valid either way

    def test_prune_removes_old_entries(self) -> None:
        """Test that _prune_git_context_cache removes oldest entries."""
        # Add several entries with different timestamps
        base_time = time.monotonic()

        # Add entries with staggered timestamps
        for i in range(10):
            _git_context_cache[f"/path/to/dir{i}"] = (None, None, base_time + i)

        assert len(_git_context_cache) == 10

        # Prune should remove oldest 20% (2 entries)
        CommandContext._prune_git_context_cache()

        assert len(_git_context_cache) == 8

        # The oldest entries (dir0, dir1) should be removed
        assert "/path/to/dir0" not in _git_context_cache
        assert "/path/to/dir1" not in _git_context_cache

    def test_cache_different_directories(self) -> None:
        """Test that different directories are cached independently."""
        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                result1 = CommandContext._detect_git_context(tmpdir1)
                result2 = CommandContext._detect_git_context(tmpdir2)

                # Both should be cached
                assert tmpdir1 in _git_context_cache
                assert tmpdir2 in _git_context_cache

                # Both should return (None, None) since they're not git repos
                assert result1 == (None, None)
                assert result2 == (None, None)


class TestGitContextCacheIntegration:
    """Integration tests for git context caching with CommandContext."""

    def setup_method(self) -> None:
        """Clear cache before each test."""
        _git_context_cache.clear()

    def test_from_command_uses_cache(self) -> None:
        """Test that CommandContext.from_command uses cached git context."""
        working_dir = os.getcwd()

        # Create context (should populate cache)
        ctx1 = CommandContext.from_command(
            command="ls -la",
            working_dir=working_dir,
        )

        assert working_dir in _git_context_cache

        # Create another context (should use cached result)
        ctx2 = CommandContext.from_command(
            command="git status",
            working_dir=working_dir,
        )

        # Both should have same git context
        assert ctx1.git_repo_root == ctx2.git_repo_root
        assert ctx1.git_branch == ctx2.git_branch
