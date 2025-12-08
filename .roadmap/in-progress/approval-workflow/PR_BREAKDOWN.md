# Approval Workflow with Monitor TUI - PR Breakdown

**Purpose**: Detailed implementation breakdown into manageable, atomic pull requests

**Scope**: Complete approval workflow from event system through working Monitor TUI

**Overview**: Breaks down Phase 2 into 5 PRs. Each PR is self-contained, testable, and maintains application functionality while incrementally building toward the complete feature.

**Dependencies**: Completed MVP Phase 1, textual library

**Exports**: PR implementation plans, file structures, testing strategies

**Related**: AI_CONTEXT.md for feature overview, PROGRESS_TRACKER.md for status tracking

**Implementation**: Atomic PR approach with detailed step-by-step guidance

---

## Overview

This document breaks down Phase 2 into 5 PRs:

| PR | Title | Status | Complexity | Priority |
|----|-------|--------|------------|----------|
| PR-1 | Event System Foundation | 🔴 Not Started | Medium | P0 |
| PR-2 | Daemon Event Publishing | 🔴 Not Started | Medium | P0 |
| PR-3 | Monitor TUI Shell | 🔴 Not Started | High | P0 |
| PR-4 | Approval Protocol | 🔴 Not Started | High | P0 |
| PR-5 | Integration and Polish | 🔴 Not Started | Medium | P0 |

---

## PR-1: Event System Foundation

**Status**: 🔴 Not Started

### Summary
Create the event type definitions and event bus infrastructure.

### Files to Create

```
src/safeshell/events/
├── __init__.py
├── types.py      # Event type definitions (Pydantic models)
└── bus.py        # EventBus with async pub/sub
```

### Key Implementation Details

**types.py**:
```python
from enum import Enum
from pydantic import BaseModel

class EventType(str, Enum):
    COMMAND_RECEIVED = "command_received"
    EVALUATION_STARTED = "evaluation_started"
    EVALUATION_COMPLETED = "evaluation_completed"
    APPROVAL_NEEDED = "approval_needed"
    APPROVAL_RESOLVED = "approval_resolved"
    DAEMON_STATUS = "daemon_status"

class Event(BaseModel):
    type: EventType
    timestamp: datetime
    data: dict[str, Any]

class CommandReceivedEvent(BaseModel):
    command: str
    working_dir: str

class ApprovalNeededEvent(BaseModel):
    approval_id: str
    command: str
    plugin_name: str
    reason: str
    challenge_code: str | None = None

class ApprovalResolvedEvent(BaseModel):
    approval_id: str
    approved: bool
    reason: str | None = None
```

**bus.py**:
```python
class EventBus:
    """Async event bus for daemon-monitor communication."""

    async def subscribe(self, callback: Callable) -> str:
        """Subscribe to events, returns subscription ID."""

    async def unsubscribe(self, sub_id: str) -> None:
        """Unsubscribe from events."""

    async def publish(self, event: Event) -> None:
        """Publish event to all subscribers."""
```

### Testing Requirements
- [ ] Test event model serialization/deserialization
- [ ] Test EventBus subscribe/unsubscribe
- [ ] Test EventBus publish delivers to all subscribers
- [ ] Test EventBus handles subscriber errors gracefully

### Success Criteria
- Event types defined with Pydantic validation
- EventBus supports multiple async subscribers
- Full test coverage for event system

---

## PR-2: Daemon Event Publishing

**Status**: 🔴 Not Started

### Summary
Integrate event publishing into the daemon and add monitor connection handling.

### Files to Create

```
src/safeshell/daemon/
├── events.py     # Daemon event publisher
└── monitor.py    # Monitor connection handler
```

### Files to Modify

- `src/safeshell/daemon/server.py` - Add event publishing
- `src/safeshell/daemon/manager.py` - Emit evaluation events
- `src/safeshell/models.py` - Add approval_id, challenge_code fields

### Key Implementation Details

**events.py**:
```python
class DaemonEventPublisher:
    """Publishes daemon events to connected monitors."""

    def __init__(self, bus: EventBus):
        self.bus = bus

    async def command_received(self, command: str, working_dir: str) -> None:
        await self.bus.publish(Event(
            type=EventType.COMMAND_RECEIVED,
            data=CommandReceivedEvent(command=command, working_dir=working_dir).model_dump()
        ))
```

**monitor.py**:
```python
class MonitorConnectionHandler:
    """Handles monitor client connections for event streaming."""

    async def handle_monitor(self, reader, writer) -> None:
        """Stream events to connected monitor."""
        sub_id = await self.bus.subscribe(
            lambda event: self._send_event(writer, event)
        )
        try:
            # Keep connection open, handle commands
            await self._handle_commands(reader)
        finally:
            await self.bus.unsubscribe(sub_id)
```

### Server Modifications

Add second Unix socket for monitor connections:
- `~/.safeshell/daemon.sock` - Wrapper requests (existing)
- `~/.safeshell/monitor.sock` - Monitor event stream (new)

### Testing Requirements
- [ ] Test event publishing from daemon
- [ ] Test monitor connection handling
- [ ] Test event delivery to connected monitor
- [ ] Test monitor disconnection cleanup

### Success Criteria
- Daemon publishes events for command lifecycle
- Monitor can connect and receive event stream
- Clean disconnection handling

---

## PR-3: Monitor TUI Shell

**Status**: 🔴 Not Started

### Summary
Create the Textual-based Monitor TUI with three-pane layout.

### Files to Create

```
src/safeshell/monitor/
├── __init__.py
├── app.py        # Main Textual App
├── widgets.py    # Custom widgets (DebugPane, HistoryPane, ApprovalPane)
├── styles.css    # Textual CSS styling
└── cli.py        # safeshell monitor command
```

### Dependencies to Add

```toml
# pyproject.toml
textual = "^0.89.0"
```

### Key Implementation Details

**app.py**:
```python
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Footer, Header

class MonitorApp(App):
    CSS_PATH = "styles.css"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("a", "approve", "Approve"),
        ("d", "deny", "Deny"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Horizontal(
            DebugPane(id="debug"),
            HistoryPane(id="history"),
            ApprovalPane(id="approval"),
        )
        yield Footer()
```

**widgets.py**:
```python
class DebugPane(Static):
    """Scrolling log pane with color-coded levels."""

class HistoryPane(Static):
    """Command history with status icons."""
    # ✓ = allowed, ✗ = blocked, ? = pending

class ApprovalPane(Static):
    """Approval prompt with buttons and reason input."""

    def compose(self) -> ComposeResult:
        yield Static("No pending approvals", id="prompt")
        yield Button("Approve", id="approve", variant="success")
        yield Button("Deny", id="deny", variant="error")
        yield Input(placeholder="Reason (optional)", id="reason")
```

**styles.css**:
```css
Horizontal {
    height: 100%;
}

#debug {
    width: 30%;
    border: solid green;
}

#history {
    width: 35%;
    border: solid blue;
}

#approval {
    width: 35%;
    border: solid yellow;
}

Button {
    margin: 1;
}
```

**cli.py**:
```python
@app.command()
def monitor() -> None:
    """Launch the SafeShell monitor TUI."""
    from safeshell.monitor.app import MonitorApp
    app = MonitorApp()
    app.run()
```

### Testing Requirements
- [ ] Test TUI launches without error
- [ ] Test three-pane layout renders correctly
- [ ] Test keyboard shortcuts work
- [ ] Test button clicks register
- [ ] Test input field captures text

### Success Criteria
- `safeshell monitor` launches TUI
- Three panes visible with correct proportions
- Buttons clickable with mouse
- Keyboard shortcuts work (q to quit, a/d for approve/deny)

---

## PR-4: Approval Protocol

**Status**: 🔴 Not Started

### Summary
Implement the approval request/response protocol between wrapper, daemon, and monitor.

### Files to Create

```
src/safeshell/daemon/
└── approval.py   # ApprovalManager, pending approval queue
```

### Files to Modify

- `src/safeshell/daemon/server.py` - Handle approval flow
- `src/safeshell/wrapper/client.py` - Wait for approval
- `src/safeshell/wrapper/shell.py` - Handle approval responses
- `src/safeshell/plugins/base.py` - Add _require_approval() helper
- `src/safeshell/plugins/git_protect.py` - Use REQUIRE_APPROVAL for force-push

### Key Implementation Details

**approval.py**:
```python
class PendingApproval(BaseModel):
    id: str
    command: str
    plugin_name: str
    reason: str
    challenge_code: str
    created_at: datetime
    timeout_seconds: float = 300.0  # 5 minutes default

class ApprovalManager:
    """Manages pending approval requests."""

    def __init__(self):
        self._pending: dict[str, PendingApproval] = {}
        self._results: dict[str, asyncio.Future] = {}

    async def request_approval(
        self,
        command: str,
        plugin_name: str,
        reason: str,
    ) -> tuple[bool, str | None]:
        """
        Request approval for a command.

        Returns:
            (approved, denial_reason)
        """
        approval_id = secrets.token_urlsafe(8)
        challenge_code = self._generate_challenge()

        pending = PendingApproval(
            id=approval_id,
            command=command,
            plugin_name=plugin_name,
            reason=reason,
            challenge_code=challenge_code,
        )

        self._pending[approval_id] = pending
        result_future = asyncio.Future()
        self._results[approval_id] = result_future

        # Publish event
        await self.event_publisher.approval_needed(pending)

        # Wait for approval or timeout
        try:
            async with asyncio.timeout(pending.timeout_seconds):
                return await result_future
        except TimeoutError:
            return False, "Approval timed out"
        finally:
            del self._pending[approval_id]
            del self._results[approval_id]

    async def resolve(
        self,
        approval_id: str,
        approved: bool,
        reason: str | None = None,
    ) -> None:
        """Resolve a pending approval."""
        if approval_id in self._results:
            self._results[approval_id].set_result((approved, reason))
            await self.event_publisher.approval_resolved(
                approval_id, approved, reason
            )
```

**Wrapper Changes**:

The wrapper needs to handle the new approval_pending response:

```python
def _evaluate_and_execute(self, command: str) -> int:
    response = client.evaluate(command, working_dir, env)

    if response.should_execute:
        return _execute(command)

    if response.approval_pending:
        # Wait for approval resolution
        resolution = client.wait_for_approval(response.approval_id)
        if resolution.approved:
            return _execute(command)
        # Fall through to denial

    # Denied
    sys.stderr.write(response.denial_message + "\n")
    return 1
```

### Testing Requirements
- [ ] Test approval request creates pending entry
- [ ] Test approval resolution completes future
- [ ] Test timeout handling
- [ ] Test challenge code generation
- [ ] Test wrapper waits for approval
- [ ] Test deny reason propagates to wrapper

### Success Criteria
- Plugin can return REQUIRE_APPROVAL
- Daemon queues approval and waits
- Monitor shows pending approval
- Approve allows command execution
- Deny blocks with optional reason in message
- Timeout blocks with timeout message

---

## PR-5: Integration and Polish

**Status**: 🔴 Not Started

### Summary
Connect all components, add polish, and ensure robust error handling.

### Tasks

1. **Connect Monitor to Daemon**
   - Monitor connects to monitor.sock
   - Receives event stream
   - Updates UI reactively

2. **Wire Up Approval Actions**
   - Approve button sends approval to daemon
   - Deny button sends denial with reason
   - Challenge code input (fallback)

3. **Add Configuration**
   ```yaml
   # ~/.safeshell/config.yaml
   approval:
     timeout_seconds: 300
     show_challenge_code: true
   ```

4. **Error Handling**
   - Daemon disconnection: Show error, attempt reconnect
   - Multiple approvals: Queue display
   - Approval during monitor restart: Fail-closed

5. **Polish**
   - Color coding in debug pane
   - Status icons in history
   - Keyboard shortcuts help
   - Graceful exit

### Files to Modify

- `src/safeshell/monitor/app.py` - Add daemon connection
- `src/safeshell/monitor/widgets.py` - Add reactive updates
- `src/safeshell/config.py` - Add approval config
- `src/safeshell/plugins/git_protect.py` - Change force-push to REQUIRE_APPROVAL

### Testing Requirements
- [ ] Integration test: full approval flow
- [ ] Integration test: denial with reason
- [ ] Integration test: timeout
- [ ] Test reconnection after disconnect
- [ ] Test multiple pending approvals

### Success Criteria
- Full end-to-end approval workflow works
- Force-push prompts for approval
- Reason text appears in denial message
- Clean error handling throughout
- All integration tests pass

---

## Implementation Guidelines

### Code Standards

| Standard | Requirement |
|----------|-------------|
| No print() | Use loguru or Textual's logging |
| Pydantic models | All event/approval types |
| No subprocess | Continue using plumbum |
| Type hints | Full coverage |
| File-level noqa | As established in MVP |

### Testing Requirements

- Unit tests for all new modules
- Integration tests for approval flow
- TUI tests using Textual's test framework
- `poetry run pytest` must pass

### Documentation Standards

- File headers per existing pattern
- Docstrings for public APIs
- Update `.ai/ai-rules.md` if new patterns emerge

### Security Considerations

- Monitor socket permissions: 0600
- Challenge codes are random, time-limited
- No sensitive data in event stream

### Performance Targets

- Event delivery: < 10ms
- TUI responsiveness: < 50ms for user actions
- Approval timeout: Configurable, default 5 min

---

## Rollout Strategy

### Phase 2: Approval Workflow (This Roadmap)

1. Complete PRs 1-5 sequentially
2. Manual testing of full flow
3. Update requirements document with learnings
4. Create PR, merge to main

### Post-Phase 2

1. Update `.roadmap/REQUIREMENTS.md` with learnings
2. Move this roadmap to `.roadmap/complete/`
3. Begin Phase 3 planning (CI/CD Hardening)

---

## Success Metrics

### Launch Metrics
- [ ] `safeshell monitor` launches TUI
- [ ] Three-pane layout visible
- [ ] Event stream connects to daemon
- [ ] Approval prompt appears for REQUIRE_APPROVAL
- [ ] Approve allows execution
- [ ] Deny blocks with reason
- [ ] Timeout blocks gracefully

### Ongoing Metrics
- Test coverage maintained > 80%
- No MyPy errors
- No Ruff errors
- TUI responsive under load
