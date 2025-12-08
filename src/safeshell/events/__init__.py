"""
File: src/safeshell/events/__init__.py
Purpose: Events module for daemon-monitor communication
Exports: EventType, Event, EventBus, and all event data types
Depends: safeshell.events.types, safeshell.events.bus
Overview: Re-exports event types and bus for convenient importing
"""

from safeshell.events.bus import EventBus
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

__all__ = [
    "EventType",
    "Event",
    "EventBus",
    "CommandReceivedEvent",
    "EvaluationStartedEvent",
    "EvaluationCompletedEvent",
    "ApprovalNeededEvent",
    "ApprovalResolvedEvent",
    "DaemonStatusEvent",
]
