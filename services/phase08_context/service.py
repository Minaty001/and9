"""
Phase 8 — Context Builder Service.

ServiceBase wrapper around ContextManager.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Dict, List, Optional

from services.base.service_base import ServiceBase
from .config import ContextConfig
from .models import TurnContext, ContextSnapshot
from .context_manager import ContextManager, TurnScore

logger = logging.getLogger(__name__)


class ContextBuilderService(ServiceBase):
    """Context builder service managing conversation state.

    Usage:
        svc = ContextBuilderService()
        await svc.initialize()
        snapshot = await svc.process("what's the weather", intent="weather_query")
        snapshot2 = await svc.process("and in Mumbai?")
        results = await svc.search("rain")
    """

    def __init__(self, config: Optional[ContextConfig] = None):
        super().__init__(name="jarvis_context", version="1.0.0")
        self.config = config or ContextConfig()
        self.manager: Optional[ContextManager] = None
        self._start_time = 0.0

    async def initialize(self) -> bool:
        """Initialize the context builder."""
        self._start_time = time.time()
        try:
            self.manager = ContextManager(self.config)
            self._metrics.reset()
            self._initialized = True
            elapsed = (time.time() - self._start_time) * 1000
            logger.info("ContextBuilderService initialized in %.0fms", elapsed)
            return True
        except Exception as e:
            logger.error("ContextBuilderService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        """Shut down the service."""
        logger.info("ContextBuilderService shutting down...")
        if self.manager:
            self.manager.clear()
        self._initialized = False

    async def process(
        self,
        query: str,
        intent: str = "",
        intent_confidence: float = 0.0,
        entities: Optional[Dict[str, List[str]]] = None,
        normalized_query: str = "",
        embedding: Optional[List[float]] = None,
        response: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ContextSnapshot:
        """Process a new turn and return the updated context snapshot.

        Args:
            query: The user query text.
            intent: Detected intent name.
            intent_confidence: Confidence of intent detection.
            entities: Extracted entities grouped by type.
            normalized_query: Pre-normalized query text.
            embedding: Query embedding vector.
            response: Assistant response text.
            metadata: Additional metadata for this turn.

        Returns:
            Updated ContextSnapshot.
        """
        if not self.manager:
            raise RuntimeError("ContextBuilderService not initialized")

        t0 = time.perf_counter()

        turn = self.manager.add_turn(
            query=query,
            intent=intent,
            intent_confidence=intent_confidence,
            entities=entities,
            normalized_query=normalized_query,
            embedding=embedding,
            response=response,
            metadata=metadata,
        )

        snapshot = self.manager.get_snapshot()
        elapsed = (time.perf_counter() - t0) * 1000

        self._metrics.counter("turns_processed", 1)
        self._metrics.histogram("process_time_ms", elapsed)

        logger.debug("Processed turn %d: intent=%s entities=%d in %.2fms",
                     turn.turn_id, intent, len(entities or {}), elapsed)

        return snapshot

    async def search(self, query: str, top_k: int = 5) -> List[TurnScore]:
        """Search relevant past turns.

        Args:
            query: Query text to match against.
            top_k: Maximum results.

        Returns:
            List of scored past turns.
        """
        if not self.manager:
            raise RuntimeError("ContextBuilderService not initialized")
        return self.manager.search_relevant(query, top_k=top_k)

    async def get_context(self) -> ContextSnapshot:
        """Get current context snapshot."""
        if not self.manager:
            raise RuntimeError("ContextBuilderService not initialized")
        return self.manager.get_snapshot()

    async def clear(self) -> None:
        """Clear all context."""
        if self.manager:
            self.manager.clear()
        logger.info("Context cleared by user request")

    async def health(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        turn_count = self.manager.get_turn_count() if self.manager else 0
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service_name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
            "turns_processed": turn_count,
            "session_active": self.manager.get_snapshot().is_active if self.manager else False,
        }

    async def stats(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            "metrics": self._metrics.snapshot(),
        }
