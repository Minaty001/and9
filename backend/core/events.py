"""
app/core/events.py — Event & Reminder System.

Part of JARVIS Cognitive Architecture (Event System layer).
Stores events/reminders in Supabase, detects event-related
user intents, and returns due reminders in every response.

Supabase table: events
"""
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# ── Natural language time keywords (Hinglish) ─────────────────
_TIME_PATTERNS = [
    # "kal 5 baje"
    (r"\bkal\b.*?(\d{1,2})(?::(\d{2}))?\s*(baje|am|pm|AM|PM)?", "tomorrow"),
    # "aaj 3 pm"
    (r"\baaj\b.*?(\d{1,2})(?::(\d{2}))?\s*(baje|am|pm|AM|PM)?", "today"),
    # "in 30 minutes" / "30 min mein"
    (r"(\d+)\s*(minute|min|ghante|hour|din|day)s?\s*(mein|baad|later|after)", "relative"),
]

_REMINDER_KEYWORDS = [
    "remind", "reminder", "yaad dilana", "yaad dila", "yaad rakhna",
    "alert", "notify", "mat bhoolna", "bhool mat", "event", "meeting",
    "schedule", "appointment", "deadline", "due",
]


def is_event_request(text: str) -> bool:
    """Check if user text contains reminder or event-related keywords.

    Args:
        text: The user's input string to check.

    Returns:
        True if any reminder/event keyword is found in the text, False otherwise.
    """
    t = text.lower()
    return any(kw in t for kw in _REMINDER_KEYWORDS)


class EventSystem:
    """Manages reminders and scheduled events."""

    def __init__(self, memory):
        """Initialize the EventSystem with a shared Memory instance.

        Args:
            memory: The Memory instance providing Supabase client access
                    and in-memory fallback storage.
        """
        self._mem = memory

    def _q(self, table):
        """Get a Supabase table query builder if the connection is available.

        Args:
            table: The name of the Supabase table to query.

        Returns:
            A Supabase table query builder, or None if the database
            connection is not ready.
        """
        if not self._mem._ok:
            return None
        return self._mem._sb.table(table)

    def _safe(self, fn, default=None):
        """Execute a callable with exception safety and logging.

        Args:
            fn: The callable to execute.
            default: Value to return if the callable raises an exception.

        Returns:
            The result of fn() on success, or the default value on failure.
        """
        try:
            return fn()
        except Exception as e:
            logger.warning(f"EventSystem error: {e}")
            return default

    # ════════════════════════════════════════════════════════════
    # Event CRUD
    # ════════════════════════════════════════════════════════════

    def add_event(self, title: str, event_time: Optional[str] = None,
                  notes: str = "", repeat: str = "none") -> Optional[dict]:
        """Add a reminder/event.

        Args:
            title: What to remind about.
            event_time: ISO datetime string or None.
            notes: Extra context.
            repeat: 'none' | 'daily' | 'weekly'
        """
        q = self._q("events")
        if q is None:
            e = {"id": len(self._mem._mem.get("events", [])) + 1,
                 "title": title, "event_time": event_time,
                 "notes": notes, "repeat": repeat, "done": False,
                 "created_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()}
            self._mem._mem.setdefault("events", []).append(e)
            return e
        res = self._safe(lambda: q.insert({
            "title": title, "event_time": event_time,
            "notes": notes, "repeat": repeat, "done": False,
        }).execute(), None)
        return res.data[0] if res and res.data else None

    def get_upcoming_events(self, hours_ahead: int = 24) -> list:
        """Return events due in the next N hours."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        cutoff = (now + timedelta(hours=hours_ahead)).isoformat()
        now_str = now.isoformat()

        q = self._q("events")
        if q is None:
            evs = self._mem._mem.get("events", [])
            return [e for e in evs
                    if not e.get("done") and e.get("event_time")
                    and now_str <= e["event_time"] <= cutoff]

        res = self._safe(lambda: q.select("*")
                         .eq("done", False)
                         .gte("event_time", now_str)
                         .lte("event_time", cutoff)
                         .order("event_time")
                         .execute(), None)
        return res.data if res and res.data else []

    def get_due_events(self) -> list:
        """Return events that are due NOW (past event_time, not done)."""
        now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        q = self._q("events")
        if q is None:
            evs = self._mem._mem.get("events", [])
            return [e for e in evs
                    if not e.get("done") and e.get("event_time", "9999") <= now]

        res = self._safe(lambda: q.select("*")
                         .eq("done", False)
                         .lte("event_time", now)
                         .execute(), None)
        return res.data if res and res.data else []

    def mark_done(self, event_id: int) -> bool:
        """Mark an event as completed by its ID.

        Args:
            event_id: The unique identifier of the event to mark as done.

        Returns:
            True if the event was found and marked done, False otherwise.
        """
        q = self._q("events")
        if q is None:
            for e in self._mem._mem.get("events", []):
                if e["id"] == event_id:
                    e["done"] = True
                    return True
            return False
        res = self._safe(lambda: q.update({"done": True})
                         .eq("id", event_id).execute(), None)
        return bool(res and res.data)

    def get_all_events(self) -> list:
        """Retrieve all events ordered by event time (ascending).

        Returns:
            A list of all event records, or an empty list if none exist.
        """
        q = self._q("events")
        if q is None:
            return self._mem._mem.get("events", [])
        res = self._safe(lambda: q.select("*")
                         .order("event_time", desc=False).execute(), None)
        return res.data if res and res.data else []

    # ════════════════════════════════════════════════════════════
    # NLP helpers
    # ════════════════════════════════════════════════════════════

    def parse_event_from_text(self, text: str) -> dict:
        """Best-effort extraction of event details from natural language.

        Returns dict with 'title' and optionally 'event_time' (ISO string).
        """
        t = text.lower()

        # Try to detect relative time
        rel = re.search(r"(\d+)\s*(minute|min|ghante|hour|din|day)", t)
        if rel:
            n   = int(rel.group(1))
            unit = rel.group(2)
            if unit in ("minute", "min"):
                dt = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=n)
            elif unit in ("ghante", "hour"):
                dt = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=n)
            else:
                dt = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=n)
            event_time = dt.isoformat()
        elif "kal" in t:
            dt = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1)
            # Try to extract hour
            hr = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(baje|am|pm)?", t)
            if hr:
                h = int(hr.group(1))
                m = int(hr.group(2) or 0)
                if "pm" in (hr.group(3) or "") and h < 12:
                    h += 12
                dt = dt.replace(hour=h, minute=m, second=0, microsecond=0)
            event_time = dt.isoformat()
        elif "aaj" in t:
            dt = datetime.now(timezone.utc).replace(tzinfo=None)
            # Try to extract hour
            hr = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(baje|am|pm)?", t)
            if hr:
                h = int(hr.group(1))
                m = int(hr.group(2) or 0)
                if "pm" in (hr.group(3) or "") and h < 12:
                    h += 12
                dt = dt.replace(hour=h, minute=m, second=0, microsecond=0)
            event_time = dt.isoformat()
        else:
            event_time = None

        # Title = strip reminder keywords and time phrases
        title = text
        for kw in REMINDER_KEYWORDS_STRIP:
            title = re.sub(kw, "", title, flags=re.IGNORECASE)
        title = re.sub(r"\d+\s*(minute|min|ghante|hour|din|day)s?\s*(mein|baad|later)?", "", title)
        title = re.sub(r"\b(kal|aaj|abhi|please|jarvis|remind|me|mujhe)\b", "", title, flags=re.IGNORECASE)
        title = " ".join(title.split()).strip(" ,.-") or text[:60]

        return {"title": title, "event_time": event_time}

    def build_event_context(self) -> str:
        """Return upcoming events as a compact string for LLM context."""
        upcoming = self.get_upcoming_events(hours_ahead=48)
        due = self.get_due_events()
        if not upcoming and not due:
            return ""

        lines = ["═══ UPCOMING REMINDERS ═══"]
        for e in due:
            lines.append(f"  🔔 DUE NOW: {e['title']}")
        for e in upcoming[:5]:
            t = e.get("event_time", "")[:16].replace("T", " ")
            lines.append(f"  📅 {t} — {e['title']}")
        return "\n".join(lines)


REMINDER_KEYWORDS_STRIP = [
    r"remind\s+me\s+(to|about|ke|ki)?",
    r"yaad\s+dilana\s+(ki|ke)?",
    r"set\s+(a\s+)?(reminder|alarm)\s+(for|ke liye)?",
    r"reminder\s+(for|ke liye)?",
]
