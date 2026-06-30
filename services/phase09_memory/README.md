# Phase 9: Memory System

## Overview

Manages long-term and working memory for the JARVIS assistant. Memories are stored as key-value pairs with importance scoring, tags, and lifecycle management.

## Architecture

```
MemoryItem                    MemoryStore                     MemoryManager
 ┌─────────────────┐         ┌──────────────────┐          ┌──────────────────┐
 │ key: str         │         │ add(item)        │          │ store(key, val)  │
 │ value: Any       │────────▶│ get(key)         │─────────▶│ recall(query)    │
 │ memory_type: enum│         │ search(query)    │          │ consolidate()    │
 │ importance: 0-1  │         │ delete(key)      │          │ forget(key)      │
 │ tags: List[str]  │         │ get_stats()      │          │ get_stats()      │
 │ access_count     │         └──────────────────┘          └──────────────────┘
 └─────────────────┘
```

## Memory Types

| Type | Purpose | Max Items | Example |
|------|---------|-----------|---------|
| Working | Short-term, transient | 50 | Current task context |
| Long-term | Important, persisted | 500 | User preferences, facts |
| Episodic | Experience-based | 500 | Past interactions |
| Semantic | Knowledge-based | 500 | Learned facts, concepts |

## Consolidation

Working memories with `importance >= threshold` (default 0.7) are automatically promoted to long-term storage. This ensures important information persists while trivial details are evicted via LRU.

```
Working Memory                    Long-Term Memory
┌─────────────────┐  0.9 ▶  ┌──────────────────┐
│ "current_page"   │         │ "user_name"       │
│ importance: 0.1  │         │ importance: 0.9   │
│ "weather_city"   │  0.4   └──────────────────┘
│ importance: 0.8  │──▶ (consolidated)
└─────────────────┘
```

## Usage

```python
from services.phase09_memory import MemoryService, MemoryType

svc = MemoryService()
await svc.initialize()

# Store
await svc.store("user_name", "Alice", memory_type="long_term", importance=0.9)
await svc.store("last_query", "what's the weather", tags=["session"])

# Recall
results = await svc.recall("alice")
for item in results:
    print(f"{item.key}: {item.value} (importance={item.importance})")

# Consolidate
count = await svc.consolidate()

# Stats
stats = await svc.get_stats()
print(f"{stats.total_items} memories stored")
```

## Integration

```python
# Wire into Phase 3 Query Pipeline
async def memory_handler(ctx):
    query = ctx.get("query", "")
    response = ctx.get("response", "")
    await memory_svc.store("last_query", query, tags=["session"])
    important_entities = ctx.get("entities", {})
    if important_entities:
        await memory_svc.store("entities", important_entities, importance=0.6)
    ctx["memory"] = await memory_svc.recall(query)
    return StageResult(stage=PipelineStage.MEMORY, data=ctx)
```
