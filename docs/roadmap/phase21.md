# Phase 21: API Manager

## Purpose
Centralized external API integration with adapters, retries, rate limiting, authentication, caching, and fallback. `ApiAdapter` base class handles rate limiting (request timestamps), retries with exponential backoff + jitter, and HTTP execution. `MockHttpAdapter` supports testing with pre-registered responses. `ApiCache` provides LRU caching with TTL.

## Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `JARVIS_PHASE21_GLOBAL_TIMEOUT_MS` | 10000 | Global timeout |
| `JARVIS_PHASE21_MAX_RETRIES` | 3 | Max retry attempts |
| `JARVIS_PHASE21_ENABLE_RATE_LIMITING` | true | Enable rate limiting |
| `JARVIS_PHASE21_REQUESTS_PER_MINUTE` | 60 | Max requests per minute |
| `JARVIS_PHASE21_ENABLE_CACHING` | true | Enable response caching |
| `JARVIS_PHASE21_CACHE_TTL_SECONDS` | 300 | Cache TTL |

## Architecture
```
ApiManagerService
  ├── register_adapter(name, adapter) — register named API adapters
  ├── execute(request) → ApiResponse — execute with caching + fallback + metrics
  └── ApiCache — LRU with TTL for response caching
```

## Code
```python
class ApiAdapter:
    async def execute(self, request: ApiRequest) -> ApiResponse:
        if self._rate_limit_exceeded(): return ApiResponse(success=False, error="Rate limited")
        for attempt in range(request.retry_count + 1):
            try:
                resp = await self._http_execute(request)
                return ApiResponse(success=resp.ok, status_code=resp.status, data=resp.json())
            except Exception as e:
                if attempt == request.retry_count: raise
                await asyncio.sleep(2 ** attempt + random.random())  # exponential backoff + jitter

class ApiCache:
    def set(self, key, response):  # LRU eviction + TTL
        self._cache[key] = (response, time.time() + self._ttl)
        self._access_order.append(key)
        while len(self._cache) > self.max_size:
            oldest = self._access_order.pop(0)
            del self._cache[oldest]
```

## Location
`app/api/` and `app/integrations/` — external API adapters and integrations
