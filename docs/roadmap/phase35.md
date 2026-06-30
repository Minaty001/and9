# Phase 35: Logging

## Purpose
Query logging and debug mode for the AND9 pipeline. `QueryLogger` records every request through the pipeline with full context including raw query, normalized query, detected intent, parameters, action, payload, brain module, timing, and success/error status. `QueryLog` represents a single logged entry with serialization. Debug mode (`AND9_DEBUG=1`) prints a formatted debug panel for every request showing the processing pipeline step by step. Provides a singleton logger for app-wide access.

## Architecture
```
QueryLogger
  ├── log(raw_query, normalized_query, intent, parameters, action, payload, brain, time_ms, success, error) → QueryLog
  ├── get_recent(limit) → List[Dict]
  ├── get_stats() → {total_queries, failed_queries, success_rate, recent}
  └── clear()

QueryLog
  └── to_dict() → serializable dict

get_logger() → QueryLogger singleton
is_debug_enabled() → bool
```

## Code
```python
class QueryLog:
    def __init__(self, raw_query, normalized_query="", intent="", parameters=None, action="", payload=None,
                 brain="", execution_time_ms=0.0, success=True, error=""):
        self.timestamp = datetime.now().isoformat()
        self.raw_query = raw_query
        self.normalized_query = normalized_query
        self.intent = intent
        self.parameters = parameters or {}
        self.action = action
        self.payload = payload or {}
        self.brain = brain
        self.execution_time_ms = execution_time_ms
        self.success = success
        self.error = error

class QueryLogger:
    def log(self, **kwargs) -> QueryLog:
        entry = QueryLog(**kwargs)
        self.logs.append(entry)
        if len(self.logs) > self.max_entries:
            self.logs = self.logs[-self.max_entries:]
        if _DEBUG_ENABLED: _print_debug(entry)
        return entry

    def get_stats(self) -> dict:
        total = len(self.logs)
        failed = sum(1 for log in self.logs if not log.success)
        return {"total_queries": total, "failed_queries": failed,
                "success_rate": f"{(total-failed)/total*100:.1f}%" if total else "N/A"}

def _print_debug(log):
    print(f"┌─ AND9 DEBUG ──────────┐\\n│ QUERY: {log.raw_query}\\n│ INTENT: {log.intent}\\n│ TIME: {log.execution_time_ms:.1f}ms\\n└────────────────────────┘")
```

## Location
`app/core/and9_logger.py` — query logger, debug mode, singleton logger accessor
