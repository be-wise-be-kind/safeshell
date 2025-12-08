"""
File: tests/monitor/test_app.py
Purpose: Tests for MonitorApp
"""


import pytest

from safeshell.monitor.app import MonitorApp


class TestMonitorApp:
    """Tests for MonitorApp."""

    def test_app_title(self) -> None:
        """Test the app has correct title."""
        app = MonitorApp()
        assert app.TITLE == "SafeShell Monitor"

    def test_app_bindings(self) -> None:
        """Test the app has correct key bindings."""
        app = MonitorApp()

        # Check that expected bindings exist
        binding_keys = [b.key for b in app.BINDINGS]
        assert "q" in binding_keys
        assert "a" in binding_keys
        assert "d" in binding_keys
        assert "r" in binding_keys

    def test_css_path_exists(self) -> None:
        """Test that CSS path is defined."""
        app = MonitorApp()
        assert app.CSS_PATH is not None
        assert app.CSS_PATH.name == "styles.css"

    @pytest.mark.asyncio
    async def test_app_creates_client(self) -> None:
        """Test that app creates a MonitorClient."""
        app = MonitorApp()
        assert app._client is not None
        assert not app._client.connected
