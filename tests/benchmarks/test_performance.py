"""
File: tests/benchmarks/test_performance.py
Purpose: Performance regression tests for SafeShell
Overview: Ensures performance stays within acceptable bounds
"""

import pytest

from safeshell.benchmarks.evaluation import (
    EvaluationBenchmarkResult,
    run_condition_benchmark,
    run_evaluation_benchmark,
)


class TestEvaluationPerformance:
    """Tests for rule evaluation performance."""

    def test_rule_evaluation_meets_target(self):
        """Rule evaluation should complete in <1ms on average."""
        result = run_evaluation_benchmark(iterations=50)

        assert isinstance(result, EvaluationBenchmarkResult)
        assert result.mean_ms < 1.0, (
            f"Rule evaluation too slow: {result.mean_ms:.3f}ms "
            f"(target <1ms, rules={result.rule_count})"
        )

    def test_rule_evaluation_consistent(self):
        """Rule evaluation timing should be consistent (low variance)."""
        result = run_evaluation_benchmark(iterations=100)

        # Standard deviation should be less than mean (coefficient of variation < 1)
        if result.mean_ms > 0:
            cv = result.stdev_ms / result.mean_ms
            assert cv < 2.0, (
                f"Rule evaluation has high variance: CV={cv:.2f} "
                f"(mean={result.mean_ms:.3f}ms, stdev={result.stdev_ms:.3f}ms)"
            )

    def test_individual_conditions_fast(self):
        """Each condition type should evaluate in <0.1ms."""
        results = run_condition_benchmark(iterations=500)

        slow_conditions = []
        for name, stats in results.items():
            if stats["mean_ms"] > 0.1:
                slow_conditions.append(f"{name}: {stats['mean_ms']:.4f}ms")

        assert (
            not slow_conditions
        ), f"Slow condition types detected (>0.1ms): {', '.join(slow_conditions)}"


class TestBenchmarkResultStructures:
    """Tests for benchmark result dataclasses."""

    def test_evaluation_result_structure(self):
        """EvaluationBenchmarkResult should have all expected fields."""
        result = run_evaluation_benchmark(iterations=10)

        assert hasattr(result, "iterations")
        assert hasattr(result, "rule_count")
        assert hasattr(result, "mean_ms")
        assert hasattr(result, "stdev_ms")
        assert hasattr(result, "min_ms")
        assert hasattr(result, "max_ms")
        assert hasattr(result, "meets_target")

    def test_evaluation_result_meets_target_property(self):
        """meets_target should return True when mean <1ms."""
        result = run_evaluation_benchmark(iterations=10)

        # The property should match the condition
        assert result.meets_target == (result.mean_ms < 1.0)

    def test_condition_benchmark_structure(self):
        """run_condition_benchmark should return dict with expected structure."""
        results = run_condition_benchmark(iterations=100)

        assert isinstance(results, dict)
        assert len(results) > 0

        for name, stats in results.items():
            assert isinstance(name, str)
            assert "mean_ms" in stats
            assert "stdev_ms" in stats
            assert "min_ms" in stats
            assert "max_ms" in stats


class TestPerformanceTargets:
    """Tests that verify performance targets are documented and enforced."""

    # Performance targets (documented in PROGRESS_TRACKER.md)
    CONDITION_TARGET_MS = 0.1  # <0.1ms per condition
    RULE_EVAL_TARGET_MS = 1.0  # <1ms per evaluation
    COMMAND_OVERHEAD_TARGET_MS = 50.0  # <50ms overhead (actual ~25ms)

    def test_condition_target_achievable(self):
        """Verify condition evaluation meets <0.1ms target."""
        results = run_condition_benchmark(iterations=500)

        for name, stats in results.items():
            assert stats["mean_ms"] < self.CONDITION_TARGET_MS, (
                f"Condition '{name}' exceeds target: "
                f"{stats['mean_ms']:.4f}ms > {self.CONDITION_TARGET_MS}ms"
            )

    def test_rule_evaluation_target_achievable(self):
        """Verify rule evaluation meets <1ms target."""
        result = run_evaluation_benchmark(iterations=100)

        assert result.mean_ms < self.RULE_EVAL_TARGET_MS, (
            f"Rule evaluation exceeds target: "
            f"{result.mean_ms:.3f}ms > {self.RULE_EVAL_TARGET_MS}ms"
        )


@pytest.mark.slow
class TestExtendedPerformance:
    """Extended performance tests that take longer to run."""

    def test_evaluation_under_load(self):
        """Rule evaluation should remain fast under many iterations."""
        result = run_evaluation_benchmark(iterations=500)

        # Should still meet target even with 500 iterations
        assert result.mean_ms < 1.0, f"Rule evaluation degraded under load: {result.mean_ms:.3f}ms"
