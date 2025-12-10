"""Tests for safeshell.config module."""

import tempfile
from pathlib import Path

import pytest

from safeshell.config import (
    SafeShellConfig,
    UnreachableBehavior,
    load_config,
    save_config,
)
from safeshell.exceptions import ConfigError


class TestUnreachableBehavior:
    """Tests for UnreachableBehavior enum."""

    def test_values(self) -> None:
        """Test enum values."""
        assert UnreachableBehavior.FAIL_CLOSED.value == "fail_closed"
        assert UnreachableBehavior.FAIL_OPEN.value == "fail_open"


class TestSafeShellConfig:
    """Tests for SafeShellConfig model."""

    def test_defaults(self) -> None:
        """Test default configuration values."""
        config = SafeShellConfig()
        assert config.unreachable_behavior == UnreachableBehavior.FAIL_CLOSED
        assert config.delegate_shell == "/bin/bash"
        assert config.log_level == "INFO"
        assert config.log_file is None

    def test_custom_values(self, tmp_path: Path) -> None:
        """Test configuration with custom values."""
        # Use /bin/bash which is guaranteed to exist
        log_file = tmp_path / "test.log"
        config = SafeShellConfig(
            unreachable_behavior=UnreachableBehavior.FAIL_OPEN,
            delegate_shell="/bin/bash",
            log_level="DEBUG",
            log_file=log_file,
        )
        assert config.unreachable_behavior == UnreachableBehavior.FAIL_OPEN
        assert config.delegate_shell == "/bin/bash"
        assert config.log_level == "DEBUG"
        assert config.log_file == log_file

    def test_detect_default_shell(self) -> None:
        """Test shell detection."""
        shell = SafeShellConfig.detect_default_shell()
        # Should return a valid path
        assert shell.startswith("/")
        assert Path(shell).exists() or shell == "/bin/bash"

    def test_log_level_validation_uppercase(self) -> None:
        """Test that log level is normalized to uppercase."""
        config = SafeShellConfig(log_level="debug")
        assert config.log_level == "DEBUG"

    def test_log_level_validation_invalid(self) -> None:
        """Test that invalid log level defaults to INFO."""
        config = SafeShellConfig(log_level="invalid")
        assert config.log_level == "INFO"

    def test_log_level_validation_all_valid_levels(self) -> None:
        """Test all valid log levels are accepted."""
        for level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            config = SafeShellConfig(log_level=level)
            assert config.log_level == level

    def test_get_log_file_path_default(self) -> None:
        """Test default log file path."""
        config = SafeShellConfig()
        log_path = config.get_log_file_path()
        assert log_path.name == "daemon.log"
        assert ".safeshell" in str(log_path)

    def test_get_log_file_path_custom(self, tmp_path: Path) -> None:
        """Test custom log file path."""
        custom_path = tmp_path / "custom.log"
        config = SafeShellConfig(log_file=custom_path)
        assert config.get_log_file_path() == custom_path


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_missing_file(self) -> None:
        """Test loading config when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "nonexistent.yaml"
            config = load_config(config_path)
            # Should return defaults
            assert config.unreachable_behavior == UnreachableBehavior.FAIL_CLOSED

    def test_load_empty_file(self) -> None:
        """Test loading config from empty file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text("")
            config = load_config(config_path)
            # Should return defaults
            assert config.unreachable_behavior == UnreachableBehavior.FAIL_CLOSED

    def test_load_valid_file(self) -> None:
        """Test loading config from valid YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text("""
unreachable_behavior: fail_open
delegate_shell: /bin/bash
log_level: DEBUG
""")
            config = load_config(config_path)
            assert config.unreachable_behavior == UnreachableBehavior.FAIL_OPEN
            assert config.delegate_shell == "/bin/bash"
            assert config.log_level == "DEBUG"

    def test_load_partial_file(self) -> None:
        """Test loading config with partial settings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text("log_level: WARNING\n")
            config = load_config(config_path)
            # Specified value
            assert config.log_level == "WARNING"
            # Default values
            assert config.unreachable_behavior == UnreachableBehavior.FAIL_CLOSED

    def test_load_invalid_yaml(self) -> None:
        """Test loading config from invalid YAML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text("invalid: yaml: syntax: [")
            with pytest.raises(ConfigError):
                load_config(config_path)


class TestSaveConfig:
    """Tests for save_config function."""

    def test_save_and_load_roundtrip(self) -> None:
        """Test saving and loading config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"

            original = SafeShellConfig(
                unreachable_behavior=UnreachableBehavior.FAIL_OPEN,
                delegate_shell="/bin/bash",
                log_level="DEBUG",
            )
            save_config(original, config_path)

            loaded = load_config(config_path)
            assert loaded.unreachable_behavior == original.unreachable_behavior
            assert loaded.delegate_shell == original.delegate_shell
            assert loaded.log_level == original.log_level

    def test_save_creates_directory(self) -> None:
        """Test that save creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "subdir" / "config.yaml"
            config = SafeShellConfig()
            save_config(config, config_path)
            assert config_path.exists()
