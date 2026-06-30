# Phase 28: Scheduler

## Purpose
Reminder scheduling with SQLite persistence and background worker thread. `ReminderEngine` provides the public API to add, cancel, list, and query reminders. Storage is delegated to a SQLite-backed persistence layer. The background `Worker` daemon polls for due reminders every 10 seconds, fires them, and marks them as completed. Supports recovery on restart — any missed reminders are fired immediately.

## Architecture
```
ReminderEngine (scheduler.py)
  ├── add(title, trigger_time) → int (row id)
  ├── cancel(reminder_id) → bool
  ├── get_upcoming(limit) → List[Dict]
  ├── get_due() → List[Dict]
  ├── mark_fired(reminder_id)
  └── list_all(status) → List[Dict]

ReminderScheduler (and9_scheduler.py)
  └── Legacy adapter wrapping ReminderEngine

Worker (worker.py)
  ├── start_worker() — background daemon thread
  ├── stop_worker()
  └── Polls every 10s, fires due reminders, enqueues to alert queue

Storage (storage.py)
  └── SQLite persistence layer
```

## Code
```python
class ReminderEngine:
    def add(self, title, trigger_time) -> int:
        rid = storage.add(title, trigger_time)
        return rid

    def get_upcoming(self, limit=10) -> List[Dict]:
        return storage.get_upcoming(limit)

# Worker — background thread
def _worker_loop():
    while not _stop_event.is_set():
        due = storage.get_due()
        for reminder in due:
            _fire(reminder)
            storage.mark_fired(reminder["id"])
        _stop_event.wait(_POLL_INTERVAL)

def start_worker():
    thread = threading.Thread(target=_worker_loop, daemon=True)
    thread.start()
```

## Location
`app/services/reminder/` — scheduler engine, legacy adapter, worker, storage, alarm/timer managers
