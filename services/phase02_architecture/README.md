# Phase 2: System Architecture

## Overview

Event-driven communication and dependency inversion between JARVIS modules. Separates reasoning from execution through a publish/subscribe event bus and centralized module registry.

## Components

### EventBus
In-process pub/sub for decoupled communication:
```python
bus = EventBus()

@bus.on("query.received")
async def handle_query(event):
    print(f"Processing: {event.payload}")

await bus.emit(Event("query.received", {"text": "hello"}))
```

Features:
- Priority ordering (CRITICAL, HIGH, NORMAL, LOW, BACKGROUND)
- Wildcard handlers (`*` for all events)
- Handler error isolation
- Timing metrics per handler

### ModuleRegistry
Central registry for all JARVIS modules:
```python
registry = ModuleRegistry()
registry.register("tokenizer", tokenizer_service, dependencies=["config"])
registry.register("intent", intent_service, dependencies=["tokenizer"])
deps = registry.resolve_dependencies("intent")  # ["config", "tokenizer", "intent"]
```

Features:
- Dependency resolution (topological sort)
- Circular dependency detection
- Status lifecycle tracking
- Filtered listing

### ArchitectureService
Coordinates registry + event bus:
```python
arch = ArchitectureService()
await arch.initialize()
await arch.register_module("my_mod", my_service)
await arch.emit_event("my.event", {"data": 123})
```

## Configuration

Environment variables prefixed with `JARVIS_ARCH_`:

| Variable | Default | Description |
|----------|---------|-------------|
| `JARVIS_ARCH_EVENT_QUEUE_MAX_SIZE` | 1000 | Max events in queue |
| `JARVIS_ARCH_MAX_MODULES` | 50 | Maximum registered modules |
| `JARVIS_ARCH_ENABLE_EVENT_LOGGING` | true | Log all events |

## Integration Guide

1. Create the ArchitectureService
2. Initialize it
3. Register modules with their dependencies
4. Subscribe handlers to events
5. Emit events to trigger processing

```python
from services.phase02_architecture import ArchitectureService
arch = ArchitectureService()
await arch.initialize()

@arch.subscribe("query.processed", my_handler)
await arch.emit_event("query.processed", {"query": "hello"})
```
