"""
Phase 40 — Bottleneck Profiler.

Integration with cProfile / time-based profiling for identifying
performance bottlenecks.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple
from collections import defaultdict
from functools import wraps

from .config import PerformanceConfig

logger = logging.getLogger(__name__)


class BottleneckProfiler:
    """Profile function calls to identify bottlenecks.

    Supports both synchronous and asynchronous profiling with
    call-count and timing statistics.

    Usage:
        profiler = BottleneckProfiler()

        # Profile a sync call
        result, timing, count = profiler.profile_call(my_func, arg1, arg2)

        # Profile an async call
        result, timing = await profiler.profile_async(async_func, arg1)

        # Get report
        report = profiler.get_profile_report()
    """

    def __init__(self, config: Optional[PerformanceConfig] = None):
        self.config = config or PerformanceConfig()
        self._stats: Dict[str, Dict[str, Any]] = {}
        self._call_times: Dict[str, List[float]] = defaultdict(list)

    def profile_call(self, func: Callable, *args: Any,
                     **kwargs: Any) -> Tuple[Any, float, int]:
        """Profile a synchronous function call.

        Args:
            func: The function to call and profile.
            *args, **kwargs: Arguments to pass to the function.

        Returns:
            Tuple of (result, elapsed_ms, call_count_so_far).
        """
        func_name = self._get_func_name(func)
        t0 = time.perf_counter()

        try:
            result = func(*args, **kwargs)
            success = True
        except Exception as e:
            result = None
            success = False
            elapsed_ms = (time.perf_counter() - t0) * 1000
            self._record_call(func_name, elapsed_ms, success=False, error=str(e))
            raise

        elapsed_ms = (time.perf_counter() - t0) * 1000
        self._record_call(func_name, elapsed_ms, success=True)

        stats = self._stats.get(func_name, {})
        return result, round(elapsed_ms, 3), stats.get("call_count", 0)

    async def profile_async(self, func: Callable, *args: Any,
                            **kwargs: Any) -> Tuple[Any, float]:
        """Profile an asynchronous function call.

        Args:
            func: The async function to call and profile.
            *args, **kwargs: Arguments to pass to the function.

        Returns:
            Tuple of (result, elapsed_ms).
        """
        func_name = self._get_func_name(func)
        t0 = time.perf_counter()

        try:
            result = await func(*args, **kwargs)
            success = True
        except Exception as e:
            result = None
            success = False
            elapsed_ms = (time.perf_counter() - t0) * 1000
            self._record_call(func_name, elapsed_ms, success=False, error=str(e))
            raise

        elapsed_ms = (time.perf_counter() - t0) * 1000
        self._record_call(func_name, elapsed_ms, success=True)
        return result, round(elapsed_ms, 3)

    def get_profile_report(self, top_n: int = 10) -> Dict[str, Any]:
        """Generate a summary report of profiled functions.

        Args:
            top_n: Number of top bottlenecks to include.

        Returns:
            Dict with statistics and sorted bottlenecks.
        """
        if not self._stats:
            return {"total_calls": 0, "total_time_ms": 0, "bottlenecks": []}

        bottlenecks = []
        total_time = 0.0
        total_calls = 0

        for func_name, stats in self._stats.items():
            total_time += stats["total_time_ms"]
            total_calls += stats["call_count"]
            bottlenecks.append({
                "function": func_name,
                "call_count": stats["call_count"],
                "total_time_ms": round(stats["total_time_ms"], 3),
                "avg_time_ms": round(stats["avg_time_ms"], 3),
                "min_time_ms": round(stats["min_time_ms"], 3),
                "max_time_ms": round(stats["max_time_ms"], 3),
                "error_count": stats["error_count"],
                "success_rate": round(
                    (stats["call_count"] - stats["error_count"])
                    / max(stats["call_count"], 1) * 100, 1
                ),
            })

        # Sort by total time descending (most expensive first)
        bottlenecks.sort(key=lambda x: x["total_time_ms"], reverse=True)

        return {
            "total_calls": total_calls,
            "total_time_ms": round(total_time, 3),
            "unique_functions": len(self._stats),
            "top_bottlenecks": bottlenecks[:top_n],
            "most_called": sorted(
                bottlenecks, key=lambda x: x["call_count"], reverse=True
            )[:top_n],
            "slowest_avg": sorted(
                bottlenecks, key=lambda x: x["avg_time_ms"], reverse=True
            )[:top_n],
        }

    def generate_text_report(self, top_n: int = 10) -> str:
        """Generate a simple human-readable text report.

        Args:
            top_n: Number of bottlenecks to include.

        Returns:
            Formatted text report.
        """
        report = self.get_profile_report(top_n)
        lines = [
            "=" * 60,
            "  Bottleneck Profiler Report",
            "=" * 60,
            f"  Total calls:      {report['total_calls']}",
            f"  Total time:       {report['total_time_ms']} ms",
            f"  Unique functions: {report['unique_functions']}",
            "",
            "  Top Bottlenecks (by total time):",
            "  " + "-" * 56,
        ]

        for i, b in enumerate(report.get("top_bottlenecks", []), 1):
            lines.append(
                f"  {i:2d}. {b['function'][:50]:50s} "
                f"{b['total_time_ms']:>8.1f}ms  "
                f"{b['call_count']:>5d}x  "
                f"avg {b['avg_time_ms']:>6.2f}ms"
            )

        lines.extend([
            "",
            "  Slowest Average:",
            "  " + "-" * 56,
        ])
        for i, b in enumerate(report.get("slowest_avg", [])[:5], 1):
            lines.append(
                f"  {i:2d}. {b['function'][:50]:50s} "
                f"avg {b['avg_time_ms']:>8.2f}ms  "
                f"({b['call_count']} calls)"
            )

        lines.append("=" * 60)
        return "\n".join(lines)

    def decorator(self, func: Callable) -> Callable:
        """Decorator that profiles the wrapped function.

        Usage:
            @profiler.decorator
            def my_func():
                ...
        """

        @wraps(func)
        def wrapper(*args, **kwargs):
            result, _, _ = self.profile_call(func, *args, **kwargs)
            return result
        return wrapper

    def _record_call(self, func_name: str, elapsed_ms: float,
                     success: bool = True, error: str = "") -> None:
        """Record a function call in the internal statistics."""
        if func_name not in self._stats:
            self._stats[func_name] = {
                "call_count": 0,
                "total_time_ms": 0.0,
                "min_time_ms": elapsed_ms,
                "max_time_ms": elapsed_ms,
                "avg_time_ms": 0.0,
                "error_count": 0,
            }

        stats = self._stats[func_name]
        stats["call_count"] += 1
        stats["total_time_ms"] += elapsed_ms
        stats["min_time_ms"] = min(stats["min_time_ms"], elapsed_ms)
        stats["max_time_ms"] = max(stats["max_time_ms"], elapsed_ms)
        stats["avg_time_ms"] = stats["total_time_ms"] / stats["call_count"]

        if not success:
            stats["error_count"] += 1

        self._call_times[func_name].append(elapsed_ms)

    @staticmethod
    def _get_func_name(func: Callable) -> str:
        """Get a human-readable name for a function."""
        if hasattr(func, "__qualname__") and func.__qualname__:
            return func.__qualname__
        if hasattr(func, "__name__") and func.__name__:
            return func.__name__
        return str(func)[:60]

    def clear(self) -> None:
        """Clear all profiling data."""
        self._stats.clear()
        self._call_times.clear()
