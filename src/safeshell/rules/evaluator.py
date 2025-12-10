"""
File: src/safeshell/rules/evaluator.py
Purpose: Rule evaluation engine for config-based rules
Exports: RuleEvaluator
Depends: safeshell.rules.schema, safeshell.models, asyncio, shlex, re, os
Overview: Evaluates commands against loaded rules using bash conditions with configurable timeout
"""

import asyncio
import os
import re
import shlex

from loguru import logger

from safeshell.models import CommandContext, Decision, EvaluationResult, ExecutionContext
from safeshell.rules.schema import Rule, RuleAction, RuleContext


class RuleEvaluator:
    """Evaluates commands against loaded rules.

    The evaluator uses a command index for fast-path evaluation -
    commands not in any rule's commands list are allowed immediately
    without condition evaluation.
    """

    def __init__(
        self,
        rules: list[Rule],
        condition_timeout_ms: int = 100,
    ) -> None:
        """Initialize evaluator with rules.

        Args:
            rules: List of rules to evaluate against
            condition_timeout_ms: Timeout for bash conditions in milliseconds (default 100ms)
        """
        self._rules = rules
        self._condition_timeout_ms = condition_timeout_ms
        self._current_rule_name: str = ""

        # Build command -> rules index for fast lookup
        self._command_index: dict[str, list[Rule]] = {}
        for rule in rules:
            for cmd in rule.commands:
                self._command_index.setdefault(cmd, []).append(rule)

        # Per-evaluation condition cache (cleared at start of each evaluate())
        # Key: (condition, raw_command, working_dir) -> result
        self._condition_cache: dict[tuple[str, str, str], bool] = {}

        logger.debug(f"RuleEvaluator initialized with {len(rules)} rules")
        logger.debug(f"Command index: {list(self._command_index.keys())}")

    async def evaluate(self, context: CommandContext) -> EvaluationResult:
        """Evaluate a command against all applicable rules.

        Evaluation flow:
        1. Clear condition cache (fresh start per evaluation)
        2. Extract executable from command
        3. Fast-path: if executable not in index, return ALLOW
        4. For each matching rule, check directory and conditions
        5. Aggregate matched rules (most restrictive wins)

        Args:
            context: Command context with parsed command and environment

        Returns:
            EvaluationResult with decision and reasoning
        """
        # Clear condition cache at start of each evaluation
        self._condition_cache.clear()

        executable = context.executable

        # Fast path: no rules for this executable
        if not executable or executable not in self._command_index:
            logger.debug(f"Fast path ALLOW: '{executable}' not in rule index")
            return EvaluationResult(
                decision=Decision.ALLOW,
                plugin_name="rules",
                reason="No rules apply to this command",
            )

        # Check each matching rule
        matching_rules: list[Rule] = []
        for rule in self._command_index[executable]:
            self._current_rule_name = rule.name
            if await self._rule_matches(rule, context):
                matching_rules.append(rule)
                logger.debug(f"Rule '{rule.name}' matched command")

        if not matching_rules:
            logger.debug(f"No rules matched for '{context.raw_command}'")
            return EvaluationResult(
                decision=Decision.ALLOW,
                plugin_name="rules",
                reason="No rules matched this command",
            )

        # Return most restrictive result
        return self._aggregate_results(matching_rules)

    async def _rule_matches(self, rule: Rule, context: CommandContext) -> bool:
        """Check if a rule matches the given context.

        A rule matches if:
        1. Execution context matches (ai_only, human_only, or all)
        2. Directory pattern matches (if specified)
        3. All bash conditions exit 0 (if specified)

        Args:
            rule: The rule to check
            context: Command context

        Returns:
            True if the rule matches, False otherwise
        """
        # Check execution context (ai_only, human_only, all)
        exec_ctx = context.execution_context
        if rule.context == RuleContext.AI_ONLY and exec_ctx != ExecutionContext.AI:
            logger.debug(f"Rule '{rule.name}': skipped (ai_only, context={exec_ctx})")
            return False
        if rule.context == RuleContext.HUMAN_ONLY and exec_ctx != ExecutionContext.HUMAN:
            logger.debug(f"Rule '{rule.name}': skipped (human_only, context={exec_ctx})")
            return False

        # Check directory pattern
        if rule.directory and not re.match(rule.directory, context.working_dir):
            logger.debug(f"Rule '{rule.name}': directory pattern didn't match")
            return False

        # Check bash conditions
        for condition in rule.conditions:
            if not await self._check_condition(condition, context):
                logger.debug(f"Rule '{rule.name}': condition failed: {condition[:50]}...")
                return False

        return True

    async def _check_condition(self, condition: str, context: CommandContext) -> bool:
        """Run a bash condition and return whether it passed.

        Uses per-evaluation caching - identical conditions for the same
        command/working_dir are only executed once per evaluate() call.

        Environment variables available:
        - $CMD: Full command string
        - $ARGS: Arguments after executable
        - $PWD: Working directory
        - $SAFESHELL_RULE: Current rule name

        Args:
            condition: Bash condition to evaluate
            context: Command context for variable substitution

        Returns:
            True if condition exited with code 0, False otherwise
        """
        # Check condition cache first
        cache_key = (condition, context.raw_command, context.working_dir)
        if cache_key in self._condition_cache:
            cached_result = self._condition_cache[cache_key]
            logger.debug(f"Condition cache hit: {condition[:40]}... -> {cached_result}")
            return cached_result

        # Execute condition
        result = await self._execute_condition(condition, context)

        # Cache result
        self._condition_cache[cache_key] = result
        return result

    async def _execute_condition(self, condition: str, context: CommandContext) -> bool:
        """Execute a bash condition subprocess.

        Args:
            condition: Bash condition to evaluate
            context: Command context for variable substitution

        Returns:
            True if condition exited with code 0, False otherwise
        """
        args_str = " ".join(context.args) if context.args else ""

        env = {
            **os.environ,
            "CMD": context.raw_command,
            "ARGS": args_str,
            "PWD": context.working_dir,
            "SAFESHELL_RULE": self._current_rule_name,
        }

        try:
            proc = await asyncio.create_subprocess_shell(
                f"bash -c {shlex.quote(condition)}",
                env=env,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
                cwd=context.working_dir,
            )

            await asyncio.wait_for(
                proc.wait(),
                timeout=self._condition_timeout_ms / 1000.0,
            )

            return proc.returncode == 0

        except TimeoutError:
            logger.warning(
                f"Condition timed out after {self._condition_timeout_ms}ms: {condition[:50]}..."
            )
            return False
        except OSError as e:
            logger.warning(f"Condition execution failed: {e}")
            return False

    def _aggregate_results(self, rules: list[Rule]) -> EvaluationResult:
        """Aggregate matched rules into a single result.

        Priority: DENY > REQUIRE_APPROVAL > REDIRECT > ALLOW

        Args:
            rules: List of matched rules

        Returns:
            EvaluationResult with the most restrictive decision
        """
        # Priority order (most restrictive first)
        priority = {
            RuleAction.DENY: 0,
            RuleAction.REQUIRE_APPROVAL: 1,
            RuleAction.REDIRECT: 2,
            RuleAction.ALLOW: 3,
        }

        # Find most restrictive rule
        most_restrictive = min(rules, key=lambda r: priority[r.action])

        # Map RuleAction to Decision
        action_to_decision = {
            RuleAction.DENY: Decision.DENY,
            RuleAction.REQUIRE_APPROVAL: Decision.REQUIRE_APPROVAL,
            RuleAction.REDIRECT: Decision.ALLOW,  # Redirect still allows, just modified
            RuleAction.ALLOW: Decision.ALLOW,
        }

        return EvaluationResult(
            decision=action_to_decision[most_restrictive.action],
            plugin_name=most_restrictive.name,
            reason=most_restrictive.message,
        )
