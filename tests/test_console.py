"""Tests for safeshell.console module."""

from io import StringIO
from unittest.mock import patch

from rich.console import Console

from safeshell.console import (
    console,
    print_error,
    print_info,
    print_status_panel,
    print_success,
    print_warning,
)


class TestConsole:
    """Tests for shared console instance."""

    def test_console_is_rich_console(self) -> None:
        """Test that console is a Rich Console instance."""
        assert isinstance(console, Console)

    def test_console_has_theme(self) -> None:
        """Test that console has a theme applied."""
        # Console should have theme styles available - check a custom style exists
        # The theme defines styles like "success", "error", "warning", etc.
        style = console.get_style("success")
        assert style is not None


class TestPrintSuccess:
    """Tests for print_success function."""

    def test_print_success_outputs_message(self) -> None:
        """Test print_success outputs the message with checkmark."""
        output = StringIO()
        test_console = Console(file=output, force_terminal=True)

        with patch("safeshell.console.console", test_console):
            print_success("Task completed")

        result = output.getvalue()
        assert "Task completed" in result
        # Should contain checkmark icon
        assert "\u2713" in result or "✓" in result


class TestPrintError:
    """Tests for print_error function."""

    def test_print_error_outputs_message(self) -> None:
        """Test print_error outputs the error message."""
        output = StringIO()
        test_console = Console(file=output, force_terminal=True)

        with patch("safeshell.console.console", test_console):
            print_error("Something went wrong")

        result = output.getvalue()
        assert "Something went wrong" in result
        # Should contain X icon
        assert "\u2717" in result or "✗" in result

    def test_print_error_with_hint(self) -> None:
        """Test print_error outputs hint when provided."""
        output = StringIO()
        test_console = Console(file=output, force_terminal=True)

        with patch("safeshell.console.console", test_console):
            print_error("File not found", "Check the path and try again")

        result = output.getvalue()
        assert "File not found" in result
        assert "Check the path and try again" in result


class TestPrintWarning:
    """Tests for print_warning function."""

    def test_print_warning_outputs_message(self) -> None:
        """Test print_warning outputs the warning message."""
        output = StringIO()
        test_console = Console(file=output, force_terminal=True)

        with patch("safeshell.console.console", test_console):
            print_warning("Proceed with caution")

        result = output.getvalue()
        assert "Proceed with caution" in result
        # Should contain warning icon
        assert "\u26a0" in result or "⚠" in result


class TestPrintInfo:
    """Tests for print_info function."""

    def test_print_info_outputs_message(self) -> None:
        """Test print_info outputs the info message."""
        output = StringIO()
        test_console = Console(file=output, force_terminal=True)

        with patch("safeshell.console.console", test_console):
            print_info("Here is some information")

        result = output.getvalue()
        assert "Here is some information" in result
        # Should contain arrow icon
        assert "\u2192" in result or "→" in result


class TestPrintStatusPanel:
    """Tests for print_status_panel function."""

    def test_print_status_panel_success(self) -> None:
        """Test print_status_panel with success styling."""
        output = StringIO()
        test_console = Console(file=output, force_terminal=True)

        with patch("safeshell.console.console", test_console):
            print_status_panel("Status", "All systems operational", success=True)

        result = output.getvalue()
        assert "All systems operational" in result

    def test_print_status_panel_failure(self) -> None:
        """Test print_status_panel with failure styling."""
        output = StringIO()
        test_console = Console(file=output, force_terminal=True)

        with patch("safeshell.console.console", test_console):
            print_status_panel("Error", "System failure", success=False)

        result = output.getvalue()
        assert "System failure" in result
