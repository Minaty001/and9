"""
AND9 — Alarm Manager (Phase 8 of Refactor).

Manages Android alarm creation using the standard
AlarmClock.ACTION_SET_ALARM intent. Always prefers the
Android intent API over web-based lookup.

The AlarmManager wraps IntentExecutor.set_alarm() and
provides a clean interface for the action layer.
"""
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class AlarmManager:
    """Manages alarm creation and metadata."""

    @staticmethod
    def set_alarm(hour: int, minute: int,
                  label: Optional[str] = None) -> Optional[dict]:
        """Set an alarm via Android Intent or IntentExecutor.

        Args:
            hour: Hour in 24h format (0-23).
            minute: Minute (0-59).
            label: Optional label.

        Returns:
            Android Intent dict or None on failure.
        """
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return None

        label = label or "AND9 Alarm"

        try:
            from app.skills.android.intent_executor import IntentExecutor
            result = IntentExecutor.set_alarm(hour, minute, label)
            if result:
                return result
        except Exception as e:
            logger.debug("IntentExecutor.set_alarm failed: %s", e)

        # Direct Android intent fallback
        return {
            "action": "android.intent.action.SET_ALARM",
            "hour": hour,
            "minute": minute,
            "label": label,
        }

    @staticmethod
    def format_time(hour: int, minute: int) -> str:
        """Format 24h time to 12h display string."""
        period = "AM" if hour < 12 else "PM"
        display_hour = hour if hour <= 12 else hour - 12
        if display_hour == 0:
            display_hour = 12
        return f"{display_hour}:{minute:02d} {period}"
