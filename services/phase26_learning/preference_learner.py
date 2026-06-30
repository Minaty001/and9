"""
Phase 26 — Preference Learner.

Learns user preferences from observations and feedback.
Supports context-aware preference retrieval and management.
"""

from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .config import LearningConfig
from .models import LearnedPreference, LearningObservation

logger = logging.getLogger(__name__)


class PreferenceLearner:
    """Learns and manages user preferences from observations.

    Usage:
        learner = PreferenceLearner()
        pref = learner.observe("theme", "color", "dark", {"time": "night"})
        pref = learner.get_preference("theme", "color")
    """

    def __init__(self, config: Optional[LearningConfig] = None):
        self.config = config or LearningConfig()
        self._preferences: Dict[str, Dict[str, LearnedPreference]] = {}
        self._observations: List[LearningObservation] = []

    def observe(
        self,
        category: str,
        key: str,
        value: Any,
        context: Optional[Dict[str, Any]] = None,
        source: str = "user",
        confidence: float = 1.0,
    ) -> LearnedPreference:
        """Observe a user preference from feedback or interaction.

        Args:
            category: Preference category (e.g., "theme", "notification").
            key: Preference key (e.g., "color", "sound_enabled").
            value: The preferred value.
            context: Context at time of observation.
            source: Source of the observation.
            confidence: Confidence in this observation.

        Returns:
            The updated LearnedPreference.
        """
        if not self.config.enable_preference_learning:
            raise RuntimeError("Preference learning is disabled")

        context = context or {}
        obs = LearningObservation(
            observation_type="preference",
            category=category,
            key=key,
            value=value,
            context=context,
            source=source,
            confidence=confidence,
        )
        self._observations.append(obs)
        self._trim_observations()

        if category not in self._preferences:
            self._preferences[category] = {}

        if key in self._preferences[category]:
            existing = self._preferences[category][key]
            # Update with exponential moving average
            lr = self.config.learning_rate
            existing.confidence = (1 - lr) * existing.confidence + lr * confidence
            existing.observation_count += 1
            existing.last_observed = datetime.now(timezone.utc)
            existing.preferred_value = value

            # Track alternatives
            if value not in existing.alternatives:
                existing.alternatives.append(value)
                if len(existing.alternatives) > 10:
                    existing.alternatives = existing.alternatives[-10:]

            # Update context conditions
            for k, v in context.items():
                existing.context_conditions[k] = v

            return existing

        pref = LearnedPreference(
            category=category,
            key=key,
            preferred_value=value,
            confidence=confidence,
            observation_count=1,
            context_conditions=context,
            alternatives=[value],
        )
        self._preferences[category][key] = pref
        return pref

    def get_preference(
        self, category: str, key: str, context: Optional[Dict[str, Any]] = None
    ) -> Optional[LearnedPreference]:
        """Get a learned preference with optional context matching.

        Args:
            category: Preference category.
            key: Preference key.
            context: Current context for matching.

        Returns:
            LearnedPreference if found, None otherwise.
        """
        if category not in self._preferences:
            return None
        pref = self._preferences[category].get(key)
        if pref is None:
            return None
        if pref.confidence < 0.1:
            return None
        # Context matching could be enhanced here
        return pref

    def get_all_preferences(self, category: Optional[str] = None) -> List[LearnedPreference]:
        """Get all preferences, optionally filtered by category.

        Args:
            category: Optional category filter.

        Returns:
            List of LearnedPreference.
        """
        if category:
            if category not in self._preferences:
                return []
            return list(self._preferences[category].values())

        result = []
        for cat in self._preferences:
            result.extend(self._preferences[cat].values())
        return result

    def forget_preference(self, category: str, key: str) -> bool:
        """Remove a learned preference.

        Args:
            category: Preference category.
            key: Preference key.

        Returns:
            True if removed, False otherwise.
        """
        if category in self._preferences and key in self._preferences[category]:
            del self._preferences[category][key]
            if not self._preferences[category]:
                del self._preferences[category]
            return True
        return False

    def get_observation_count(self) -> int:
        """Return total observation count."""
        return len(self._observations)

    def clear(self) -> None:
        """Clear all preferences and observations."""
        self._preferences.clear()
        self._observations.clear()

    def _trim_observations(self) -> None:
        """Keep observations list bounded."""
        if len(self._observations) > 10000:
            self._observations = self._observations[-5000:]
