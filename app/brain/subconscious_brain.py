"""
AND9 — Subconscious Brain: Pattern Learning & Habit Detection.

The Subconscious Brain operates in the background, tracking user
actions and detecting two types of patterns:

  1. Time-based frequency patterns:
     Actions that the user performs repeatedly at the same time
     of day or on the same day of week.
     Example: "You usually open WhatsApp at 9 AM (5 times) 🤔"

  2. Sequential action patterns:
     Actions that frequently follow other actions.
     Example: "After opening YouTube, you usually play music (3 times)"

Pattern detection requires minimum thresholds to avoid false positives:
  - Time-based: 3+ occurrences at the same hour
  - Sequential: 2+ occurrences of the same follow

The subconscious brain maintains an in-memory action history (max 1000
records). In production, this should be persisted to disk or a database
for cross-session pattern learning.
"""
import logging
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any

from app.brain.brain_types import BrainResult

logger = logging.getLogger(__name__)

# Minimum occurrences to consider a time-based pattern significant
_TIME_PATTERN_THRESHOLD = 3
# Minimum occurrences to consider a sequential pattern significant
_SEQUENCE_PATTERN_THRESHOLD = 2
# Maximum action history entries to keep in memory
_MAX_HISTORY_SIZE = 1000


@dataclass
class PatternRecord:
    """A single recorded user action in the subconscious history.

    Attributes:
        action: The action type string (e.g., "LAUNCH_APP", "CALL").
        intent: The IntentType that was detected.
        query: The original user query.
        timestamp: When the action occurred (ISO format).
        hour: Hour of the day (0-23) for time-based pattern analysis.
        day_of_week: Day name for weekday-pattern analysis.
        app_name: Optional app name extracted from open_app intents.
    """
    action: str
    intent: str
    query: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    hour: int = field(default_factory=lambda: datetime.now().hour)
    day_of_week: str = field(
        default_factory=lambda: datetime.now().strftime("%A")
    )
    app_name: Optional[str] = None


class SubconsciousBrain:
    """AND9's pattern learning and habit detection engine.

    Tracks user actions over time and surfaces detected patterns
    to enable predictive assistance and routine automation.

    Patterns are purely in-memory during this session. The class
    is designed to be extended with persistent storage (SQLite,
    Supabase, etc.) for cross-session learning.

    Attributes:
        history: List of PatternRecord entries (max 1000).
        enable_learning: If False, disables pattern recording.
    """

    def __init__(self, enable_learning: bool = True):
        self.history: List[PatternRecord] = []
        self.enable_learning = enable_learning

    def record_action(self, result: BrainResult, query: str) -> None:
        """Record a user action for pattern learning.

        Stores the action in the in-memory history. Drops the oldest
        entry when history exceeds _MAX_HISTORY_SIZE.

        Args:
            result: The BrainResult from executing the action.
            query: The original user query before normalization.
        """
        if not self.enable_learning:
            return
        if not result.action:
            return

        now = datetime.now()
        record = PatternRecord(
            action=result.action,
            intent=result.intent.value if result.intent else "unknown",
            query=query,
            timestamp=now.isoformat(),
            hour=now.hour,
            day_of_week=now.strftime("%A"),
            app_name=result.parameters.get("app_name")
            if result.parameters else None,
        )

        self.history.append(record)

        # Trim to max size
        if len(self.history) > _MAX_HISTORY_SIZE:
            self.history = self.history[-_MAX_HISTORY_SIZE:]

        logger.debug("Recorded action: %s at hour %d", result.action, now.hour)

    def get_pattern(self, hour: Optional[int] = None,
                    day: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Detect time-based frequency patterns.

        Analyzes action history to find actions the user frequently
        performs at a given time of day or day of week.

        Args:
            hour: Hour to check (default: current hour).
            day: Day name to check (default: current day).

        Returns:
            Dict with pattern info:
              - action: Most frequent action at this time
              - count: How many times it occurred
              - total: Total actions recorded at this time
              - suggestion: Natural language suggestion
            Returns None if no pattern meets the threshold or if
            history is empty.
        """
        if not self.history:
            return None

        now = datetime.now()
        hour = hour if hour is not None else now.hour
        day = day or now.strftime("%A")

        # Filter by both hour and day for more specific patterns
        matching = [
            r for r in self.history
            if r.hour == hour and r.day_of_week == day
        ]

        if not matching:
            return None

        # Find the most common action at this time
        counter = Counter(r.action for r in matching)
        most_common = counter.most_common(1)

        if most_common and most_common[0][1] >= _TIME_PATTERN_THRESHOLD:
            action, count = most_common[0]

            # Build a human-readable suggestion
            hour_display = hour if hour <= 12 else hour - 12
            period = "AM" if hour < 12 else "PM"
            if hour == 0:
                hour_display = 12
            elif hour == 12:
                hour_display = 12

            suggestion = (
                f"Aap generally {hour_display}:00 {period} {day} ko "
                f"'{action}' karte ho ({count} baar) 🤔"
            )

            return {
                "action": action,
                "count": count,
                "total": len(matching),
                "hour": hour,
                "day": day,
                "suggestion": suggestion,
            }

        return None

    def get_sequential_pattern(self, last_action: str) -> Optional[Dict[str, Any]]:
        """Detect patterns where one action typically follows another.

        Analyzes the ordered action history to find actions that
        commonly follow a given action.

        Args:
            last_action: The action to check for followers.

        Returns:
            Dict with:
              - next_action: Most common action that follows
              - count: How many times this sequence was observed
              - suggestion: Natural language suggestion
            Returns None if no sequential pattern meets the threshold.
        """
        if len(self.history) < 2:
            return None

        # Find all occurrences of the last action and what follows
        followers = []
        for i, record in enumerate(self.history):
            if record.action == last_action and i + 1 < len(self.history):
                followers.append(self.history[i + 1].action)

        if not followers:
            return None

        # Find the most common follower
        counter = Counter(followers)
        most_common = counter.most_common(1)

        if most_common and most_common[0][1] >= _SEQUENCE_PATTERN_THRESHOLD:
            next_action, count = most_common[0]
            return {
                "next_action": next_action,
                "count": count,
                "total_occurrences": len(followers),
                "suggestion": (
                    f"After '{last_action}', you usually "
                    f"'{next_action}' ({count} times) 🔄"
                ),
            }

        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get summary statistics of recorded action history.

        Returns:
            Dict with:
              - total_actions: Number of recorded actions
              - top_actions: Top 10 most frequent actions
              - unique_actions: Count of distinct action types
              - top_hours: Top 5 most active hours
              - top_days: Top 5 most active days
        """
        if not self.history:
            return {
                "total_actions": 0,
                "top_actions": [],
                "unique_actions": 0,
                "top_hours": [],
                "top_days": [],
            }

        action_counter = Counter(r.action for r in self.history)
        hour_counter = Counter(r.hour for r in self.history)
        day_counter = Counter(r.day_of_week for r in self.history)

        return {
            "total_actions": len(self.history),
            "top_actions": action_counter.most_common(10),
            "unique_actions": len(action_counter),
            "top_hours": hour_counter.most_common(5),
            "top_days": day_counter.most_common(5),
        }

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent action history as serializable dicts.

        Args:
            limit: Maximum number of recent records to return.

        Returns:
            List of action record dicts, most recent first.
        """
        recent = self.history[-limit:] if self.history else []
        return [
            {
                "action": r.action,
                "intent": r.intent,
                "query": r.query,
                "timestamp": r.timestamp,
                "hour": r.hour,
                "day": r.day_of_week,
                "app_name": r.app_name,
            }
            for r in reversed(recent)
        ]
