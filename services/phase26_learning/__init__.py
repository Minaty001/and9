"""
Phase 26 — Learning Engine
===========================

Learns from user feedback, corrections, and repeated queries. Stores
interaction patterns for preference learning, pattern recognition,
and activity summarization.

Components:
    - PreferenceLearner: Learns user preferences from observations
    - PatternLearner: Recognizes recurring interaction patterns
    - ActivitySummarizer: Generates activity summaries
    - LearningEngineService: ServiceBase wrapper
"""

from .preference_learner import PreferenceLearner
from .pattern_learner import PatternLearner
from .activity_summarizer import ActivitySummarizer
from .service import LearningEngineService
from .config import LearningConfig
from .models import (
    LearningObservation,
    LearnedPreference,
    LearnedPattern,
    ActivitySummary,
)

__all__ = [
    "PreferenceLearner",
    "PatternLearner",
    "ActivitySummarizer",
    "LearningEngineService",
    "LearningConfig",
    "LearningObservation",
    "LearnedPreference",
    "LearnedPattern",
    "ActivitySummary",
]
