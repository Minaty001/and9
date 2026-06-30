# Phase 20 — Search Engine

Unified search engine combining web, memory, and document search sources with merging, ranking, caching, and telemetry.

## Components

### SearchConfig
Configuration for the search engine. Uses environment variable prefix `JARVIS_PHASE20_`.

| Field | Default | Description |
|---|---|---|
| service_name | `jarvis_search` | Service name |
| enable_web_search | `True` | Enable web search |
| enable_memory_search | `True` | Enable memory search |
| enable_document_search | `True` | Enable document search |
| max_results | `20` | Max merged results |
| cache_ttl_seconds | `300` | Cache TTL |
| enable_cache | `True` | Enable result caching |
| enable_telemetry | `True` | Enable telemetry |
| web_search_timeout_ms | `5000` | Web search timeout |
| rerank_min_score | `0.3` | Min score for reranking |

### SearchResult
Pydantic model with fields: `id`, `title`, `snippet`, `url` (optional), `source` (web/memory/document), `score` (0-1), `metadata`, `timestamp`.

### SearchQuery
Pydantic model with: `text`, `intent` (optional), `filters`, `max_results`, `sources`, `min_score`.

### WebSearcher
Simulated web search. Matches query against mock result titles/snippets. Supports `set_custom_results()` for testing.

### MemorySearcher
Simulated memory search. Uses keyword matching against stored memory items. Supports `add_memory()` and `clear_memory()`.

### DocumentSearcher
Simulated document search. Uses keyword matching against stored documents. Supports `add_document()` and `clear_documents()`.

### SearchMerger
Merges results from multiple sources with deduplication (by title/url), score filtering, and sorting by score descending.

### SearchCache
LRU cache with TTL for search results. Supports `get`, `set`, `invalidate`, `clear`. Automatically evicts oldest entries when over capacity.

### SearchEngineService
ServiceBase wrapper providing async access to all search functionality.
