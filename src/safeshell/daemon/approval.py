"""
File: src/safeshell/daemon/approval.py
Purpose: Approval manager for handling require_approval decisions
Exports: ApprovalManager, ApprovalResult, PendingApproval
Depends: asyncio, safeshell.daemon.events, loguru
Overview: Manages pending approval requests, allowing commands to wait for
          human approval via the Monitor TUI before executing
"""

from __future__ import annotations

import asyncio
import contextlib
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from safeshell.daemon.events import DaemonEventPublisher


class ApprovalResult(str, Enum):
    """Result of an approval request."""

    APPROVED = "approved"
    DENIED = "denied"
    TIMEOUT = "timeout"


@dataclass
class PendingApproval:
    """A pending approval request awaiting resolution."""

    id: str
    command: str
    plugin_name: str
    reason: str
    timeout_seconds: float
    future: asyncio.Future[tuple[ApprovalResult, str | None]]
    timeout_task: asyncio.Task[None] | None = field(default=None)
    created_at: float = field(default_factory=time.monotonic)


class ApprovalManager:
    """Manages pending approval requests.

    When a rule returns REQUIRE_APPROVAL, this manager creates a pending
    approval entry, publishes an event for the monitor, and waits for
    resolution (approve/deny) or timeout.

    The wrapper's request blocks until the approval is resolved, at which
    point the command is either allowed to execute or denied.

    Example:
        manager = ApprovalManager(event_publisher, default_timeout=300.0)
        result, reason = await manager.request_approval(
            command="git push --force",
            plugin_name="git-protect",
            reason="Force push to protected branch",
        )
        if result == ApprovalResult.APPROVED:
            # Allow command execution
        else:
            # Block command with denial reason
    """

    def __init__(
        self,
        event_publisher: DaemonEventPublisher,
        default_timeout: float = 300.0,
    ) -> None:
        """Initialize the approval manager.

        Args:
            event_publisher: Publisher for emitting approval events
            default_timeout: Default timeout in seconds for approval requests
        """
        self._event_publisher = event_publisher
        self._default_timeout = default_timeout
        self._pending: dict[str, PendingApproval] = {}
        self._lock = asyncio.Lock()

    @property
    def pending_count(self) -> int:
        """Return the number of pending approvals."""
        return len(self._pending)

    async def request_approval(
        self,
        command: str,
        plugin_name: str,
        reason: str,
        timeout: float | None = None,
        approval_id: str | None = None,
    ) -> tuple[ApprovalResult, str | None]:
        """Request approval for a command.

        Creates a pending approval entry, publishes an event for the monitor,
        and blocks until the approval is resolved or times out.

        Args:
            command: The command string awaiting approval
            plugin_name: Name of the rule/plugin that triggered approval
            reason: Human-readable reason why approval is required
            timeout: Optional timeout override in seconds
            approval_id: Optional pre-generated approval ID

        Returns:
            Tuple of (result, denial_reason):
            - result: APPROVED, DENIED, or TIMEOUT
            - denial_reason: Reason string if denied, None otherwise
        """
        if approval_id is None:
            approval_id = str(uuid.uuid4())
        timeout_seconds = timeout if timeout is not None else self._default_timeout

        # Create future for this approval
        loop = asyncio.get_running_loop()
        future: asyncio.Future[tuple[ApprovalResult, str | None]] = loop.create_future()

        # Create pending approval entry
        pending = PendingApproval(
            id=approval_id,
            command=command,
            plugin_name=plugin_name,
            reason=reason,
            timeout_seconds=timeout_seconds,
            future=future,
        )

        async with self._lock:
            self._pending[approval_id] = pending

        logger.info(
            f"Approval requested: {approval_id[:8]}... "
            f"for '{command}' (timeout={timeout_seconds}s)"
        )

        # Publish approval_needed event
        await self._event_publisher.approval_needed(
            approval_id=approval_id,
            command=command,
            plugin_name=plugin_name,
            reason=reason,
        )

        # Start timeout task
        timeout_task = asyncio.create_task(self._handle_timeout(approval_id, timeout_seconds))
        pending.timeout_task = timeout_task

        # Wait for resolution
        try:
            result, denial_reason = await future
            logger.info(f"Approval {approval_id[:8]}... resolved: {result.value}")
            return result, denial_reason
        finally:
            # Clean up timeout task if still running
            if not timeout_task.done():
                timeout_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await timeout_task

            # Remove from pending (may already be removed by timeout)
            async with self._lock:
                self._pending.pop(approval_id, None)

    async def approve(self, approval_id: str) -> bool:
        """Approve a pending request.

        Args:
            approval_id: ID of the approval to approve

        Returns:
            True if approval existed and was resolved, False otherwise
        """
        async with self._lock:
            pending = self._pending.get(approval_id)
            if pending is None:
                logger.warning(f"Approve called for unknown approval: {approval_id[:8]}...")
                return False

            if pending.future.done():
                logger.warning(
                    f"Approve called for already-resolved approval: {approval_id[:8]}..."
                )
                return False

            # Resolve the future
            pending.future.set_result((ApprovalResult.APPROVED, None))

        # Publish event (outside lock)
        await self._event_publisher.approval_resolved(
            approval_id=approval_id,
            approved=True,
        )

        logger.info(f"Approved: {approval_id[:8]}... for '{pending.command}'")
        return True

    async def deny(self, approval_id: str, reason: str | None = None) -> bool:
        """Deny a pending request.

        Args:
            approval_id: ID of the approval to deny
            reason: Optional reason for denial

        Returns:
            True if approval existed and was resolved, False otherwise
        """
        async with self._lock:
            pending = self._pending.get(approval_id)
            if pending is None:
                logger.warning(f"Deny called for unknown approval: {approval_id[:8]}...")
                return False

            if pending.future.done():
                logger.warning(f"Deny called for already-resolved approval: {approval_id[:8]}...")
                return False

            # Resolve the future
            pending.future.set_result((ApprovalResult.DENIED, reason))

        # Publish event (outside lock)
        await self._event_publisher.approval_resolved(
            approval_id=approval_id,
            approved=False,
            reason=reason,
        )

        logger.info(
            f"Denied: {approval_id[:8]}... for '{pending.command}'"
            + (f" (reason: {reason})" if reason else "")
        )
        return True

    async def _handle_timeout(self, approval_id: str, timeout_seconds: float) -> None:
        """Handle approval timeout.

        Called by timeout task when approval expires without resolution.

        Args:
            approval_id: ID of the approval that timed out
            timeout_seconds: The timeout duration (for logging)
        """
        await asyncio.sleep(timeout_seconds)

        async with self._lock:
            pending = self._pending.get(approval_id)
            if pending is None:
                # Already resolved or cleaned up
                return

            if pending.future.done():
                # Already resolved
                return

            # Publish event first (before setting future, to avoid race)
            await self._event_publisher.approval_resolved(
                approval_id=approval_id,
                approved=False,
                reason="Approval timed out",
            )

            logger.warning(f"Approval timed out: {approval_id[:8]}... " f"after {timeout_seconds}s")

            # Resolve as timeout (after publishing event)
            pending.future.set_result((ApprovalResult.TIMEOUT, None))

    async def get_pending(self, approval_id: str) -> PendingApproval | None:
        """Get a pending approval by ID.

        Args:
            approval_id: ID of the approval to retrieve

        Returns:
            PendingApproval if found, None otherwise
        """
        async with self._lock:
            return self._pending.get(approval_id)

    async def list_pending(self) -> list[PendingApproval]:
        """List all pending approvals.

        Returns:
            List of pending approval entries
        """
        async with self._lock:
            return list(self._pending.values())
