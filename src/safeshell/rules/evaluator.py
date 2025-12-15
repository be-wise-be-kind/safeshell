"""
File: src/safeshell/rules/evaluator.py
Purpose: Rule evaluation engine for config-based rules
Exports: RuleEvaluator, ConditionCache
Depends: safeshell.rules.schema, safeshell.models, asyncio, shlex, re, os, time
Overview: Evaluates commands against loaded rules using bash conditions with configurable timeout
"""

from __future__ import annotations

import asyncio
import os
import re
import shlex
import time

from loguru import logger

from safeshell.models import CommandContext, Decision, EvaluationResult, ExecutionContext
from safeshell.rules.schema import Rule, RuleAction, RuleContext


class ConditionCache:
    """Cross-request condition cache with TTL-based expiration.

    Caches bash condition results to avoid re-executing the same conditions
    for repeated commands. Uses a TTL to ensure cached results don't become stale.
    """

    def __init__(self, ttl_seconds: float = 5.0, max_size: int = 1000) -> None:
        """Initialize condition cache.

        Args:
            ttl_seconds: Time-to-live for cached entries in seconds
            max_size: Maximum number of entries before eviction
        """
        self._cache: dict[tuple[str, str, str], tuple[bool, float]] = {}
        self._ttl = ttl_seconds
        self._max_size = max_size

    def get(self, key: tuple[str, str, str]) -> bool | None:
        """Get cached condition result if not expired.

        Args:
            key: Tuple of (condition, raw_command, working_dir)

        Returns:
            Cached result or None if not found/expired
        """
        if key in self._cache:
            result, timestamp = self._cache[key]
            if time.monotonic() - timestamp < self._ttl:
                return result
            # Expired - remove it
            del self._cache[key]
        return None

    def set(self, key: tuple[str, str, str], result: bool) -> None:
        """Cache a condition result.

        Args:
            key: Tuple of (condition, raw_command, working_dir)
            result: The condition evaluation result
        """
        # Evict oldest entries if at capacity
        if len(self._cache) >= self._max_size:
            self._evict_oldest()
        self._cache[key] = (result, time.monotonic())

    def _evict_oldest(self) -> None:
        """Evict oldest 10% of entries."""
        if not self._cache:
            return
        # Sort by timestamp, remove oldest 10%
        sorted_keys = sorted(self._cache.keys(), key=lambda k: self._cache[k][1])
        to_remove = max(1, len(sorted_keys) // 10)
        for key in sorted_keys[:to_remove]:
            del self._cache[key]

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()

    def __len__(self) -> int:
        """Return number of cached entries."""
        return len(self._cache)


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
        condition_cache: ConditionCache | None = None,
    ) -> None:
        """Initialize evaluator with rules.

        Args:
            rules: List of rules to evaluate against
            condition_timeout_ms: Timeout for bash conditions in milliseconds (default 100ms)
            condition_cache: Optional shared condition cache for cross-request caching.
                If not provided, creates a local cache (cleared per evaluate()).
        """
        self._rules = rules
        self._condition_timeout_ms = condition_timeout_ms
        self._current_rule_name: str = ""

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

        # Condition cache - use shared cache if provided, else create local
        self._condition_cache: ConditionCache | None = condition_cache
        self._local_cache: dict[tuple[str, str, str], bool] = {}
        self._use_shared_cache = condition_cache is not None

        logger.debug(f"RuleEvaluator initialized with {len(rules)} rules")
        logger.debug(f"Command index: {list(self._command_index.keys())}")

    async def evaluate(self, context: CommandContext) -> EvaluationResult:
        """Evaluate a command against all applicable rules.

        Evaluation flow:
        1. Clear local condition cache (if not using shared cache)
        2. Extract executable from command
        3. Fast-path: if executable not in index, return ALLOW
        4. For each matching rule, check directory and conditions
        5. Aggregate matched rules (most restrictive wins)

        Args:
            context: Command context with parsed command and environment

        Returns:
            EvaluationResult with decision and reasoning
        """
        # Clear local cache if not using shared cache
        if not self._use_shared_cache:
            self._local_cache.clear()

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

        # Check bash conditions
        for condition in rule.conditions:
            if not await self._check_condition(condition, context):
                logger.debug(f"Rule '{rule.name}': condition failed: {condition[:50]}...")
                return False

        return True

    async def _check_condition(self, condition: str, context: CommandContext) -> bool:
        """Run a bash condition and return whether it passed.

        Uses caching - identical conditions for the same command/working_dir
        are only executed once. If a shared ConditionCache was provided,
        results persist across requests with TTL-based expiration.

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
        cache_key = (condition, context.raw_command, context.working_dir)

        # Check cache first (shared or local)
        if self._use_shared_cache and self._condition_cache is not None:
            cached_result = self._condition_cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Condition cache hit (shared): {condition[:40]}... -> {cached_result}")
                return cached_result
        else:
            if cache_key in self._local_cache:
                cached_result = self._local_cache[cache_key]
                logger.debug(f"Condition cache hit (local): {condition[:40]}... -> {cached_result}")
                return cached_result

        # Execute condition
        result = await self._execute_condition(condition, context)

        # Cache result
        if self._use_shared_cache and self._condition_cache is not None:
            self._condition_cache.set(cache_key, result)
        else:
            self._local_cache[cache_key] = result

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
