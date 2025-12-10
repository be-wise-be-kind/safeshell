"""
File: src/safeshell/config.py
Purpose: Configuration loading and validation
Exports: SafeShellConfig, UnreachableBehavior, load_config, CONFIG_PATH, SAFESHELL_DIR
Depends: pydantic, pyyaml, pathlib, os
Overview: Loads and validates SafeShell configuration from ~/.safeshell/config.yaml
"""

import os
from enum import Enum
from pathlib import Path

import yaml
from loguru import logger
from pydantic import BaseModel, Field, field_validator

from safeshell.exceptions import ConfigError

# Base directory for SafeShell data (also defined in daemon.lifecycle for daemon-specific paths)
SAFESHELL_DIR = Path.home() / ".safeshell"
CONFIG_PATH = SAFESHELL_DIR / "config.yaml"


class UnreachableBehavior(str, Enum):
    """Behavior when daemon is unreachable."""

    FAIL_CLOSED = "fail_closed"  # Block all commands (safe, default)
    FAIL_OPEN = "fail_open"  # Allow with warning (less safe)


class SafeShellConfig(BaseModel):
    """SafeShell configuration model.

    Loaded from ~/.safeshell/config.yaml with defaults applied.
    """

    unreachable_behavior: UnreachableBehavior = Field(
        default=UnreachableBehavior.FAIL_CLOSED,
        description="Behavior when daemon is unreachable",
    )

    delegate_shell: str = Field(
        default="/bin/bash",
        description="Shell to delegate commands to after evaluation",
    )

    log_level: str = Field(
        default="INFO",
        description="Logging level for daemon (DEBUG, INFO, WARNING, ERROR)",
    )

    log_file: Path | None = Field(
        default=None,
        description="Log file path (defaults to ~/.safeshell/daemon.log)",
    )

    condition_timeout_ms: int = Field(
        default=100,
        description="Timeout in milliseconds for bash condition evaluation",
        ge=10,
        le=5000,
    )

    approval_timeout_seconds: float = Field(
        default=300.0,
        description="Timeout in seconds for approval requests",
        ge=10.0,
        le=3600.0,
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate that log level is valid."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR"}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            logger.warning(f"Invalid log level '{v}', using INFO")
            return "INFO"
        return v_upper

    def get_log_file_path(self) -> Path:
        """Get the log file path, using default if not set.

        Returns:
            Path to log file (either configured or default)
        """
        if self.log_file is not None:
            return self.log_file
        return SAFESHELL_DIR / "daemon.log"

    @field_validator("delegate_shell")
    @classmethod
    def validate_delegate_shell(cls, v: str) -> str:
        """Validate that delegate shell exists."""
        if not Path(v).exists():
            logger.warning(f"Delegate shell '{v}' does not exist, using default")
            return "/bin/bash"
        return v

    @classmethod
    def detect_default_shell(cls) -> str:
        """Detect the user's default shell.

        Returns:
            Path to user's shell from SHELL env var, or /bin/bash as fallback
        """
        shell = os.environ.get("SHELL", "/bin/bash")
        if Path(shell).exists():
            return shell
        return "/bin/bash"


def load_config(config_path: Path | None = None) -> SafeShellConfig:
    """Load configuration from file or return defaults.

    Args:
        config_path: Optional path to config file (defaults to ~/.safeshell/config.yaml)

    Returns:
        Loaded and validated configuration

    Raises:
        ConfigError: If config file exists but is invalid
    """
    path = config_path or CONFIG_PATH

    if not path.exists():
        logger.debug(f"No config file at {path}, using defaults")
        return SafeShellConfig(delegate_shell=SafeShellConfig.detect_default_shell())

    try:
        content = path.read_text()
        data = yaml.safe_load(content)

        if data is None:
            # Empty file
            return SafeShellConfig(delegate_shell=SafeShellConfig.detect_default_shell())

        return SafeShellConfig.model_validate(data)

    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in config file: {e}") from e
    except Exception as e:
        raise ConfigError(f"Failed to load config: {e}") from e


def save_config(config: SafeShellConfig, config_path: Path | None = None) -> None:
    """Save configuration to file.

    Args:
        config: Configuration to save
        config_path: Optional path (defaults to ~/.safeshell/config.yaml)
    """
    path = config_path or CONFIG_PATH

    # Ensure directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to dict with mode='json' to get primitive types (strings for enums)
    data = config.model_dump(mode="json")
    content = yaml.dump(data, default_flow_style=False, sort_keys=False)

    # Add header comment
    header = """# SafeShell Configuration
# See https://github.com/safeshell/safeshell for documentation

"""
    path.write_text(header + content)
    logger.info(f"Saved configuration to {path}")


def create_default_config() -> SafeShellConfig:
    """Create and save default configuration.

    Returns:
        The created default configuration
    """
    config = SafeShellConfig(delegate_shell=SafeShellConfig.detect_default_shell())
    save_config(config)
    return config
