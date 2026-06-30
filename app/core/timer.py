"""
app/core/timer.py — Server-side countdown timer service.

Manages in-memory timers with a background worker that marks them as
expired. The frontend polls /api/timer/alerts to discover expirations.

No database dependency — timers are ephemeral and lost on restart.
For persistent reminders see events.py + Supabase.
"""
import time
import logging
import threading
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

_timer_id_counter = 0
_id_lock = threading.Lock()


def _next_id() -> int:
    global _timer_id_counter
    with _id_lock:
        _timer_id_counter += 1
        return _timer_id_counter


@dataclass
class Timer:
    id: int
    label: str
    end_time: float
    duration_secs: int
    alerted: bool = False
    created_at: float = field(default_factory=time.time)


class TimerService:
    """Thread-safe in-memory timer manager.

    A background daemon thread wakes every second and marks expired
    timers as alert-ready. The frontend discovers these via polling.
    Timers older than ``cleanup_age`` seconds are pruned automatically.
    """

    def __init__(self, cleanup_age: int = 3600):
        self._timers: dict[int, Timer] = {}
        self._lock = threading.Lock()
        self._cleanup_age = cleanup_age
        self._worker = threading.Thread(target=self._run, daemon=True, name="timer-worker")
        self._worker.start()

    # ── Public API ──────────────────────────────────────────────

    def create_timer(self, duration_secs: int, label: str = "Alarm") -> dict:
        """Create a new countdown timer.

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
        logger.info("Timer %d created: '%s' for %ds", tid, label, duration_secs)
        return {"id": tid, "remaining": duration_secs, "end_time": end, "label": label}

    def get(self, timer_id: int) -> Optional[dict]:
        """Return status dict for a timer, or None if it doesn't exist."""
        with self._lock:
            t = self._timers.get(timer_id)
            if not t:
                return None
            remaining = max(0, int(t.end_time - time.time()))
            return {
                "id": t.id,
                "label": t.label,
                "remaining": remaining,
                "expired": remaining == 0,
                "alerted": t.alerted,
                "duration_secs": t.duration_secs,
            }

    def get_alerts(self) -> list[dict]:
        """Return timers that have just expired (claim-based, once per timer).

        The frontend calls this every ~1 s. Each expired timer is returned
        exactly once; subsequent calls will not include it until a new
        timer is created.
        """
        now = time.time()
        alerts: list[dict] = []
        with self._lock:
            for t in list(self._timers.values()):
                if not t.alerted and now >= t.end_time:
                    t.alerted = True
                    alerts.append({"id": t.id, "label": t.label})
        if alerts:
            logger.info("Timer alerts: %s", [a["id"] for a in alerts])
        return alerts

    def cancel(self, timer_id: int) -> bool:
        """Cancel and remove a running timer. Returns True if found."""
        with self._lock:
            if timer_id in self._timers:
                del self._timers[timer_id]
                logger.info("Timer %d cancelled", timer_id)
                return True
        return False

    def active_count(self) -> int:
        """Number of timers currently in memory (alerted + pending)."""
        with self._lock:
            return len(self._timers)

    # ── Internal ────────────────────────────────────────────────

    def _prune(self):
        """Remove timers older than cleanup_age to prevent memory leaks."""
        now = time.time()
        with self._lock:
            stale = [k for k, v in self._timers.items() if now - v.created_at > self._cleanup_age]
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
    """Return the shared TimerService singleton (created on first call)."""
    global _service
    if _service is None:
        with _service_lock:
            if _service is None:
                _service = TimerService()
    return _service
