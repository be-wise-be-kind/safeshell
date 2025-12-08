"""
File: src/safeshell/daemon/manager.py
Purpose: Plugin management and command evaluation
Exports: PluginManager
Depends: safeshell.plugins, safeshell.models, loguru
Overview: Loads plugins and evaluates commands against all loaded plugins
"""

from loguru import logger

from safeshell.models import (
    CommandContext,
    DaemonRequest,
    DaemonResponse,
    Decision,
    EvaluationResult,
    RequestType,
)
from safeshell.plugins.base import Plugin
from safeshell.plugins.git_protect import GitProtectPlugin


class PluginManager:
    """Manages plugin loading and command evaluation.

    Loads built-in plugins on initialization and provides
    command evaluation against all loaded plugins.
    """

    def __init__(self) -> None:
        """Initialize plugin manager with built-in plugins."""
        self.plugins: list[Plugin] = []
        self._load_builtin_plugins()

    def _load_builtin_plugins(self) -> None:
        """Load built-in plugins."""
        # MVP: Only git-protect plugin
        self.plugins.append(GitProtectPlugin())
        logger.info(f"Loaded {len(self.plugins)} built-in plugin(s)")
        for plugin in self.plugins:
            logger.debug(f"  - {plugin.name}: {plugin.description}")

    def process_request(self, request: DaemonRequest) -> DaemonResponse:
        """Process a request from the shell wrapper.

        Args:
            request: Request from wrapper

        Returns:
            Response to send back to wrapper
        """
        if request.type == RequestType.PING:
            return self._handle_ping()

        if request.type == RequestType.STATUS:
            return self._handle_status()

        if request.type == RequestType.EVALUATE:
            return self._handle_evaluate(request)

        return DaemonResponse.error(f"Unknown request type: {request.type}")

    def _handle_ping(self) -> DaemonResponse:
        """Handle ping request."""
        return DaemonResponse(
            success=True,
            final_decision=Decision.ALLOW,
            should_execute=True,
        )

    def _handle_status(self) -> DaemonResponse:
        """Handle status request."""
        # Could include more status info in the future
        return DaemonResponse(
            success=True,
            final_decision=Decision.ALLOW,
            should_execute=True,
        )

    def _handle_evaluate(self, request: DaemonRequest) -> DaemonResponse:
        """Handle command evaluation request.

        Args:
            request: Request containing command to evaluate

        Returns:
            Response with evaluation results and final decision
        """
        if not request.command:
            return DaemonResponse.error("No command provided for evaluation")

        if not request.working_dir:
            return DaemonResponse.error("No working directory provided")

        # Build command context
        context = CommandContext.from_command(
            command=request.command,
            working_dir=request.working_dir,
            env=request.env,
        )

        logger.debug(f"Evaluating command: {request.command}")
        logger.debug(f"  Working dir: {request.working_dir}")
        logger.debug(f"  Git repo: {context.git_repo_root}")
        logger.debug(f"  Git branch: {context.git_branch}")

        # Evaluate against all plugins
        results: list[EvaluationResult] = []
        for plugin in self.plugins:
            if plugin.matches(context):
                result = plugin.evaluate(context)
                results.append(result)
                logger.debug(f"  Plugin {plugin.name}: {result.decision.value}")

        # Aggregate decisions (most restrictive wins)
        final_decision = self._aggregate_decisions(results)

        # Build response
        response = DaemonResponse(
            success=True,
            results=results,
            final_decision=final_decision,
            should_execute=(final_decision == Decision.ALLOW),
        )

        # Add denial message if blocked
        if final_decision == Decision.DENY:
            response.denial_message = self._build_denial_message(results)

        logger.info(
            f"Command '{request.command}' -> {final_decision.value}"
            + (f" ({response.denial_message})" if response.denial_message else "")
        )

        return response

    def _aggregate_decisions(self, results: list[EvaluationResult]) -> Decision:
        """Aggregate plugin decisions - most restrictive wins.

        Priority: DENY > REQUIRE_APPROVAL > ALLOW

        Args:
            results: List of evaluation results from plugins

        Returns:
            Most restrictive decision
        """
        if not results:
            return Decision.ALLOW

        if any(r.decision == Decision.DENY for r in results):
            return Decision.DENY

        if any(r.decision == Decision.REQUIRE_APPROVAL for r in results):
            return Decision.REQUIRE_APPROVAL

        return Decision.ALLOW

    def _build_denial_message(self, results: list[EvaluationResult]) -> str:
        """Build denial message from results.

        Args:
            results: Evaluation results (should contain at least one DENY)

        Returns:
            Formatted denial message for AI terminal
        """
        deny_results = [r for r in results if r.decision == Decision.DENY]
        if not deny_results:
            return "Command blocked by SafeShell policy"

        # Use the first denial (could combine in future)
        result = deny_results[0]
        return DaemonResponse._format_denial_message(result.reason, result.plugin_name)
