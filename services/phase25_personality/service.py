"""
Phase 25 — Personality Engine Service.

ServiceBase wrapper for the personality engine.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Dict, List, Optional

from services.base.service_base import ServiceBase
from .config import PersonalityConfig
from .models import Persona, PersonalityProfile
from .engine import PersonalityEngine

logger = logging.getLogger(__name__)


class PersonalityEngineService(ServiceBase):
    """Personality engine service managing personas and response processing.

    Usage:
        svc = PersonalityEngineService()
        await svc.initialize()
        greeting = await svc.generate_greeting()
    """

    def __init__(self, config: Optional[PersonalityConfig] = None):
        super().__init__(name="jarvis_personality", version="1.0.0")
        self.config = config or PersonalityConfig()
        self.engine: Optional[PersonalityEngine] = None
        self._start_time = 0.0

    async def initialize(self) -> bool:
        """Initialize the personality engine service."""
        self._start_time = time.time()
        try:
            self.engine = PersonalityEngine(
                active_persona_id=self.config.active_persona,
            )
            self._metrics.reset()
            self._initialized = True
            logger.info("PersonalityEngineService initialized")
            return True
        except Exception as e:
            logger.error("PersonalityEngineService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        """Shut down the personality engine service."""
        logger.info("PersonalityEngineService shutting down...")
        self._initialized = False

    async def apply_tone(self, text: str, persona_id: Optional[str] = None) -> str:
        """Apply tone adjustments to text.

        Args:
            text: Input text.
            persona_id: Optional persona ID (uses active if not specified).

        Returns:
            Tone-adjusted text.
        """
        if not self._initialized or not self.engine:
            raise RuntimeError("PersonalityEngineService not initialized")

        persona = self._resolve_persona(persona_id)
        self._metrics.counter("tone_applications", 1)
        return self.engine.apply_tone(text, persona)

    async def generate_greeting(self, context: Optional[Dict[str, Any]] = None) -> str:
        """Generate a greeting based on active persona.

        Args:
            context: Optional context for time-based greetings.

        Returns:
            Greeting string.
        """
        if not self._initialized or not self.engine:
            raise RuntimeError("PersonalityEngineService not initialized")

        self._metrics.counter("greetings_generated", 1)
        return self.engine.generate_greeting(context)

    async def constrain_response(self, text: str, persona_id: Optional[str] = None) -> str:
        """Apply response constraints.

        Args:
            text: Response text.
            persona_id: Optional persona ID.

        Returns:
            Constrained text.
        """
        if not self._initialized or not self.engine:
            raise RuntimeError("PersonalityEngineService not initialized")

        persona = self._resolve_persona(persona_id)
        self._metrics.counter("responses_constrained", 1)
        return self.engine.constrain_response(text, persona)

    async def set_persona(self, persona_id: str) -> bool:
        """Set the active persona.

        Args:
            persona_id: Persona identifier.

        Returns:
            True if set successfully.
        """
        if not self._initialized or not self.engine:
            raise RuntimeError("PersonalityEngineService not initialized")

        if not self.config.enable_persona_switching:
            logger.warning("Persona switching is disabled")
            return False

        result = self.engine.set_persona(persona_id)
        if result:
            self._metrics.counter("persona_switches", 1)
        return result

    async def get_persona(self, persona_id: Optional[str] = None) -> Optional[Persona]:
        """Get a persona by ID, or active persona if not specified.

        Args:
            persona_id: Optional persona ID.

        Returns:
            Persona or None.
        """
        if not self._initialized or not self.engine:
            raise RuntimeError("PersonalityEngineService not initialized")

        if persona_id:
            return self.engine.get_persona_by_id(persona_id)
        return self.engine.get_persona()

    async def detect_tone(self, text: str) -> str:
        """Detect the tone of a text.

        Args:
            text: Text to analyze.

        Returns:
            Detected tone string.
        """
        if not self._initialized or not self.engine:
            raise RuntimeError("PersonalityEngineService not initialized")

        self._metrics.counter("tone_detections", 1)
        return self.engine.detect_tone(text)

    async def list_personas(self) -> List[str]:
        """List all registered persona IDs.

        Returns:
            List of persona ID strings.
        """
        if not self._initialized or not self.engine:
            raise RuntimeError("PersonalityEngineService not initialized")
        return self.engine.list_personas()

    async def register_persona(self, persona: Persona) -> bool:
        """Register a new persona.

        Args:
            persona: Persona to register.

        Returns:
            True if registered successfully.
        """
        if not self._initialized or not self.engine:
            raise RuntimeError("PersonalityEngineService not initialized")
        result = self.engine.register_persona(persona)
        if result:
            self._metrics.counter("personas_registered", 1)
        return result

    async def get_profile(self) -> Optional[PersonalityProfile]:
        """Get the current personality profile.

        Returns:
            PersonalityProfile or None.
        """
        if not self._initialized or not self.engine:
            raise RuntimeError("PersonalityEngineService not initialized")
        return self.engine.get_profile()

    async def health(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service_name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
        }

    async def stats(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        persona = self.engine.get_persona() if self.engine else None
        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            "active_persona": persona.id if persona else "unknown",
            "persona_count": len(self.engine.list_personas()) if self.engine else 0,
            "metrics": self._metrics.snapshot(),
        }

    def _resolve_persona(self, persona_id: Optional[str] = None) -> Optional[Persona]:
        """Resolve a persona ID to a Persona object."""
        if persona_id:
            return self.engine.get_persona_by_id(persona_id)
        return self.engine.get_persona()
