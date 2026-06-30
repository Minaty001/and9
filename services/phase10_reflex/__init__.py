"""
Phase 10 — Reflex Brain
=========================

Fast, low-latency pattern matching layer for well-known commands.
The first processing layer before the full NLU pipeline.

Components:
    - ReflexAction: A registered pattern-action pair
    - ReflexResult: Output from reflex processing
    - ReflexBrain: Core pattern matching engine
    - ReflexService: ServiceBase wrapper

Usage:
    svc = ReflexService()
    await svc.initialize()
    result = await svc.process("hello")
    print(result.matched)  # True
    print(result.action.intent)  # "greeting"
"""

from .reflex_brain import ReflexBrain, ReflexAction, ReflexResult
from .service import ReflexService
from .config import ReflexConfig

__all__ = [
    "ReflexBrain",
    "ReflexAction",
    "ReflexResult",
    "ReflexService",
    "ReflexConfig",
]
