"""
File: src/safeshell/config.py
Purpose: Configuration loading and validation
Exports: SafeShellConfig, UnreachableBehavior, load_config, CONFIG_PATH, SAFESHELL_DIR
Depends: pydantic, pyyaml, pathlib, os, safeshell.common
Overview: Loads and validates SafeShell configuration from ~/.safeshell/config.yaml
"""

import os
from enum import Enum
from pathlib import Path

import yaml
from loguru import logger
from pydantic import BaseModel, Field, field_validator

from safeshell.common import SAFESHELL_DIR
from safeshell.exceptions import ConfigError

# Config-specific path derived from SAFESHELL_DIR
CONFIG_PATH = SAFESHELL_DIR / "config.yaml"

# Configuration limits and defaults
_MAX_CONDITION_TIMEOUT_MS = 5000  # Maximum allowed condition evaluation timeout
_DEFAULT_APPROVAL_TIMEOUT_SECONDS = 300.0  # 5 minutes
_MAX_APPROVAL_TIMEOUT_SECONDS = 3600.0  # 1 hour
_DEFAULT_APPROVAL_MEMORY_TTL_SECONDS = 300  # 5 minutes
_MAX_APPROVAL_MEMORY_TTL_SECONDS = 86400  # 24 hours


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
        le=_MAX_CONDITION_TIMEOUT_MS,
    )

    approval_timeout_seconds: float = Field(
        default=_DEFAULT_APPROVAL_TIMEOUT_SECONDS,
        description="Timeout in seconds for approval requests",
        ge=10.0,
        le=_MAX_APPROVAL_TIMEOUT_SECONDS,
    )

    approval_memory_ttl_seconds: int = Field(
        default=_DEFAULT_APPROVAL_MEMORY_TTL_SECONDS,
        description="TTL for 'don't ask again' approvals. 0 = session-only (no expiry)",
        ge=0,
        le=_MAX_APPROVAL_MEMORY_TTL_SECONDS,
    )

    # Builtin override settings - control which shell builtins are intercepted
    check_cd: bool = Field(
        default=True,
        description="Override cd builtin to check directory changes",
    )
    check_source: bool = Field(
        default=True,
        description="Override source/. builtin to check sourced scripts",
    )
    check_eval: bool = Field(
        default=False,
        description="Override eval builtin (disabled by default due to shell hook overhead)",
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


# Shell-readable config path (written on daemon start)
SHELL_CONFIG_PATH = SAFESHELL_DIR / "shell_config"


def write_shell_config(config: SafeShellConfig) -> None:
    """Write shell-readable configuration for init.bash.

    Creates a file that can be sourced by bash to get config values.
    This is written by the daemon on startup.

    Args:
        config: Configuration to write
    """
    # Ensure directory exists
    SHELL_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Convert booleans to shell format (1/0)
    content = f"""# SafeShell shell configuration (auto-generated by daemon)
# Do not edit - changes will be overwritten on daemon restart

SAFESHELL_CHECK_CD={1 if config.check_cd else 0}
SAFESHELL_CHECK_SOURCE={1 if config.check_source else 0}
SAFESHELL_CHECK_EVAL={1 if config.check_eval else 0}
"""
    SHELL_CONFIG_PATH.write_text(content)
    logger.debug(f"Wrote shell config to {SHELL_CONFIG_PATH}")
