"""
app/core/timer.py — Server-side countdown timer service with SQLite persistence.

Manages timers with in-memory speed + SQLite durability.
Timers survive restarts via recover().
Supports pause/resume and API listing.

Schema:
    timers(
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        label          TEXT    NOT NULL,
        duration_secs  INTEGER NOT NULL,
        remaining_secs INTEGER,              -- NULL for active, set when paused
        end_time       REAL    NOT NULL,      -- Unix epoch
        status         TEXT    NOT NULL DEFAULT 'active'
                           CHECK(status IN ('active','paused','expired','cancelled')),
        created_at     REAL    NOT NULL,
        paused_at      REAL                  -- when it was last paused
    )
"""
import os
import time
import logging
import sqlite3
import threading
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

_timer_id_counter = 0
_id_lock = threading.Lock()

_DB_PATH = os.environ.get(
    "AND9_REMINDERS_STORAGE_DB",
    "/app/.jarvis_data/reminders_engine.db",
)

_TIMERS_SCHEMA = """
CREATE TABLE IF NOT EXISTS timers (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    label          TEXT    NOT NULL,
    duration_secs  INTEGER NOT NULL,
    remaining_secs INTEGER,
    end_time       REAL    NOT NULL,
    status         TEXT    NOT NULL DEFAULT 'active'
                         CHECK(status IN ('active','paused','expired','cancelled')),
    created_at     REAL    NOT NULL,
    paused_at      REAL
);
"""


def _next_id() -> int:
    """Thread-safe monotonically increasing timer identifier generator."""
    global _timer_id_counter
    with _id_lock:
        _timer_id_counter += 1
        return _timer_id_counter


@dataclass
class Timer:
    """An active countdown timer with alert and expiry tracking."""
    id: int
    label: str
    end_time: float
    duration_secs: int
    remaining_secs: Optional[int] = None   # set when paused
    alerted: bool = False
    status: str = "active"
    created_at: float = field(default_factory=time.time)
    paused_at: Optional[float] = None


class TimerService:
    """Thread-safe timer manager with in-memory + SQLite persistence.

    A background daemon thread wakes every second, marks expired timers
    as alert-ready, and prunes stale entries. Timers are persisted to the
    same SQLite DB as reminders for crash recovery.
    """

    def __init__(self, cleanup_age: int = 3600):
        """Initialise the timer service.

        Args:
            cleanup_age: Seconds after which expired timers are pruned.
        """
        self._timers: dict[int, Timer] = {}
        self._lock = threading.Lock()
        self._cleanup_age = cleanup_age
        self._init_db()
        self._worker = threading.Thread(target=self._run, daemon=True, name="timer-worker")
        self._worker.start()

    # ── DB init ─────────────────────────────────────────────────

    @staticmethod
    def _init_db():
        """Create the timers table if it doesn't exist."""
        try:
            os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
            with sqlite3.connect(_DB_PATH, check_same_thread=False) as con:
                con.execute(_TIMERS_SCHEMA)
                con.commit()
        except Exception as e:
            logger.warning("Could not init timers DB: %s", e)

    def _db_insert(self, t: Timer):
        """Insert a timer row into SQLite."""
        try:
            with sqlite3.connect(_DB_PATH, check_same_thread=False) as con:
                con.execute(
                    "INSERT INTO timers (id, label, duration_secs, remaining_secs, "
                    "end_time, status, created_at, paused_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (t.id, t.label, t.duration_secs, t.remaining_secs,
                     t.end_time, t.status, t.created_at, t.paused_at),
                )
                con.commit()
        except Exception as e:
            logger.error("DB insert failed for timer %d: %s", t.id, e)

    def _db_update_status(self, timer_id: int, status: str,
                          remaining_secs: Optional[int] = None,
                          end_time: Optional[float] = None,
                          paused_at: Optional[float] = None):
        """Update a timer's status and optional fields in SQLite."""
        try:
            with sqlite3.connect(_DB_PATH, check_same_thread=False) as con:
                fields = ["status = ?"]
                params: list = [status]
                if remaining_secs is not None:
                    fields.append("remaining_secs = ?")
                    params.append(remaining_secs)
                if end_time is not None:
                    fields.append("end_time = ?")
                    params.append(end_time)
                if paused_at is not None:
                    fields.append("paused_at = ?")
                    params.append(paused_at)
                params.append(timer_id)
                con.execute(
                    f"UPDATE timers SET {', '.join(fields)} WHERE id = ?",
                    tuple(params),
                )
                con.commit()
        except Exception as e:
            logger.error("DB update failed for timer %d: %s", timer_id, e)

    def _db_delete(self, timer_id: int):
        """Remove a timer row from SQLite."""
        try:
            with sqlite3.connect(_DB_PATH, check_same_thread=False) as con:
                con.execute("DELETE FROM timers WHERE id = ?", (timer_id,))
                con.commit()
        except Exception as e:
            logger.error("DB delete failed for timer %d: %s", timer_id, e)

    def _db_load_active(self) -> list[Timer]:
        """Load all active timers from SQLite."""
        timers: list[Timer] = []
        try:
            with sqlite3.connect(_DB_PATH, check_same_thread=False) as con:
                con.row_factory = sqlite3.Row
                rows = con.execute(
                    "SELECT * FROM timers WHERE status IN ('active', 'paused') "
                    "ORDER BY id ASC"
                ).fetchall()
                for row in rows:
                    t = Timer(
                        id=row["id"],
                        label=row["label"],
                        end_time=row["end_time"],
                        duration_secs=row["duration_secs"],
                        remaining_secs=row["remaining_secs"],
                        status=row["status"],
                        created_at=row["created_at"],
                        paused_at=row["paused_at"],
                    )
                    timers.append(t)
        except Exception as e:
            logger.warning("Could not load timers from DB: %s", e)
        return timers

    # ── Public API ──────────────────────────────────────────────

    def create_timer(self, duration_secs: int, label: str = "Alarm") -> dict:
        """Create a new countdown timer with DB persistence.

        Args:
            duration_secs: How long until the timer expires (> 0).
            label: Human-readable label for the timer.

        Returns:
            dict with keys: id, remaining, end_time, label
        """
        tid = _next_id()
        end = time.time() + duration_secs
        t = Timer(id=tid, label=label, end_time=end, duration_secs=duration_secs)
        with self._lock:
            self._timers[tid] = t
        self._db_insert(t)
        logger.info("Timer %d created: '%s' for %ds", tid, label, duration_secs)
        return {"id": tid, "remaining": duration_secs, "end_time": end, "label": label}

    def get(self, timer_id: int) -> Optional[dict]:
        """Return status dict for a timer, or None if it doesn't exist."""
        with self._lock:
            t = self._timers.get(timer_id)
            if not t:
                return None
            remaining = self._get_remaining(t)
            return {
                "id": t.id,
                "label": t.label,
                "remaining": remaining,
                "expired": remaining == 0 and t.status == "active",
                "alerted": t.alerted,
                "duration_secs": t.duration_secs,
                "status": t.status,
                "paused_at": t.paused_at,
            }

    def get_alerts(self) -> list[dict]:
        """Return timers that have just expired (claim-based, once per timer)."""
        now = time.time()
        alerts: list[dict] = []
        with self._lock:
            for t in list(self._timers.values()):
                if not t.alerted and now >= t.end_time and t.status == "active":
                    t.alerted = True
                    t.status = "expired"
                    self._db_update_status(t.id, "expired")
                    alerts.append({"id": t.id, "label": t.label})
        if alerts:
            logger.info("Timer alerts: %s", [a["id"] for a in alerts])
        return alerts

    def cancel(self, timer_id: int) -> bool:
        """Cancel and remove a running timer. Returns True if found."""
        with self._lock:
            if timer_id in self._timers:
                del self._timers[timer_id]
                self._db_update_status(timer_id, "cancelled")
                logger.info("Timer %d cancelled", timer_id)
                return True
        return False

    def pause(self, timer_id: int) -> Optional[dict]:
        """Pause an active timer.

        Args:
            timer_id: The timer to pause.

        Returns:
            Status dict for the paused timer, or None if not found / not active.
        """
        with self._lock:
            t = self._timers.get(timer_id)
            if not t or t.status != "active":
                logger.warning("Cannot pause timer %d: status=%s", timer_id, getattr(t, 'status', 'not_found'))
                return None
            remaining = int(t.end_time - time.time())
            if remaining <= 0:
                remaining = 0
            t.remaining_secs = remaining
            t.status = "paused"
            t.paused_at = time.time()
            self._db_update_status(timer_id, "paused",
                                   remaining_secs=remaining,
                                   paused_at=t.paused_at)
            logger.info("Timer %d paused with %ds remaining", timer_id, remaining)
            return {
                "id": t.id,
                "label": t.label,
                "remaining": remaining,
                "status": "paused",
                "duration_secs": t.duration_secs,
            }

    def resume(self, timer_id: int) -> Optional[dict]:
        """Resume a paused timer.

        Args:
            timer_id: The timer to resume.

        Returns:
            Status dict for the resumed timer, or None if not found / not paused.
        """
        with self._lock:
            t = self._timers.get(timer_id)
            if not t or t.status != "paused":
                logger.warning("Cannot resume timer %d: status=%s", timer_id, getattr(t, 'status', 'not_found'))
                return None
            remaining = t.remaining_secs or 0
            t.end_time = time.time() + remaining
            t.remaining_secs = None
            t.paused_at = None
            t.status = "active"
            self._db_update_status(timer_id, "active",
                                   remaining_secs=None,
                                   end_time=t.end_time,
                                   paused_at=None)
            logger.info("Timer %d resumed with %ds remaining", timer_id, remaining)
            return {
                "id": t.id,
                "label": t.label,
                "remaining": remaining,
                "status": "active",
                "duration_secs": t.duration_secs,
            }

    def get_all_active(self) -> list[dict]:
        """Return all non-terminal timers with their current state."""
        results: list[dict] = []
        with self._lock:
            for t in list(self._timers.values()):
                if t.status in ("active", "paused"):
                    remaining = self._get_remaining(t)
                    results.append({
                        "id": t.id,
                        "label": t.label,
                        "remaining": remaining,
                        "status": t.status,
                        "duration_secs": t.duration_secs,
                        "expired": remaining == 0 and t.status == "active",
                    })
        return sorted(results, key=lambda x: x["id"])

    def recover(self) -> int:
        """Reload active/paused timers from SQLite into memory.

        Called on startup to restore timers that survived a restart.
        Paused timers keep their remaining_secs; active timers that
        expired during downtime are marked as alerts.

        Returns:
            Number of timers recovered.
        """
        global _timer_id_counter
        db_timers = self._db_load_active()
        now = time.time()
        count = 0
        with self._lock:
            for t in db_timers:
                # Update global counter to avoid id collision
                with _id_lock:
                    if t.id > _timer_id_counter:
                        _timer_id_counter = t.id

                if t.status == "paused":
                    # Reconstruct end_time from remaining_secs
                    remaining = t.remaining_secs or 0
                    t.end_time = now + remaining
                    t.status = "active"
                    t.remaining_secs = None
                    t.paused_at = None
                    self._db_update_status(t.id, "active",
                                           remaining_secs=None,
                                           end_time=t.end_time,
                                           paused_at=None)
                    logger.info("Recovered paused timer %d → active (%ds left)", t.id, remaining)
                elif t.status == "active" and now >= t.end_time:
                    # Already expired during downtime
                    t.alerted = True
                    t.status = "expired"
                    self._db_update_status(t.id, "expired")
                    logger.info("Recovered timer %d as already expired", t.id)

                self._timers[t.id] = t
                count += 1

        if count:
            logger.info("Recovered %d timer(s) from SQLite", count)
        return count

    def active_count(self) -> int:
        """Number of timers currently in memory (alerted + pending)."""
        with self._lock:
            return len(self._timers)

    # ── Internal ────────────────────────────────────────────────

    @staticmethod
    def _get_remaining(t: Timer) -> int:
        """Compute remaining seconds for a timer."""
        if t.status == "paused":
            return t.remaining_secs or 0
        return max(0, int(t.end_time - time.time()))

    def _prune(self):
        """Remove timers older than cleanup_age to prevent memory leaks."""
        now = time.time()
        with self._lock:
            stale = [k for k, v in self._timers.items()
                     if now - v.created_at > self._cleanup_age]
            for k in stale:
                del self._timers[k]
            if stale:
                logger.debug("Pruned %d stale timer(s)", len(stale))

    def _run(self):
        """Background worker: wake every second, prune stale timers."""
        while True:
            time.sleep(1)
            self._prune()


# ── Module-level singleton (lazy, thread-safe) ─────────────────

_service: Optional[TimerService] = None
_service_lock = threading.Lock()


def get_timer_service() -> TimerService:
    """Return the shared TimerService singleton (created on first call).

    On first creation, automatically recovers persisted timers from SQLite.
    """
    global _service
    if _service is None:
        with _service_lock:
            if _service is None:
                _service = TimerService()
                _service.recover()
    return _service
