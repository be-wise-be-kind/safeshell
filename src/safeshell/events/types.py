"""
File: src/safeshell/events/types.py
Purpose: Event type definitions for daemon-monitor communication
Exports: EventType, Event, CommandReceivedEvent, EvaluationStartedEvent,
         EvaluationCompletedEvent, ApprovalNeededEvent, ApprovalResolvedEvent, DaemonStatusEvent
Depends: pydantic, enum, datetime
Overview: Defines all event types used for streaming updates from daemon to connected monitors
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from safeshell.models import Decision


class EventType(str, Enum):
    """Types of events emitted by the daemon."""

    COMMAND_RECEIVED = "command_received"
    EVALUATION_STARTED = "evaluation_started"
    EVALUATION_COMPLETED = "evaluation_completed"
    APPROVAL_NEEDED = "approval_needed"
    APPROVAL_RESOLVED = "approval_resolved"
    DAEMON_STATUS = "daemon_status"


class CommandReceivedEvent(BaseModel):
    """Event data for when a command is received for evaluation."""

    command: str = Field(description="The raw command string")
    working_dir: str = Field(description="Working directory for the command")


class EvaluationStartedEvent(BaseModel):
    """Event data for when command evaluation begins."""

    command: str = Field(description="The command being evaluated")
    plugin_count: int = Field(description="Number of plugins that will evaluate")


class EvaluationCompletedEvent(BaseModel):
    """Event data for when command evaluation completes."""

    command: str = Field(description="The command that was evaluated")
    decision: Decision = Field(description="Final decision for the command")
    plugin_name: str | None = Field(
        default=None, description="Plugin that made the decision (if denied)"
    )
    reason: str | None = Field(default=None, description="Reason for the decision")


class ApprovalNeededEvent(BaseModel):
    """Event data for when a command requires human approval."""

    approval_id: str = Field(description="Unique identifier for this approval request")
    command: str = Field(description="The command awaiting approval")
    plugin_name: str = Field(description="Plugin that requires approval")
    reason: str = Field(description="Why approval is needed")
    challenge_code: str | None = Field(
        default=None, description="Optional challenge code for verification"
    )


class ApprovalResolvedEvent(BaseModel):
    """Event data for when an approval request is resolved."""

    approval_id: str = Field(description="The approval request that was resolved")
    approved: bool = Field(description="Whether the request was approved")
    reason: str | None = Field(default=None, description="Reason for denial (if denied)")


class DaemonStatusEvent(BaseModel):
    """Event data for daemon status updates."""

    status: str = Field(description="Current daemon status")
    uptime_seconds: float = Field(description="Daemon uptime in seconds")
    commands_processed: int = Field(description="Total commands processed")
    active_connections: int = Field(description="Number of active connections")


class Event(BaseModel):
    """A daemon event with type, timestamp, and data.

    Events are the primary mechanism for daemon-monitor communication.
    The monitor subscribes to the event stream and updates its UI
    based on received events.
    """

    type: EventType = Field(description="Type of the event")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the event occurred (UTC)",
    )
    data: dict[str, Any] = Field(description="Event-specific data")

    @classmethod
    def command_received(cls, command: str, working_dir: str) -> "Event":
        """Create a COMMAND_RECEIVED event."""
        return cls(
            type=EventType.COMMAND_RECEIVED,
            data=CommandReceivedEvent(command=command, working_dir=working_dir).model_dump(),
        )

    @classmethod
    def evaluation_started(cls, command: str, plugin_count: int) -> "Event":
        """Create an EVALUATION_STARTED event."""
        return cls(
            type=EventType.EVALUATION_STARTED,
            data=EvaluationStartedEvent(command=command, plugin_count=plugin_count).model_dump(),
        )

    @classmethod
    def evaluation_completed(
        cls,
        command: str,
        decision: Decision,
        plugin_name: str | None = None,
        reason: str | None = None,
    ) -> "Event":
        """Create an EVALUATION_COMPLETED event."""
        return cls(
            type=EventType.EVALUATION_COMPLETED,
            data=EvaluationCompletedEvent(
                command=command, decision=decision, plugin_name=plugin_name, reason=reason
            ).model_dump(),
        )

    @classmethod
    def approval_needed(
        cls,
        approval_id: str,
        command: str,
        plugin_name: str,
        reason: str,
        challenge_code: str | None = None,
    ) -> "Event":
        """Create an APPROVAL_NEEDED event."""
        return cls(
            type=EventType.APPROVAL_NEEDED,
            data=ApprovalNeededEvent(
                approval_id=approval_id,
                command=command,
                plugin_name=plugin_name,
                reason=reason,
                challenge_code=challenge_code,
            ).model_dump(),
        )

    @classmethod
    def approval_resolved(
        cls, approval_id: str, approved: bool, reason: str | None = None
    ) -> "Event":
        """Create an APPROVAL_RESOLVED event."""
        return cls(
            type=EventType.APPROVAL_RESOLVED,
            data=ApprovalResolvedEvent(
                approval_id=approval_id, approved=approved, reason=reason
            ).model_dump(),
        )

    @classmethod
    def daemon_status(
        cls, status: str, uptime_seconds: float, commands_processed: int, active_connections: int
    ) -> "Event":
        """Create a DAEMON_STATUS event."""
        return cls(
            type=EventType.DAEMON_STATUS,
            data=DaemonStatusEvent(
                status=status,
                uptime_seconds=uptime_seconds,
                commands_processed=commands_processed,
                active_connections=active_connections,
            ).model_dump(),
        )
