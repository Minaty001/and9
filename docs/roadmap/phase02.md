# Phase 02: System Architecture

## Purpose
Event-driven communication and dependency inversion between JARVIS modules. Provides an in-process publish/subscribe `EventBus` with priority ordering (CRITICAL→BACKGROUND) and a `ModuleRegistry` with topological dependency resolution and circular-detection, enabling decoupled module interactions.

## Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `JARVIS_ARCH_EVENT_QUEUE_MAX_SIZE` | 1000 | Max events in queue |
| `JARVIS_ARCH_MAX_MODULES` | 50 | Maximum registered modules |
| `JARVIS_ARCH_ENABLE_EVENT_LOGGING` | true | Log all events |

## Architecture
```
ArchitectureService
  ├── bus: EventBus          — pub/sub, priority, handler isolation
  ├── registry: ModuleRegistry — registration, dependency resolution
  ├── initialize()/shutdown()
  ├── register_module(name, service, deps)
  ├── emit_event(type, payload) → handler count
  └── subscribe(event_type, handler)
```

## Code
```python
class EventBus:
    async def emit(self, event: Event) -> int:
        handlers = list(self._wildcard_handlers)
        if event.type in self._handlers: handlers += self._handlers[event.type]
        for handler in handlers:
            try: await handler(event)
            except Exception: self._failed_events += 1

class ModuleRegistry:
    def register(self, name, service, dependencies=None) -> ModuleRegistration:
        if name in self._modules: raise ModuleRegistrationError(...)
        self._modules[name] = ModuleInfo(...)

    def resolve_dependencies(self, name) -> List[str]:
        # DFS topological sort with circular detection
```

## Location
`app/brain/` — event bus and module registry underpin all brain modules
