"""
File: src/safeshell/daemon/session_memory.py
Purpose: Session-scoped memory for "don't ask again" approvals
Exports: SessionMemory, ApprovalMemoryKey
Depends: dataclasses, time, loguru
Overview: Tracks approved rule+command combinations for the current daemon session
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from loguru import logger

# Default TTL for approval memory (5 minutes)
_DEFAULT_APPROVAL_MEMORY_TTL_SECONDS = 300


@dataclass(frozen=True)
class ApprovalMemoryKey:
    """Key for session memory: rule_name + base_command.

    Example: ("git-protect", "git") for any git command triggering git-protect rule.
    This allows "git push --force" approval to also approve "git push origin".

    Attributes:
        rule_name: Name of the rule that triggered the approval
        base_command: The executable (first word of command)
    """

    rule_name: str
    base_command: str

    def __str__(self) -> str:
        """Return string representation of the key."""
        return f"{self.rule_name}:{self.base_command}"


class SessionMemory:
    """Session-scoped memory for "don't ask again" approvals.

    Stores approved/denied rule+command combinations for the current daemon session.
    Memory is cleared when the daemon restarts - nothing is persisted to disk.

    The keying strategy uses rule_name + base_command (executable) so that:
    - "git push --force" approval covers "git push --force origin"
    - Different rules for same command are tracked separately

    Approvals can be time-bound with a configurable TTL. Expired approvals
    are treated as if they never existed (user will be re-prompted).

    Thread Safety:
        This class is not thread-safe. It's designed for use within
        a single async event loop (the daemon's asyncio loop).
    """

    def __init__(self, ttl_seconds: int = _DEFAULT_APPROVAL_MEMORY_TTL_SECONDS) -> None:
        """Initialize session memory.

        Args:
            ttl_seconds: Time-to-live for approvals in seconds. Default is 300 (5 min).
                        Set to 0 for no time expiry (session-only).
        """
        self._approved: dict[ApprovalMemoryKey, float] = {}  # key -> approval timestamp
        self._denied: dict[ApprovalMemoryKey, float] = {}  # key -> denial timestamp
        self._ttl_seconds = ttl_seconds

    def is_pre_approved(self, rule_name: str, command: str) -> bool:
        """Check if rule+command combination was pre-approved.

        Returns True only if the approval exists AND hasn't expired (within TTL).

        Args:
            rule_name: Name of the rule that triggered approval
            command: Full command string

        Returns:
            True if this combination was approved with "don't ask again" and hasn't expired
        """
        key = self._make_key(rule_name, command)
        if key not in self._approved:
            return False

        # Check TTL
        if self._ttl_seconds > 0:
            elapsed = time.time() - self._approved[key]
            if elapsed >= self._ttl_seconds:
                # Expired - remove from cache
                logger.debug(f"Approval expired for {key} (elapsed: {elapsed:.1f}s)")
                del self._approved[key]
                return False

        return True

    def is_pre_denied(self, rule_name: str, command: str) -> bool:
        """Check if rule+command combination was pre-denied.

        Returns True only if the denial exists AND hasn't expired (within TTL).

        Args:
            rule_name: Name of the rule that triggered approval
            command: Full command string

        Returns:
            True if this combination was denied with "don't ask again" and hasn't expired
        """
        key = self._make_key(rule_name, command)
        if key not in self._denied:
            return False

        # Check TTL
        if self._ttl_seconds > 0:
            elapsed = time.time() - self._denied[key]
            if elapsed >= self._ttl_seconds:
                # Expired - remove from cache
                logger.debug(f"Denial expired for {key} (elapsed: {elapsed:.1f}s)")
                del self._denied[key]
                return False

        return True

    def remember_approval(self, rule_name: str, command: str) -> None:
        """Remember an approval for this session.

        Args:
            rule_name: Name of the rule that triggered approval
            command: Full command string
        """
        key = self._make_key(rule_name, command)
        self._approved[key] = time.time()
        # Remove from denied if it was there
        self._denied.pop(key, None)
        logger.info(
            f"Session memory: remembered approval for {key}"
            + (f" (TTL: {self._ttl_seconds}s)" if self._ttl_seconds > 0 else " (no expiry)")
        )

    def remember_denial(self, rule_name: str, command: str) -> None:
        """Remember a denial for this session.

        Args:
            rule_name: Name of the rule that triggered approval
            command: Full command string
        """
        key = self._make_key(rule_name, command)
        self._denied[key] = time.time()
        # Remove from approved if it was there
        self._approved.pop(key, None)
        logger.info(
            f"Session memory: remembered denial for {key}"
            + (f" (TTL: {self._ttl_seconds}s)" if self._ttl_seconds > 0 else " (no expiry)")
        )

    def clear(self) -> None:
        """Clear all session memory."""
        count = len(self._approved) + len(self._denied)
        self._approved.clear()
        self._denied.clear()
        logger.info(f"Session memory cleared ({count} entries)")

    def _make_key(self, rule_name: str, command: str) -> ApprovalMemoryKey:
        """Create memory key from rule name and command.

        Args:
            rule_name: Name of the rule
            command: Full command string

        Returns:
            ApprovalMemoryKey with rule name and base command (executable)
        """
        # Extract base command (first word)
        base_command = command.split()[0] if command else ""
        return ApprovalMemoryKey(rule_name=rule_name, base_command=base_command)

    @property
    def ttl_seconds(self) -> int:
        """Get the TTL in seconds."""
        return self._ttl_seconds

    @property
    def stats(self) -> dict[str, int]:
        """Get memory statistics.

        Returns:
            Dict with approved_count, denied_count, and ttl_seconds
        """
        return {
            "approved_count": len(self._approved),
            "denied_count": len(self._denied),
            "ttl_seconds": self._ttl_seconds,
        }
