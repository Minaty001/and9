# Phase 7: Entity Extraction

## Overview

Extracts structured entities from user queries — apps, contacts, times, locations, and media. Validates entities before execution and resolves ambiguities using context.

## Extractors

| Extractor | Entity Types | Example |
|-----------|-------------|---------|
| AppExtractor | App names → Package names | "open whatsapp" → `com.whatsapp` |
| ContactExtractor | Contact names | "call mom" → `mom` |
| TimeExtractor | Dates, times, durations | "set alarm for 7am" → `07:00` |
| LocationExtractor | Cities, locations | "weather in delhi" → "Delhi, India" |
| MediaExtractor | Songs, videos | "play despacito" → `despacito` |

## Validation

Each entity type has specific validation rules:
- Apps: must have a package name or be a known app
- Contacts: non-empty, reasonable length, no dangerous chars
- Times: valid hour (0-23), minute (0-59)
- Locations: non-empty, reasonable length
- Media: non-empty, safe characters

## Usage

```python
from services.phase07_entity import EntityExtractionService

svc = EntityExtractionService()
await svc.initialize()

result = await svc.extract("call mom at 5pm")
for entity in result.entities:
    print(f"{entity.type}: {entity.value} (conf={entity.confidence})")

# Grouped access
for etype, ents in result.grouped.items():
    print(f"  {etype}: {[e.value for e in ents]}")
```

## Integration

```python
# Wire into Phase 3 Query Pipeline
async def entity_handler(ctx):
    text = ctx.get("query", "")
    intent = ctx.get("intent", "")
    result = await entity_svc.extract(text, intent)
    ctx["entities"] = {e.type: e.value for e in result.entities}
    return StageResult(stage=PipelineStage.ENTITIES, data=ctx)
```
