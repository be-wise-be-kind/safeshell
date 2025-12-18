"""Tests for safeshell.rules.cache module."""

import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from safeshell.rules.cache import CachedRuleSet, RuleCache
from safeshell.rules.schema import Rule, RuleAction


@pytest.fixture
def sample_rules() -> list[Rule]:
    """Create sample rules for testing."""
    return [
        Rule(
            name="test-rule-1",
            commands=["git"],
            action=RuleAction.DENY,
            message="Test rule 1",
        ),
        Rule(
            name="test-rule-2",
            commands=["rm"],
            action=RuleAction.REQUIRE_APPROVAL,
            message="Test rule 2",
        ),
    ]


class TestCachedRuleSet:
    """Tests for CachedRuleSet dataclass."""

    def test_creation_with_defaults(self, sample_rules: list[Rule]) -> None:
        """Test creating a CachedRuleSet with default values."""
        cached = CachedRuleSet(rules=sample_rules)
        assert cached.rules == sample_rules
        assert cached.file_mtimes == {}
        assert cached.loaded_at > 0

    def test_creation_with_mtimes(self, sample_rules: list[Rule]) -> None:
        """Test creating a CachedRuleSet with file mtimes."""
        mtimes = {Path("/test/rules.yaml"): 1234567890.0}
        cached = CachedRuleSet(
            rules=sample_rules,
            file_mtimes=mtimes,
            loaded_at=1000.0,
        )
        assert cached.file_mtimes == mtimes
        assert cached.loaded_at == 1000.0


class TestRuleCache:
    """Tests for RuleCache class."""

    def test_initial_state(self) -> None:
        """Test cache starts empty."""
        cache = RuleCache()
        assert cache.stats["hits"] == 0
        assert cache.stats["misses"] == 0
        assert cache.stats["cached_entries"] == 0

    def test_cache_miss_on_first_request(self, sample_rules: list[Rule]) -> None:
        """Test first request is a cache miss."""
        cache = RuleCache()

        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch("safeshell.rules.cache._load_rule_file", return_value=(sample_rules, [])),
            patch(
                "safeshell.rules.cache.GLOBAL_RULES_PATH",
                Path(tmpdir) / "nonexistent.yaml",
            ),
        ):
            rules, cache_hit = cache.get_rules(tmpdir)

        assert cache_hit is False
        assert cache.stats["misses"] == 1
        assert cache.stats["hits"] == 0

    def test_cache_hit_on_second_request(self, sample_rules: list[Rule]) -> None:
        """Test second request to same directory is a cache hit."""
        cache = RuleCache()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a rules file
            rules_path = Path(tmpdir) / "rules.yaml"
            rules_path.write_text("rules: []")

            with (
                patch(
                    "safeshell.rules.cache._load_rule_file",
                    return_value=(sample_rules, []),
                ),
                patch("safeshell.rules.cache.GLOBAL_RULES_PATH", rules_path),
            ):
                # First request - cache miss
                rules1, hit1 = cache.get_rules(tmpdir)
                assert hit1 is False

                # Second request - cache hit
                rules2, hit2 = cache.get_rules(tmpdir)
                assert hit2 is True

        assert cache.stats["misses"] == 1
        assert cache.stats["hits"] == 1
        assert rules1 == rules2

    def test_cache_invalidation_on_file_change(self, sample_rules: list[Rule]) -> None:
        """Test cache is invalidated when rule file is modified."""
        cache = RuleCache()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a rules file
            rules_path = Path(tmpdir) / "rules.yaml"
            rules_path.write_text("rules: []")

            with (
                patch(
                    "safeshell.rules.cache._load_rule_file",
                    return_value=(sample_rules, []),
                ),
                patch("safeshell.rules.cache.GLOBAL_RULES_PATH", rules_path),
            ):
                # First request - cache miss
                _, hit1 = cache.get_rules(tmpdir)
                assert hit1 is False

                # Modify the file (need to ensure different mtime)
                time.sleep(0.01)  # Ensure mtime changes
                rules_path.write_text("rules: []\n# modified")

                # Third request - should be cache miss due to mtime change
                _, hit3 = cache.get_rules(tmpdir)
                assert hit3 is False

        assert cache.stats["misses"] == 2

    def test_cache_invalidation_on_file_deletion(self, sample_rules: list[Rule]) -> None:
        """Test cache is invalidated when rule file is deleted."""
        cache = RuleCache()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a rules file
            rules_path = Path(tmpdir) / "rules.yaml"
            rules_path.write_text("rules: []")

            with (
                patch(
                    "safeshell.rules.cache._load_rule_file",
                    return_value=(sample_rules, []),
                ),
                patch("safeshell.rules.cache.GLOBAL_RULES_PATH", rules_path),
            ):
                # First request - cache miss
                _, hit1 = cache.get_rules(tmpdir)
                assert hit1 is False

                # Delete the file
                rules_path.unlink()

                # Second request - should be cache miss due to file deletion
                _, hit2 = cache.get_rules(tmpdir)
                assert hit2 is False

        assert cache.stats["misses"] == 2

    def test_manual_invalidation_all(self, sample_rules: list[Rule]) -> None:
        """Test manual invalidation of entire cache."""
        cache = RuleCache()

        with (
            tempfile.TemporaryDirectory() as tmpdir1,
            tempfile.TemporaryDirectory() as tmpdir2,
        ):
            # Create rules files
            rules1 = Path(tmpdir1) / "rules.yaml"
            rules1.write_text("rules: []")
            rules2 = Path(tmpdir2) / "rules.yaml"
            rules2.write_text("rules: []")

            with patch("safeshell.rules.cache._load_rule_file", return_value=(sample_rules, [])):
                # Populate cache for both directories
                with patch("safeshell.rules.cache.GLOBAL_RULES_PATH", rules1):
                    cache.get_rules(tmpdir1)
                with patch("safeshell.rules.cache.GLOBAL_RULES_PATH", rules2):
                    cache.get_rules(tmpdir2)

                assert cache.stats["cached_entries"] == 2

                # Invalidate all
                cache.invalidate()
                assert cache.stats["cached_entries"] == 0

    def test_manual_invalidation_specific_dir(self, sample_rules: list[Rule]) -> None:
        """Test manual invalidation of specific directory."""
        cache = RuleCache()

        with (
            tempfile.TemporaryDirectory() as tmpdir1,
            tempfile.TemporaryDirectory() as tmpdir2,
        ):
            # Create rules files
            rules1 = Path(tmpdir1) / "rules.yaml"
            rules1.write_text("rules: []")
            rules2 = Path(tmpdir2) / "rules.yaml"
            rules2.write_text("rules: []")

            with patch("safeshell.rules.cache._load_rule_file", return_value=(sample_rules, [])):
                # Populate cache for both directories
                with patch("safeshell.rules.cache.GLOBAL_RULES_PATH", rules1):
                    cache.get_rules(tmpdir1)
                with patch("safeshell.rules.cache.GLOBAL_RULES_PATH", rules2):
                    cache.get_rules(tmpdir2)

                assert cache.stats["cached_entries"] == 2

                # Invalidate only tmpdir1
                cache.invalidate(tmpdir1)
                assert cache.stats["cached_entries"] == 1

    def test_different_working_dirs_cached_separately(self, sample_rules: list[Rule]) -> None:
        """Test different working directories have separate cache entries."""
        cache = RuleCache()

        with (
            tempfile.TemporaryDirectory() as tmpdir1,
            tempfile.TemporaryDirectory() as tmpdir2,
            patch("safeshell.rules.cache._load_rule_file", return_value=(sample_rules, [])),
            patch(
                "safeshell.rules.cache.GLOBAL_RULES_PATH",
                Path("/nonexistent/rules.yaml"),
            ),
        ):
            # Request rules for both directories
            cache.get_rules(tmpdir1)
            cache.get_rules(tmpdir2)

            # Both should be cached separately
            assert cache.stats["cached_entries"] == 2
            assert cache.stats["misses"] == 2
