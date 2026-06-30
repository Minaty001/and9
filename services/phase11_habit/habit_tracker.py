"""
Phase 11 — Habit Tracker.

Observes events, builds habit patterns, decays unused habits,
and manages the pattern lifecycle.
"""

from __future__ import annotations

import uuid
import math
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from .config import HabitConfig
from .models import HabitPattern, HabitObservation, HabitAuditEntry

logger = logging.getLogger(__name__)


class HabitTracker:
    """Tracks and learns habit patterns from observations.

    Usage:
        tracker = HabitTracker()
        tracker.observe(HabitObservation(command="play music", time_hour=9))
        tracker.observe(HabitObservation(command="play music", time_hour=9))
        patterns = tracker.get_patterns()
    """

    def __init__(self, config: Optional[HabitConfig] = None):
        self.config = config or HabitConfig()
        self._patterns: Dict[str, HabitPattern] = {}
        self._observations: List[HabitObservation] = []
        self._audit_log: List[HabitAuditEntry] = []

    # ── Observation ────────────────────────────────────────────────

    def observe(self, observation: HabitObservation) -> Optional[HabitPattern]:
        """Record an observation and update matching habits.

        Returns the matched/updated pattern, or None.
        """
        self._observations.append(observation)

        # Prune old observations if too many
        if len(self._observations) > 10000:
            self._observations = self._observations[-5000:]

        # Try to match existing pattern
        pattern = self._find_matching_pattern(observation)
        if pattern:
            self._update_pattern(pattern, observation)
            self._apply_decay(exclude_id=pattern.pattern_id)
            return pattern

        # Create new pattern if at capacity
        if len(self._patterns) >= self.config.max_habits:
            # Evict lowest-confidence pattern
            lowest = min(self._patterns.values(), key=lambda p: p.confidence)
            del self._patterns[lowest.pattern_id]
            logger.debug("Evicted low-confidence habit: %s", lowest.command)

        pattern = HabitPattern(
            pattern_id=uuid.uuid4().hex[:8],
            command=observation.command,
            intent=observation.intent,
            typical_hour=float(observation.time_hour),
            typical_day=observation.day_of_week,
            location=observation.location,
            frequency=1,
            confidence=0.1,
            entities=observation.entities,
        )
        self._patterns[pattern.pattern_id] = pattern
        self._apply_decay(exclude_id=pattern.pattern_id)
        return pattern

    # ── Approval / Rejection ───────────────────────────────────────

    def approve(self, pattern_id: str) -> bool:
        """Mark a habit as user-approved."""
        pattern = self._patterns.get(pattern_id)
        if not pattern:
            return False
        pattern.user_approved = True
        pattern.user_rejected = False
        self._audit(HabitAuditEntry(
            action="approved", pattern_id=pattern_id,
            command=pattern.command,
        ))
        return True

    def reject(self, pattern_id: str) -> bool:
        """Mark a habit as user-rejected (suppress future suggestions)."""
        pattern = self._patterns.get(pattern_id)
        if not pattern:
            return False
        pattern.user_rejected = True
        pattern.user_approved = False
        self._audit(HabitAuditEntry(
            action="rejected", pattern_id=pattern_id,
            command=pattern.command,
        ))
        return True

    def remove(self, pattern_id: str) -> bool:
        """Remove a habit entirely."""
        if pattern_id in self._patterns:
            del self._patterns[pattern_id]
            return True
        return False

    # ── Queries ────────────────────────────────────────────────────

    def get_patterns(self, min_confidence: float = 0.0) -> List[HabitPattern]:
        """Get all patterns meeting minimum confidence."""
        return sorted(
            [p for p in self._patterns.values() if p.confidence >= min_confidence],
            key=lambda p: p.confidence, reverse=True,
        )

    def get_pattern(self, pattern_id: str) -> Optional[HabitPattern]:
        return self._patterns.get(pattern_id)

    def get_pattern_count(self) -> int:
        return len(self._patterns)

    def get_audit_log(self, limit: int = 50) -> List[HabitAuditEntry]:
        return sorted(self._audit_log, key=lambda e: e.timestamp, reverse=True)[:limit]

    def clear(self) -> None:
        self._patterns.clear()
        self._observations.clear()
        self._audit_log.clear()

    # ── Internal ───────────────────────────────────────────────────

    def _find_matching_pattern(self, obs: HabitObservation) -> Optional[HabitPattern]:
        """Find a pattern that matches this observation."""
        for pattern in self._patterns.values():
            if pattern.user_rejected:
                continue
            if pattern.command != obs.command:
                continue
            # Time proximity
            time_diff = abs(pattern.typical_hour - obs.time_hour)
            if time_diff > self.config.time_window_minutes / 60.0:
                continue
            # Day match (if pattern has a specific day)
            if pattern.typical_day >= 0 and obs.day_of_week >= 0:
                if pattern.typical_day != obs.day_of_week:
                    continue
            return pattern
        return None

    def _update_pattern(self, pattern: HabitPattern, obs: HabitObservation) -> None:
        """Update a pattern with a new observation."""
        old_count = pattern.frequency
        pattern.frequency += 1

        # Exponential moving average for typical hour
        alpha = 1.0 / max(pattern.frequency, 1)
        pattern.typical_hour = (1 - alpha) * pattern.typical_hour + alpha * obs.time_hour

        # Update typical day
        if obs.day_of_week >= 0:
            if pattern.typical_day < 0:
                pattern.typical_day = obs.day_of_week
            elif pattern.typical_day != obs.day_of_week:
                pattern.typical_day = -1  # varies, no longer predictive

        # Update location
        if obs.location:
            pattern.location = obs.location

        # Update entities
        for etype, values in obs.entities.items():
            if etype not in pattern.entities:
                pattern.entities[etype] = []
            for v in values:
                if v not in pattern.entities[etype]:
                    pattern.entities[etype].append(v)
                    if len(pattern.entities[etype]) > 10:
                        pattern.entities[etype] = pattern.entities[etype][-10:]

        # Compute confidence: sigmoid-like growth with frequency
        # Higher frequency + recency = higher confidence
        days_since_first = pattern.age_days()
        freq_factor = 1.0 - math.exp(-pattern.frequency / 5.0)
        recency_factor = 1.0 / (1.0 + days_since_first / 30.0)  # decays over 30 days
        pattern.confidence = min(0.95, round(0.3 + 0.5 * freq_factor + 0.2 * recency_factor, 3))

        pattern.last_observed = datetime.now(timezone.utc)

    def _apply_decay(self, exclude_id: Optional[str] = None) -> None:
        """Apply time-based decay to all patterns except excluded."""
        now = datetime.now(timezone.utc)
        for pid, pattern in self._patterns.items():
            if pid == exclude_id:
                continue
            days_since = (now - pattern.last_observed).total_seconds() / 86400.0
            if days_since > 1:
                decay = self.config.decay_rate ** days_since
                pattern.confidence = max(0.0, pattern.confidence * decay)

    def _audit(self, entry: HabitAuditEntry) -> None:
        if self.config.enable_audit_log:
            self._audit_log.append(entry)
            if len(self._audit_log) > 1000:
                self._audit_log = self._audit_log[-500:]
