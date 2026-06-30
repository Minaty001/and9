# Phase 20: Search Engine

## Purpose
Unified search engine combining web, memory, and document search sources. `WebSearcher`, `MemorySearcher`, and `DocumentSearcher` each provide keyword-matched mock results. `SearchMerger` merges, deduplicates (by title/URL), filters by minimum score, and sorts by descending score. `SearchCache` provides LRU caching with TTL.

## Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `JARVIS_PHASE20_ENABLE_WEB_SEARCH` | true | Enable web search |
| `JARVIS_PHASE20_ENABLE_MEMORY_SEARCH` | true | Enable memory search |
| `JARVIS_PHASE20_ENABLE_DOCUMENT_SEARCH` | true | Enable document search |
| `JARVIS_PHASE20_MAX_RESULTS` | 20 | Max merged results |
| `JARVIS_PHASE20_CACHE_TTL_SECONDS` | 300 | Cache TTL |
| `JARVIS_PHASE20_RERANK_MIN_SCORE` | 0.3 | Min score for reranking |

## Architecture
```
SearchEngineService
  ├── WebSearcher          — keyword match on mock result titles/snippets
  ├── MemorySearcher       — keyword match on stored memories
  ├── DocumentSearcher     — keyword match on stored documents
  ├── SearchMerger         — deduplicate + sort by score
  └── SearchCache          — LRU with TTL
```

## Code
```python
class SearchMerger:
    def merge(self, web_results, memory_results, doc_results, max_results=20, min_score=0.0):
        seen = {}  # title → SearchResult
        for r in web_results + memory_results + doc_results:
            if r.score < min_score: continue
            key = r.title.lower().strip()
            if key not in seen: seen[key] = r
        return sorted(seen.values(), key=lambda x: x.score, reverse=True)[:max_results]

class SearchCache:
    def get(self, key):  # LRU with TTL
        entry = self._cache.get(key)
        if not entry or time.time() > entry[1]: return None
        return entry[0]
```

## Location
`app/brain/` — search integration across multiple sources
