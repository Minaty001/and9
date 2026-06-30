# Phase 3: Query Understanding Pipeline

## Overview

Orchestrates the full query processing pipeline:

```
Input → Normalize → Tokenize → Intent → Entities → Context → Planner → Skill Router
```

Every stage returns confidence and structured output. Falls back to clarification when confidence is low.

## Architecture

The `QueryPipeline` is a configurable chain of stage handlers. Each stage receives a shared context dict and returns a `StageResult`. The pipeline stops early if:
- A stage fails
- Clarification is required
- Overall confidence is below threshold

## Components

### QueryPipeline
```python
pipeline = QueryPipeline()
result = await pipeline.process("open whatsapp")
print(result.intent, result.confidence)
```

**Custom stages:**
```python
async def my_entity_extractor(ctx):
    ctx["entities"] = {"app": "whatsapp"}
    return StageResult(stage=PipelineStage.ENTITIES, data={"entities": ctx["entities"]})

pipeline.register_stage(PipelineStage.ENTITIES, my_entity_extractor)
```

### QueryUnderstandingService
Wraps the pipeline with lifecycle management:
```python
svc = QueryUnderstandingService()
await svc.initialize()
result = await svc.process("hello")
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `JARVIS_QUERY_MIN_CONFIDENCE_TO_ACT` | 0.7 | Minimum confidence to execute |
| `JARVIS_QUERY_CLARIFICATION_CONFIDENCE_THRESHOLD` | 0.5 | Below this, ask for clarification |
| `JARVIS_QUERY_MAX_QUERY_LENGTH` | 500 | Max input query length |
| `JARVIS_QUERY_PIPELINE_TIMEOUT_MS` | 5000 | Max pipeline execution time |

## Models

### QueryResult
```python
result = QueryResult(
    query="open whatsapp",
    normalized="open whatsapp",
    intent="open_app",
    intent_confidence=0.95,
    entities={"app": "whatsapp"},
    requires_clarification=False,
    trace=[...],
    total_time_ms=120.5,
    success=True
)
```

### StageResult
```python
result = StageResult(
    stage=PipelineStage.INTENT,
    success=True,
    confidence=0.95,
    data={"intent": "open_app"}
)
```

## Integration Guide

1. Create a `QueryUnderstandingService` or `QueryPipeline` directly
2. Register custom stage handlers for specific phases
3. Process queries and handle clarification requests
4. Wire the service into the ArchitectureService event bus

```python
from services.phase03_query import QueryUnderstandingService

svc = QueryUnderstandingService()
await svc.initialize()

async def my_intent_handler(ctx):
    # Call Phase 6 Intent Detection
    ctx["intent"] = "open_app"
    ctx["confidence"] = 0.95
    return StageResult(stage=PipelineStage.INTENT, data=ctx)

await svc.register_stage_handler(PipelineStage.INTENT, my_intent_handler)

result = await svc.process("open whatsapp")
if result.requires_clarification:
    print(f"Please clarify: {result.clarification_reason}")
else:
    print(f"Intent: {result.intent} (conf={result.intent_confidence:.2f})")
```
