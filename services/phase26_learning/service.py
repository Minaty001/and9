"""
Phase 26 — Learning Engine Service.

ServiceBase wrapper for the Learning Engine.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Dict, List, Optional

from services.base.service_base import ServiceBase
from .config import LearningConfig
from .models import LearnedPreference, LearnedPattern, ActivitySummary
from .preference_learner import PreferenceLearner
from .pattern_learner import PatternLearner
from .activity_summarizer import ActivitySummarizer

logger = logging.getLogger(__name__)


class LearningEngineService(ServiceBase):
    """Learning engine service for preference and pattern learning.

    Usage:
        svc = LearningEngineService()
        await svc.initialize()
        await svc.observe("theme", "color", "dark")
        pref = await svc.get_preference("theme", "color")
    """

    def __init__(self, config: Optional[LearningConfig] = None):
        super().__init__(name="jarvis_learning", version="1.0.0")
        self.config = config or LearningConfig()
        self.preference_learner: Optional[PreferenceLearner] = None
        self.pattern_learner: Optional[PatternLearner] = None
        self.activity_summarizer: Optional[ActivitySummarizer] = None
        self._start_time = 0.0

    async def initialize(self) -> bool:
        self._start_time = time.time()
        try:
            self.preference_learner = PreferenceLearner(self.config)
            self.pattern_learner = PatternLearner(self.config)
            self.activity_summarizer = ActivitySummarizer(self.config)
            self._metrics.reset()
            self._initialized = True
            logger.info("LearningEngineService initialized")
            return True
        except Exception as e:
            logger.error("LearningEngineService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        logger.info("LearningEngineService shutting down...")
        self._initialized = False

    async def observe(
        self,
        category: str,
        key: str,
        value: Any,
        context: Optional[Dict[str, Any]] = None,
        source: str = "user",
        confidence: float = 1.0,
    ) -> LearnedPreference:
        """Observe a user preference."""
        if not self.preference_learner:
            raise RuntimeError("LearningEngineService not initialized")
        t0 = time.perf_counter()
        result = self.preference_learner.observe(category, key, value, context, source, confidence)
        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.counter("preferences_observed", 1)
        self._metrics.histogram("observe_time_ms", elapsed)
        return result

    async def get_preference(
        self, category: str, key: str, context: Optional[Dict[str, Any]] = None
    ) -> Optional[LearnedPreference]:
        """Get a learned preference."""
        if not self.preference_learner:
            raise RuntimeError("LearningEngineService not initialized")
        return self.preference_learner.get_preference(category, key, context)

    async def get_all_preferences(self, category: Optional[str] = None) -> List[LearnedPreference]:
        """Get all preferences."""
        if not self.preference_learner:
            raise RuntimeError("LearningEngineService not initialized")
        return self.preference_learner.get_all_preferences(category)

    async def forget_preference(self, category: str, key: str) -> bool:
        """Forget a learned preference."""
        if not self.preference_learner:
            raise RuntimeError("LearningEngineService not initialized")
        return self.preference_learner.forget_preference(category, key)

    async def record_pattern(
        self,
        trigger: str,
        action: str,
        context: Optional[Dict[str, Any]] = None,
        success: bool = True,
    ) -> LearnedPattern:
        """Record a pattern observation."""
        if not self.pattern_learner:
            raise RuntimeError("LearningEngineService not initialized")
        t0 = time.perf_counter()
        result = self.pattern_learner.record(trigger, action, context, success)
        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.counter("patterns_recorded", 1)
        self._metrics.histogram("record_pattern_time_ms", elapsed)
        return result

    async def find_patterns(self, context: Dict[str, Any]) -> List[LearnedPattern]:
        """Find patterns matching context."""
        if not self.pattern_learner:
            raise RuntimeError("LearningEngineService not initialized")
        return self.pattern_learner.find_matching_patterns(context)

    async def get_patterns(self, category: Optional[str] = None) -> List[LearnedPattern]:
        """Get all patterns."""
        if not self.pattern_learner:
            raise RuntimeError("LearningEngineService not initialized")
        return self.pattern_learner.get_patterns(category)

    async def generate_summary(self, period: str = "daily") -> ActivitySummary:
        """Generate an activity summary."""
        if not self.activity_summarizer:
            raise RuntimeError("LearningEngineService not initialized")
        t0 = time.perf_counter()
        result = self.activity_summarizer.generate_summary(period)
        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.counter("summaries_generated", 1)
        self._metrics.histogram("summarize_time_ms", elapsed)
        return result

    async def health(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        pref_count = len(self.preference_learner.get_all_preferences()) if self.preference_learner else 0
        pat_count = self.pattern_learner.get_pattern_count() if self.pattern_learner else 0
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service_name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
            "preferences_count": pref_count,
            "patterns_count": pat_count,
        }

    async def stats(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            "preferences_count": len(self.preference_learner.get_all_preferences()) if self.preference_learner else 0,
            "patterns_count": self.pattern_learner.get_pattern_count() if self.pattern_learner else 0,
            "observations_count": self.preference_learner.get_observation_count() if self.preference_learner else 0,
            "metrics": self._metrics.snapshot(),
        }
