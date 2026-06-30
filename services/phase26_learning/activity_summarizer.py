"""
Phase 26 — Activity Summarizer.

Generates periodic summaries of user activity.
Summarizes interactions, intents, entities, and produces insights.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from collections import Counter

from .config import LearningConfig
from .models import ActivitySummary, LearningObservation

logger = logging.getLogger(__name__)


class ActivitySummarizer:
    """Generates activity summaries from observations.

    Usage:
        summarizer = ActivitySummarizer()
        summary = summarizer.generate_summary("daily")
    """

    def __init__(self, config: Optional[LearningConfig] = None):
        self.config = config or LearningConfig()
        self._observations: List[LearningObservation] = []

    def add_observation(self, observation: LearningObservation) -> None:
        """Add an observation for future summarization."""
        self._observations.append(observation)
        if len(self._observations) > 50000:
            self._observations = self._observations[-25000:]

    def generate_summary(self, period: str = "daily") -> ActivitySummary:
        """Generate an activity summary for the given period.

        Args:
            period: Summary period: "hourly", "daily", or "weekly".

        Returns:
            An ActivitySummary instance.
        """
        now = datetime.now(timezone.utc)

        if period == "hourly":
            start_time = now - timedelta(hours=1)
        elif period == "weekly":
            start_time = now - timedelta(weeks=1)
        else:  # daily
            start_time = now - timedelta(days=1)

        # Filter observations in the period
        period_obs = [o for o in self._observations if start_time <= o.timestamp <= now]

        # Count interactions by type
        type_counts = Counter(o.observation_type for o in period_obs)

        # Top intents (from context)
        intents = []
        for o in period_obs:
            intent = o.context.get("intent", o.observation_type)
            intents.append(intent)
        intent_counts = Counter(intents)

        # Top entities (from context)
        entities = []
        for o in period_obs:
            entity = o.context.get("entity", "")
            if entity:
                entities.append(entity)
        entity_counts = Counter(entities)

        # Top queries
        queries = []
        for o in period_obs:
            query = o.context.get("query", "")
            if query:
                queries.append(query)
        query_counts = Counter(queries)

        # Average confidence
        if period_obs:
            avg_conf = sum(o.confidence for o in period_obs) / len(period_obs)
        else:
            avg_conf = 0.0

        # Generate insights
        insights = self._generate_insights(period_obs, period, intent_counts, query_counts)

        return ActivitySummary(
            period=period,
            start_time=start_time,
            end_time=now,
            total_interactions=len(period_obs),
            top_intents=[{"intent": k, "count": v} for k, v in intent_counts.most_common(5)],
            top_entities=[{"entity": k, "count": v} for k, v in entity_counts.most_common(5)],
            avg_confidence=round(avg_conf, 3),
            top_queries=[{"query": k, "count": v} for k, v in query_counts.most_common(5)],
            insights=insights,
        )

    def get_observation_count(self) -> int:
        """Return total observation count."""
        return len(self._observations)

    def clear(self) -> None:
        """Clear all observations."""
        self._observations.clear()

    def _generate_insights(
        self,
        observations: List[LearningObservation],
        period: str,
        intent_counts: Counter,
        query_counts: Counter,
    ) -> List[str]:
        """Generate human-readable insights from observations.

        Args:
            observations: Observations in the period.
            period: Period string.
            intent_counts: Counter of intents.
            query_counts: Counter of queries.

        Returns:
            List of insight strings.
        """
        insights = []

        if not observations:
            insights.append(f"No activity detected in the last {period}.")
            return insights

        insights.append(f"Total interactions: {len(observations)} in the last {period}.")

        if intent_counts:
            top_intent = intent_counts.most_common(1)[0]
            insights.append(f"Most frequent intent: '{top_intent[0]}' ({top_intent[1]} times).")

        if query_counts:
            insights.append(f"Top query: '{query_counts.most_common(1)[0][0]}'.")

        # Check for new topics (observed only once)
        new_topics = [q for q, c in query_counts.most_common() if c <= 2]
        if new_topics:
            insights.append(f"New topics detected: {len(new_topics)}.")

        return insights
