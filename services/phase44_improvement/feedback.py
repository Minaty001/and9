"""
Phase 44 — Feedback Collector.

Collects, queries, analyzes, and exports user feedback.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from .models import Feedback
from .config import ImprovementConfig

logger = logging.getLogger(__name__)


class FeedbackCollector:
    """Collects and manages user feedback.

    Usage:
        fc = FeedbackCollector()
        feedback = fc.submit_feedback("user1", 4, "usability", "Great UI!")
        stats = fc.get_stats()
    """

    def __init__(self, config: Optional[ImprovementConfig] = None):
        self.config = config or ImprovementConfig()
        self._feedback: Dict[str, Feedback] = {}

    def submit_feedback(
        self,
        user_id: str,
        rating: int,
        category: str = "other",
        comment: str = "",
        session_id: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Feedback:
        """Submit a new feedback entry.

        Args:
            user_id: User identifier.
            rating: Rating from 1 (worst) to 5 (best).
            category: Feedback category.
            comment: Free-text comment.
            session_id: Session identifier.
            metadata: Additional metadata.

        Returns:
            The created Feedback.
        """
        if not self.config.enable_feedback_collection:
            raise RuntimeError("Feedback collection is disabled")

        feedback_id = uuid.uuid4().hex[:12]
        feedback = Feedback(
            id=feedback_id,
            user_id=user_id,
            session_id=session_id,
            rating=rating,
            category=category,
            comment=comment,
            metadata=metadata or {},
        )
        self._feedback[feedback_id] = feedback
        logger.info("Feedback submitted by %s: rating=%d, category=%s", user_id, rating, category)
        return feedback

    def get_feedback(self, feedback_id: str) -> Optional[Feedback]:
        """Get a specific feedback by ID."""
        return self._feedback.get(feedback_id)

    def list_feedback(
        self,
        category: Optional[str] = None,
        min_rating: Optional[int] = None,
    ) -> List[Feedback]:
        """List feedback entries with optional filters.

        Args:
            category: Filter by category.
            min_rating: Minimum rating filter.

        Returns:
            Filtered list of Feedback, newest first.
        """
        results = list(self._feedback.values())
        if category:
            results = [f for f in results if f.category == category]
        if min_rating is not None:
            results = [f for f in results if f.rating >= min_rating]
        return sorted(results, key=lambda f: f.timestamp, reverse=True)

    def get_stats(self) -> Dict[str, Any]:
        """Compute aggregate feedback statistics.

        Returns:
            Dict with average_rating, counts by category, and trend info.
        """
        if not self._feedback:
            return {
                "total_count": 0,
                "avg_rating": 0.0,
                "counts_by_category": {},
                "rating_distribution": {},
            }

        ratings = [f.rating for f in self._feedback.values()]
        avg_rating = sum(ratings) / len(ratings)

        counts_by_category: Dict[str, int] = {}
        for f in self._feedback.values():
            counts_by_category[f.category] = counts_by_category.get(f.category, 0) + 1

        rating_dist: Dict[str, int] = {}
        for r in ratings:
            rating_dist[str(r)] = rating_dist.get(str(r), 0) + 1

        return {
            "total_count": len(self._feedback),
            "avg_rating": round(avg_rating, 2),
            "counts_by_category": counts_by_category,
            "rating_distribution": rating_dist,
        }

    def resolve_feedback(self, feedback_id: str) -> bool:
        """Mark feedback as resolved.

        Args:
            feedback_id: ID of the feedback to resolve.

        Returns:
            True if resolved, False if not found.
        """
        feedback = self._feedback.get(feedback_id)
        if not feedback:
            return False
        feedback.resolved = True
        logger.info("Feedback %s resolved", feedback_id)
        return True

    def export_feedback(self, fmt: str = "json") -> str:
        """Export all feedback in the specified format.

        Args:
            fmt: Output format ("json" or "csv").

        Returns:
            Formatted string of all feedback.

        Raises:
            ValueError: If fmt is unsupported.
        """
        if fmt == "json":
            return json.dumps(
                [f.model_dump(mode="json") for f in self.list_feedback()],
                indent=2,
                default=str,
            )
        elif fmt == "csv":
            lines = ["id,user_id,rating,category,comment,timestamp,resolved"]
            for f in self.list_feedback():
                comment_escaped = f.comment.replace('"', '""')
                lines.append(
                    f'{f.id},{f.user_id},{f.rating},{f.category},"{comment_escaped}",'
                    f'{f.timestamp.isoformat()},{f.resolved}'
                )
            return "\n".join(lines)
        else:
            raise ValueError(f"Unsupported export format: {fmt}")
