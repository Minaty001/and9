# Phase 34: Logging System

## Overview

Centralized logging with structured JSON output, multiple sinks (console, file), log levels, async buffering, and query interface.

## Architecture

```
Log Entry
     │
     ▼
┌──────────────────────┐
│ StructuredFormatter   │  ◄── JSON format with trace_id, correlation_id
└─────────┬────────────┘
          │
     ┌────┴────┐
     ▼         ▼
┌────────┐ ┌────────┐
│Console │ │ File   │  ◄── File rotation at max_file_size_mb
│ Sink   │ │ Sink   │      Retention: file_retention_days
└────────┘ └────────┘
     │         │
     └────┬────┘
          ▼
┌──────────────────────┐
│ LogBuffer             │  ◄── Async buffering with auto-flush
│ (Async Buffer)        │      at batch_size
└──────────────────────┘
          │
          ▼
┌──────────────────────┐
│ LoggingService        │  ◄── Query interface, log levels, sink mgmt
│ (ServiceBase)         │
└──────────────────────┘
```

## Components

- **StructuredFormatter**: Formats LogEntry as JSON with trace_id, correlation_id, timestamp in ISO format. Supports text format as well.
- **ConsoleSink**: Writes to stdout/stderr based on log level.
- **FileSink**: Writes to file with rotation at max_file_size_mb. Cleans up rotated files older than retention_days.
- **LogBuffer**: Thread-safe async buffer. Auto-flushes at batch_size when batch logging is enabled.
- **LoggingService**: ServiceBase wrapper with debug/info/warn/error/fatal shorthands. Query with multiple filters (level, time, service, trace_id, etc.).

## Usage

```python
from services.phase34_logging import LoggingService, LogQuery
svc = LoggingService()
await svc.initialize()

await svc.info("System started", module="main")
await svc.error("Request failed", metadata={"status": 500})

# Query logs
result = await svc.query(LogQuery(levels=["ERROR"], search="timeout"))
for entry in result.entries:
    print(f"{entry.timestamp}: {entry.message}")
```

## Test Coverage

22+ tests covering formatter, sinks, buffer, and service wrapper.
