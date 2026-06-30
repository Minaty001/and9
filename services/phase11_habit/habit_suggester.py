"""
Phase 11 — Habit Suggester.

Ranks habit patterns by relevance to current context and returns
top suggestions for user approval.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from .config import HabitConfig
from .models import HabitPattern, HabitSuggestion
from .habit_tracker import HabitTracker

logger = logging.getLogger(__name__)


class HabitSuggester:
    """Generates ranked habit suggestions based on current context.

    Usage:
        suggester = HabitSuggester(tracker)
        suggestions = suggester.suggest(current_hour=9, current_day=0)
    """

    def __init__(self, tracker: HabitTracker, config: Optional[HabitConfig] = None):
        self.tracker = tracker
        self.config = config or HabitConfig()

    def suggest(
        self,
        current_hour: int,
        current_day: int = -1,
        location: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[HabitSuggestion]:
        """Get ranked habit suggestions for the current context.

        Args:
            current_hour: Current hour (0-23).
            current_day: Current day of week (0=Mon, -1=unknown).
            location: Current location context.
            limit: Max suggestions. Defaults to config value.

        Returns:
            List of HabitSuggestion, highest confidence first.
        """
        limit = limit if limit is not None else self.config.max_suggestions
        patterns = self.tracker.get_patterns(min_confidence=0.0)
        scored: list[tuple[float, HabitPattern]] = []

        for pattern in patterns:
            # Skip rejected or below-threshold
            if pattern.user_rejected:
                continue
            if pattern.confidence < self.config.confidence_threshold:
                continue
            if pattern.frequency < self.config.min_observations:
                continue

            # Context match scoring
            score = pattern.confidence

            # Time proximity bonus
            time_diff = abs(pattern.typical_hour - current_hour)
            if time_diff <= self.config.time_window_minutes / 60.0:
                score += 0.15 * (1.0 - time_diff / 2.0)
            else:
                score -= 0.1  # slight penalty for wrong time

            # Day match bonus
            if pattern.typical_day >= 0 and current_day >= 0:
                if pattern.typical_day == current_day:
                    score += 0.1
                else:
                    score -= 0.05

            # Location match bonus
            if pattern.location and location:
                if pattern.location.lower() == location.lower():
                    score += 0.1

            # Approved habits get a boost
            if pattern.user_approved:
                score += 0.1

            score = max(0.0, min(1.0, score))
            scored.append((score, pattern))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        suggestions = []
        for score, pattern in scored[:limit]:
            suggestions.append(self._build_suggestion(pattern, score))

        return suggestions

    def suggest_for_pattern(self, pattern_id: str) -> Optional[HabitSuggestion]:
        """Get a suggestion for a specific pattern by ID."""
        pattern = self.tracker.get_pattern(pattern_id)
        if not pattern:
            return None
        return self._build_suggestion(pattern, pattern.confidence)

    def _build_suggestion(self, pattern: HabitPattern, score: float) -> HabitSuggestion:
        """Build a user-facing HabitSuggestion from a pattern."""
        hour = int(pattern.typical_hour)
        minute = int((pattern.typical_hour % 1) * 60)
        period = "AM" if hour < 12 else "PM"
        display_hour = hour if hour <= 12 else hour - 12
        if display_hour == 0:
            display_hour = 12
        time_str = f"{display_hour}:{minute:02d} {period}"

        # Frequency text
        if pattern.frequency > 20:
            freq_str = f"almost daily ({pattern.frequency} times)"
        elif pattern.frequency > 10:
            freq_str = f"very frequent ({pattern.frequency} times)"
        elif pattern.frequency > 5:
            freq_str = f"frequent ({pattern.frequency} times)"
        else:
            freq_str = f"{pattern.frequency} times"

        # Reason
        if pattern.location:
            reason = f"You often {pattern.command} around {time_str} when at {pattern.location}"
        else:
            reason = f"You often {pattern.command} around {time_str}"

        return HabitSuggestion(
            pattern_id=pattern.pattern_id,
            command=pattern.command,
            intent=pattern.intent,
            confidence=round(score, 3),
            reason=reason,
            requires_approval=self.config.require_user_approval,
            typical_time=time_str,
            frequency_text=freq_str,
        )
