"""
File: src/safeshell/daemon/manager.py
Purpose: Rule management and command evaluation
Exports: RuleManager
Depends: safeshell.rules, safeshell.models, safeshell.daemon.events,
         safeshell.daemon.approval, loguru
Overview: Loads rules and evaluates commands against all loaded rules, emitting events
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from safeshell.models import (
    CommandContext,
    DaemonRequest,
    DaemonResponse,
    Decision,
    EvaluationResult,
    RequestType,
)
from safeshell.rules import RuleEvaluator, load_rules

if TYPE_CHECKING:
    from safeshell.daemon.approval import ApprovalManager
    from safeshell.daemon.events import DaemonEventPublisher


class RuleManager:
    """Manages rule loading and command evaluation.

    Loads rules from global and repo configuration files and provides
    command evaluation against all loaded rules. Optionally publishes
    events during evaluation for monitor visibility.
    """

    def __init__(
        self,
        event_publisher: DaemonEventPublisher | None = None,
        approval_manager: ApprovalManager | None = None,
        condition_timeout_ms: int = 100,
    ) -> None:
        """Initialize rule manager.

        Args:
            event_publisher: Optional publisher for emitting evaluation events
            approval_manager: Optional manager for handling REQUIRE_APPROVAL decisions
            condition_timeout_ms: Timeout for bash conditions in milliseconds
        """
        self._event_publisher = event_publisher
        self._approval_manager = approval_manager
        self._condition_timeout_ms = condition_timeout_ms
        self._evaluator: RuleEvaluator | None = None
        self._rule_count: int = 0

    @property
    def rule_count(self) -> int:
        """Return the number of loaded rules."""
        return self._rule_count

    async def process_request(self, request: DaemonRequest) -> DaemonResponse:
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
            return await self._handle_evaluate(request)

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
        return DaemonResponse(
            success=True,
            final_decision=Decision.ALLOW,
            should_execute=True,
        )

    async def _handle_evaluate(self, request: DaemonRequest) -> DaemonResponse:
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

        # Emit command received event
        if self._event_publisher:
            await self._event_publisher.command_received(
                request.command, request.working_dir
            )

        # Load rules for the working directory
        rules = load_rules(request.working_dir)
        self._rule_count = len(rules)

        # Create evaluator
        evaluator = RuleEvaluator(
            rules=rules,
            condition_timeout_ms=self._condition_timeout_ms,
        )

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
        logger.debug(f"  Rules loaded: {len(rules)}")

        # Emit evaluation started event
        if self._event_publisher:
            await self._event_publisher.evaluation_started(
                request.command, len(rules)
            )

        # Evaluate against rules
        result = await evaluator.evaluate(context)

        # Handle REQUIRE_APPROVAL decision
        if result.decision == Decision.REQUIRE_APPROVAL:
            result = await self._handle_approval(request.command, result)

        results = [result]

        # Build response
        response = DaemonResponse(
            success=True,
            results=results,
            final_decision=result.decision,
            should_execute=(result.decision == Decision.ALLOW),
        )

        # Add denial message if blocked
        if result.decision == Decision.DENY:
            response.denial_message = self._build_denial_message(result)

        # Emit evaluation completed event
        if self._event_publisher:
            await self._event_publisher.evaluation_completed(
                request.command,
                result.decision,
                result.plugin_name,
                result.reason,
            )

        logger.info(
            f"Command '{request.command}' -> {result.decision.value}"
            + (f" ({response.denial_message})" if response.denial_message else "")
        )

        return response

    def _build_denial_message(self, result: EvaluationResult) -> str:
        """Build denial message from result.

        Args:
            result: Evaluation result with DENY decision

        Returns:
            Formatted denial message for AI terminal
        """
        return DaemonResponse._format_denial_message(result.reason, result.plugin_name)

    async def _handle_approval(
        self, command: str, result: EvaluationResult
    ) -> EvaluationResult:
        """Handle REQUIRE_APPROVAL decision by waiting for approval.

        Args:
            command: The command awaiting approval
            result: Original evaluation result with REQUIRE_APPROVAL

        Returns:
            New EvaluationResult with ALLOW or DENY based on approval resolution
        """
        # Import here to avoid circular dependency at runtime
        from safeshell.daemon.approval import ApprovalResult

        if self._approval_manager is None:
            # No approval manager configured - treat as deny
            logger.warning(
                f"REQUIRE_APPROVAL for '{command}' but no ApprovalManager configured"
            )
            return EvaluationResult(
                decision=Decision.DENY,
                plugin_name=result.plugin_name,
                reason=f"{result.reason} (approval system unavailable)",
            )

        # Request approval and wait for resolution
        logger.info(f"Requesting approval for: {command}")
        approval_result, denial_reason = await self._approval_manager.request_approval(
            command=command,
            plugin_name=result.plugin_name,
            reason=result.reason,
        )

        if approval_result == ApprovalResult.APPROVED:
            logger.info(f"Command approved: {command}")
            return EvaluationResult(
                decision=Decision.ALLOW,
                plugin_name=result.plugin_name,
                reason=f"Approved: {result.reason}",
            )

        # Denied or timed out
        if approval_result == ApprovalResult.TIMEOUT:
            denial_reason = "Approval timed out"
            logger.warning(f"Command timed out waiting for approval: {command}")
        else:
            logger.info(f"Command denied: {command}")

        return EvaluationResult(
            decision=Decision.DENY,
            plugin_name=result.plugin_name,
            reason=denial_reason or result.reason,
        )


# Backward compatibility alias
PluginManager = RuleManager
