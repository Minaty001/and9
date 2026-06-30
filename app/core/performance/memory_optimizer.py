"""
Performance — Memory Optimizer.

Monitor and optimize memory usage across the application.
"""

from __future__ import annotations

import sys
import logging
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

_ATOMIC_TYPES = (str, bytes, int, float, bool, type(None))


class MemoryOptimizer:
    """Monitor and optimize memory usage.

    Provides memory profiling, object size estimation,
    large object detection, and compression suggestions.

    Usage:
        opt = MemoryOptimizer()
        profile = opt.profile_memory()
        size = opt.estimate_size(large_object)
        large = opt.get_large_objects(threshold_mb=10)
    """

    def __init__(self):
        self._cache_sizes: Dict[str, int] = {}
        self._seen: Set[int] = set()

    def profile_memory(self) -> Dict[str, Any]:
        """Profile current memory usage."""
        usage = {}
        try:
            import psutil
            process = psutil.Process()
            mem_info = process.memory_info()
            usage["rss_bytes"] = mem_info.rss
            usage["rss_mb"] = round(mem_info.rss / (1024 * 1024), 2)
            usage["vms_bytes"] = mem_info.vms
            usage["vms_mb"] = round(mem_info.vms / (1024 * 1024), 2)
            usage["percent"] = process.memory_percent()
        except ImportError:
            try:
                with open("/proc/self/status") as f:
                    for line in f:
                        if line.startswith("VmRSS:"):
                            parts = line.split()
                            if len(parts) >= 2:
                                rss_kb = int(parts[1])
                                usage["rss_kb"] = rss_kb
                                usage["rss_mb"] = round(rss_kb / 1024, 2)
                                break
            except Exception:
                usage["rss_mb"] = 0
                usage["error"] = "psutil not available, fallback also failed"

        usage["monitored_caches"] = dict(self._cache_sizes)
        return usage

    def estimate_size(self, obj: Any, depth: int = 0) -> int:
        """Recursively estimate the size of an object in bytes.

        Limits recursion depth to 5 to avoid infinite loops.
        """
        if depth > 5:
            return sys.getsizeof(obj, default=0)

        obj_id = id(obj)
        if obj_id in self._seen:
            return 0
        self._seen.add(obj_id)

        try:
            size = sys.getsizeof(obj)
        except Exception:
            size = 0

        if isinstance(obj, _ATOMIC_TYPES):
            self._seen.discard(obj_id)
            return size

        if isinstance(obj, (list, tuple, set, frozenset)):
            for item in obj:
                size += self.estimate_size(item, depth + 1)

        elif isinstance(obj, dict):
            for k, v in obj.items():
                size += self.estimate_size(k, depth + 1)
                size += self.estimate_size(v, depth + 1)

        elif hasattr(obj, "__dict__"):
            size += self.estimate_size(obj.__dict__, depth + 1)

        elif hasattr(obj, "__slots__"):
            for slot in getattr(obj, "__slots__", []):
                try:
                    val = getattr(obj, slot, None)
                    if val is not None:
                        size += self.estimate_size(val, depth + 1)
                except Exception:
                    pass

        self._seen.discard(obj_id)
        return size

    def get_large_objects(self, threshold_mb: float = 10.0) -> List[Dict[str, Any]]:
        """Find large objects using gc.get_objects."""
        import gc
        large: List[Dict[str, Any]] = []
        threshold_bytes = int(threshold_mb * 1024 * 1024)

        for obj in gc.get_objects():
            try:
                s = sys.getsizeof(obj)
                if s >= threshold_bytes:
                    large.append({
                        "type": type(obj).__name__,
                        "size_bytes": s,
                        "size_mb": round(s / (1024 * 1024), 2),
                        "repr": repr(obj)[:200],
                    })
            except Exception:
                continue

        large.sort(key=lambda x: x["size_bytes"], reverse=True)
        return large[:50]

    def suggest_compression(self) -> List[str]:
        """Suggest memory optimizations based on current state."""
        suggestions = []
        profile = self.profile_memory()
        rss_mb = profile.get("rss_mb", 0)

        if rss_mb > 500:
            suggestions.append(
                f"Memory usage is high ({rss_mb} MB RSS). "
                "Consider reducing cache sizes or implementing LRU eviction."
            )

        if self._cache_sizes:
            total_cache = sum(self._cache_sizes.values())
            if total_cache > 100 * 1024 * 1024:
                suggestions.append(
                    f"Cache memory is {total_cache / (1024*1024):.0f} MB. "
                    "Consider reducing TTL or using compression for cached values."
                )

        if not suggestions:
            suggestions.append("Memory usage appears normal.")

        return suggestions

    def track_cache(self, name: str, size_bytes: int) -> None:
        """Track the size of a named cache."""
        self._cache_sizes[name] = size_bytes

    def clear(self) -> None:
        """Clear tracking data."""
        self._cache_sizes.clear()
        self._seen.clear()
