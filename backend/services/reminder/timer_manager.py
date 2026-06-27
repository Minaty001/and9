"""
AND9 — Timer Manager (Phase 10 of Refactor).

Manages Android countdown timers using the standard
AlarmClock.ACTION_SET_TIMER intent.

Maximum timer duration is 24 hours (configurable in
core/config.py via MAX_TIMER_SECONDS).
"""
import logging
from typing import Optional

from backend.core.and9_config import MAX_TIMER_SECONDS

logger = logging.getLogger(__name__)


class TimerManager:
    """Manages countdown timer creation."""

    @staticmethod
    def set_timer(duration_seconds: int,
                  label: str = "AND9 Timer") -> Optional[dict]:
        """Set a countdown timer.

        Args:
            duration_seconds: Duration in seconds.
            label: Optional label.

        Returns:
            Android Intent dict or None if invalid.
        """
        if not duration_seconds or duration_seconds <= 0:
            return None
        if duration_seconds > MAX_TIMER_SECONDS:
            return None

        return {
            "action": "android.intent.action.SET_TIMER",
            "length": duration_seconds,
            "label": label,
        }

    @staticmethod
    def format_duration(seconds: int) -> str:
        """Format seconds to human-readable string."""
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        parts = []
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if secs > 0 or not parts:
            parts.append(f"{secs} second{'s' if secs != 1 else ''}")
        return " ".join(parts)
