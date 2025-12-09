"""
File: src/safeshell/models.py
Purpose: Core Pydantic models for SafeShell data structures
Exports: Decision, CommandContext, EvaluationResult, DaemonRequest, DaemonResponse
Depends: pydantic, enum
Overview: Defines all data models used for IPC between wrapper and daemon, and plugin evaluation
"""

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class Decision(str, Enum):
    """Plugin decision for a command."""

    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"  # Phase 2


class ExecutionContext(str, Enum):
    """Context indicating who is executing the command."""

    AI = "ai"  # Command from AI agent (Claude Code, Cursor, etc.)
    HUMAN = "human"  # Command from human in terminal


class CommandContext(BaseModel):
    """Context for command evaluation by plugins.

    Contains all information a plugin needs to evaluate a command,
    including the command itself, working directory, and git context.
    """

    raw_command: str = Field(description="Full command string as received")
    parsed_args: list[str] = Field(default_factory=list, description="Command split into arguments")
    working_dir: str = Field(description="Current working directory")
    git_repo_root: str | None = Field(default=None, description="Root of git repository if in one")
    git_branch: str | None = Field(default=None, description="Current git branch if in a git repo")
    environment: dict[str, str] = Field(
        default_factory=dict, description="Relevant environment variables"
    )
    execution_context: ExecutionContext = Field(
        default=ExecutionContext.HUMAN,
        description="Who is executing: ai or human",
    )

    @property
    def executable(self) -> str | None:
        """Return the executable (first argument) if available."""
        return self.parsed_args[0] if self.parsed_args else None

    @property
    def args(self) -> list[str]:
        """Return arguments after the executable."""
        return self.parsed_args[1:] if len(self.parsed_args) > 1 else []

    @classmethod
    def from_command(
        cls,
        command: str,
        working_dir: str | Path,
        env: dict[str, str] | None = None,
        execution_context: "ExecutionContext | None" = None,
    ) -> "CommandContext":
        """Create CommandContext from a command string.

        Args:
            command: The raw command string
            working_dir: Current working directory
            env: Environment variables (optional)
            execution_context: Who is executing (ai or human)

        Returns:
            CommandContext with parsed command and detected git context
        """
        import shlex

        working_dir_str = str(working_dir)

        # Parse command into arguments
        try:
            parsed = shlex.split(command)
        except ValueError:
            # If shlex fails, fall back to simple split
            parsed = command.split()

        # Detect git context
        git_root, git_branch = cls._detect_git_context(working_dir_str)

        return cls(
            raw_command=command,
            parsed_args=parsed,
            working_dir=working_dir_str,
            git_repo_root=git_root,
            git_branch=git_branch,
            environment=env or {},
            execution_context=execution_context or ExecutionContext.HUMAN,
        )

    @staticmethod
    def _detect_git_context(working_dir: str) -> tuple[str | None, str | None]:
        """Detect git repository root and current branch.

        Walks up from working_dir looking for .git directory.
        Reads .git/HEAD directly for speed.

        Returns:
            Tuple of (git_root, branch_name) or (None, None) if not in a repo
        """
        current = Path(working_dir).resolve()

        # Walk up looking for .git
        while current != current.parent:
            git_dir = current / ".git"
            if git_dir.is_dir():
                # Found git repo, read branch from HEAD
                head_file = git_dir / "HEAD"
                branch = None
                if head_file.exists():
                    try:
                        content = head_file.read_text().strip()
                        if content.startswith("ref: refs/heads/"):
                            branch = content[16:]  # len("ref: refs/heads/") == 16
                        elif content.startswith("ref: "):
                            # Other ref format
                            branch = content[5:].split("/")[-1]
                        # If detached HEAD (just a SHA), branch stays None
                    except OSError:
                        pass
                return str(current), branch
            current = current.parent

        return None, None


class EvaluationResult(BaseModel):
    """Result from a single plugin's evaluation."""

    decision: Decision = Field(description="The plugin's decision")
    plugin_name: str = Field(description="Name of the plugin that made this decision")
    reason: str = Field(description="Human-readable explanation of the decision")
    challenge_code: str | None = Field(
        default=None, description="Challenge code for approval workflow (Phase 2)"
    )


class RequestType(str, Enum):
    """Types of requests from wrapper to daemon."""

    EVALUATE = "evaluate"
    PING = "ping"
    STATUS = "status"


class DaemonRequest(BaseModel):
    """Request from shell wrapper to daemon."""

    type: RequestType = Field(description="Type of request")
    command: str | None = Field(default=None, description="Command to evaluate")
    working_dir: str | None = Field(default=None, description="Working directory")
    env: dict[str, str] = Field(default_factory=dict, description="Environment variables")
    execution_context: ExecutionContext = Field(
        default=ExecutionContext.HUMAN,
        description="Who is executing: ai or human",
    )


class DaemonResponse(BaseModel):
    """Response from daemon to shell wrapper."""

    success: bool = Field(description="Whether the request was processed successfully")
    results: list[EvaluationResult] = Field(
        default_factory=list, description="Results from each plugin"
    )
    final_decision: Decision = Field(
        default=Decision.ALLOW, description="Aggregate decision (most restrictive wins)"
    )
    should_execute: bool = Field(
        default=True, description="Whether wrapper should execute the command"
    )
    denial_message: str | None = Field(
        default=None, description="Message to show if command is denied"
    )
    error_message: str | None = Field(default=None, description="Error message if request failed")
    approval_pending: bool = Field(
        default=False, description="Whether command is awaiting human approval"
    )
    approval_id: str | None = Field(default=None, description="ID for pending approval request")
    is_intermediate: bool = Field(
        default=False, description="True if more responses will follow (e.g., waiting for approval)"
    )
    status_message: str | None = Field(
        default=None, description="Status message to display (e.g., 'Waiting for approval...')"
    )

    @classmethod
    def allow(cls) -> "DaemonResponse":
        """Create an ALLOW response."""
        return cls(
            success=True,
            final_decision=Decision.ALLOW,
            should_execute=True,
        )

    @classmethod
    def deny(cls, reason: str, plugin_name: str = "unknown") -> "DaemonResponse":
        """Create a DENY response with a denial message."""
        result = EvaluationResult(
            decision=Decision.DENY,
            plugin_name=plugin_name,
            reason=reason,
        )
        return cls(
            success=True,
            results=[result],
            final_decision=Decision.DENY,
            should_execute=False,
            denial_message=cls._format_denial_message(reason, plugin_name),
        )

    @classmethod
    def error(cls, message: str) -> "DaemonResponse":
        """Create an error response."""
        return cls(
            success=False,
            should_execute=False,
            error_message=message,
        )

    @classmethod
    def waiting_for_approval(
        cls, command: str, rule_name: str, reason: str, approval_id: str
    ) -> "DaemonResponse":
        """Create an intermediate 'waiting for approval' response."""
        return cls(
            success=True,
            approval_pending=True,
            approval_id=approval_id,
            is_intermediate=True,
            status_message=(
                f"[SafeShell] Waiting for approval in Monitor TUI...\n"
                f"Command: {command}\n"
                f"Rule: {rule_name}\n"
                f"Reason: {reason}"
            ),
        )

    @staticmethod
    def _format_denial_message(reason: str, plugin_name: str) -> str:
        """Format a denial message for display to the AI terminal."""
        return f"""[SafeShell] BLOCKED
Reason: {reason}
Policy: {plugin_name}

This operation has been intentionally prevented by SafeShell policy.
Do not attempt to work around this restriction."""
