# Phase 40: Performance Optimization

## Overview

Caching (L1/L2), lazy loading, request coalescing, resource pooling, and benchmark utilities for optimizing service performance.

## Architecture

```
PerformanceOptimizer
     │
     ├── L1Cache ◄──── Small, fast LRU cache (configurable size/TTL)
     │
     ├── L2Cache ◄──── Larger distributed LRU cache (configurable size/TTL)
     │
     ├── RequestCoalescer ◄──── Deduplicate concurrent requests for same key
     │                           First caller triggers, others wait
     │
     ├── ResourcePool ◄──── Pool reusable resources (connections, workers)
     │                       Create, acquire, release, idle timeout
     │
     └── LazyLoader ◄──── Cache loaded results on demand
                          Loading statistics and tracking
```

## Components

- **L1Cache**: Small, fast LRU cache with TTL and eviction
- **L2Cache**: Larger LRU cache with TTL and eviction
- **RequestCoalescer**: Deduplicate concurrent async requests; first caller triggers work
- **ResourcePool**: Pool reusable resources with acquire/release and idle timeout
- **LazyLoader**: Lazily load and cache values with loading statistics
- **PerformanceOptimizerService**: ServiceBase wrapper with benchmark utilities

## Usage

```python
from services.phase40_performance import PerformanceOptimizerService

svc = PerformanceOptimizerService()
await svc.initialize()

# L1/L2 caching
svc.l1_set("my_key", "my_value", ttl=60)
value, hit = svc.l1_get("my_key")

svc.l2_set("config", {"key": "val"})
cfg, hit = svc.l2_get("config")

# Request coalescing
result = await svc.coalesce("api_call", fetch_from_api)

# Resource pooling
resource, rid = svc.pool_acquire()
# ... use resource ...
svc.pool_release(rid)

# Lazy loading
value = svc.lazy_load("expensive_data", load_expensive_data)

# Benchmarking
timing = svc.benchmark(lambda: do_work(), iterations=100)
print(f"Average: {timing['avg_ms']}ms")
```
