"""
File: src/safeshell/benchmarks/cli.py
Purpose: CLI commands for performance benchmarking
Exports: app (Typer app)
Depends: typer, rich, safeshell.benchmarks
Overview: Provides perf-stats command for measuring SafeShell performance
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import typer
from rich.console import Console
from rich.table import Table

if TYPE_CHECKING:
    from safeshell.benchmarks.evaluation import EvaluationBenchmarkResult
    from safeshell.benchmarks.overhead import BenchmarkResult

# Benchmark iteration counts
_QUICK_EVAL_ITERATIONS = 50
_FULL_EVAL_ITERATIONS = 100
_QUICK_CONDITION_ITERATIONS = 500
_FULL_CONDITION_ITERATIONS = 1000

app = typer.Typer(
    name="perf",
    help="Performance benchmarking tools.",
    no_args_is_help=True,
)
console = Console()


@app.command(name="stats")
def stats(
    quick: bool = typer.Option(
        False,
        "--quick",
        "-q",
        help="Run quick benchmark (fewer iterations)",
    ),
    detailed: bool = typer.Option(
        False,
        "--detailed",
        "-d",
        help="Show detailed per-condition benchmarks",
    ),
) -> None:
    """Show performance statistics and run benchmarks.

    Measures SafeShell's overhead and rule evaluation performance.
    Use this to verify performance after configuration changes.

    Metrics measured:
    - Command overhead: Time added by SafeShell to command execution
    - Socket latency: IPC round-trip time to daemon
    - Rule evaluation: Time to evaluate rules (pure Python)
    - Condition types: Per-condition-type timing (with --detailed)

    Target performance:
    - Command overhead: <50ms (actual ~25ms with daemon execution)
    - Rule evaluation: <1ms
    - Socket latency: <5ms
    """
    import os

    from loguru import logger

    from safeshell.benchmarks import run_evaluation_benchmark, run_overhead_benchmark
    from safeshell.benchmarks.evaluation import run_condition_benchmark
    from safeshell.benchmarks.overhead import run_socket_latency_benchmark
    from safeshell.daemon.lifecycle import DaemonLifecycle

    # Suppress debug logging during benchmarks
    logger.remove()
    logger.add(os.devnull, level="ERROR")

    iterations = 5 if quick else 10

    # Check if daemon is running
    if not DaemonLifecycle.is_running():
        console.print("[yellow]Daemon is not running.[/yellow]")
        console.print("Start it with: safeshell up")
        console.print()
        console.print("[dim]Running evaluation benchmark only (no daemon required)...[/dim]")

        # Run evaluation benchmark only
        console.print()
        console.print("[bold]Rule Evaluation Benchmark[/bold]")
        eval_result = run_evaluation_benchmark(
            iterations=_QUICK_EVAL_ITERATIONS if quick else _FULL_EVAL_ITERATIONS
        )

        table = Table(show_header=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Rules loaded", str(eval_result.rule_count))
        table.add_row("Evaluations", str(eval_result.iterations))
        table.add_row("Mean", f"{eval_result.mean_ms:.3f}ms")
        table.add_row("Std Dev", f"{eval_result.stdev_ms:.3f}ms")
        table.add_row("Min", f"{eval_result.min_ms:.3f}ms")
        table.add_row("Max", f"{eval_result.max_ms:.3f}ms")
        status = "[green]PASS[/green]" if eval_result.meets_target else "[red]FAIL[/red]"
        table.add_row("Target (<1ms)", status)
        console.print(table)

        raise typer.Exit(0)

    console.print("[bold]SafeShell Performance Benchmarks[/bold]")
    console.print()

    # Socket latency benchmark
    console.print("[dim]Measuring socket latency...[/dim]")
    socket_result = run_socket_latency_benchmark(iterations=iterations * 2)

    if "error" not in socket_result:
        _print_socket_results(socket_result)
    else:
        console.print(f"[yellow]Socket benchmark skipped: {socket_result['error']}[/yellow]")

    # Command overhead benchmark
    console.print()
    console.print("[dim]Measuring command overhead...[/dim]")
    overhead_result = run_overhead_benchmark(iterations=iterations)
    _print_overhead_results(overhead_result)

    # Rule evaluation benchmark
    console.print()
    console.print("[dim]Measuring rule evaluation...[/dim]")
    eval_result = run_evaluation_benchmark(
        iterations=_QUICK_EVAL_ITERATIONS if quick else _FULL_EVAL_ITERATIONS
    )
    _print_evaluation_results(eval_result)

    # Detailed condition benchmarks
    if detailed:
        console.print()
        console.print("[dim]Measuring individual condition types...[/dim]")
        condition_results = run_condition_benchmark(
            iterations=_QUICK_CONDITION_ITERATIONS if quick else _FULL_CONDITION_ITERATIONS
        )
        _print_condition_results(condition_results)

    # Summary
    console.print()
    all_pass = (
        overhead_result.meets_target
        and eval_result.meets_target
        and ("error" in socket_result or float(socket_result["mean_ms"]) < 5.0)
    )

    if all_pass:
        console.print("[bold green]All performance targets met![/bold green]")
    else:
        console.print("[bold yellow]Some targets not met - see details above[/bold yellow]")


def _print_socket_results(socket_result: dict[str, float | str | int]) -> None:
    """Print socket latency results."""
    console.print()
    console.print("[bold]Socket Latency (ping)[/bold]")
    table = Table(show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Iterations", str(int(socket_result["iterations"])))
    table.add_row("Mean", f"{socket_result['mean_ms']:.2f}ms")
    table.add_row("Std Dev", f"{socket_result['stdev_ms']:.2f}ms")
    table.add_row("Min", f"{socket_result['min_ms']:.2f}ms")
    table.add_row("Max", f"{socket_result['max_ms']:.2f}ms")
    target_met = float(socket_result["mean_ms"]) < 5.0
    status = "[green]PASS[/green]" if target_met else "[yellow]WARN[/yellow]"
    table.add_row("Target (<5ms)", status)
    console.print(table)


def _print_overhead_results(overhead_result: BenchmarkResult) -> None:
    """Print command overhead results."""
    console.print()
    console.print("[bold]Command Overhead[/bold]")
    table = Table(show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Iterations", str(overhead_result.iterations))
    table.add_row(
        "Native (true)",
        f"{overhead_result.native_mean_ms:.2f}ms ± {overhead_result.native_stdev_ms:.2f}ms",
    )
    table.add_row(
        "SafeShell",
        f"{overhead_result.safeshell_mean_ms:.2f}ms ± {overhead_result.safeshell_stdev_ms:.2f}ms",
    )
    table.add_row(
        "Overhead",
        f"{overhead_result.overhead_ms:.2f}ms ({overhead_result.overhead_percent:.1f}%)",
    )
    status = "[green]PASS[/green]" if overhead_result.meets_target else "[red]FAIL[/red]"
    table.add_row("Target (<50ms)", status)
    console.print(table)


def _print_evaluation_results(eval_result: EvaluationBenchmarkResult) -> None:
    """Print rule evaluation results."""
    console.print()
    console.print("[bold]Rule Evaluation[/bold]")
    table = Table(show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Rules loaded", str(eval_result.rule_count))
    table.add_row("Evaluations", str(eval_result.iterations))
    table.add_row("Mean", f"{eval_result.mean_ms:.3f}ms")
    table.add_row("Std Dev", f"{eval_result.stdev_ms:.3f}ms")
    table.add_row("Min", f"{eval_result.min_ms:.3f}ms")
    table.add_row("Max", f"{eval_result.max_ms:.3f}ms")
    status = "[green]PASS[/green]" if eval_result.meets_target else "[red]FAIL[/red]"
    table.add_row("Target (<1ms)", status)
    console.print(table)


def _print_condition_results(condition_results: dict[str, dict[str, float]]) -> None:
    """Print per-condition benchmark results."""
    console.print()
    console.print("[bold]Condition Type Performance[/bold]")
    table = Table()
    table.add_column("Condition", style="cyan")
    table.add_column("Mean", style="green", justify="right")
    table.add_column("Std Dev", justify="right")
    table.add_column("Min", justify="right")
    table.add_column("Max", justify="right")

    for cond_name, cond_stats in sorted(condition_results.items()):
        table.add_row(
            cond_name,
            f"{cond_stats['mean_ms']:.4f}ms",
            f"{cond_stats['stdev_ms']:.4f}ms",
            f"{cond_stats['min_ms']:.4f}ms",
            f"{cond_stats['max_ms']:.4f}ms",
        )
    console.print(table)
