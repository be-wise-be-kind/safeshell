"""
File: src/safeshell/benchmarks/evaluation.py
Purpose: Measure rule evaluation performance
Exports: run_evaluation_benchmark, EvaluationBenchmarkResult
Depends: time, statistics, asyncio, safeshell.rules
Overview: Benchmarks pure Python rule evaluation without IPC overhead
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, stdev


@dataclass
class EvaluationBenchmarkResult:
    """Results from rule evaluation benchmark."""

    iterations: int
    rule_count: int
    mean_ms: float
    stdev_ms: float
    min_ms: float
    max_ms: float
    conditions_evaluated: int

    @property
    def meets_target(self) -> bool:
        """Check if evaluation meets the target of <1ms."""
        return self.mean_ms < 1.0


def run_evaluation_benchmark(
    test_commands: list[str] | None = None,
    iterations: int = 100,
    working_dir: str | None = None,
) -> EvaluationBenchmarkResult:
    """Benchmark rule evaluation performance.

    Measures pure Python rule evaluation time without any IPC overhead.
    This tests the evaluator directly.

    Args:
        test_commands: Commands to evaluate (default: common commands)
        iterations: Number of iterations per command
        working_dir: Working directory for evaluation context

    Returns:
        EvaluationBenchmarkResult with timing statistics
    """
    from safeshell.models import CommandContext, ExecutionContext
    from safeshell.rules import RuleCache, RuleEvaluator

    if test_commands is None:
        test_commands = [
            "ls -la",
            "git status",
            "git commit -m 'test'",
            "rm -rf /",
            "echo hello",
            "npm install",
            "docker run --privileged ubuntu",
        ]

    if working_dir is None:
        working_dir = str(Path.cwd())

    # Load rules
    rule_cache = RuleCache()
    rules, _ = rule_cache.get_rules(working_dir)
    evaluator = RuleEvaluator(rules=rules)

    times: list[float] = []
    total_conditions = 0

    async def evaluate_once(cmd: str) -> float:
        """Evaluate a single command and return time in ms."""
        context = CommandContext.from_command(
            command=cmd,
            working_dir=working_dir,
            env={},
            execution_context=ExecutionContext.HUMAN,
        )

        start = time.perf_counter()
        await evaluator.evaluate(context)
        end = time.perf_counter()

        return (end - start) * 1000

    # Run benchmark
    async def run_all() -> None:
        nonlocal total_conditions

        for _ in range(iterations):
            for cmd in test_commands:
                elapsed = await evaluate_once(cmd)
                times.append(elapsed)

        # Count conditions across all rules
        for rule in rules:
            total_conditions += len(rule.conditions)

    asyncio.run(run_all())

    return EvaluationBenchmarkResult(
        iterations=iterations * len(test_commands),
        rule_count=len(rules),
        mean_ms=mean(times),
        stdev_ms=stdev(times) if len(times) > 1 else 0.0,
        min_ms=min(times),
        max_ms=max(times),
        conditions_evaluated=total_conditions,
    )


def run_condition_benchmark(
    iterations: int = 1000,
) -> dict[str, dict[str, float]]:
    """Benchmark individual condition type performance.

    Tests each condition type in isolation to identify any slow conditions.

    Args:
        iterations: Number of iterations per condition type

    Returns:
        Dict mapping condition type to timing stats
    """

    from safeshell.models import CommandContext, ExecutionContext
    from safeshell.rules.condition_types import (
        CommandContains,
        CommandMatches,
        CommandStartswith,
        EnvEquals,
        FileExists,
        GitBranchIn,
        InGitRepo,
        PathMatches,
    )

    context = CommandContext.from_command(
        command="git push --force origin main",
        working_dir=str(Path.cwd()),
        env={"TEST_VAR": "test_value"},
        execution_context=ExecutionContext.HUMAN,
    )

    # Define test conditions
    conditions = {
        "CommandMatches": CommandMatches(command_matches=r"^git\s+push"),
        "CommandContains": CommandContains(command_contains="--force"),
        "CommandStartswith": CommandStartswith(command_startswith="git"),
        "GitBranchIn": GitBranchIn(git_branch_in=["main", "master"]),
        "InGitRepo": InGitRepo(in_git_repo=True),
        "PathMatches": PathMatches(path_matches=r"/home/.*/Projects"),
        "FileExists": FileExists(file_exists="pyproject.toml"),
        "EnvEquals": EnvEquals(env_equals={"variable": "TEST_VAR", "value": "test_value"}),
    }

    results: dict[str, dict[str, float]] = {}

    for name, condition in conditions.items():
        times: list[float] = []

        for _ in range(iterations):
            start = time.perf_counter()
            condition.evaluate(context)  # type: ignore[attr-defined]
            end = time.perf_counter()
            times.append((end - start) * 1000)

        results[name] = {
            "mean_ms": mean(times),
            "stdev_ms": stdev(times) if len(times) > 1 else 0.0,
            "min_ms": min(times),
            "max_ms": max(times),
        }

    return results
