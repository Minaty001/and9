"""
app/core/performance/ — Performance Optimization

Caching (L1/L2), lazy loading, request coalescing, resource pooling,
startup optimization, memory optimization, profiling, benchmark suite.
"""

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
from .service import PerformanceOptimizerService, PerformanceConfig

__all__ = [
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
    "PerformanceConfig",
]
