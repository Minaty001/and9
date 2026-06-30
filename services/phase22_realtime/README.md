# Phase 22 — Real-Time Info Engine

Retrieve live info: weather, news, search, time. Validate freshness, source metadata, cache.

## Components

### RealtimeConfig
Configuration for the real-time engine. Uses environment variable prefix `JARVIS_PHASE22_`.

| Field | Default | Description |
|---|---|---|
| service_name | `jarvis_realtime` | Service name |
| enable_live_fetch | `True` | Enable live data fetching |
| default_cache_ttl_seconds | `120` | Default cache TTL |
| enable_source_metadata | `True` | Enable source metadata |
| max_concurrent_requests | `5` | Max concurrent requests |
| freshness_timeout_ms | `3000` | Freshness timeout |

### InfoSource
Pydantic model: `source_type`, `name`, `priority`, `enabled`, `cache_ttl`.

### InfoRequest
Pydantic model: `query`, `source_types`, `max_age_seconds`, `max_results`, `require_fresh`.

### InfoResult
Pydantic model: `source`, `query`, `data`, `retrieved_at`, `freshness_score` (0-1), `cache_hit`.

### RealtimeEngine
Core engine that:
- Registers and manages providers by source type
- Fetches from multiple providers
- Checks freshness timeout and adjusts scores
- Sorts results by freshness score descending

### Providers
- **MockWeatherProvider** — Returns mock weather data (temperature, humidity, forecast)
- **MockNewsProvider** — Returns mock news articles
- **MockSearchProvider** — Returns mock search results
- **TimeProvider** — Returns real current date/time data

### RealtimeInfoService
ServiceBase wrapper providing `fetch(request)`, `refresh()`, `get_providers()`.
