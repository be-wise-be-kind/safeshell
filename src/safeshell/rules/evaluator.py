"""
File: src/safeshell/rules/evaluator.py
Purpose: Rule evaluation engine for config-based rules
Exports: RuleEvaluator
Depends: safeshell.rules.schema, safeshell.models, re
Overview: Evaluates commands against loaded rules using structured Python conditions
"""

from __future__ import annotations

import re

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
    ) -> None:
        """Initialize evaluator with rules.

        Args:
            rules: List of rules to evaluate against
        """
        self._rules = rules

        # Build command -> rules index for fast lookup
        self._command_index: dict[str, list[Rule]] = {}
        for rule in rules:
            for cmd in rule.commands:
                self._command_index.setdefault(cmd, []).append(rule)

        # Pre-compile directory regex patterns for performance
        self._compiled_directories: dict[str, re.Pattern[str] | None] = {}
        for rule in rules:
            if rule.directory:
                try:
                    self._compiled_directories[rule.name] = re.compile(rule.directory)
                except re.error as e:
                    logger.warning(f"Invalid regex in rule '{rule.name}': {e}")
                    self._compiled_directories[rule.name] = None
            else:
                self._compiled_directories[rule.name] = None

        logger.debug(f"RuleEvaluator initialized with {len(rules)} rules")
        logger.debug(f"Command index: {list(self._command_index.keys())}")

    async def evaluate(self, context: CommandContext) -> EvaluationResult:
        """Evaluate a command against all applicable rules.

        Evaluation flow:
        1. Extract executable from command
        2. Fast-path: if executable not in index, return ALLOW
        3. For each matching rule, check directory and conditions
        4. Aggregate matched rules (most restrictive wins)

        Args:
            context: Command context with parsed command and environment

        Returns:
            EvaluationResult with decision and reasoning
        """
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
            if self._rule_matches(rule, context):
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

    def _rule_matches(self, rule: Rule, context: CommandContext) -> bool:
        """Check if a rule matches the given context.

        A rule matches if:
        1. Execution context matches (ai_only, human_only, or all)
        2. Directory pattern matches (if specified)
        3. All structured conditions evaluate to True (if specified)

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

        # Check directory pattern using pre-compiled regex
        compiled_dir = self._compiled_directories.get(rule.name)
        if rule.directory and compiled_dir:
            if not compiled_dir.match(context.working_dir):
                logger.debug(f"Rule '{rule.name}': directory pattern didn't match")
                return False
        elif rule.directory and not compiled_dir:
            # Regex was invalid, skip this rule
            logger.debug(f"Rule '{rule.name}': invalid directory regex, skipping")
            return False

        # Check structured conditions (pure Python evaluation)
        for condition in rule.conditions:
            if not condition.evaluate(context):
                logger.debug(f"Rule '{rule.name}': condition failed: {type(condition).__name__}")
                return False

        return True

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
