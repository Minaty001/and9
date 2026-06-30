"""
Phase 40 — Performance Optimizer Service.

ServiceBase wrapper for the Performance Optimization service.
Exposes startup optimization, memory optimization, profiling,
benchmarking, and cache warmup methods.
"""

from __future__ import annotations

import time
import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple, Awaitable

from services.base.service_base import ServiceBase
from .config import PerformanceConfig
from .models import CacheEntry, CacheStats
from .l1_cache import L1Cache
from .l2_cache import L2Cache
from .request_coalescer import RequestCoalescer
from .resource_pool import ResourcePool
from .lazy_loader import LazyLoader
from .startup_optimizer import StartupOptimizer
from .memory_optimizer import MemoryOptimizer
from .profiler import BottleneckProfiler
from .benchmark_suite import BenchmarkSuite

logger = logging.getLogger(__name__)


class PerformanceOptimizerService(ServiceBase):
    """Performance optimization service with caching, pooling, and benchmarking.

    Usage:
        svc = PerformanceOptimizerService()
        await svc.initialize()
        svc.l1_set("key", "value")
        value, hit = svc.l1_get("key")
    """

    def __init__(self, config: Optional[PerformanceConfig] = None):
        super().__init__(name="jarvis_performance", version="1.0.0")
        self.config = config or PerformanceConfig()
        self.l1: Optional[L1Cache] = None
        self.l2: Optional[L2Cache] = None
        self.coalescer: Optional[RequestCoalescer] = None
        self.resource_pool: Optional[ResourcePool] = None
        self.lazy_loader: Optional[LazyLoader] = None
        self.startup_optimizer: Optional[StartupOptimizer] = None
        self.memory_optimizer: Optional[MemoryOptimizer] = None
        self.profiler: Optional[BottleneckProfiler] = None
        self.benchmark_suite: Optional[BenchmarkSuite] = None
        self._start_time = 0.0

    async def initialize(self) -> bool:
        self._start_time = time.time()
        try:
            if self.config.enable_l1_cache:
                self.l1 = L1Cache(self.config)
            if self.config.enable_l2_cache:
                self.l2 = L2Cache(self.config)
            if self.config.enable_request_coalescing:
                self.coalescer = RequestCoalescer(self.config)
            if self.config.enable_resource_pooling:
                self.resource_pool = ResourcePool(self.config)
            if self.config.enable_lazy_loading:
                self.lazy_loader = LazyLoader(self.config)

            # New components (always available)
            self.startup_optimizer = StartupOptimizer(self.config)
            self.memory_optimizer = MemoryOptimizer(self.config)
            self.profiler = BottleneckProfiler(self.config)
            self.benchmark_suite = BenchmarkSuite(self.config)

            self._metrics.reset()
            self._initialized = True
            logger.info("PerformanceOptimizerService initialized")
            return True
        except Exception as e:
            logger.error("PerformanceOptimizerService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        logger.info("PerformanceOptimizerService shutting down...")
        self._initialized = False

    # ── L1 Cache Operations ────────────────────────────────────────

    async def l1_get(self, key: str) -> Tuple[Optional[Any], bool]:
        if not self.l1:
            raise RuntimeError("L1 cache not enabled")
        value, hit = self.l1.get(key)
        if hit:
            self._metrics.counter("l1_hits", 1)
        else:
            self._metrics.counter("l1_misses", 1)
        return value, hit

    async def l1_set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        if not self.l1:
            raise RuntimeError("L1 cache not enabled")
        self.l1.set(key, value, ttl)

    async def l1_invalidate(self, key: str) -> bool:
        if not self.l1:
            raise RuntimeError("L1 cache not enabled")
        return self.l1.invalidate(key)

    async def l1_clear(self) -> None:
        if not self.l1:
            raise RuntimeError("L1 cache not enabled")
        self.l1.clear()

    async def l1_preload(self, keys: List[str],
                          loader_func: Callable[[str], Any],
                          ttl: Optional[int] = None) -> int:
        """Preload multiple keys into L1 cache."""
        if not self.l1:
            raise RuntimeError("L1 cache not enabled")
        return self.l1.preload(keys, loader_func, ttl)

    async def l1_warmup(self, keys: List[str],
                         loader_func: Callable[[str], Any],
                         ttl: Optional[int] = None) -> int:
        """Warm up L1 cache according to warmup strategy."""
        if not self.l1:
            raise RuntimeError("L1 cache not enabled")
        return self.l1.warmup(keys, loader_func, ttl)

    # ── L2 Cache Operations ────────────────────────────────────────

    async def l2_get(self, key: str) -> Tuple[Optional[Any], bool]:
        if not self.l2:
            raise RuntimeError("L2 cache not enabled")
        value, hit = self.l2.get(key)
        if hit:
            self._metrics.counter("l2_hits", 1)
        else:
            self._metrics.counter("l2_misses", 1)
        return value, hit

    async def l2_set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        if not self.l2:
            raise RuntimeError("L2 cache not enabled")
        self.l2.set(key, value, ttl)

    async def l2_invalidate(self, key: str) -> bool:
        if not self.l2:
            raise RuntimeError("L2 cache not enabled")
        return self.l2.invalidate(key)

    async def l2_clear(self) -> None:
        if not self.l2:
            raise RuntimeError("L2 cache not enabled")
        self.l2.clear()

    async def l2_preload(self, keys: List[str],
                          loader_func: Callable[[str], Any],
                          ttl: Optional[int] = None) -> int:
        """Preload multiple keys into L2 cache."""
        if not self.l2:
            raise RuntimeError("L2 cache not enabled")
        return self.l2.preload(keys, loader_func, ttl)

    async def l2_warmup(self, keys: List[str],
                         loader_func: Callable[[str], Any],
                         ttl: Optional[int] = None) -> int:
        """Warm up L2 cache according to warmup strategy."""
        if not self.l2:
            raise RuntimeError("L2 cache not enabled")
        return self.l2.warmup(keys, loader_func, ttl)

    # ── Request Coalescing ─────────────────────────────────────────

    async def coalesce(self, key: str, request_func: Callable[[], Awaitable[Any]],
                       timeout: Optional[float] = None) -> Any:
        if not self.coalescer:
            raise RuntimeError("Request coalescing not enabled")
        return await self.coalescer.coalesce(key, request_func, timeout)

    # ── Resource Pool ───────────────────────────────────────────────

    async def pool_acquire(self) -> Tuple[Optional[Any], Optional[str]]:
        if not self.resource_pool:
            raise RuntimeError("Resource pooling not enabled")
        return self.resource_pool.acquire()

    async def pool_release(self, rid: str) -> bool:
        if not self.resource_pool:
            raise RuntimeError("Resource pooling not enabled")
        return self.resource_pool.release(rid)

    # ── Lazy Loading ───────────────────────────────────────────────

    async def lazy_load(self, key: str, loader_func: Callable[[], Any]) -> Any:
        if not self.lazy_loader:
            raise RuntimeError("Lazy loading not enabled")
        return self.lazy_loader.load(key, loader_func)

    # ── Benchmark (legacy) ─────────────────────────────────────────

    async def benchmark(self, func: Callable[[], Any], iterations: int = 100) -> Dict[str, Any]:
        """Benchmark a function's execution time.

        Returns timing statistics (min, max, avg, median).
        """
        times = []
        for _ in range(iterations):
            t0 = time.perf_counter()
            func()
            elapsed = (time.perf_counter() - t0) * 1000
            times.append(elapsed)

        times.sort()
        n = len(times)
        return {
            "iterations": iterations,
            "min_ms": round(times[0], 3),
            "max_ms": round(times[-1], 3),
            "avg_ms": round(sum(times) / n, 3),
            "median_ms": round(times[n // 2], 3),
            "p95_ms": round(times[int(n * 0.95)], 3),
            "p99_ms": round(times[int(n * 0.99)], 3),
            "total_ms": round(sum(times), 3),
        }

    # ── Memory Usage (legacy) ───────────────────────────────────────

    async def memory_usage(self) -> Dict[str, Any]:
        """Estimate memory usage of cache components."""
        import sys
        usage = {}
        if self.l1:
            usage["l1_cache_entries"] = len(self.l1._cache)
            usage["l1_cache_size_bytes"] = sys.getsizeof(self.l1._cache)
        if self.l2:
            usage["l2_cache_entries"] = len(self.l2._cache)
            usage["l2_cache_size_bytes"] = sys.getsizeof(self.l2._cache)
        return usage

    # ── Startup Optimizer ───────────────────────────────────────────

    async def profile_startup(self, module_list: Dict[str, Callable[[], Any]]) -> Dict[str, Any]:
        """Profile startup time of service initializers."""
        if not self.startup_optimizer:
            raise RuntimeError("Startup optimizer not available")
        return self.startup_optimizer.profile_startup(module_list)

    async def get_startup_metrics(self) -> Dict[str, Any]:
        """Get aggregated startup metrics."""
        if not self.startup_optimizer:
            raise RuntimeError("Startup optimizer not available")
        return self.startup_optimizer.get_startup_metrics()

    async def suggest_startup_optimizations(self) -> List[str]:
        """Get startup optimization suggestions."""
        if not self.startup_optimizer:
            raise RuntimeError("Startup optimizer not available")
        return self.startup_optimizer.suggest_optimizations()

    # ── Memory Optimizer ────────────────────────────────────────────

    async def profile_memory(self) -> Dict[str, Any]:
        """Profile current memory usage."""
        if not self.memory_optimizer:
            raise RuntimeError("Memory optimizer not available")
        return self.memory_optimizer.profile_memory()

    async def estimate_size(self, obj: Any) -> int:
        """Estimate the size of an object in bytes."""
        if not self.memory_optimizer:
            raise RuntimeError("Memory optimizer not available")
        return self.memory_optimizer.estimate_size(obj)

    async def get_large_objects(self, threshold_mb: float = 10.0) -> List[Dict[str, Any]]:
        """Find large objects above a threshold."""
        if not self.memory_optimizer:
            raise RuntimeError("Memory optimizer not available")
        return self.memory_optimizer.get_large_objects(threshold_mb)

    async def suggest_memory_optimizations(self) -> List[str]:
        """Get memory optimization suggestions."""
        if not self.memory_optimizer:
            raise RuntimeError("Memory optimizer not available")
        return self.memory_optimizer.suggest_compression()

    # ── Bottleneck Profiler ─────────────────────────────────────────

    async def profile_call(self, func: Callable, *args, **kwargs) -> Tuple[Any, float, int]:
        """Profile a synchronous function call."""
        if not self.profiler:
            raise RuntimeError("Profiler not available")
        return self.profiler.profile_call(func, *args, **kwargs)

    async def profile_async(self, func: Callable, *args, **kwargs) -> Tuple[Any, float]:
        """Profile an async function call."""
        if not self.profiler:
            raise RuntimeError("Profiler not available")
        return await self.profiler.profile_async(func, *args, **kwargs)

    async def get_profile_report(self, top_n: int = 10) -> Dict[str, Any]:
        """Get profiling report."""
        if not self.profiler:
            raise RuntimeError("Profiler not available")
        return self.profiler.get_profile_report(top_n)

    async def generate_text_report(self, top_n: int = 10) -> str:
        """Generate a text profiling report."""
        if not self.profiler:
            raise RuntimeError("Profiler not available")
        return self.profiler.generate_text_report(top_n)

    # ── Benchmark Suite ─────────────────────────────────────────────

    async def register_benchmark(self, name: str, func: Callable[[], Any],
                                  iterations: int = 100) -> bool:
        """Register a benchmark function."""
        if not self.benchmark_suite:
            raise RuntimeError("Benchmark suite not available")
        return self.benchmark_suite.register_benchmark(name, func, iterations)

    async def run_benchmark(self, name: str) -> Dict[str, Any]:
        """Run a specific benchmark."""
        if not self.benchmark_suite:
            raise RuntimeError("Benchmark suite not available")
        return self.benchmark_suite.run(name)

    async def run_all_benchmarks(self) -> Dict[str, Dict[str, Any]]:
        """Run all registered benchmarks."""
        if not self.benchmark_suite:
            raise RuntimeError("Benchmark suite not available")
        return self.benchmark_suite.run_all()

    async def compare_benchmarks(self, baseline: Dict[str, Any],
                                  current: Dict[str, Any]) -> Dict[str, Any]:
        """Compare two benchmark results."""
        if not self.benchmark_suite:
            raise RuntimeError("Benchmark suite not available")
        return self.benchmark_suite.compare_results(baseline, current)

    # ── Detailed Stats ─────────────────────────────────────────────

    async def get_detailed_stats(self) -> Dict[str, Any]:
        """Get detailed performance statistics from all components."""
        stats = {}
        if self.l1:
            l1_stats = self.l1.stats()
            stats["l1_cache"] = l1_stats.model_dump() if hasattr(l1_stats, 'model_dump') else dict(l1_stats)
        if self.l2:
            l2_stats = self.l2.stats()
            stats["l2_cache"] = l2_stats.model_dump() if hasattr(l2_stats, 'model_dump') else dict(l2_stats)
        if self.coalescer:
            stats["coalescer"] = self.coalescer.get_stats()
        if self.resource_pool:
            stats["resource_pool"] = self.resource_pool.stats()
        if self.lazy_loader:
            stats["lazy_loader"] = self.lazy_loader.get_stats()
        if self.startup_optimizer:
            stats["startup_optimizer"] = self.startup_optimizer.get_startup_metrics()
        if self.memory_optimizer:
            stats["memory_optimizer"] = self.memory_optimizer.profile_memory()
        if self.profiler:
            stats["profiler"] = self.profiler.get_profile_report(top_n=5)
        if self.benchmark_suite:
            stats["benchmark_suite"] = self.benchmark_suite.get_summary()
        return stats

    async def health(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service_name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
            "l1_enabled": self.l1 is not None,
            "l2_enabled": self.l2 is not None,
        }

    async def stats(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            "detailed": await self.get_detailed_stats(),
            "metrics": self._metrics.snapshot(),
        }
