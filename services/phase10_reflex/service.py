"""
Phase 10 — Reflex Brain Service.

ServiceBase wrapper around ReflexBrain.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Callable, Dict, List, Optional

from services.base.service_base import ServiceBase
from .config import ReflexConfig
from .reflex_brain import ReflexBrain, ReflexAction, ReflexResult

logger = logging.getLogger(__name__)


class ReflexService(ServiceBase):
    """Reflex brain service for fast pattern matching.

    Usage:
        svc = ReflexService()
        await svc.initialize()
        result = await svc.process("hello")
        if result.matched:
            print(f"Intent: {result.intent}, Response: {result.response}")
    """

    def __init__(self, config: Optional[ReflexConfig] = None):
        super().__init__(name="jarvis_reflex", version="1.0.0")
        self.config = config or ReflexConfig()
        self.brain: Optional[ReflexBrain] = None
        self._start_time = 0.0

    async def initialize(self) -> bool:
        """Initialize the reflex brain with default actions."""
        self._start_time = time.time()
        try:
            self.brain = ReflexBrain(self.config)
            self.brain.initialize()
            self._metrics.reset()
            self._initialized = True
            elapsed = (time.time() - self._start_time) * 1000
            logger.info("ReflexService initialized with %d actions in %.0fms",
                        self.brain.get_action_count(), elapsed)
            return True
        except Exception as e:
            logger.error("ReflexService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        """Shut down the service."""
        logger.info("ReflexService shutting down...")
        self._initialized = False

    async def process(self, text: str) -> ReflexResult:
        """Process input through the reflex brain.

        Args:
            text: Input text to match.

        Returns:
            ReflexResult with match status.
        """
        if not self.brain:
            raise RuntimeError("ReflexService not initialized")

        t0 = time.perf_counter()
        result = self.brain.process(text)
        elapsed = (time.perf_counter() - t0) * 1000

        self._metrics.counter("inputs_processed", 1)
        if result.matched:
            self._metrics.counter("reflex_matches", 1)
        self._metrics.histogram("process_time_ms", elapsed)

        return result

    async def add_action(
        self,
        action_id: str,
        pattern: str,
        intent: str = "",
        response: Optional[str] = None,
        priority: int = 100,
        handler: Optional[Callable[[str], Optional[str]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ReflexAction:
        """Register a custom reflex action.

        Args:
            action_id: Unique identifier.
            pattern: Regex pattern to match.
            intent: Intent label.
            response: Static response (or None if handler provides it).
            priority: Lower = higher priority.
            handler: Optional callable fn(text) → response.
            metadata: Arbitrary extra data.

        Returns:
            The registered ReflexAction.
        """
        if not self.brain:
            raise RuntimeError("ReflexService not initialized")

        action = ReflexAction(
            action_id=action_id,
            pattern=pattern,
            intent=intent,
            response=response,
            priority=priority,
            handler=handler,
            metadata=metadata or {},
        )
        self.brain.add_action(action)
        self._metrics.counter("actions_registered", 1)
        return action

    async def remove_action(self, action_id: str) -> bool:
        """Unregister a reflex action."""
        if not self.brain:
            raise RuntimeError("ReflexService not initialized")
        result = self.brain.remove_action(action_id)
        if result:
            self._metrics.counter("actions_removed", 1)
        return result

    async def list_actions(self) -> List[Dict[str, Any]]:
        """List all registered actions as dicts."""
        if not self.brain:
            raise RuntimeError("ReflexService not initialized")
        return [a.to_dict() for a in self.brain.list_actions()]

    async def get_action(self, action_id: str) -> Optional[Dict[str, Any]]:
        """Get a registered action by ID."""
        if not self.brain:
            raise RuntimeError("ReflexService not initialized")
        action = self.brain.get_action(action_id)
        return action.to_dict() if action else None

    async def health(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        action_count = self.brain.get_action_count() if self.brain else 0
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service_name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
            "registered_actions": action_count,
        }

    async def stats(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            "metrics": self._metrics.snapshot(),
        }
