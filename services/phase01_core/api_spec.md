# Core Service API Specification

## Overview

The Core Service is the central entry point for JARVIS. It manages lifecycle, sub-service registration, and provides the main `process()` pipeline.

## Endpoints

### `CoreService.initialize()`

Initializes the service, validates config, sets up logging and metrics.

**Input:** None (uses `CoreConfig` from constructor)

**Output:** `bool` — True if initialization succeeded

**Errors:** `InitializationError`, `ConfigError`

---

### `CoreService.process(query: str) -> ProcessingResult`

Process a user query through the full pipeline.

**Input:**
```json
{
    "query": "open whatsapp"
}
```

**Output:**
```json
{
    "query": "open whatsapp",
    "normalized_query": "open whatsapp",
    "intent": "open_app",
    "confidence": 0.97,
    "entities": {"app": "whatsapp"},
    "brain": "reflex",
    "stages": [
        {"stage": "received", "success": true, "time_ms": 0.5},
        {"stage": "normalized", "success": true, "time_ms": 0.8},
        {"stage": "intent_detected", "success": true, "confidence": 0.97, "time_ms": 15.2},
        {"stage": "executed", "success": true, "time_ms": 45.0}
    ],
    "total_time_ms": 61.5,
    "action": "open_app",
    "response": "Opened WhatsApp",
    "success": true,
    "timestamp": "2025-01-15T10:30:00"
}
```

**Errors:** `InvalidQueryError`, `ProcessingError`

---

### `CoreService.health() -> dict`

Service health check.

**Output:**
```json
{
    "status": "healthy",
    "service_name": "jarvis_core",
    "version": "1.0.0",
    "initialized": true,
    "uptime_seconds": 3600.0,
    "sub_services": {},
    "config": {
        "log_level": "INFO",
        "local_first": true,
        "deterministic": true
    }
}
```

---

### `CoreService.stats() -> dict`

Service metrics and statistics.

**Output:**
```json
{
    "service": "jarvis_core",
    "version": "1.0.0",
    "uptime_seconds": 3600.0,
    "initialized": true,
    "sub_services_count": 0,
    "metrics": {
        "counters": {"queries_processed": 42},
        "gauges": {"services_initialized": 1.0},
        "histograms": {}
    }
}
```

---

### `CoreService.shutdown()`

Gracefully shut down all services.

**Input:** None

**Output:** None (returns on completion)

---

## Request/Response Examples

### Example 1: Basic query
```python
result = await core.process("what time is it")
print(result.intent)       # IntentType.TIME
print(result.confidence)   # 0.95
print(result.response)     # "Current time is 02:30 PM"
```

### Example 2: Invalid query
```python
try:
    result = await core.process("")
except InvalidQueryError as e:
    print(e.message)  # "Query cannot be empty"
```

### Example 3: Health check
```python
health = await core.health()
if health["status"] != "healthy":
    print("Service degraded:", health.get("error"))
```
