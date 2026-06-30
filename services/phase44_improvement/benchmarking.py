"""
Phase 44 — Benchmark Engine.

Runs benchmarks, tracks historical results, detects regressions,
and generates performance reports.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from .models import BenchmarkResult
from .config import ImprovementConfig

logger = logging.getLogger(__name__)


class BenchmarkEngine:
    """Runs and analyzes performance benchmarks.

    Usage:
        be = BenchmarkEngine()
        result = be.run_benchmark("parse-speed", lambda: parse(data), iterations=20)
        regression = be.check_regression("parse-speed")
    """

    def __init__(self, config: Optional[ImprovementConfig] = None):
        self.config = config or ImprovementConfig()
        self._results: Dict[str, List[BenchmarkResult]] = {}

    def run_benchmark(
        self,
        name: str,
        test_func: Callable[[], Any],
        iterations: int = 10,
    ) -> BenchmarkResult:
        """Run a benchmark and record the result.

        Args:
            name: Benchmark name.
            test_func: The function to benchmark.
            iterations: Number of iterations to run.

        Returns:
            A BenchmarkResult with aggregated metrics.
        """
        if not self.config.enable_benchmarking:
            raise RuntimeError("Benchmarking is disabled")

        latencies: List[float] = []
        score_sum = 0.0
        successes = 0

        for _ in range(iterations):
            t0 = time.perf_counter()
            try:
                result = test_func()
                elapsed = (time.perf_counter() - t0) * 1000  # ms
                latencies.append(elapsed)
                score_sum += 1.0
                successes += 1
            except Exception as e:
                logger.warning("Benchmark iteration failed: %s", e)
                latencies.append(float("inf"))

        avg_latency = sum(l for l in latencies if l != float("inf")) / max(successes, 1)
        accuracy = successes / max(iterations, 1)
        score = score_sum / max(iterations, 1)

        result_id = uuid.uuid4().hex[:12]
        result = BenchmarkResult(
            id=result_id,
            benchmark_name=name,
            score=round(score, 4),
            latency_ms=round(avg_latency, 2),
            accuracy=round(accuracy, 4),
            memory_bytes=0,
            version="1.0.0",
            environment={},
            tags=[],
        )

        if name not in self._results:
            self._results[name] = []
        self._results[name].append(result)

        logger.info(
            "Benchmark '%s' completed: score=%.4f, latency=%.2fms, accuracy=%.4f",
            name, score, avg_latency, accuracy,
        )
        return result

    def compare(self, baseline_name: str, current_name: str) -> Dict[str, Any]:
        """Compare the latest results of two benchmarks.

        Args:
            baseline_name: Name of the baseline benchmark.
            current_name: Name of the current benchmark.

        Returns:
            Dict with comparison data.
        """
        baseline_results = self._results.get(baseline_name, [])
        current_results = self._results.get(current_name, [])

        if not baseline_results or not current_results:
            return {"error": "One or both benchmark names not found"}

        baseline = baseline_results[-1]
        current = current_results[-1]

        score_delta = current.score - baseline.score
        latency_delta = current.latency_ms - baseline.latency_ms
        accuracy_delta = current.accuracy - baseline.accuracy

        return {
            "baseline": baseline_name,
            "current": current_name,
            "score_delta": round(score_delta, 4),
            "latency_delta_ms": round(latency_delta, 2),
            "accuracy_delta": round(accuracy_delta, 4),
            "baseline_score": baseline.score,
            "current_score": current.score,
            "baseline_latency_ms": baseline.latency_ms,
            "current_latency_ms": current.latency_ms,
        }

    def get_history(self, benchmark_name: str) -> List[BenchmarkResult]:
        """Get historical results for a benchmark.

        Args:
            benchmark_name: Name of the benchmark.

        Returns:
            List of results, newest first.
        """
        results = self._results.get(benchmark_name, [])
        return sorted(results, key=lambda r: r.timestamp, reverse=True)

    def check_regression(self, name: str, threshold: float = 0.1) -> bool:
        """Check if the latest result represents a regression.

        Compares the latest result to the previous one. A regression
        is detected if score drops by more than the threshold.

        Args:
            name: Benchmark name.
            threshold: Maximum allowed score drop (0.0-1.0).

        Returns:
            True if a regression is detected, False otherwise.
        """
        results = self._results.get(name, [])
        if len(results) < 2:
            return False

        latest = results[-1]
        previous = results[-2]
        return latest.score < previous.score * (1.0 - threshold)

    def get_top_slowest(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get the slowest benchmarks by average latency.

        Args:
            limit: Maximum number of entries to return.

        Returns:
            List of dicts with benchmark_name and avg_latency_ms.
        """
        averages: Dict[str, float] = {}
        for name, results in self._results.items():
            if results:
                avg = sum(r.latency_ms for r in results) / len(results)
                averages[name] = avg

        sorted_avgs = sorted(averages.items(), key=lambda item: item[1], reverse=True)
        return [
            {"benchmark_name": name, "avg_latency_ms": round(avg, 2)}
            for name, avg in sorted_avgs[:limit]
        ]

    def generate_report(self) -> str:
        """Generate a text summary of all benchmarks.

        Returns:
            Multi-line string with benchmark summaries.
        """
        if not self._results:
            return "No benchmarks recorded."

        lines = ["Benchmark Report", "=" * 40, ""]
        for name in sorted(self._results.keys()):
            results = self._results[name]
            if results:
                latest = results[-1]
                lines.append(f"  {name}:")
                lines.append(f"    Score:     {latest.score}")
                lines.append(f"    Latency:   {latest.latency_ms} ms")
                lines.append(f"    Accuracy:  {latest.accuracy}")
                lines.append(f"    Runs:      {len(results)}")
                lines.append("")

        # Add top slowest
        slowest = self.get_top_slowest()
        if slowest:
            lines.append("Top Slowest Benchmarks:")
            for s in slowest:
                lines.append(f"  {s['benchmark_name']}: {s['avg_latency_ms']} ms avg")

        return "\n".join(lines)
