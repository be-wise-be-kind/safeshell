"""
Tests for ConditionCache TTL-based caching.
"""

import time

import pytest

from safeshell.rules.evaluator import ConditionCache


class TestConditionCache:
    """Tests for ConditionCache class."""

    def test_cache_set_and_get(self) -> None:
        """Test basic set and get operations."""
        cache = ConditionCache(ttl_seconds=10.0)
        key = ("condition", "ls -la", "/tmp")

        cache.set(key, True)
        assert cache.get(key) is True

        cache.set(key, False)
        assert cache.get(key) is False

    def test_cache_miss_returns_none(self) -> None:
        """Test that missing keys return None."""
        cache = ConditionCache(ttl_seconds=10.0)
        key = ("condition", "ls", "/tmp")

        assert cache.get(key) is None

    def test_cache_expiry(self) -> None:
        """Test that entries expire after TTL."""
        cache = ConditionCache(ttl_seconds=0.1)  # 100ms TTL
        key = ("condition", "ls", "/tmp")

        cache.set(key, True)
        assert cache.get(key) is True

        # Wait for expiry
        time.sleep(0.15)
        assert cache.get(key) is None

    def test_cache_different_keys(self) -> None:
        """Test that different keys are stored independently."""
        cache = ConditionCache(ttl_seconds=10.0)
        key1 = ("cond1", "ls", "/tmp")
        key2 = ("cond2", "ls", "/tmp")
        key3 = ("cond1", "ls", "/home")

        cache.set(key1, True)
        cache.set(key2, False)
        cache.set(key3, True)

        assert cache.get(key1) is True
        assert cache.get(key2) is False
        assert cache.get(key3) is True

    def test_cache_max_size_eviction(self) -> None:
        """Test that old entries are evicted when max size is reached."""
        cache = ConditionCache(ttl_seconds=10.0, max_size=5)

        # Fill cache to max
        for i in range(5):
            cache.set((f"cond{i}", "ls", "/tmp"), True)

        assert len(cache) == 5

        # Add one more - should trigger eviction
        cache.set(("cond_new", "ls", "/tmp"), True)

        # Should have evicted some entries
        assert len(cache) <= 5

    def test_cache_clear(self) -> None:
        """Test cache clear operation."""
        cache = ConditionCache(ttl_seconds=10.0)
        key = ("condition", "ls", "/tmp")

        cache.set(key, True)
        assert cache.get(key) is True

        cache.clear()
        assert cache.get(key) is None
        assert len(cache) == 0

    def test_cache_len(self) -> None:
        """Test __len__ returns correct count."""
        cache = ConditionCache(ttl_seconds=10.0)

        assert len(cache) == 0

        cache.set(("cond1", "ls", "/tmp"), True)
        assert len(cache) == 1

        cache.set(("cond2", "ls", "/tmp"), False)
        assert len(cache) == 2


class TestConditionCacheIntegration:
    """Integration tests for condition cache with RuleEvaluator."""

    @pytest.mark.asyncio
    async def test_shared_cache_persists_across_evaluations(self) -> None:
        """Test that shared cache persists results across evaluate() calls."""
        from safeshell.models import CommandContext, ExecutionContext
        from safeshell.rules.evaluator import RuleEvaluator
        from safeshell.rules.schema import Rule, RuleAction

        # Create a rule with a bash condition
        rule = Rule(
            name="test-rule",
            commands=["echo"],
            conditions=['echo "$CMD" | grep -q "hello"'],
            action=RuleAction.DENY,
            message="Test denial",
        )

        # Create shared cache
        shared_cache = ConditionCache(ttl_seconds=10.0)

        # Create evaluator with shared cache
        evaluator = RuleEvaluator(
            rules=[rule],
            condition_timeout_ms=1000,
            condition_cache=shared_cache,
        )

        # First evaluation
        context = CommandContext(
            raw_command="echo hello",
            parsed_args=["echo", "hello"],
            working_dir="/tmp",
            execution_context=ExecutionContext.HUMAN,
        )
        await evaluator.evaluate(context)

        # Cache should have entry
        assert len(shared_cache) > 0

        # Second evaluation with same command should use cached result
        await evaluator.evaluate(context)

        # Cache should still have same number of entries (result was reused)
        cache_size_after = len(shared_cache)
        assert cache_size_after > 0
