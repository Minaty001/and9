# Phase 07: Entity Extraction

## Purpose
Extracts structured entities from user queries — apps (mapped to Android package names), contacts, times/dates/durations, locations (60+ known cities), and media (songs/videos). Validates entities before execution and resolves ambiguities. Supports Hindi script variants for app and city names.

## Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `JARVIS_ENTITY_ENABLE_APP_EXTRACTION` | true | Enable app name extraction |
| `JARVIS_ENTITY_ENABLE_CONTACT_EXTRACTION` | true | Enable contact extraction |
| `JARVIS_ENTITY_ENABLE_TIME_EXTRACTION` | true | Enable date/time extraction |
| `JARVIS_ENTITY_ENABLE_LOCATION_EXTRACTION` | true | Enable location extraction |
| `JARVIS_ENTITY_ENABLE_MEDIA_EXTRACTION` | true | Enable media extraction |

## Architecture
```
EntityExtractionService
  ├── AppExtractor       — 30+ known apps → package names, Hindi variants
  ├── ContactExtractor   — Regex patterns on call/message queries
  ├── TimeExtractor      — Absolute/relative/named times, dates, durations
  ├── LocationExtractor  — 60+ known cities, Hindi names
  ├── MediaExtractor     — Song/video names with platform detection
  └── EntityValidator    — Type-specific validation rules
```

## Code
```python
class AppExtractor:
    KNOWN_APPS = {"whatsapp": "com.whatsapp", "youtube": "com.google.android.youtube", ...}

    def extract(self, text) -> List[Entity]:
        for name in sorted(self.KNOWN_APPS, key=len, reverse=True):
            if name in text_lower:
                entities.append(Entity(type="app", value=KNOWN_APPS[name], confidence=0.95))
        for pattern in self.TRIGGER_PATTERNS:
            for match in re.finditer(pattern, text_lower):
                entities.append(Entity(type="app", value=match.group(1), confidence=0.7))
        return entities
```

## Location
`app/brain/` — entity extraction runs as a pipeline stage
