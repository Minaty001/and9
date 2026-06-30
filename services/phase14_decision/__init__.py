"""
Phase 14 — Decision Engine
===========================

Route across Reflex / Habit / Conscious brains based on confidence,
latency, permissions, and cost.

Components:
    - BrainRouter: Core routing logic with confidence thresholds
    - DecisionEngineService: ServiceBase wrapper
"""

from .router import BrainRouter
from .service import DecisionEngineService
from .config import DecisionConfig
from .models import DecisionRequest, DecisionResult

__all__ = [
    "BrainRouter",
    "DecisionEngineService",
    "DecisionConfig",
    "DecisionRequest",
    "DecisionResult",
]
