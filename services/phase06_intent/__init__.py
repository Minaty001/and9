"""
Phase 6 — Intent Detection
============================

Classify commands, questions, automation, media, Android control,
and search queries. Supports multi-intent queries with confidence
scores and fallback intent.

Core components:
    - TinyNeuralNetwork: 128→64→32→28 NumPy neural net
    - IntentClassifier: High-level classification interface
    - ConfidenceScorer: Multi-source confidence computation
"""

from .classifier import TinyNeuralNetwork, IntentClassifier
from .confidence import ConfidenceScorer
from .service import IntentDetectionService
from .config import IntentConfig
from .models import IntentResult, IntentType

__all__ = [
    "TinyNeuralNetwork",
    "IntentClassifier",
    "ConfidenceScorer",
    "IntentDetectionService",
    "IntentConfig",
    "IntentResult",
    "IntentType",
]
