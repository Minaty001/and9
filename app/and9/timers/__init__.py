"""AND9 — Timer Manager.

Manages Android timer intents (via AlarmClock.ACTION_SET_TIMER).
For server-side countdown timers, see app.core.timer.
"""

from .timer_manager import TimerManager

__all__ = ["TimerManager"]
