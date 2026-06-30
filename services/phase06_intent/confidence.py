"""
Phase 6 — Confidence Scoring.

Combines multiple confidence signals:
    - Neural network softmax probability
    - Keyword match strength (exact, partial, none)
    - Query specificity (length, structure)
    - Historical accuracy for this intent
"""

import logging
from typing import Dict, Optional

from .config import IntentConfig

logger = logging.getLogger(__name__)


class ConfidenceScorer:
    """Multi-source confidence computation for intent detection.

    Combines neural network confidence with other signals to produce
    a robust overall confidence score.

    Usage:
        scorer = ConfidenceScorer()
        score = scorer.compute(
            nn_confidence=0.85,
            query="open whatsapp",
            intent="OPEN_APP",
            keyword_match=1.0,
        )
    """

    def __init__(self, config: Optional[IntentConfig] = None):
        self.config = config or IntentConfig()

    def compute(
        self,
        nn_confidence: float = 0.0,
        query: str = "",
        intent: str = "",
        keyword_match: float = 0.0,
        historical_accuracy: float = 0.5,
    ) -> float:
        """Compute overall confidence from multiple signals.

        Args:
            nn_confidence: Softmax probability from neural network (0-1).
            query: Original query text.
            intent: Detected intent name.
            keyword_match: Keyword match strength (0-1).
            historical_accuracy: Historical accuracy for this intent (0-1).

        Returns:
            Combined confidence score (0-1).
        """
        # 1. Query quality signal
        query_quality = self._query_quality(query)

        # 2. Keyword boost
        keyword_boost = keyword_match * 0.2  # max +0.2 from keywords

        # 3. Combine: weighted average
        base = (
            nn_confidence * 0.5
            + query_quality * 0.15
            + historical_accuracy * 0.15
        )

        # Add keyword boost
        score = base + keyword_boost

        # NN confidence caps the maximum
        score = min(score, nn_confidence + 0.15)

        # Clamp
        return max(0.0, min(1.0, score))

    def requires_clarification(self, confidence: float) -> bool:
        """Determine if clarification is needed based on confidence.

        Args:
            confidence: Overall confidence score.

        Returns:
            True if clarification should be requested.
        """
        return confidence < self.config.min_confidence

    def is_high_confidence(self, confidence: float) -> bool:
        """Check if confidence is high enough for automatic execution.

        Args:
            confidence: Overall confidence score.

        Returns:
            True if action can be executed automatically.
        """
        return confidence >= self.config.high_confidence

    @staticmethod
    def _query_quality(query: str) -> float:
        """Rate query quality based on length and structure.

        Very short queries (< 2 words) get lower quality.
        Queries with good structure get higher quality.

        Args:
            query: The query string.

        Returns:
            Quality score (0-1).
        """
        if not query or not query.strip():
            return 0.0

        words = query.strip().split()
        word_count = len(words)

        if word_count == 0:
            return 0.0
        elif word_count == 1:
            return 0.4
        elif word_count == 2:
            return 0.7
        elif word_count <= 5:
            return 0.9
        elif word_count <= 10:
            return 1.0
        else:
            return 0.8  # very long queries can be noisy

    @staticmethod
    def estimate_keyword_match(query: str, intent: str) -> float:
        """Estimate keyword match strength for an intent.

        Uses simple heuristics based on the intent name.

        Args:
            query: The query string.
            intent: The detected intent name.

        Returns:
            Match strength (0-1).
        """
        if not query or not intent:
            return 0.0

        query_lower = query.lower().strip()
        intent_lower = intent.lower()

        # Extract meaningful keywords from intent name
        intent_words = intent_lower.replace("_", " ").split()

        matches = sum(1 for word in intent_words if word in query_lower.split())
        if not intent_words:
            return 0.0

        return matches / len(intent_words)
