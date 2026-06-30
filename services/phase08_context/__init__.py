"""
Phase 8 — Context Builder
===========================

Manages conversation context across turns using a sliding window
with time-based decay, entity overlap scoring, and relevance search.

Components:
    - TurnContext: Data model for a single conversation turn
    - ContextManager: Sliding window, decay, merging, relevance search
    - ContextBuilderService: ServiceBase wrapper

Usage:
    svc = ContextBuilderService()
    await svc.initialize()
    ctx = await svc.process("what's the weather", "weather_query", {"location": "Delhi"})
    ctx = await svc.process("and in Mumbai?")
    print(ctx.recent_intents)
"""

from .context_manager import ContextManager, TurnScore
from .service import ContextBuilderService
from .config import ContextConfig
from .models import TurnContext, ContextSnapshot

__all__ = [
    "ContextManager",
    "TurnScore",
    "ContextBuilderService",
    "ContextConfig",
    "TurnContext",
    "ContextSnapshot",
]
