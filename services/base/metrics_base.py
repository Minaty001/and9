"""
Metrics tracking for all JARVIS services.

Provides a simple, thread-safe metrics collector that can be
subclassed or extended with prometheus_client later.
"""

import time
import json
import threading
from typing import Dict, List, Any
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class MetricSample:
    """A single metric measurement."""

    name: str
    value: float
    timestamp: float
    tags: Dict[str, str] = field(default_factory=dict)


class MetricsTracker:
    """Thread-safe metrics collector.

    Supports:
        - Counters (increment / decrement)
        - Gauges (set current value)
        - Histograms (record latency distributions)
        - Summaries (min, max, avg, p50, p95, p99)

    Usage:
        metrics = MetricsTracker()
        metrics.counter("requests_total", 1)
        metrics.histogram("latency_ms", 45.2)
        metrics.gauge("active_connections", 5)
        report = metrics.snapshot()
    """

    def __init__(self, service_name: str = "jarvis"):
        self._service = service_name
        self._lock = threading.RLock()
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._samples: List[MetricSample] = []
        self._max_samples = 1000

    # ── Counters ────────────────────────────────────────────────

    def counter(self, name: str, value: int = 1, tags: Dict[str, str] = None) -> None:
        """Increment a counter metric."""
        with self._lock:
            self._counters[name] += value
            if tags:
                self._samples.append(MetricSample(name, float(value), time.time(), tags or {}))
                self._trim_samples()

    def counter_value(self, name: str) -> int:
        """Return the current counter value."""
        with self._lock:
            return self._counters.get(name, 0)

    # ── Gauges ──────────────────────────────────────────────────

    def gauge(self, name: str, value: float) -> None:
        """Set a gauge metric."""
        with self._lock:
            self._gauges[name] = value

    def gauge_value(self, name: str) -> float:
        """Return the current gauge value."""
        with self._lock:
            return self._gauges.get(name, 0.0)

    # ── Histograms ──────────────────────────────────────────────

    def histogram(self, name: str, value: float, tags: Dict[str, str] = None) -> None:
        """Record a histogram observation."""
        with self._lock:
            self._histograms[name].append(value)
            if len(self._histograms[name]) > 10000:
                self._histograms[name] = self._histograms[name][-5000:]
            if tags:
                self._samples.append(MetricSample(name, value, time.time(), tags))
                self._trim_samples()

    def histogram_summary(self, name: str) -> Dict[str, float]:
        """Compute summary statistics for a histogram metric."""
        with self._lock:
            values = sorted(self._histograms.get(name, []))
            if not values:
                return {"count": 0, "min": 0, "max": 0, "avg": 0, "p50": 0, "p95": 0, "p99": 0}
            n = len(values)
            return {
                "count": n,
                "min": values[0],
                "max": values[-1],
                "avg": sum(values) / n,
                "p50": values[int(n * 0.50)],
                "p95": values[int(n * 0.95)],
                "p99": values[int(n * 0.99)],
            }

    # ── Snapshot ────────────────────────────────────────────────

    def snapshot(self) -> Dict[str, Any]:
        """Capture a point-in-time snapshot of all metrics."""
        with self._lock:
            hist_summaries = {k: self.histogram_summary(k) for k in list(self._histograms.keys())}
            return {
                "service": self._service,
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": hist_summaries,
                "samples_count": len(self._samples),
            }

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._samples.clear()

    # ── Internal ────────────────────────────────────────────────

    def _trim_samples(self) -> None:
        """Keep sample list bounded."""
        while len(self._samples) > self._max_samples:
            self._samples.pop(0)

    def __repr__(self) -> str:
        return f"MetricsTracker(service={self._service})"
