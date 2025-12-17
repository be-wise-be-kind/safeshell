"""
File: src/safeshell/benchmarks/overhead.py
Purpose: Measure command execution overhead introduced by SafeShell
Exports: BenchmarkResult, run_overhead_benchmark
Depends: subprocess, time, statistics, pathlib
Overview: Benchmarks the overhead of running commands through SafeShell vs native execution
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, stdev


@dataclass
class BenchmarkResult:
    """Results from a benchmark run."""

    iterations: int
    native_mean_ms: float
    native_stdev_ms: float
    safeshell_mean_ms: float
    safeshell_stdev_ms: float
    overhead_ms: float
    overhead_percent: float

    @property
    def meets_target(self) -> bool:
        """Check if overhead meets the target of <50ms."""
        return self.overhead_ms < 50.0


def _time_command(command: str, env: dict[str, str] | None = None) -> float:
    """Time a single command execution.

    Args:
        command: Shell command to execute
        env: Environment variables

    Returns:
        Execution time in milliseconds
    """
    import os

    exec_env = os.environ.copy()
    if env:
        exec_env.update(env)

    start = time.perf_counter()
    subprocess.run(  # nosec B602 # noqa: S602 - shell=True intentional for benchmarking
        command,
        shell=True,
        env=exec_env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    end = time.perf_counter()

    return (end - start) * 1000


def run_overhead_benchmark(
    command: str = "true",  # Minimal command for pure overhead measurement
    iterations: int = 10,
    warmup: int = 2,
    safeshell_shim_dir: Path | None = None,
) -> BenchmarkResult:
    """Run overhead benchmark comparing native vs SafeShell execution.

    Measures the difference in execution time between running a command
    directly vs through SafeShell's shim layer.

    Args:
        command: Command to benchmark (default: "true" for minimal work)
        iterations: Number of timed iterations
        warmup: Number of warmup iterations (not counted)
        safeshell_shim_dir: Path to SafeShell shims (default: ~/.safeshell/shims)

    Returns:
        BenchmarkResult with timing statistics
    """
    import os

    if safeshell_shim_dir is None:
        safeshell_shim_dir = Path.home() / ".safeshell" / "shims"

    # Warmup runs (ensure daemon is warm, filesystem caches populated)
    for _ in range(warmup):
        _time_command(command)

    # Native execution (without SafeShell) - find 'true' binary location
    native_path = subprocess.run(  # noqa: S603, S607
        ["/usr/bin/which", "true"], capture_output=True, text=True
    ).stdout.strip()

    native_times: list[float] = []
    for _ in range(iterations):
        native_times.append(_time_command(native_path))

    # SafeShell execution (through shim)
    # Add SafeShell shims to PATH if they exist
    safeshell_env = os.environ.copy()
    if safeshell_shim_dir.exists():
        safeshell_env["PATH"] = f"{safeshell_shim_dir}:{safeshell_env.get('PATH', '')}"

    # Use safeshell-check -e for daemon-based execution
    safeshell_check = Path(__file__).parent.parent / "shims" / "safeshell-check"
    if not safeshell_check.exists():
        # Fall back to user's home directory
        safeshell_check = Path.home() / ".safeshell" / "shims" / "safeshell-check"

    safeshell_times: list[float] = []
    for _ in range(iterations):
        # Measure safeshell-check -e execution (trusted internal script)
        start = time.perf_counter()
        subprocess.run(  # noqa: S603
            [str(safeshell_check), "-e", command],
            env=safeshell_env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        end = time.perf_counter()
        safeshell_times.append((end - start) * 1000)

    native_mean = mean(native_times)
    safeshell_mean = mean(safeshell_times)

    native_std = stdev(native_times) if len(native_times) > 1 else 0.0
    safeshell_std = stdev(safeshell_times) if len(safeshell_times) > 1 else 0.0

    overhead = safeshell_mean - native_mean
    overhead_pct = (overhead / native_mean * 100) if native_mean > 0 else 0.0

    return BenchmarkResult(
        iterations=iterations,
        native_mean_ms=native_mean,
        native_stdev_ms=native_std,
        safeshell_mean_ms=safeshell_mean,
        safeshell_stdev_ms=safeshell_std,
        overhead_ms=overhead,
        overhead_percent=overhead_pct,
    )


def run_socket_latency_benchmark(
    iterations: int = 20,
) -> dict[str, float | str | int]:
    """Benchmark raw socket communication latency with daemon.

    Measures ping-pong time to daemon without command evaluation.

    Args:
        iterations: Number of iterations

    Returns:
        Dict with mean_ms, stdev_ms, min_ms, max_ms
    """
    import json
    import socket

    socket_path = Path.home() / ".safeshell" / "daemon.sock"

    if not socket_path.exists():
        return {"error": "Daemon socket not found"}

    times: list[float] = []
    ping_request = json.dumps({"type": "ping"}).encode() + b"\n"

    for _ in range(iterations):
        try:
            start = time.perf_counter()

            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(str(socket_path))
            sock.sendall(ping_request)
            sock.recv(4096)
            sock.close()

            end = time.perf_counter()
            times.append((end - start) * 1000)
        except OSError:
            # Connection failed - skip this iteration
            continue

    if not times:
        return {"error": "No successful connections"}

    return {
        "mean_ms": mean(times),
        "stdev_ms": stdev(times) if len(times) > 1 else 0.0,
        "min_ms": min(times),
        "max_ms": max(times),
        "iterations": len(times),
    }
