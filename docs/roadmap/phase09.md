# Phase 09: Memory System

## Purpose
Manages long-term and working memory as key-value items with importance scoring, tags, and lifecycle management. Four memory types (Working/Long-term/Episodic/Semantic) with per-type LRU eviction caps. Working memories with importance ≥ 0.7 auto-consolidate to long-term storage, ensuring important information persists.

## Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `JARVIS_MEMORY_MAX_WORKING_MEMORIES` | 50 | Max working items |
| `JARVIS_MEMORY_MAX_LONG_TERM_MEMORIES` | 500 | Max long-term items |
| `JARVIS_MEMORY_CONSOLIDATION_IMPORTANCE_THRESHOLD` | 0.7 | Working→long-term promotion threshold |
| `JARVIS_MEMORY_AUTO_CONSOLIDATE_ON_STORE` | true | Auto-consolidate after each store |
| `JARVIS_MEMORY_DEFAULT_IMPORTANCE` | 0.3 | Default importance |

## Architecture
```
MemoryManager
  └── MemoryStore (in-memory dict with LRU eviction)
        ├── add/get/update/delete/search
        ├── list_by_type / count_by_type
        └── search(query): matches by key, value string, tags
```

## Code
```python
class MemoryItem(BaseModel):
    key: str; value: Any; memory_type: MemoryType
    importance: float; tags: List[str]; access_count: int
    def touch(self): self.access_count += 1; self.last_accessed = now()

class MemoryManager:
    def store(self, key, value, memory_type=WORKING, importance=None, tags=None):
        importance = importance or self.config.default_importance
        item = MemoryItem(key=key, value=value, memory_type=memory_type, importance=importance, ...)
        self._store.add(item)
        if self.config.auto_consolidate_on_store: self.consolidate()
        return item

    def consolidate(self) -> int:
        for item in self._store.list_by_type(WORKING):
            if item.importance >= self.config.consolidation_importance_threshold:
                item.memory_type = LONG_TERM; consolidated += 1
        return consolidated
```

## Location
`app/memory/` — working, short_term, episodic, semantic stores
