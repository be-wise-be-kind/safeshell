"""
File: tests/monitor/test_widgets.py
Purpose: Tests for monitor TUI widgets
"""

from datetime import datetime

from safeshell.monitor.widgets import ApprovalPane, CommandHistoryItem, DebugPane, HistoryPane


class TestCommandHistoryItem:
    """Tests for CommandHistoryItem model."""

    def test_create_basic(self) -> None:
        """Test creating a basic history item."""
        item = CommandHistoryItem(
            command="git commit -m test",
            timestamp=datetime.now(),
        )
        assert item.command == "git commit -m test"
        assert item.status == "pending"
        assert item.decision is None
        assert item.reason is None
        assert item.approval_id is None

    def test_create_with_all_fields(self) -> None:
        """Test creating item with all fields."""
        now = datetime.now()
        item = CommandHistoryItem(
            command="git push --force",
            timestamp=now,
            status="blocked",
            decision="deny",
            reason="Force push not allowed",
            approval_id="test-id-123",
        )
        assert item.command == "git push --force"
        assert item.timestamp == now
        assert item.status == "blocked"
        assert item.decision == "deny"
        assert item.reason == "Force push not allowed"
        assert item.approval_id == "test-id-123"


class TestDebugPane:
    """Tests for DebugPane widget."""

    def test_default_css_exists(self) -> None:
        """Test that DEFAULT_CSS is defined."""
        assert DebugPane.DEFAULT_CSS is not None
        assert "DebugPane" in DebugPane.DEFAULT_CSS


class TestHistoryPane:
    """Tests for HistoryPane widget."""

    def test_default_css_exists(self) -> None:
        """Test that DEFAULT_CSS is defined."""
        assert HistoryPane.DEFAULT_CSS is not None
        assert "HistoryPane" in HistoryPane.DEFAULT_CSS


class TestApprovalPane:
    """Tests for ApprovalPane widget."""

    def test_default_css_exists(self) -> None:
        """Test that DEFAULT_CSS is defined."""
        assert ApprovalPane.DEFAULT_CSS is not None
        assert "ApprovalPane" in ApprovalPane.DEFAULT_CSS

    def test_approval_action_message(self) -> None:
        """Test ApprovalAction message creation."""
        action = ApprovalPane.ApprovalAction(
            approved=True,
            approval_id="test-id",
            reason=None,
        )
        assert action.approved is True
        assert action.approval_id == "test-id"
        assert action.reason is None

    def test_approval_action_with_reason(self) -> None:
        """Test ApprovalAction message with denial reason."""
        action = ApprovalPane.ApprovalAction(
            approved=False,
            approval_id="test-id",
            reason="Not authorized",
        )
        assert action.approved is False
        assert action.approval_id == "test-id"
        assert action.reason == "Not authorized"

    def test_approval_action_with_remember_true(self) -> None:
        """Test ApprovalAction message with remember flag for approval."""
        action = ApprovalPane.ApprovalAction(
            approved=True,
            approval_id="test-id",
            remember=True,
        )
        assert action.approved is True
        assert action.approval_id == "test-id"
        assert action.remember is True

    def test_approval_action_deny_with_remember(self) -> None:
        """Test ApprovalAction message with remember flag for denial."""
        action = ApprovalPane.ApprovalAction(
            approved=False,
            approval_id="test-id",
            reason="Security risk",
            remember=True,
        )
        assert action.approved is False
        assert action.approval_id == "test-id"
        assert action.reason == "Security risk"
        assert action.remember is True

    def test_css_has_deny_remember_button(self) -> None:
        """Test that CSS includes styling for deny-remember button."""
        assert "#deny-remember-btn" in ApprovalPane.DEFAULT_CSS
