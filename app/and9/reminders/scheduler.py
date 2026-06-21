"""
AND9 — Reminder Scheduler (Phase 9 of Refactor).

Manages reminder scheduling with optional persistence via
the EventSystem. Reminders can be absolute (7 pm meeting)
or relative (after 10 minutes).

The scheduler stores reminders in the EventSystem database
for cross-session retention and alerting.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Any

logger = logging.getLogger(__name__)


class ReminderScheduler:
    """Schedule and manage reminders."""

    @staticmethod
    def schedule(trigger_at: dict, label: str,
                 events_sys: Optional[Any] = None) -> dict:
        """Schedule a reminder.

        Args:
            trigger_at: Dict with time info:
                - {"type": "absolute", "hour": N, "minute": N}
                - {"type": "relative", "seconds": N}
            label: Reminder title.
            events_sys: Optional EventSystem for persistence.

        Returns:
            Dict with result info including persistence status.
        """
        now = datetime.now()
        reminder_time = None

        if trigger_at.get("type") == "absolute":
            reminder_time = now.replace(
                hour=trigger_at["hour"],
                minute=trigger_at["minute"],
                second=0, microsecond=0,
            )
            if reminder_time < now:
                reminder_time += timedelta(days=1)

        elif trigger_at.get("type") == "relative":
            reminder_time = now + timedelta(seconds=trigger_at.get("seconds", 0))

        persisted = False
        if events_sys and reminder_time:
            try:
                events_sys.add_event(
                    event_type="reminder",
                    timestamp=reminder_time.timestamp(),
                    metadata={
                        "title": label,
                        "time": reminder_time.isoformat(),
                    },
                )
                persisted = True
            except Exception as e:
                logger.error("Failed to persist reminder: %s", e)

        return {
            "trigger_at": trigger_at,
            "label": label,
            "reminder_time": reminder_time.isoformat() if reminder_time else None,
            "persisted": persisted,
        }

    @staticmethod
    def extract_label(query: str) -> Optional[str]:
        """Extract clean reminder label from a query.

        Strips action keywords and time expressions, leaving
        only the meaningful label text.
        """
        import re
        q = query.lower().strip()

        for word in [
            "set alarm", "set reminder", "set timer",
            "alarm", "reminder", "timer",
            "remind me to", "remind me about", "remind me for",
            "remind me", "yaad dilana", "yaad dila",
        ]:
            q = q.replace(word, " ")

        q = re.sub(
            r'(?:after|in|baad|me|ke\s*baad|for|at|ko)\s+'
            r'\d+(?:\.\d+)?\s*(?:second|sec|minute|min|hour|hr)s?',
            '', q
        )
        q = re.sub(r'\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM|baje)?', '', q)

        noise = ["minute", "minutes", "second", "seconds", "hour", "hours",
                 "sec", "min", "hr", "hrs", "baad", "me", "ke", "ka", "ki",
                 "ko", "se", "par", "pe", "after", "in", "for", "at",
                 "baje", "bajkar"]
        for w in noise:
            q = q.replace(f" {w} ", " ")

        q = re.sub(r'\s+', ' ', q).strip()
        return q if q and len(q) > 1 else None
