# Phase 1: Project Vision & Core Rules

## Overview

The foundation of JARVIS — an AI Operating System, not just a chatbot. This phase establishes the design principles, shared models, error hierarchy, logging, and core service lifecycle that all other phases build upon.

## Design Principles

| Principle | Description |
|-----------|-------------|
| **Modularity** | Every component is independently testable and replaceable |
| **Local-first** | All core functionality works offline without cloud dependencies |
| **Deterministic** | Same input always produces the same output |
| **Security** | All inputs validated, no injection surfaces |
| **Logging** | Structured JSON logs with rotation |
| **Testing** | Unit tests for every public method |

## Architecture

```
CoreService
  ├── initialize()    — Validate config, set up logging, metrics
  ├── process(query)  — Entry point for query processing
  ├── health()        — Service health check
  ├── stats()         — Metrics and statistics
  ├── shutdown()      — Graceful teardown
  └── register_service() — Register sub-services
```

## Models

### `BrainResult`
Standard brain output compatible with existing AND9:

```python
BrainResult(
    response="Opened WhatsApp",
    action="open_app",
    payload={"app": "whatsapp"},
    brain=BrainType.REFLEX,
    intent=IntentType.OPEN_APP,
    execution_time_ms=45.2,
    success=True
)
```

### `ProcessingResult`
Full pipeline trace:

```python
ProcessingResult(
    query="open whatsapp",
    normalized_query="open whatsapp",
    intent=IntentType.OPEN_APP,
    confidence=0.97,
    entities={"app": "whatsapp"},
    stages=[...],
    total_time_ms=120.5,
    response="Opened WhatsApp"
)
```

## Error Hierarchy

```
JarvisError
  ├── ServiceError
  │   ├── InitializationError
  │   ├── ShutdownError
  │   └── HealthCheckError
  ├── ProcessingError
  │   ├── TimeoutError
  │   └── PipelineError
  ├── ValidationError
  │   ├── InvalidQueryError
  │   └── InvalidParameterError
  └── ConfigError
      ├── MissingConfigError
      └── InvalidConfigError
```

## Configuration

Environment variables prefixed with `JARVIS_CORE_`:

| Variable | Default | Description |
|----------|---------|-------------|
| `JARVIS_CORE_LOG_LEVEL` | `INFO` | Logging level |
| `JARVIS_CORE_LOG_FORMAT` | `json` | `json` or `text` |
| `JARVIS_CORE_DETERMINISTIC_EXECUTION` | `true` | Deterministic mode |
| `JARVIS_CORE_LOCAL_FIRST` | `true` | Prefer local execution |

## Usage

```python
import asyncio
from services.phase01_core import CoreService, CoreConfig

async def main():
    config = CoreConfig(log_level="DEBUG")
    core = CoreService(config)
    await core.initialize()

    result = await core.process("hello jarvis")
    print(result.response)

    health = await core.health()
    print(health)

    await core.shutdown()

asyncio.run(main())
```

## API Specification

See [api_spec.md](./api_spec.md) for full API reference.

## Integration Guide

1. Install dependencies: `pip install pydantic`
2. Import the service: `from services.phase01_core import CoreService`
3. Configure: `CoreConfig(log_level="DEBUG")`
4. Initialize: `await core.initialize()`
5. Process queries: `await core.process("your query")`
6. Shutdown: `await core.shutdown()`
