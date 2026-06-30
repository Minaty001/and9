"""
Phase 26 — Pattern Learner.

Recognizes recurring interaction patterns from observations.
Supports context matching and success rate tracking.
"""

from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .config import LearningConfig
from .models import LearnedPattern

logger = logging.getLogger(__name__)


class PatternLearner:
    """Learns and manages recurring interaction patterns.

    Usage:
        learner = PatternLearner()
        pattern = learner.record({"trigger": "morning", "action": "play music"})
        matches = learner.find_matching_patterns({"time": "morning"})
    """

    def __init__(self, config: Optional[LearningConfig] = None):
        self.config = config or LearningConfig()
        self._patterns: Dict[str, LearnedPattern] = {}

    def record(
        self,
        trigger: str,
        action: str,
        context: Any = None,
        success: bool = True,
    ) -> LearnedPattern:
        """Record a pattern observation.

        Args:
            trigger: The trigger condition or event.
            action: The action taken.
            context: Context at time of recording (dict, or string wrapped into dict).
            success: Whether the action was successful.

        Returns:
            The created or updated LearnedPattern.
        """
        if not self.config.enable_pattern_learning:
            raise RuntimeError("Pattern learning is disabled")

        # Normalize string context to a dict for List[Dict[str, Any]] model field
        if isinstance(context, str):
            context = {"value": context}
        context = context or {}

        # Try to match existing pattern
        for pattern in self._patterns.values():
            if pattern.trigger == trigger and pattern.action == action:
                pattern.frequency += 1
                pattern.last_triggered = datetime.now(timezone.utc)
                if context and context not in pattern.contexts:
                    pattern.contexts.append(context)
                    max_ctx = 50
                    if len(pattern.contexts) > max_ctx:
                        pattern.contexts = pattern.contexts[-max_ctx:]

                # Update confidence
                pattern.confidence = min(0.99, pattern.confidence + self.config.learning_rate * (1 - pattern.confidence))

                # Update success rate
                total = pattern.frequency
                pattern.success_rate = ((pattern.success_rate * (total - 1)) + (1.0 if success else 0.0)) / total

                return pattern

        # Create new pattern
        pattern_id = uuid.uuid4().hex[:12]
        pattern = LearnedPattern(
            pattern_id=pattern_id,
            trigger=trigger,
            action=action,
            frequency=1,
            confidence=self.config.learning_rate,
            contexts=[context] if context else [],
            success_rate=1.0 if success else 0.0,
        )

        # Enforce category limits
        self._enforce_category_limit()

        self._patterns[pattern_id] = pattern
        return pattern

    def find_matching_patterns(self, context: Dict[str, Any]) -> List[LearnedPattern]:
        """Find patterns matching the given context.

        Args:
            context: Current context to match against.

        Returns:
            List of matching LearnedPattern, sorted by confidence desc.
        """
        matches = []
        for pattern in self._patterns.values():
            score = self._match_score(pattern, context)
            if score > 0:
                matches.append((score, pattern))

        matches.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in matches]

    def get_patterns(self, category: Optional[str] = None) -> List[LearnedPattern]:
        """Get all patterns, optionally filtered by category.

        Args:
            category: Optional category filter (via trigger prefix).

        Returns:
            List of LearnedPattern.
        """
        if category:
            return [p for p in self._patterns.values() if p.trigger.startswith(category)]
        return list(self._patterns.values())

    def calculate_success_rate(self, pattern_id: str) -> float:
        """Calculate success rate for a specific pattern.

        Args:
            pattern_id: Pattern identifier.

        Returns:
            Success rate as float 0-1, or 0.0 if not found.
        """
        pattern = self._patterns.get(pattern_id)
        if not pattern:
            return 0.0
        return pattern.success_rate

    def get_pattern(self, pattern_id: str) -> Optional[LearnedPattern]:
        """Get a specific pattern by ID."""
        return self._patterns.get(pattern_id)

    def remove_pattern(self, pattern_id: str) -> bool:
        """Remove a pattern by ID."""
        if pattern_id in self._patterns:
            del self._patterns[pattern_id]
            return True
        return False

    def get_pattern_count(self) -> int:
        """Return total pattern count."""
        return len(self._patterns)

    def clear(self) -> None:
        """Clear all patterns."""
        self._patterns.clear()

    def _match_score(self, pattern: LearnedPattern, context: Dict[str, Any]) -> float:
        """Compute context match score for a pattern.

        Args:
            pattern: Pattern to match.
            context: Current context.

        Returns:
            Match score (0.0 to 1.0).
        """
        if not context:
            return 0.0

        # Direct context match
        for ctx in pattern.contexts:
            matches = 0
            total = 0
            for k, v in context.items():
                total += 1
                if k in ctx and ctx[k] == v:
                    matches += 1
            if total > 0 and matches == total:
                return pattern.confidence

        # Partial match
        for ctx in pattern.contexts:
            matches = 0
            total = 0
            for k, v in context.items():
                total += 1
                if k in ctx and ctx[k] == v:
                    matches += 1
            if total > 0 and matches / total > 0.5:
                return pattern.confidence * (matches / total)

        return 0.0

    def _enforce_category_limit(self) -> None:
        """Remove lowest-confidence patterns if limit exceeded."""
        if len(self._patterns) > self.config.max_patterns_per_category:
            sorted_patterns = sorted(self._patterns.values(), key=lambda p: p.confidence)
            to_remove = len(self._patterns) - self.config.max_patterns_per_category
            for p in sorted_patterns[:to_remove]:
                del self._patterns[p.pattern_id]
