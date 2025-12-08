"""Tests for safeshell.events.types module."""

from datetime import UTC, datetime

from safeshell.events.types import (
    ApprovalNeededEvent,
    ApprovalResolvedEvent,
    CommandReceivedEvent,
    DaemonStatusEvent,
    EvaluationCompletedEvent,
    EvaluationStartedEvent,
    Event,
    EventType,
)
from safeshell.models import Decision


class TestEventType:
    """Tests for EventType enum."""

    def test_event_type_values(self) -> None:
        """Test that EventType has expected values."""
        assert EventType.COMMAND_RECEIVED.value == "command_received"
        assert EventType.EVALUATION_STARTED.value == "evaluation_started"
        assert EventType.EVALUATION_COMPLETED.value == "evaluation_completed"
        assert EventType.APPROVAL_NEEDED.value == "approval_needed"
        assert EventType.APPROVAL_RESOLVED.value == "approval_resolved"
        assert EventType.DAEMON_STATUS.value == "daemon_status"

    def test_event_type_is_string(self) -> None:
        """Test that EventType values are strings."""
        assert isinstance(EventType.COMMAND_RECEIVED.value, str)
        assert EventType.COMMAND_RECEIVED == "command_received"


class TestCommandReceivedEvent:
    """Tests for CommandReceivedEvent model."""

    def test_creation(self) -> None:
        """Test basic creation."""
        event = CommandReceivedEvent(command="ls -la", working_dir="/home/user")
        assert event.command == "ls -la"
        assert event.working_dir == "/home/user"

    def test_serialization(self) -> None:
        """Test serialization to dict."""
        event = CommandReceivedEvent(command="git status", working_dir="/home/user")
        data = event.model_dump()
        assert data["command"] == "git status"
        assert data["working_dir"] == "/home/user"


class TestEvaluationStartedEvent:
    """Tests for EvaluationStartedEvent model."""

    def test_creation(self) -> None:
        """Test basic creation."""
        event = EvaluationStartedEvent(command="git push", plugin_count=3)
        assert event.command == "git push"
        assert event.plugin_count == 3


class TestEvaluationCompletedEvent:
    """Tests for EvaluationCompletedEvent model."""

    def test_allow_result(self) -> None:
        """Test allowed command event."""
        event = EvaluationCompletedEvent(
            command="ls",
            decision=Decision.ALLOW,
        )
        assert event.command == "ls"
        assert event.decision == Decision.ALLOW
        assert event.plugin_name is None
        assert event.reason is None

    def test_deny_result(self) -> None:
        """Test denied command event."""
        event = EvaluationCompletedEvent(
            command="git push --force",
            decision=Decision.DENY,
            plugin_name="git-protect",
            reason="Force push to protected branch",
        )
        assert event.decision == Decision.DENY
        assert event.plugin_name == "git-protect"
        assert event.reason == "Force push to protected branch"


class TestApprovalNeededEvent:
    """Tests for ApprovalNeededEvent model."""

    def test_creation(self) -> None:
        """Test basic creation."""
        event = ApprovalNeededEvent(
            approval_id="abc123",
            command="git push --force",
            plugin_name="git-protect",
            reason="Requires human approval",
        )
        assert event.approval_id == "abc123"
        assert event.command == "git push --force"
        assert event.plugin_name == "git-protect"
        assert event.reason == "Requires human approval"
        assert event.challenge_code is None

    def test_with_challenge_code(self) -> None:
        """Test creation with challenge code."""
        event = ApprovalNeededEvent(
            approval_id="abc123",
            command="rm -rf /",
            plugin_name="dangerous-ops",
            reason="Destructive operation",
            challenge_code="CONFIRM-1234",
        )
        assert event.challenge_code == "CONFIRM-1234"


class TestApprovalResolvedEvent:
    """Tests for ApprovalResolvedEvent model."""

    def test_approved(self) -> None:
        """Test approved resolution."""
        event = ApprovalResolvedEvent(
            approval_id="abc123",
            approved=True,
        )
        assert event.approval_id == "abc123"
        assert event.approved is True
        assert event.reason is None

    def test_denied_with_reason(self) -> None:
        """Test denied resolution with reason."""
        event = ApprovalResolvedEvent(
            approval_id="abc123",
            approved=False,
            reason="Not authorized for this operation",
        )
        assert event.approved is False
        assert event.reason == "Not authorized for this operation"


class TestDaemonStatusEvent:
    """Tests for DaemonStatusEvent model."""

    def test_creation(self) -> None:
        """Test basic creation."""
        event = DaemonStatusEvent(
            status="running",
            uptime_seconds=3600.5,
            commands_processed=42,
            active_connections=2,
        )
        assert event.status == "running"
        assert event.uptime_seconds == 3600.5
        assert event.commands_processed == 42
        assert event.active_connections == 2


class TestEvent:
    """Tests for Event model."""

    def test_basic_creation(self) -> None:
        """Test basic event creation."""
        event = Event(
            type=EventType.COMMAND_RECEIVED,
            data={"command": "ls", "working_dir": "/home/user"},
        )
        assert event.type == EventType.COMMAND_RECEIVED
        assert event.data["command"] == "ls"
        assert isinstance(event.timestamp, datetime)

    def test_timestamp_is_utc(self) -> None:
        """Test that default timestamp is UTC."""
        event = Event(
            type=EventType.DAEMON_STATUS,
            data={
                "status": "running",
                "uptime_seconds": 0,
                "commands_processed": 0,
                "active_connections": 0,
            },
        )
        assert event.timestamp.tzinfo == UTC

    def test_command_received_factory(self) -> None:
        """Test Event.command_received() factory."""
        event = Event.command_received("git status", "/home/user/project")
        assert event.type == EventType.COMMAND_RECEIVED
        assert event.data["command"] == "git status"
        assert event.data["working_dir"] == "/home/user/project"

    def test_evaluation_started_factory(self) -> None:
        """Test Event.evaluation_started() factory."""
        event = Event.evaluation_started("git push", 3)
        assert event.type == EventType.EVALUATION_STARTED
        assert event.data["command"] == "git push"
        assert event.data["plugin_count"] == 3

    def test_evaluation_completed_factory(self) -> None:
        """Test Event.evaluation_completed() factory."""
        event = Event.evaluation_completed(
            command="git commit",
            decision=Decision.DENY,
            plugin_name="git-protect",
            reason="Cannot commit to main",
        )
        assert event.type == EventType.EVALUATION_COMPLETED
        assert event.data["command"] == "git commit"
        assert event.data["decision"] == "deny"
        assert event.data["plugin_name"] == "git-protect"
        assert event.data["reason"] == "Cannot commit to main"

    def test_approval_needed_factory(self) -> None:
        """Test Event.approval_needed() factory."""
        event = Event.approval_needed(
            approval_id="test-123",
            command="git push --force",
            plugin_name="git-protect",
            reason="Force push requires approval",
            challenge_code="CONFIRM-ABC",
        )
        assert event.type == EventType.APPROVAL_NEEDED
        assert event.data["approval_id"] == "test-123"
        assert event.data["command"] == "git push --force"
        assert event.data["challenge_code"] == "CONFIRM-ABC"

    def test_approval_resolved_factory(self) -> None:
        """Test Event.approval_resolved() factory."""
        event = Event.approval_resolved(
            approval_id="test-123",
            approved=False,
            reason="User denied the request",
        )
        assert event.type == EventType.APPROVAL_RESOLVED
        assert event.data["approval_id"] == "test-123"
        assert event.data["approved"] is False
        assert event.data["reason"] == "User denied the request"

    def test_daemon_status_factory(self) -> None:
        """Test Event.daemon_status() factory."""
        event = Event.daemon_status(
            status="running",
            uptime_seconds=1234.5,
            commands_processed=100,
            active_connections=3,
        )
        assert event.type == EventType.DAEMON_STATUS
        assert event.data["status"] == "running"
        assert event.data["uptime_seconds"] == 1234.5
        assert event.data["commands_processed"] == 100
        assert event.data["active_connections"] == 3

    def test_serialization_roundtrip(self) -> None:
        """Test event serialization and deserialization."""
        original = Event.command_received("echo hello", "/home/user")
        json_str = original.model_dump_json()
        restored = Event.model_validate_json(json_str)

        assert restored.type == original.type
        assert restored.data == original.data
        # Timestamps might have slight differences due to serialization
        original_ts = original.timestamp.replace(microsecond=0)
        restored_ts = restored.timestamp.replace(microsecond=0)
        assert restored_ts == original_ts
