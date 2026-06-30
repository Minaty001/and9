# Phase 21 — API Manager

Centralized external API integrations behind adapters. Retries, timeout, rate limiting, auth, caching, fallback.

## Components

### ApiConfig
Configuration for the API manager. Uses environment variable prefix `JARVIS_PHASE21_`.

| Field | Default | Description |
|---|---|---|
| service_name | `jarvis_api` | Service name |
| global_timeout_ms | `10000` | Global timeout in ms |
| max_retries | `3` | Max retry attempts |
| enable_rate_limiting | `True` | Enable rate limiting |
| requests_per_minute | `60` | Max requests per minute |
| enable_caching | `True` | Enable response caching |
| cache_ttl_seconds | `300` | Cache TTL |
| fallback_enabled | `True` | Enable fallback adapters |

### ApiRequest
Pydantic model: `endpoint`, `method` (GET/POST/PUT/DELETE), `headers`, `params`, `body`, `timeout_ms`, `retry_count`, `adapter_name`.

### ApiResponse
Pydantic model: `success`, `status_code`, `data`, `headers`, `duration_ms`, `cached`, `error`.

### ApiAdapter
Base abstract adapter with:
- `execute(request)` → ApiResponse
- Rate limiting via request timestamps
- Retries with exponential backoff + jitter
- `MockHttpAdapter` for testing with pre-registered responses

### ApiCache
LRU cache with TTL. Supports `get`, `set`, `invalidate`, `clear`. Automatically evicts oldest entries when over capacity.

### ApiManagerService
ServiceBase wrapper providing:
- `execute(request)` — Execute with caching, fallback, and metrics
- `register_adapter(name, adapter)` — Register named adapters
- `get_cached(key)` / `clear_cache()` / `invalidate_cache(key)` — Cache management
- `list_adapters()` — List registered adapters
