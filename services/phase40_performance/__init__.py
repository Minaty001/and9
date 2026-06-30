"""
Phase 40 — Performance Optimization
====================================

Caching (L1/L2), lazy loading, request coalescing, resource pooling,
startup optimization, memory optimization, profiling, benchmark suite.

Components:
    - L1Cache: Small, fast LRU cache
    - L2Cache: Larger distributed LRU cache
    - RequestCoalescer: Deduplicate concurrent requests for same key
    - ResourcePool: Pool reusable resources
    - LazyLoader: Cache loaded results on demand
    - StartupOptimizer: Profile and optimize startup
    - MemoryOptimizer: Monitor and optimize memory
    - BottleneckProfiler: Profile function calls for bottlenecks
    - BenchmarkSuite: Run and compare benchmarks
    - PerformanceOptimizerService: ServiceBase wrapper
"""

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
from .service import PerformanceOptimizerService

__all__ = [
    "PerformanceConfig",
    "CacheEntry",
    "CacheStats",
    "L1Cache",
    "L2Cache",
    "RequestCoalescer",
    "ResourcePool",
    "LazyLoader",
    "StartupOptimizer",
    "MemoryOptimizer",
    "BottleneckProfiler",
    "BenchmarkSuite",
    "PerformanceOptimizerService",
]
