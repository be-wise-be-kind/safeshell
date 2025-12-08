"""
File: src/safeshell/plugins/base.py
Purpose: Abstract base class for SafeShell plugins
Exports: Plugin
Depends: abc, safeshell.models
Overview: Defines the Plugin ABC that all policy plugins must implement
"""

from abc import ABC, abstractmethod

from safeshell.models import CommandContext, Decision, EvaluationResult


class Plugin(ABC):
    """Abstract base class for SafeShell plugins.

    All policy logic in SafeShell lives in plugins. Each plugin:
    - Has a unique name and description
    - Can filter which commands it evaluates via matches()
    - Evaluates commands and returns decisions via evaluate()

    Example:
        class MyPlugin(Plugin):
            @property
            def name(self) -> str:
                return "my-plugin"

            @property
            def description(self) -> str:
                return "Example plugin"

            def evaluate(self, ctx: CommandContext) -> EvaluationResult:
                if some_dangerous_condition(ctx):
                    return self._deny("Dangerous operation detected")
                return self._allow("Operation permitted")
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this plugin.

        Used in logs, config, and denial messages.
        Should be lowercase with hyphens (e.g., 'git-protect').
        """
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this plugin does."""
        ...

    def matches(self, ctx: CommandContext) -> bool:
        """Check if this plugin should evaluate the given command.

        Override this method to filter commands for performance.
        By default, all commands are evaluated.

        Args:
            ctx: Command context with parsed command and environment

        Returns:
            True if this plugin should evaluate the command, False to skip
        """
        return True

    @abstractmethod
    def evaluate(self, ctx: CommandContext) -> EvaluationResult:
        """Evaluate a command and return a decision.

        This is the core policy logic. Plugins should:
        - Analyze the command context
        - Return ALLOW if the command is safe
        - Return DENY with a reason if the command should be blocked
        - Return REQUIRE_APPROVAL for risky-but-legitimate operations (Phase 2)

        Args:
            ctx: Command context with parsed command, working dir, git info, etc.

        Returns:
            EvaluationResult with decision and reasoning
        """
        ...

    def _allow(self, reason: str) -> EvaluationResult:
        """Helper to create an ALLOW result.

        Args:
            reason: Brief explanation of why the command is allowed

        Returns:
            EvaluationResult with Decision.ALLOW
        """
        return EvaluationResult(
            decision=Decision.ALLOW,
            plugin_name=self.name,
            reason=reason,
        )

    def _deny(self, reason: str) -> EvaluationResult:
        """Helper to create a DENY result.

        Args:
            reason: Explanation of why the command is blocked

        Returns:
            EvaluationResult with Decision.DENY
        """
        return EvaluationResult(
            decision=Decision.DENY,
            plugin_name=self.name,
            reason=reason,
        )

    def _require_approval(self, reason: str) -> EvaluationResult:
        """Helper to create a REQUIRE_APPROVAL result (Phase 2).

        Args:
            reason: Explanation of why approval is needed

        Returns:
            EvaluationResult with Decision.REQUIRE_APPROVAL
        """
        return EvaluationResult(
            decision=Decision.REQUIRE_APPROVAL,
            plugin_name=self.name,
            reason=reason,
        )
