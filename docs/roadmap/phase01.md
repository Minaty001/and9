# Phase 01: Project Vision & Core Rules

## Purpose
Foundation layer establishing shared models, error hierarchy, structured logging, and core service lifecycle. Provides `BrainResult`/`ProcessingResult` Pydantic models, a comprehensive `JarvisError` exception tree, JSON rotating-file logging, and the `CoreService` orchestration entry point that all other phases build upon.

## Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `JARVIS_CORE_LOG_LEVEL` | `INFO` | Logging level |
| `JARVIS_CORE_LOG_FORMAT` | `json` | `json` or `text` |
| `JARVIS_CORE_DETERMINISTIC_EXECUTION` | `true` | Deterministic mode |
| `JARVIS_CORE_LOCAL_FIRST` | `true` | Prefer local execution |

## Architecture
```
CoreService
  ├── initialize()      — Validate config, set up logging, metrics
  ├── process(query)    — Entry point → ProcessingResult
  ├── health()          — Collect sub-service health
  ├── stats()           — Metrics snapshot
  ├── shutdown()        — Graceful teardown
  └── register_service()/get_service() — Sub-service lifecycle
```

## Code
```python
class CoreService(ServiceBase):
    async def initialize(self):
        self._validate_config()
        self._logger = setup_logging(...)
        self._initialized = True

    async def process(self, query, **kwargs) -> ProcessingResult:
        if not query.strip(): raise InvalidQueryError()
        result = ProcessingResult(query=query)
        result.stages.append(PipelineStageResult(stage=RECEIVED, ...))
        result.response = f"Processing: '{query}'"
        return result

    def register_service(self, name, service: ServiceBase):
        self._sub_services[name] = service
```

## Location
`app/core/` — core models, errors, logging, and service lifecycle
