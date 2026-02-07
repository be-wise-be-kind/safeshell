"""
File: src/safeshell/benchmarks/__init__.py
Purpose: Benchmark utilities for measuring SafeShell performance
Exports: run_overhead_benchmark, run_evaluation_benchmark, BenchmarkResult
Depends: safeshell.benchmarks.evaluation, safeshell.benchmarks.overhead
Overview: Provides tools to measure command overhead and rule evaluation performance
"""

from safeshell.benchmarks.evaluation import run_evaluation_benchmark
from safeshell.benchmarks.overhead import BenchmarkResult, run_overhead_benchmark

__all__ = [
    "BenchmarkResult",
    "run_overhead_benchmark",
    "run_evaluation_benchmark",
]
