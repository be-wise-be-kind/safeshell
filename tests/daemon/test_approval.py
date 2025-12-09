"""Tests for safeshell.daemon.approval module."""

import asyncio

import pytest

from safeshell.daemon.approval import ApprovalManager, ApprovalResult, PendingApproval
from safeshell.daemon.events import DaemonEventPublisher
from safeshell.events.bus import EventBus
from safeshell.events.types import Event, EventType


class TestApprovalResult:
    """Tests for ApprovalResult enum."""

    def test_approval_result_values(self) -> None:
        """Test ApprovalResult has correct values."""
        assert ApprovalResult.APPROVED.value == "approved"
        assert ApprovalResult.DENIED.value == "denied"
        assert ApprovalResult.TIMEOUT.value == "timeout"


class TestPendingApproval:
    """Tests for PendingApproval dataclass."""

    def test_pending_approval_creation(self) -> None:
        """Test creating a PendingApproval instance."""
        loop = asyncio.new_event_loop()
        future: asyncio.Future[tuple[ApprovalResult, str | None]] = loop.create_future()
        loop.close()

        pending = PendingApproval(
            id="test-id",
            command="git push --force",
            plugin_name="git-protect",
            reason="Force push requires approval",
            timeout_seconds=300.0,
            future=future,
        )

        assert pending.id == "test-id"
        assert pending.command == "git push --force"
        assert pending.plugin_name == "git-protect"
        assert pending.reason == "Force push requires approval"
        assert pending.timeout_seconds == 300.0
        assert pending.timeout_task is None
        assert pending.created_at > 0


class TestApprovalManager:
    """Tests for ApprovalManager class."""

    @pytest.fixture
    def bus(self) -> EventBus:
        """Create an EventBus instance."""
        return EventBus()

    @pytest.fixture
    def publisher(self, bus: EventBus) -> DaemonEventPublisher:
        """Create a DaemonEventPublisher instance."""
        return DaemonEventPublisher(bus)

    @pytest.fixture
    def manager(self, publisher: DaemonEventPublisher) -> ApprovalManager:
        """Create an ApprovalManager instance."""
        return ApprovalManager(publisher, default_timeout=1.0)  # Short timeout for tests

    @pytest.mark.asyncio
    async def test_initial_state(self, manager: ApprovalManager) -> None:
        """Test initial manager state."""
        assert manager.pending_count == 0
        pending_list = await manager.list_pending()
        assert pending_list == []

    @pytest.mark.asyncio
    async def test_request_approval_and_approve(
        self, manager: ApprovalManager, bus: EventBus
    ) -> None:
        """Test requesting approval and approving it."""
        received_events: list[Event] = []

        async def handler(event: Event) -> None:
            received_events.append(event)

        await bus.subscribe(handler)

        # Start approval request in background
        async def request_approval() -> tuple[ApprovalResult, str | None]:
            return await manager.request_approval(
                command="git push --force",
                plugin_name="git-protect",
                reason="Force push requires approval",
            )

        request_task = asyncio.create_task(request_approval())

        # Wait briefly for the request to be registered
        await asyncio.sleep(0.05)

        # Verify pending approval exists
        assert manager.pending_count == 1
        pending_list = await manager.list_pending()
        assert len(pending_list) == 1
        approval_id = pending_list[0].id

        # Approve it
        success = await manager.approve(approval_id)
        assert success is True

        # Wait for request to complete
        result, reason = await request_task

        assert result == ApprovalResult.APPROVED
        assert reason is None
        assert manager.pending_count == 0

        # Verify events
        event_types = [e.type for e in received_events]
        assert EventType.APPROVAL_NEEDED in event_types
        assert EventType.APPROVAL_RESOLVED in event_types

        # Check resolved event details
        resolved_events = [e for e in received_events if e.type == EventType.APPROVAL_RESOLVED]
        assert len(resolved_events) == 1
        assert resolved_events[0].data["approved"] is True

    @pytest.mark.asyncio
    async def test_request_approval_and_deny(self, manager: ApprovalManager, bus: EventBus) -> None:
        """Test requesting approval and denying it with reason."""
        received_events: list[Event] = []

        async def handler(event: Event) -> None:
            received_events.append(event)

        await bus.subscribe(handler)

        # Start approval request in background
        async def request_approval() -> tuple[ApprovalResult, str | None]:
            return await manager.request_approval(
                command="rm -rf /",
                plugin_name="dangerous-commands",
                reason="Dangerous command requires approval",
            )

        request_task = asyncio.create_task(request_approval())

        # Wait briefly for the request to be registered
        await asyncio.sleep(0.05)

        # Get the pending approval
        pending_list = await manager.list_pending()
        approval_id = pending_list[0].id

        # Deny it with reason
        success = await manager.deny(approval_id, reason="Too dangerous")
        assert success is True

        # Wait for request to complete
        result, reason = await request_task

        assert result == ApprovalResult.DENIED
        assert reason == "Too dangerous"
        assert manager.pending_count == 0

        # Check resolved event details
        resolved_events = [e for e in received_events if e.type == EventType.APPROVAL_RESOLVED]
        assert len(resolved_events) == 1
        assert resolved_events[0].data["approved"] is False
        assert resolved_events[0].data["reason"] == "Too dangerous"

    @pytest.mark.asyncio
    async def test_request_approval_timeout(
        self, publisher: DaemonEventPublisher, bus: EventBus
    ) -> None:
        """Test that approval times out correctly."""
        # Create manager with very short timeout
        manager = ApprovalManager(publisher, default_timeout=0.1)

        received_events: list[Event] = []

        async def handler(event: Event) -> None:
            received_events.append(event)

        await bus.subscribe(handler)

        # Request approval and let it timeout
        result, reason = await manager.request_approval(
            command="git push --force",
            plugin_name="git-protect",
            reason="Force push requires approval",
        )

        assert result == ApprovalResult.TIMEOUT
        assert reason is None
        assert manager.pending_count == 0

        # Check resolved event
        resolved_events = [e for e in received_events if e.type == EventType.APPROVAL_RESOLVED]
        assert len(resolved_events) == 1
        assert resolved_events[0].data["approved"] is False
        assert resolved_events[0].data["reason"] == "Approval timed out"

    @pytest.mark.asyncio
    async def test_approve_nonexistent_returns_false(self, manager: ApprovalManager) -> None:
        """Test that approving non-existent approval returns False."""
        success = await manager.approve("nonexistent-id")
        assert success is False

    @pytest.mark.asyncio
    async def test_deny_nonexistent_returns_false(self, manager: ApprovalManager) -> None:
        """Test that denying non-existent approval returns False."""
        success = await manager.deny("nonexistent-id")
        assert success is False

    @pytest.mark.asyncio
    async def test_approve_already_resolved_returns_false(self, manager: ApprovalManager) -> None:
        """Test that approving already-resolved approval returns False."""
        # Start approval request
        request_task = asyncio.create_task(
            manager.request_approval(
                command="test-command",
                plugin_name="test",
                reason="test",
            )
        )

        await asyncio.sleep(0.05)

        # Get approval ID
        pending_list = await manager.list_pending()
        approval_id = pending_list[0].id

        # Approve it
        success1 = await manager.approve(approval_id)
        assert success1 is True

        # Try to approve again
        success2 = await manager.approve(approval_id)
        assert success2 is False

        await request_task

    @pytest.mark.asyncio
    async def test_get_pending(self, manager: ApprovalManager) -> None:
        """Test getting a specific pending approval."""
        # No pending approvals
        result = await manager.get_pending("nonexistent")
        assert result is None

        # Start approval request
        request_task = asyncio.create_task(
            manager.request_approval(
                command="test-command",
                plugin_name="test",
                reason="test reason",
            )
        )

        await asyncio.sleep(0.05)

        # Get pending approval
        pending_list = await manager.list_pending()
        approval_id = pending_list[0].id

        pending = await manager.get_pending(approval_id)
        assert pending is not None
        assert pending.id == approval_id
        assert pending.command == "test-command"
        assert pending.plugin_name == "test"
        assert pending.reason == "test reason"

        # Clean up
        await manager.approve(approval_id)
        await request_task

    @pytest.mark.asyncio
    async def test_concurrent_approvals(self, manager: ApprovalManager) -> None:
        """Test handling multiple concurrent approval requests."""
        # Start multiple approval requests
        task1 = asyncio.create_task(
            manager.request_approval(
                command="command-1",
                plugin_name="plugin-1",
                reason="reason-1",
            )
        )
        task2 = asyncio.create_task(
            manager.request_approval(
                command="command-2",
                plugin_name="plugin-2",
                reason="reason-2",
            )
        )

        await asyncio.sleep(0.05)

        # Both should be pending
        assert manager.pending_count == 2
        pending_list = await manager.list_pending()
        assert len(pending_list) == 2

        # Get IDs
        ids = [p.id for p in pending_list]

        # Approve first, deny second
        await manager.approve(ids[0])
        await manager.deny(ids[1], "Not allowed")

        # Wait for both to complete
        result1, reason1 = await task1
        result2, reason2 = await task2

        # Check results (order depends on which was registered first)
        results = [(result1, reason1), (result2, reason2)]
        assert (ApprovalResult.APPROVED, None) in results
        assert (ApprovalResult.DENIED, "Not allowed") in results

        assert manager.pending_count == 0

    @pytest.mark.asyncio
    async def test_custom_timeout(self, publisher: DaemonEventPublisher) -> None:
        """Test that custom timeout is respected."""
        manager = ApprovalManager(publisher, default_timeout=10.0)

        # Start approval with custom short timeout
        start_time = asyncio.get_event_loop().time()
        result, _ = await manager.request_approval(
            command="test",
            plugin_name="test",
            reason="test",
            timeout=0.1,  # Override default
        )
        elapsed = asyncio.get_event_loop().time() - start_time

        assert result == ApprovalResult.TIMEOUT
        assert elapsed < 1.0  # Should be close to 0.1s, not 10s

    @pytest.mark.asyncio
    async def test_approval_needed_event_published(
        self, manager: ApprovalManager, bus: EventBus
    ) -> None:
        """Test that approval_needed event is published with correct data."""
        received_events: list[Event] = []

        async def handler(event: Event) -> None:
            received_events.append(event)

        await bus.subscribe(handler)

        # Start approval request
        request_task = asyncio.create_task(
            manager.request_approval(
                command="git push --force origin main",
                plugin_name="git-protect",
                reason="Force push to main branch",
            )
        )

        await asyncio.sleep(0.05)

        # Check approval_needed event
        needed_events = [e for e in received_events if e.type == EventType.APPROVAL_NEEDED]
        assert len(needed_events) == 1

        event_data = needed_events[0].data
        assert event_data["command"] == "git push --force origin main"
        assert event_data["plugin_name"] == "git-protect"
        assert event_data["reason"] == "Force push to main branch"
        assert "approval_id" in event_data

        # Clean up
        pending_list = await manager.list_pending()
        await manager.approve(pending_list[0].id)
        await request_task

    @pytest.mark.asyncio
    async def test_deny_without_reason(self, manager: ApprovalManager) -> None:
        """Test denying without providing a reason."""
        # Start approval request
        request_task = asyncio.create_task(
            manager.request_approval(
                command="test",
                plugin_name="test",
                reason="test",
            )
        )

        await asyncio.sleep(0.05)

        pending_list = await manager.list_pending()
        await manager.deny(pending_list[0].id)  # No reason

        result, reason = await request_task

        assert result == ApprovalResult.DENIED
        assert reason is None
