"""
Phase 6 — Intent Detection Service.

Wraps the IntentClassifier and ConfidenceScorer in a ServiceBase.
"""

import time
import logging
from typing import Any, Dict, List, Optional

from services.base.service_base import ServiceBase
from .config import IntentConfig
from .classifier import IntentClassifier
from .confidence import ConfidenceScorer
from .models import IntentResult

logger = logging.getLogger(__name__)


class IntentDetectionService(ServiceBase):
    """Intent detection service wrapping the classifier and confidence scorer."""

    def __init__(self, config: Optional[IntentConfig] = None):
        super().__init__(name="jarvis_intent", version="1.0.0")
        self.config = config or IntentConfig()
        self.classifier = IntentClassifier(config=self.config)
        self.scorer = ConfidenceScorer(config=self.config)
        self._start_time = 0.0

    async def initialize(self) -> bool:
        """Initialize the intent detection service."""
        self._start_time = time.time()
        try:
            self._metrics.reset()
            ok = self.classifier.initialize()
            if ok:
                self._initialized = True
                elapsed = (time.time() - self._start_time) * 1000
                logger.info("IntentDetectionService initialized in %.0fms", elapsed)
            else:
                logger.error("IntentDetectionService: classifier init failed")
            return ok
        except Exception as e:
            logger.error("IntentDetectionService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        """Shut down the service."""
        logger.info("IntentDetectionService shutting down...")
        self._initialized = False

    async def detect(
        self,
        embedding: List[float],
        text: str = "",
        historical_accuracy: float = 0.5,
    ) -> IntentResult:
        """Detect intent from embedding vector.

        Args:
            embedding: 128-dim embedding from Phase 5.
            text: Original query text (for keyword override).
            historical_accuracy: Historical accuracy for this intent type.

        Returns:
            IntentResult with intent name and confidence.
        """
        t0 = time.perf_counter()

        # Classify
        result = self.classifier.classify(embedding, text)

        # Compute multi-source confidence
        keyword_match = self.scorer.estimate_keyword_match(text, result.intent) if text else 0.0
        overall_confidence = self.scorer.compute(
            nn_confidence=result.confidence,
            query=text,
            intent=result.intent,
            keyword_match=keyword_match,
            historical_accuracy=historical_accuracy,
        )
        result.confidence = round(overall_confidence, 4)

        elapsed = (time.perf_counter() - t0) * 1000
        result.time_ms = round(elapsed, 2)

        self._metrics.counter("intents_detected")
        self._metrics.histogram("intent_confidence", overall_confidence)
        self._metrics.histogram("intent_time_ms", elapsed)

        return result

    async def detect_top_k(
        self, embedding: List[float], k: int = 3
    ) -> List[dict]:
        """Return top-k intent predictions.

        Args:
            embedding: 128-dim embedding.
            k: Number of predictions.

        Returns:
            List of {"intent": str, "confidence": float}.
        """
        return self.classifier.classify_top_k(embedding, k=k)

    async def requires_clarification(self, confidence: float) -> bool:
        """Check if confidence is below threshold for automatic execution.

        Args:
            confidence: Overall confidence score.

        Returns:
            True if clarification should be requested.
        """
        return self.scorer.requires_clarification(confidence)

    # ── Health / Stats ──────────────────────────────────────────

    async def health(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        stats = self.classifier.nn.get_stats()
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service_name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
            "nn_initialized": stats.get("initialized", False),
            "nn_parameters": stats.get("parameters", 0),
            "intents_count": stats.get("intents", 0),
        }

    async def stats(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            "nn": self.classifier.nn.get_stats(),
            "metrics": self._metrics.snapshot(),
        }
