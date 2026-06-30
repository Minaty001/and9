# Phase 40: Performance

## Purpose
Performance optimization infrastructure with multi-level caching, request coalescing, resource pooling, lazy loading, startup profiling, bottleneck detection, and benchmarking. `L1Cache` is a small fast LRU cache with TTL and warmup strategies. `L2Cache` is a larger cache with the same interface. `RequestCoalescer` deduplicates concurrent requests for the same key. `ResourcePool` manages reusable resource instances (connections, workers) with idle timeout and eviction. `StartupOptimizer` profiles initialization time and suggests lazy-loading optimizations. `BottleneckProfiler` identifies slow operations. `BenchmarkSuite` runs N-iteration benchmarks with regression detection against baselines.

## Architecture
```
PerformanceOptimizerService
  ├── initialize() — configures all subsystems
  ├── health() / stats()
  │
  ├── L1Cache (capacity=128, TTL=60s)
  │     ├── get(key) → (value, hit)
  │     ├── set(key, value, ttl)
  │     ├── preload(keys, loader) / warmup(keys, loader)
  │     ├── invalidate(key) / clear()
  │     └── stats() → CacheStats
  │
  ├── L2Cache (capacity=1024, TTL=600s)
  │     └── Same interface as L1Cache
  │
  ├── RequestCoalescer
  │     └── coalesce(key, request_func, timeout) → result
  │
  ├── ResourcePool
  │     ├── acquire() → (resource, rid)
  │     ├── release(rid) → bool
  │     └── stats()
  │
  ├── StartupOptimizer
  │     ├── profile_startup(module_list) → timing results
  │     ├── get_startup_metrics()
  │     └── suggest_optimizations()
  │
  ├── BottleneckProfiler
  │     └── profile_operation(name, func, args) → ProfileResult
  │
  └── BenchmarkSuite
        ├── register_benchmark(name, func, iterations)
        ├── run(name) → {min, max, avg, median, stddev}
        ├── run_all() → all results
        └── compare_to_baseline(name) → regression detection
```

## Code
```python
class L1Cache:
    def get(self, key) -> Tuple[Any, bool]:
        entry = self._cache.get(key)
        if not entry: return None, False
        if entry["expires_at"] and time.time() > entry["expires_at"]:
            del self._cache[key]; return None, False
        self._cache.move_to_end(key)
        return entry["value"], True

    def set(self, key, value, ttl=None):
        expires_at = time.time() + (ttl or self._ttl) if (ttl or self._ttl) > 0 else None
        self._cache[key] = {"value": value, "expires_at": expires_at}
        while len(self._cache) > self._capacity:
            self._cache.popitem(last=False)

class RequestCoalescer:
    async def coalesce(self, key, request_func, timeout=None):
        if key in self._futures:
            return await self._futures[key]
        self._futures[key] = asyncio.Future()
        try:
            result = await request_func()
            self._futures[key].set_result(result)
        except Exception as e:
            self._futures[key].set_exception(e)
        finally:
            del self._futures[key]
        return result

class ResourcePool:
    def acquire(self) -> Tuple[Any, str]:
        if self._available:
            rid, (resource, _) = self._available.popitem(last=False)
            self._active[rid] = resource
            return resource, rid
        if self._total_created - self._total_destroyed < self._max_size:
            rid = uuid.uuid4().hex[:12]
            resource = self._creator()
            self._active[rid] = resource
            return resource, rid
        return None, None
```

## Location
`app/core/performance/` — L1/L2 cache, request coalescer, resource pool, lazy loader, startup optimizer, profiler, benchmark suite, memory optimizer, models, service wrapper
