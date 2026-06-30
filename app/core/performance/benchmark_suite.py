"""
Performance — Benchmark Suite.

Run regular benchmarks to measure performance and detect regressions.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple
from datetime import datetime, timezone
from statistics import median, stdev

logger = logging.getLogger(__name__)

REGRESSION_THRESHOLD = 0.10  # 10% slowdown indicates regression


class BenchmarkSuite:
    """Register and run performance benchmarks.

    Each benchmark runs N iterations and reports min, max, avg, median.
    Results can be compared against a baseline to detect regressions.

    Usage:
        suite = BenchmarkSuite()

        def my_bench():
            return sum(range(1000))

        suite.register_benchmark("sum_range", my_bench, iterations=100)
        results = suite.run("sum_range")
        all_results = suite.run_all()
    """

    def __init__(self):
        self._benchmarks: Dict[str, Dict[str, Any]] = {}
        self._results: Dict[str, List[Dict[str, Any]]] = {}
        self._baselines: Dict[str, Dict[str, Any]] = {}

    def register_benchmark(self, name: str, func: Callable[[], Any],
                           iterations: int = 100) -> bool:
        """Register a benchmark function."""
        if name in self._benchmarks:
            logger.warning("Benchmark '%s' already registered, overwriting", name)
        self._benchmarks[name] = {
            "func": func,
            "iterations": max(1, iterations),
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }
        return True

    def run_all(self) -> Dict[str, Dict[str, Any]]:
        """Run all registered benchmarks."""
        results = {}
        for name in list(self._benchmarks.keys()):
            try:
                results[name] = self.run(name)
            except Exception as e:
                logger.error("Benchmark '%s' failed: %s", name, e)
                results[name] = {"error": str(e)}
        return results

    def run(self, name: str) -> Dict[str, Any]:
        """Run a specific benchmark by name."""
        if name not in self._benchmarks:
            raise ValueError(f"Benchmark '{name}' not registered")

        bench = self._benchmarks[name]
        func = bench["func"]
        iterations = bench["iterations"]

        # Warmup run
        try:
            func()
        except Exception:
            pass

        times: List[float] = []
        errors = 0

        for _ in range(iterations):
            t0 = time.perf_counter()
            try:
                func()
                elapsed = (time.perf_counter() - t0) * 1000
                times.append(elapsed)
            except Exception as e:
                elapsed = (time.perf_counter() - t0) * 1000
                times.append(elapsed)
                errors += 1
                logger.warning("Benchmark '%s' iteration failed: %s", name, e)

        times.sort()
        n = len(times)
        avg_ms = sum(times) / n if n > 0 else 0

        result = {
            "name": name,
            "iterations": iterations,
            "successful": iterations - errors,
            "errors": errors,
            "min_ms": round(times[0], 3) if times else 0,
            "max_ms": round(times[-1], 3) if times else 0,
            "avg_ms": round(avg_ms, 3),
            "median_ms": round(median(times), 3) if times else 0,
            "stddev_ms": round(stdev(times), 3) if len(times) > 1 else 0,
            "p95_ms": round(times[int(n * 0.95)], 3) if n > 0 else 0,
            "p99_ms": round(times[int(n * 0.99)], 3) if n > 0 else 0,
            "total_ms": round(sum(times), 3),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if name not in self._results:
            self._results[name] = []
        self._results[name].append(result)

        if name not in self._baselines:
            self._baselines[name] = result
            logger.info("Baseline set for benchmark '%s': avg=%.3f ms", name, avg_ms)

        return result

    def compare_results(self, baseline: Dict[str, Any],
                        current: Dict[str, Any]) -> Dict[str, Any]:
        """Compare two benchmark results to detect regressions."""
        baseline_avg = baseline.get("avg_ms", 0)
        current_avg = current.get("avg_ms", 0)

        if baseline_avg == 0:
            change_pct = 0
        else:
            change_pct = ((current_avg - baseline_avg) / baseline_avg) * 100

        return {
            "name": current.get("name", baseline.get("name", "unknown")),
            "baseline_avg_ms": round(baseline_avg, 3),
            "current_avg_ms": round(current_avg, 3),
            "change_percent": round(change_pct, 2),
            "is_regression": change_pct > (REGRESSION_THRESHOLD * 100),
            "is_improvement": change_pct < -(REGRESSION_THRESHOLD * 100),
            "regression_threshold_pct": REGRESSION_THRESHOLD * 100,
            "baseline_min_ms": baseline.get("min_ms", 0),
            "current_min_ms": current.get("min_ms", 0),
            "baseline_median_ms": baseline.get("median_ms", 0),
            "current_median_ms": current.get("median_ms", 0),
        }

    def compare_with_baseline(self, name: str) -> Optional[Dict[str, Any]]:
        """Compare the latest result with stored baseline."""
        if name not in self._baselines or name not in self._results:
            return None
        baseline = self._baselines[name]
        current = self._results[name][-1]
        return self.compare_results(baseline, current)

    def get_history(self, name: str) -> List[Dict[str, Any]]:
        """Get all historical results for a benchmark (newest first)."""
        results = self._results.get(name, [])
        return list(reversed(results))

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all benchmarks and their latest results."""
        summary = {}
        for name in self._benchmarks:
            if name in self._results and self._results[name]:
                latest = self._results[name][-1]
                comparison = self.compare_with_baseline(name)
                summary[name] = {
                    "latest": latest,
                    "comparison": comparison,
                    "history_count": len(self._results[name]),
                }
            else:
                summary[name] = {
                    "latest": None, "comparison": None, "history_count": 0,
                }
        return summary

    def set_baseline(self, name: str) -> bool:
        if name not in self._results or not self._results[name]:
            return False
        self._baselines[name] = self._results[name][-1]
        return True

    def clear_results(self) -> None:
        self._results.clear()

    def reset(self) -> None:
        self._benchmarks.clear()
        self._results.clear()
        self._baselines.clear()
