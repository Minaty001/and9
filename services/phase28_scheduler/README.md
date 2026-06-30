# Phase 28: Scheduler

## Overview

Manages reminders, recurring tasks, alarms, and calendar entries with conflict detection, natural language time parsing, and persistence.

## Architecture

```
User Commands
     │
     ▼
┌─────────────────────┐
│    TimeParser        │  ◄── Parses natural language time expressions
│                      │       "in 5 min", "tomorrow at 3pm", etc.
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  SchedulerEngine     │  ◄── Core scheduling with conflict detection
│                      │       Recurrence management, item lifecycle
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  ReminderManager     │  ◄── Create/snooze/dismiss reminders
│                      │       Active reminder tracking
└─────────┬───────────┘
          │
          ▼
    Notifications / Triggers
```

## Components

- **TimeParser**: Parses expressions like "in 5 minutes", "every weekday at 9am", "next Monday"
- **SchedulerEngine**: Core engine with conflict detection, recurrence computation
- **ReminderManager**: Create, snooze, dismiss reminders
- **SchedulerService**: ServiceBase wrapper

## Usage

```python
from services.phase28_scheduler import SchedulerService, ScheduledItem
from datetime import datetime, timezone, timedelta
svc = SchedulerService()
await svc.initialize()

# Create a reminder
rid = await svc.create_reminder("Meeting", datetime.now(timezone.utc) + timedelta(hours=1))

# Parse a time
expr = await svc.parse_time("tomorrow at 3pm")
print(expr.parsed_time)
```
