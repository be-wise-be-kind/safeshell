"""Tests for safeshell.daemon.server module."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from safeshell.config import SafeShellConfig
from safeshell.daemon.server import configure_logging


class TestConfigureLogging:
    """Tests for configure_logging function."""

    def test_configure_logging_creates_log_file_directory(self) -> None:
        """Test that configure_logging creates the log file's parent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "subdir" / "test.log"
            config = SafeShellConfig(log_file=log_path, log_level="DEBUG")

            # Mock logger.add to avoid actually configuring loguru
            with patch("safeshell.daemon.server.logger") as mock_logger:
                configure_logging(config)

            # Should have called logger.remove() once
            mock_logger.remove.assert_called_once()

            # Should have called logger.add() twice (stderr and file)
            assert mock_logger.add.call_count == 2

            # Directory should be created
            assert log_path.parent.exists()

    def test_configure_logging_uses_config_log_level(self) -> None:
        """Test that configure_logging uses the log level from config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "test.log"
            config = SafeShellConfig(log_file=log_path, log_level="WARNING")

            with patch("safeshell.daemon.server.logger") as mock_logger:
                configure_logging(config)

            # Check that both add calls used WARNING level
            for call in mock_logger.add.call_args_list:
                assert call.kwargs.get("level") == "WARNING"
