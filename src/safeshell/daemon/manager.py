"""
File: src/safeshell/daemon/manager.py
Purpose: Rule management and command evaluation
Exports: RuleManager
Depends: safeshell.rules, safeshell.models, safeshell.daemon.events,
         safeshell.daemon.approval, loguru
Overview: Loads rules and evaluates commands against all loaded rules, emitting events
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
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
from safeshell.rules import RuleCache, RuleEvaluator

if TYPE_CHECKING:
    from safeshell.daemon.approval import ApprovalManager
    from safeshell.daemon.events import DaemonEventPublisher
    from safeshell.daemon.session_memory import SessionMemory


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
        session_memory: SessionMemory | None = None,
    ) -> None:
        """Initialize rule manager.

        Args:
            event_publisher: Optional publisher for emitting evaluation events
            approval_manager: Optional manager for handling REQUIRE_APPROVAL decisions
            session_memory: Optional session memory for "don't ask again" approvals
        """
        self._event_publisher = event_publisher
        self._approval_manager = approval_manager
        self._session_memory = session_memory
        self._evaluator: RuleEvaluator | None = None
        self._rule_count: int = 0
        self._rule_cache = RuleCache()

        # Cached evaluator for reuse when rules haven't changed
        self._cached_evaluator: RuleEvaluator | None = None
        self._cached_rules_hash: int | None = None

    @property
    def rule_count(self) -> int:
        """Return the number of loaded rules."""
        return self._rule_count

    async def process_request(
        self,
        request: DaemonRequest,
        send_intermediate: Callable[[DaemonResponse], Awaitable[None]] | None = None,
    ) -> DaemonResponse:
        """Process a request from the shell wrapper.

        Args:
            request: Request from wrapper
            send_intermediate: Optional callback to send intermediate responses
                (e.g., "waiting for approval" messages)

        Returns:
            Response to send back to wrapper
        """
        if request.type == RequestType.PING:
            return self._handle_ping()

        if request.type == RequestType.STATUS:
            return self._handle_status()

        if request.type == RequestType.EVALUATE:
            return await self._handle_evaluate(request, send_intermediate)

        if request.type == RequestType.EXECUTE:
            return await self._handle_execute(request, send_intermediate)

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

    async def _handle_evaluate(
        self,
        request: DaemonRequest,
        send_intermediate: Callable[[DaemonResponse], Awaitable[None]] | None = None,
    ) -> DaemonResponse:
        """Handle command evaluation request.

        Args:
            request: Request containing command to evaluate
            send_intermediate: Optional callback to send intermediate responses

        Returns:
            Response with evaluation results and final decision
        """
        if not request.command:
            return DaemonResponse.error("No command provided for evaluation")

        if not request.working_dir:
            return DaemonResponse.error("No working directory provided")

        # Emit command received event
        if self._event_publisher:
            await self._event_publisher.command_received(request.command, request.working_dir)

        # Load rules for the working directory (with caching)
        rules, cache_hit = self._rule_cache.get_rules(request.working_dir)
        self._rule_count = len(rules)

        # Compute hash of rules to detect changes (using rule names and content)
        rules_hash = hash(tuple((r.name, r.action, tuple(r.commands)) for r in rules))

        # Reuse cached evaluator if rules haven't changed (performance optimization)
        if cache_hit and self._cached_evaluator and self._cached_rules_hash == rules_hash:
            evaluator = self._cached_evaluator
            logger.debug(f"Rules: {len(rules)} (cache_hit={cache_hit}, evaluator_reused=True)")
        else:
            # Create new evaluator
            evaluator = RuleEvaluator(rules=rules)
            self._cached_evaluator = evaluator
            self._cached_rules_hash = rules_hash
            logger.debug(f"Rules: {len(rules)} (cache_hit={cache_hit}, evaluator_reused=False)")

        # Build command context
        context = CommandContext.from_command(
            command=request.command,
            working_dir=request.working_dir,
            env=request.env,
            execution_context=request.execution_context,
        )

        logger.debug(f"Evaluating command: {request.command}")
        logger.debug(f"  Working dir: {request.working_dir}")
        logger.debug(f"  Execution context: {context.execution_context}")
        logger.debug(f"  Git repo: {context.git_repo_root}")
        logger.debug(f"  Git branch: {context.git_branch}")
        logger.debug(f"  Rules loaded: {len(rules)}")

        # Emit evaluation started event
        if self._event_publisher:
            await self._event_publisher.evaluation_started(request.command, len(rules))

        # Evaluate against rules
        result = await evaluator.evaluate(context)

        # Handle REQUIRE_APPROVAL decision
        if result.decision == Decision.REQUIRE_APPROVAL:
            result = await self._handle_approval(request.command, result, send_intermediate)

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

        # Log at appropriate level: DEBUG for allowed, INFO for denied/approval
        log_msg = f"Command '{request.command}' -> {result.decision.value}"
        if response.denial_message:
            log_msg += f" ({response.denial_message})"

        if result.decision == Decision.ALLOW:
            logger.debug(log_msg)
        else:
            logger.info(log_msg)

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
        self,
        command: str,
        result: EvaluationResult,
        send_intermediate: Callable[[DaemonResponse], Awaitable[None]] | None = None,
    ) -> EvaluationResult:
        """Handle REQUIRE_APPROVAL decision by waiting for approval.

        Checks session memory first for "don't ask again" decisions.
        If not found in memory, requests approval from user.

        Args:
            command: The command awaiting approval
            result: Original evaluation result with REQUIRE_APPROVAL
            send_intermediate: Optional callback to send "waiting" message

        Returns:
            New EvaluationResult with ALLOW or DENY based on approval resolution
        """
        # Import here to avoid circular dependency at runtime
        from safeshell.daemon.approval import ApprovalResult

        # Check session memory first for "don't ask again" decisions
        if self._session_memory is not None:
            if self._session_memory.is_pre_approved(result.plugin_name, command):
                logger.info(f"Auto-approved via session memory: {command}")
                return EvaluationResult(
                    decision=Decision.ALLOW,
                    plugin_name=result.plugin_name,
                    reason=f"Auto-approved (remembered): {result.reason}",
                )

            if self._session_memory.is_pre_denied(result.plugin_name, command):
                logger.info(f"Auto-denied via session memory: {command}")
                return EvaluationResult(
                    decision=Decision.DENY,
                    plugin_name=result.plugin_name,
                    reason=f"Auto-denied (remembered): {result.reason}",
                )

        if self._approval_manager is None:
            # No approval manager configured - treat as deny
            logger.warning(f"REQUIRE_APPROVAL for '{command}' but no ApprovalManager configured")
            return EvaluationResult(
                decision=Decision.DENY,
                plugin_name=result.plugin_name,
                reason=f"{result.reason} (approval system unavailable)",
            )

        # Generate approval ID first so we can include it in the waiting message
        import uuid

        approval_id = str(uuid.uuid4())

        # Send "waiting for approval" message to client
        if send_intermediate:
            waiting_response = DaemonResponse.waiting_for_approval(
                command=command,
                rule_name=result.plugin_name,
                reason=result.reason,
                approval_id=approval_id,
            )
            await send_intermediate(waiting_response)

        # Request approval and wait for resolution
        logger.info(f"Requesting approval for: {command}")
        approval_result, denial_reason = await self._approval_manager.request_approval(
            command=command,
            plugin_name=result.plugin_name,
            reason=result.reason,
            approval_id=approval_id,
        )

        # Handle approval results - check for "remember" variants
        if approval_result in (ApprovalResult.APPROVED, ApprovalResult.APPROVED_REMEMBER):
            # Store in session memory if "remember" was selected
            if (
                approval_result == ApprovalResult.APPROVED_REMEMBER
                and self._session_memory is not None
            ):
                self._session_memory.remember_approval(result.plugin_name, command)

            logger.info(f"Command approved: {command}")
            return EvaluationResult(
                decision=Decision.ALLOW,
                plugin_name=result.plugin_name,
                reason=f"Approved: {result.reason}",
            )

        # Denied, denied_remember, or timed out
        if approval_result == ApprovalResult.TIMEOUT:
            denial_reason = "Approval timed out"
            logger.warning(f"Command timed out waiting for approval: {command}")
        else:
            # Store denial in session memory if "remember" was selected
            if (
                approval_result == ApprovalResult.DENIED_REMEMBER
                and self._session_memory is not None
            ):
                self._session_memory.remember_denial(result.plugin_name, command)
            logger.info(f"Command denied: {command}")

        return EvaluationResult(
            decision=Decision.DENY,
            plugin_name=result.plugin_name,
            reason=denial_reason or result.reason,
        )

    async def _handle_execute(
        self,
        request: DaemonRequest,
        send_intermediate: Callable[[DaemonResponse], Awaitable[None]] | None = None,
    ) -> DaemonResponse:
        """Handle command execution request (evaluate + execute).

        Evaluates the command first, and if allowed, executes it and returns
        the output. This eliminates the Python wrapper startup overhead by
        keeping execution within the already-warm daemon process.

        Args:
            request: Request containing command to execute
            send_intermediate: Optional callback to send intermediate responses

        Returns:
            Response with evaluation results and execution output
        """
        from safeshell.daemon.executor import execute_command

        # First, evaluate the command (reuses existing logic)
        eval_response = await self._handle_evaluate(request, send_intermediate)

        # If not allowed to execute, return the evaluation response as-is
        if not eval_response.should_execute:
            return eval_response

        # Command is allowed - execute it
        # Type narrowing: command is validated as not None before _handle_evaluate
        assert request.command is not None
        logger.debug(f"Executing command: {request.command}")

        exec_result = execute_command(
            command=request.command,
            working_dir=request.working_dir or ".",
            env=request.env,
        )

        # Build response with execution results
        response = DaemonResponse(
            success=True,
            results=eval_response.results,
            final_decision=eval_response.final_decision,
            should_execute=True,
            executed=True,
            exit_code=exec_result.exit_code,
            stdout=exec_result.stdout,
            stderr=exec_result.stderr,
            execution_time_ms=exec_result.execution_time_ms,
        )

        logger.debug(
            f"Executed '{request.command}' -> exit_code={exec_result.exit_code} "
            f"({exec_result.execution_time_ms:.1f}ms)"
        )

        return response
