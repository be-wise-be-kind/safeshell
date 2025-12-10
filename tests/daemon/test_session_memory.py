"""Tests for session memory module."""

from unittest.mock import patch

from safeshell.daemon.session_memory import ApprovalMemoryKey, SessionMemory


class TestApprovalMemoryKey:
    """Tests for ApprovalMemoryKey."""

    def test_create_key(self) -> None:
        """Test creating a key."""
        key = ApprovalMemoryKey(rule_name="git-protect", base_command="git")
        assert key.rule_name == "git-protect"
        assert key.base_command == "git"

    def test_key_is_hashable(self) -> None:
        """Test key can be used in sets/dicts."""
        key = ApprovalMemoryKey(rule_name="git-protect", base_command="git")
        d = {key: True}
        assert d[key] is True

    def test_key_str(self) -> None:
        """Test string representation."""
        key = ApprovalMemoryKey(rule_name="git-protect", base_command="git")
        assert str(key) == "git-protect:git"

    def test_key_equality(self) -> None:
        """Test key equality."""
        key1 = ApprovalMemoryKey(rule_name="git-protect", base_command="git")
        key2 = ApprovalMemoryKey(rule_name="git-protect", base_command="git")
        key3 = ApprovalMemoryKey(rule_name="other-rule", base_command="git")
        assert key1 == key2
        assert key1 != key3


class TestSessionMemory:
    """Tests for SessionMemory."""

    def test_initial_state(self) -> None:
        """Test initial state is empty."""
        memory = SessionMemory()
        assert not memory.is_pre_approved("any-rule", "any command")
        assert not memory.is_pre_denied("any-rule", "any command")

    def test_remember_approval(self) -> None:
        """Test remembering an approval."""
        memory = SessionMemory()
        memory.remember_approval("git-protect", "git push --force")
        assert memory.is_pre_approved("git-protect", "git push --force")
        assert not memory.is_pre_denied("git-protect", "git push --force")

    def test_remember_denial(self) -> None:
        """Test remembering a denial."""
        memory = SessionMemory()
        memory.remember_denial("git-protect", "git push --force")
        assert memory.is_pre_denied("git-protect", "git push --force")
        assert not memory.is_pre_approved("git-protect", "git push --force")

    def test_approval_covers_same_executable(self) -> None:
        """Test that approval for 'git push' also covers 'git pull'."""
        memory = SessionMemory()
        memory.remember_approval("git-protect", "git push --force")
        # Same rule + same base command should match
        assert memory.is_pre_approved("git-protect", "git pull origin main")

    def test_different_rules_tracked_separately(self) -> None:
        """Test that different rules are tracked separately."""
        memory = SessionMemory()
        memory.remember_approval("git-protect", "git push")
        # Different rule should NOT be approved
        assert not memory.is_pre_approved("other-rule", "git push")

    def test_approval_overrides_denial(self) -> None:
        """Test that approval clears previous denial."""
        memory = SessionMemory()
        memory.remember_denial("git-protect", "git push")
        assert memory.is_pre_denied("git-protect", "git push")
        memory.remember_approval("git-protect", "git push")
        assert memory.is_pre_approved("git-protect", "git push")
        assert not memory.is_pre_denied("git-protect", "git push")

    def test_denial_overrides_approval(self) -> None:
        """Test that denial clears previous approval."""
        memory = SessionMemory()
        memory.remember_approval("git-protect", "git push")
        assert memory.is_pre_approved("git-protect", "git push")
        memory.remember_denial("git-protect", "git push")
        assert memory.is_pre_denied("git-protect", "git push")
        assert not memory.is_pre_approved("git-protect", "git push")

    def test_clear(self) -> None:
        """Test clearing all memory."""
        memory = SessionMemory()
        memory.remember_approval("rule1", "cmd1")
        memory.remember_denial("rule2", "cmd2")
        memory.clear()
        assert not memory.is_pre_approved("rule1", "cmd1")
        assert not memory.is_pre_denied("rule2", "cmd2")

    def test_stats(self) -> None:
        """Test stats property."""
        memory = SessionMemory(ttl_seconds=300)
        memory.remember_approval("rule1", "cmd1")
        memory.remember_denial("rule2", "cmd2")
        stats = memory.stats
        assert stats["approved_count"] == 1
        assert stats["denied_count"] == 1
        assert stats["ttl_seconds"] == 300

    def test_ttl_seconds_property(self) -> None:
        """Test ttl_seconds property."""
        memory = SessionMemory(ttl_seconds=600)
        assert memory.ttl_seconds == 600


class TestSessionMemoryTTL:
    """Tests for session memory time-to-live behavior."""

    def test_approval_expires_after_ttl(self) -> None:
        """Test that approvals expire after TTL."""
        memory = SessionMemory(ttl_seconds=60)

        # Record the approval at a known time
        base_time = 1000.0
        with patch("safeshell.daemon.session_memory.time.time", return_value=base_time):
            memory.remember_approval("git-protect", "git push")

        # Check immediately after - should be approved
        with patch("safeshell.daemon.session_memory.time.time", return_value=base_time + 1):
            assert memory.is_pre_approved("git-protect", "git push")

        # Check after TTL expires - should NOT be approved
        with patch("safeshell.daemon.session_memory.time.time", return_value=base_time + 61):
            assert not memory.is_pre_approved("git-protect", "git push")

    def test_denial_expires_after_ttl(self) -> None:
        """Test that denials expire after TTL."""
        memory = SessionMemory(ttl_seconds=60)

        base_time = 1000.0
        with patch("safeshell.daemon.session_memory.time.time", return_value=base_time):
            memory.remember_denial("git-protect", "git push")

        # Check immediately after - should be denied
        with patch("safeshell.daemon.session_memory.time.time", return_value=base_time + 1):
            assert memory.is_pre_denied("git-protect", "git push")

        # Check after TTL expires - should NOT be denied
        with patch("safeshell.daemon.session_memory.time.time", return_value=base_time + 61):
            assert not memory.is_pre_denied("git-protect", "git push")

    def test_zero_ttl_means_no_expiry(self) -> None:
        """Test that TTL=0 means no time-based expiry."""
        memory = SessionMemory(ttl_seconds=0)
        memory.remember_approval("git-protect", "git push")

        # Even with time far in the future, should still be approved (TTL=0 means no expiry)
        assert memory.is_pre_approved("git-protect", "git push")

    def test_approval_within_ttl(self) -> None:
        """Test that approval is valid within TTL."""
        memory = SessionMemory(ttl_seconds=60)

        base_time = 1000.0
        with patch("safeshell.daemon.session_memory.time.time", return_value=base_time):
            memory.remember_approval("git-protect", "git push")

        # 30 seconds later should still be approved
        with patch("safeshell.daemon.session_memory.time.time", return_value=base_time + 30):
            assert memory.is_pre_approved("git-protect", "git push")

    def test_expired_entry_removed_from_cache(self) -> None:
        """Test that checking expired entry removes it from cache."""
        memory = SessionMemory(ttl_seconds=60)

        base_time = 1000.0
        with patch("safeshell.daemon.session_memory.time.time", return_value=base_time):
            memory.remember_approval("git-protect", "git push")
        assert memory.stats["approved_count"] == 1

        # Check after TTL expires - entry should be removed
        with patch("safeshell.daemon.session_memory.time.time", return_value=base_time + 61):
            memory.is_pre_approved("git-protect", "git push")
            # Entry should be removed
            assert memory.stats["approved_count"] == 0
