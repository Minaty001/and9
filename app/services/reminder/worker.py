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
    - Enqueues to _alert_queue (polled by GET /api/reminder/alerts)
    - Tries Termux local notification (Android)

Usage:
    from app.services.reminder.worker import start_worker, stop_worker
    start_worker()   # call at app startup
    stop_worker()    # call at app shutdown (optional — thread is daemon)
"""
import logging
import json
import os
import subprocess
import shutil
import threading
import time
from typing import Callable, List, Optional, Set

from app.services.reminder import storage
from app.services.reminder.scheduler import get_engine

logger = logging.getLogger(__name__)

# Poll every 10 seconds
_POLL_INTERVAL = 10

_worker_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()
_worker_lock = threading.Lock()

# Optional callbacks invoked when a reminder fires
# Signature: (reminder: dict) -> None
_fire_callbacks: List[Callable[[dict], None]] = []
_fire_callbacks_lock = threading.Lock()

# Deduplication set to prevent double firing: contains (reminder_id, trigger_time)
_fired_reminders: Set[tuple] = set()

# ── In-app alert queue (polled by GET /api/reminder/alerts) ─────────
_alert_queue: List[dict] = []
_alert_queue_lock = threading.Lock()

# ── Worker state persistence (survives APK close/reopen) ────────────
_STATE_DIR = os.environ.get(
    "AND9_REMINDERS_STORAGE_DB",
    "/app/.jarvis_data",
)
_STATE_FILE = os.path.join(os.path.dirname(_STATE_DIR) if _STATE_DIR.endswith(".db") else _STATE_DIR, "worker_state.json")


def _save_worker_state() -> None:
    """Persist pending reminder IDs so we can detect missed firings."""
    try:
        pending = storage.list_all(status="pending")
        ids = [r["id"] for r in pending]
        os.makedirs(os.path.dirname(_STATE_FILE), exist_ok=True)
        with open(_STATE_FILE, "w") as f:
            json.dump({"pending_ids": ids, "timestamp": time.time()}, f)
    except Exception as e:
        logger.debug("Failed to save worker state: %s", e)


def _load_worker_state() -> Set[int]:
    """Load previously saved pending reminder IDs."""
    try:
        if not os.path.exists(_STATE_FILE):
            return set()
        with open(_STATE_FILE) as f:
            data = json.load(f)
        return set(data.get("pending_ids", []))
    except Exception as e:
        logger.debug("Failed to load worker state: %s", e)
        return set()


def _detect_missed_reminders() -> List[dict]:
    """Cross-check saved state vs current DB to find reminders missed during downtime."""
    saved_ids = _load_worker_state()
    if not saved_ids:
        return []
    # Get all pending reminders from DB
    try:
        all_pending = storage.list_all(status="pending")
        current_ids = {r["id"] for r in all_pending}
        # IDs that were pending before but are no longer in DB → likely missed
        vanished = saved_ids - current_ids
        if vanished:
            logger.warning(
                "Missed reminders detected: %d reminders may have fired during downtime.",
                len(vanished),
            )
        # Also fetch overdue reminders (already done in recovery path)
        return []
    except Exception as e:
        logger.error("Missed reminder detection error: %s", e)
        return []


def register_callback(fn: Callable[[dict], None]) -> None:
    """Register a callback to be called when a reminder fires."""
    with _fire_callbacks_lock:
        _fire_callbacks.append(fn)


def get_alerts() -> List[dict]:
    """Return queued reminder alerts (claim-based, each alert once).

    Called by the GET /api/reminder/alerts endpoint.
    Returns all queued alerts and clears them.
    """
    with _alert_queue_lock:
        alerts = list(_alert_queue)
        _alert_queue.clear()
    return alerts


def _try_termux_notify(title: str) -> None:
    """Send a Termux notification/speech/vibrate (Android-local, best-effort)."""
    if shutil.which("termux-notification"):
        try:
            subprocess.Popen(
                ["termux-notification", "-t", "⏰ JARVIS Reminder", "-c", title],
            )
        except Exception as e:
            logger.debug("termux-notification failed: %s", e)
    if shutil.which("termux-tts-speak"):
        try:
            subprocess.Popen(["termux-tts-speak", title])
        except Exception as e:
            logger.debug("termux-tts-speak failed: %s", e)
    if shutil.which("termux-vibrate"):
        try:
            subprocess.Popen(["termux-vibrate", "-d", "500"])
        except Exception as e:
            logger.debug("termux-vibrate failed: %s", e)


def _fire(reminder: dict) -> None:
    """Fire a single reminder notification."""
    rid = reminder["id"]
    title = reminder["title"]
    trigger_time = reminder["trigger_time"]

    # Deduplicate in-memory to prevent double firing in edge cases or double threads
    dedup_key = (rid, trigger_time)
    if dedup_key in _fired_reminders:
        logger.warning("Reminder #%d at %s already fired this session, skipping.", rid, trigger_time)
        return

    # Detect if the reminder is from v2 table (has user_id) or legacy table
    from_v2 = "user_id" in reminder

    # Mark fired first (prevent double-firing even if callback raises).
    # If mark_fired fails (e.g. DB lock) do NOT add the dedup key so
    # the reminder remains pending and can be retried on the next poll.
    try:
        storage.mark_fired(rid, from_v2=from_v2)
    except Exception as e:
        logger.error("Failed to mark reminder #%d as fired: %s", rid, e)
        return

    _fired_reminders.add(dedup_key)
    logger.warning("REMINDER FIRED: #%d '%s' (was due: %s)", rid, title, trigger_time)

    # Reschedule if recurring
    try:
        from app.services.reminder.recurring import RecurringEngine
        RecurringEngine().reschedule(reminder)
    except Exception as e:
        logger.error("Failed to reschedule recurring reminder #%d: %s", rid, e)

    # Enqueue for in-app alert polling
    with _alert_queue_lock:
        _alert_queue.append({
            "id": rid,
            "title": title,
            "trigger_time": trigger_time,
            "timestamp": time.time(),
        })

    # Try Termux local notification/speech (Android)
    _try_termux_notify(title)

    with _fire_callbacks_lock:
        callbacks_copy = list(_fire_callbacks)

    for cb in callbacks_copy:
        try:
            cb(reminder)
        except Exception as e:
            logger.error("Reminder callback error for #%d: %s", rid, e)


def _worker_loop() -> None:
    """Background loop: poll for due reminders and fire them."""
    logger.info("AND9 ReminderWorker started (poll every %ds).", _POLL_INTERVAL)

    # Recovery: fire any overdue reminders from before restart
    try:
        _detect_missed_reminders()
        overdue = storage.get_due()
        if overdue:
            logger.info("ReminderWorker recovery: %d overdue reminders.", len(overdue))
            for rem in overdue:
                _fire(rem)
    except Exception as e:
        logger.error("ReminderWorker recovery error: %s", e)

    # Save initial state snapshot
    _save_worker_state()

    poll_count = 0
    while not _stop_event.is_set():
        try:
            due = storage.get_due()
            for reminder in due:
                _fire(reminder)
            # Save state every 6 polls (~60s) to track pending IDs
            poll_count += 1
            if poll_count % 6 == 0:
                _save_worker_state()
        except Exception as e:
            logger.error("ReminderWorker poll error: %s", e)
        _stop_event.wait(_POLL_INTERVAL)

    # Save state on graceful stop
    _save_worker_state()
    logger.info("AND9 ReminderWorker stopped.")


def start_worker() -> None:
    """Start the background reminder worker thread.

    Idempotent — safe to call multiple times.
    Thread is a daemon so it won't block app shutdown.
    """
    global _worker_thread
    with _worker_lock:
        if _worker_thread and _worker_thread.is_alive():
            logger.debug("ReminderWorker already running.")
            return

        # If there's an old thread running/stopping, wait briefly for it to exit
        if _worker_thread:
            _stop_event.set()
            _worker_thread.join(timeout=1.0)

        _stop_event.clear()
        _worker_thread = threading.Thread(
            target=_worker_loop,
            name="AND9-ReminderWorker",
            daemon=True,
        )
        _worker_thread.start()
        logger.info("AND9 ReminderWorker thread started.")


def stop_worker() -> None:
    """Signal the worker to stop."""
    with _worker_lock:
        _stop_event.set()
        logger.info("AND9 ReminderWorker stop signalled.")
