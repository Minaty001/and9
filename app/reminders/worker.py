"""
AND9 — Reminder Worker (Priority 3).

Background daemon thread that polls the DB every N seconds,
fires due reminders, and marks them as completed.

Recovery after restart:
    On startup the worker reads ALL pending reminders from storage.
    Any reminders with trigger_time <= now are fired immediately.
    This handles the case where the server was down when a reminder was due.

Notification mechanism:
    - Logs a REMINDER FIRED event (picked up by log aggregators)
    - Calls any registered callbacks (e.g., WebSocket push, SSE)
    - TODO: integrate with Android push / FCM for real device notifications

Usage:
    from app.reminders.worker import start_worker, stop_worker
    start_worker()   # call at app startup
    stop_worker()    # call at app shutdown (optional — thread is daemon)
"""
import logging
import threading
import time
from typing import Callable, List, Optional

from app.reminders import storage
from app.reminders.scheduler import get_engine

logger = logging.getLogger(__name__)

# Poll every 10 seconds
_POLL_INTERVAL = 10

_worker_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()

# Optional callbacks invoked when a reminder fires
# Signature: (reminder: dict) -> None
_fire_callbacks: List[Callable[[dict], None]] = []


def register_callback(fn: Callable[[dict], None]) -> None:
    """Register a callback to be called when a reminder fires."""
    _fire_callbacks.append(fn)


def _fire(reminder: dict) -> None:
    """Fire a single reminder notification."""
    rid = reminder["id"]
    title = reminder["title"]
    trigger_time = reminder["trigger_time"]

    # Mark fired first (prevent double-firing even if callback raises)
    storage.mark_fired(rid)
    logger.warning("REMINDER FIRED: #%d '%s' (was due: %s)", rid, title, trigger_time)

    for cb in _fire_callbacks:
        try:
            cb(reminder)
        except Exception as e:
            logger.error("Reminder callback error for #%d: %s", rid, e)


def _worker_loop() -> None:
    """Background loop: poll for due reminders and fire them."""
    logger.info("AND9 ReminderWorker started (poll every %ds).", _POLL_INTERVAL)

    # Recovery: fire any overdue reminders from before restart
    try:
        overdue = storage.get_due()
        if overdue:
            logger.info("ReminderWorker recovery: %d overdue reminders.", len(overdue))
            for rem in overdue:
                _fire(rem)
    except Exception as e:
        logger.error("ReminderWorker recovery error: %s", e)

    while not _stop_event.is_set():
        try:
            due = storage.get_due()
            for reminder in due:
                _fire(reminder)
        except Exception as e:
            logger.error("ReminderWorker poll error: %s", e)
        _stop_event.wait(_POLL_INTERVAL)

    logger.info("AND9 ReminderWorker stopped.")


def start_worker() -> None:
    """Start the background reminder worker thread.

    Idempotent — safe to call multiple times.
    Thread is a daemon so it won't block app shutdown.
    """
    global _worker_thread
    if _worker_thread and _worker_thread.is_alive():
        logger.debug("ReminderWorker already running.")
        return
    _stop_event.clear()
    _worker_thread = threading.Thread(
        target=_worker_loop,
        name="AND9-ReminderWorker",
        daemon=True,
    )
    _worker_thread.start()
    logger.info("AND9 ReminderWorker thread started.")


def stop_worker() -> None:
    """Signal the worker to stop. Does not block."""
    _stop_event.set()
    logger.info("AND9 ReminderWorker stop signalled.")
