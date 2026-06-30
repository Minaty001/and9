"""
Performance — Startup Optimizer.

Profile and optimize service startup time.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

_SLOW_THRESHOLD_MS = 100.0


class StartupOptimizer:
    """Profile and optimize service startup.

    Tracks initialization time for registered services and provides
    optimization suggestions such as lazy loading.

    Usage:
        opt = StartupOptimizer()
        opt.profile_startup({"svc_a": init_a, "svc_b": init_b})
        metrics = opt.get_startup_metrics()
        suggestions = opt.suggest_optimizations()
    """

    def __init__(self):
        self._timings: Dict[str, Dict[str, Any]] = {}
        self._total_start_time: Optional[float] = None
        self._total_end_time: Optional[float] = None

    def profile_startup(self, module_list: Dict[str, Callable[[], Any]]) -> Dict[str, Any]:
        """Profile the startup time of each service initializer."""
        self._total_start_time = time.perf_counter()
        results: Dict[str, Any] = {}

        for name, init_func in module_list.items():
            t0 = time.perf_counter()
            try:
                init_func()
                elapsed_ms = (time.perf_counter() - t0) * 1000
                success = True
                error = None
            except Exception as e:
                elapsed_ms = (time.perf_counter() - t0) * 1000
                success = False
                error = str(e)
                logger.error("Startup profile failed for '%s': %s", name, error)

            info = {
                "service": name,
                "time_ms": round(elapsed_ms, 3),
                "success": success,
                "error": error,
                "is_slow": elapsed_ms > _SLOW_THRESHOLD_MS,
            }
            results[name] = info
            self._timings[name] = info

        self._total_end_time = time.perf_counter()
        return results

    def get_startup_metrics(self) -> Dict[str, Any]:
        """Get aggregated startup metrics."""
        if not self._timings:
            return {"total_time_ms": 0, "services": {}, "slow_initializers": []}

        total = 0.0
        slow = []
        for name, info in self._timings.items():
            total += info["time_ms"]
            if info.get("is_slow"):
                slow.append({"service": name, "time_ms": info["time_ms"]})

        return {
            "total_time_ms": round(total, 3),
            "wall_time_ms": round(
                ((self._total_end_time or 0) - (self._total_start_time or 0)) * 1000, 3
            ),
            "service_count": len(self._timings),
            "services": dict(self._timings),
            "slow_initializers": sorted(slow, key=lambda x: x["time_ms"], reverse=True),
            "slow_threshold_ms": _SLOW_THRESHOLD_MS,
        }

    def suggest_optimizations(self) -> List[str]:
        """Generate optimization suggestions based on profiling."""
        suggestions = []
        metrics = self.get_startup_metrics()
        total = metrics["total_time_ms"]

        if total > 1000:
            suggestions.append(
                f"Total startup time is {total:.0f}ms. "
                "Consider parallelizing independent initializers."
            )

        for entry in metrics.get("slow_initializers", []):
            svc = entry["service"]
            t = entry["time_ms"]
            suggestions.append(
                f"'{svc}' is slow ({t:.0f}ms > {_SLOW_THRESHOLD_MS:.0f}ms threshold). "
                "Consider lazy loading or deferred initialization."
            )

        if not suggestions:
            suggestions.append("All startup initializers are within acceptable time.")

        return suggestions

    def clear(self) -> None:
        self._timings.clear()
        self._total_start_time = None
        self._total_end_time = None
