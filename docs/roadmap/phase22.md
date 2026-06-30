# Phase 22: Real-Time Info Engine

## Purpose
Retrieves live information from multiple provider sources (weather, news, search, time). `RealtimeEngine` registers and manages providers by source type, fetches data from multiple providers concurrently, checks freshness timeout, and returns results sorted by freshness score. Includes mock providers for weather, news, and search, plus a real `TimeProvider`.

## Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `JARVIS_PHASE22_ENABLE_LIVE_FETCH` | true | Enable live data fetching |
| `JARVIS_PHASE22_DEFAULT_CACHE_TTL_SECONDS` | 120 | Default cache TTL |
| `JARVIS_PHASE22_ENABLE_SOURCE_METADATA` | true | Enable source metadata |
| `JARVIS_PHASE22_MAX_CONCURRENT_REQUESTS` | 5 | Max concurrent requests |
| `JARVIS_PHASE22_FRESHNESS_TIMEOUT_MS` | 3000 | Freshness timeout |

## Architecture
```
RealtimeInfoService
  └── RealtimeEngine
        ├── register_provider(source_type, provider)
        ├── fetch(request) → List[InfoResult] — multi-provider fetch, freshness check
        └── Providers:
              ├── MockWeatherProvider — mock temp/humidity/forecast
              ├── MockNewsProvider — mock news articles
              ├── MockSearchProvider — mock search results
              └── TimeProvider — real current date/time
```

## Code
```python
class RealtimeEngine:
    def register_provider(self, source_type, provider):
        self._providers.setdefault(source_type, []).append(provider)

    async def fetch(self, request: InfoRequest) -> List[InfoResult]:
        results = []
        for source_type in request.source_types:
            for provider in self._providers.get(source_type, []):
                if time.time() - provider.last_fetch > provider.cache_ttl:
                    data = await provider.fetch(request.query)
                    results.append(InfoResult(source=provider.name, data=data, freshness_score=1.0))
        results.sort(key=lambda r: r.freshness_score, reverse=True)
        return results[:request.max_results]

class TimeProvider:
    async def fetch(self, query) -> dict:
        now = datetime.now()
        return {"time": now.strftime("%I:%M %p"), "date": now.strftime("%B %d, %Y"),
                "day": now.strftime("%A"), "timezone": "UTC", "timestamp": now.isoformat()}
```

## Location
`app/integrations/` and `app/services/` — live data providers and integration
