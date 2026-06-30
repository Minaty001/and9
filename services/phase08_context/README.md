# Phase 8: Context Builder

## Overview

Manages conversation context across turns using a sliding window with time-based decay, entity overlap scoring, and relevance search. Enables the assistant to understand follow-up queries like "and in Mumbai?" after "what's the weather in Delhi?".

## Architecture

```
TurnContext                 ContextManager               ContextSnapshot
 ┌─────────────────┐        ┌──────────────────┐        ┌─────────────────┐
 │ turn_id: int     │───▶   │  add_turn()       │───▶   │ turn_count      │
 │ query: str       │        │  search_relevant()│        │ recent_turns[]  │
 │ intent: str      │        │  get_snapshot()   │        │ current_turn    │
 │ entities: dict   │        │  clear()          │        │ active_entities │
 │ timestamp: datetime│      │  _prune()         │        │ recent_intents  │
 └─────────────────┘        └──────────────────┘        └─────────────────┘
```

## Relevance Scoring

Each past turn is scored against a query using:

| Component | Weight | Description |
|-----------|--------|-------------|
| Recency | 40% | Later turns score higher, multiplied by decay factor |
| Entity Overlap | 35% | Jaccard similarity between query hints and stored entities |
| Intent Match | 25% | Whether the turn's intent matches the query |

Decay: `decay_rate ^ (age_minutes / 5)`. Default rate: 0.85.

## Usage

```python
from services.phase08_context import ContextBuilderService

svc = ContextBuilderService()
await svc.initialize()

# Add turns
s1 = await svc.process("what's the weather", intent="weather_query",
                        entities={"location": ["Delhi"]})
s2 = await svc.process("and in Mumbai?")  # inherits intent via context

# Search relevant turns
results = await svc.search("delhi")
for ts in results:
    print(f"turn {ts.turn.turn_id}: score={ts.score:.2f}, query={ts.turn.query}")

# Get snapshot
ctx = await svc.get_context()
print(ctx.active_entities)  # {"location": ["Delhi", "Mumbai"]}
```

## Integration

```python
# Wire into Phase 3 Query Pipeline
async def context_handler(ctx):
    query = ctx.get("query", "")
    intent = ctx.get("intent", "")
    entities = ctx.get("entities", {})
    snapshot = await context_svc.process(query, intent=intent, entities=entities)
    ctx["context_snapshot"] = snapshot.model_dump()
    ctx["active_entities"] = snapshot.active_entities
    return StageResult(stage=PipelineStage.CONTEXT, data=ctx)
```
