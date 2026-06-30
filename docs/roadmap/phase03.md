# Phase 03: Query Understanding Pipeline

## Purpose
Orchestrates the full query processing pipeline as a configurable chain of stage handlers: Input → Normalize → Tokenize → Intent → Entities → Context → Planner → Skill Router. Each stage returns `StageResult` with confidence; the pipeline stops early on failure, low confidence, or clarification needed.

## Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `JARVIS_QUERY_MIN_CONFIDENCE_TO_ACT` | 0.7 | Minimum confidence to execute |
| `JARVIS_QUERY_CLARIFICATION_CONFIDENCE_THRESHOLD` | 0.5 | Below this, ask for clarification |
| `JARVIS_QUERY_MAX_QUERY_LENGTH` | 500 | Max input query length |
| `JARVIS_QUERY_PIPELINE_TIMEOUT_MS` | 5000 | Max pipeline execution time |

## Architecture
```
QueryUnderstandingService
  └── pipeline: QueryPipeline
        ├── register_stage(stage, handler)  — Override any stage
        └── process(query) → QueryResult
              └── Executes stages in order, tracking trace + confidence
```

## Code
```python
class QueryPipeline:
    def register_stage(self, stage: PipelineStage, handler: StageHandler):
        self._stages = [(s, h) for s, h in self._stages if s != stage]
        self._stages.append((stage, handler))

    async def process(self, query, **kwargs) -> QueryResult:
        ctx = {"query": query, "normalized": None, "intent": None, ...}
        for stage_name, handler in self._stages:
            stage_result = await handler(ctx)
            ctx.update(stage_result.data)
            if ctx.get("requires_clarification"): break
        return QueryResult(intent=ctx["intent"], ...)
```

## Location
`app/brain/` — pipeline orchestrates brain modules
