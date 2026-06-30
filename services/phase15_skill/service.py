"""
Phase 15 — Skill Router Service.

Wraps SkillRegistry and SkillRouter in a ServiceBase lifecycle.
"""

import time
import logging
from typing import Any, Dict, List, Optional

from services.base.service_base import ServiceBase
from .config import SkillConfig
from .models import SkillDefinition, SkillResult
from .skill_registry import SkillRegistry
from .skill_router import SkillRouter


class SkillRouterService(ServiceBase):
    """Service wrapper for the Skill Router.

    Manages the lifecycle of SkillRegistry and SkillRouter,
    and exposes their functionality through a clean service API.
    """

    def __init__(self, config: Optional[SkillConfig] = None):
        super().__init__(name="jarvis_skill_router", version="1.0.0")
        self.config = config or SkillConfig()
        self._registry: Optional[SkillRegistry] = None
        self._router: Optional[SkillRouter] = None
        self._start_time = 0.0
        self._logger = None

    async def initialize(self) -> bool:
        """Initialize the skill router service.

        Returns:
            True if initialization succeeded.
        """
        self._start_time = time.time()
        try:
            self._logger = logging.getLogger("skill_router_service")
            self._metrics.reset()

            self._registry = SkillRegistry(
                max_skills=self.config.max_skills,
                enable_versioning=self.config.enable_versioning,
            )

            self._router = SkillRouter(
                registry=self._registry,
                enable_fallback=self.config.enable_fallback,
                fallback_timeout_ms=self.config.fallback_timeout_ms,
            )

            self._initialized = True
            self._metrics.counter("initializations")
            self._logger.info("SkillRouterService initialized")
            return True

        except Exception as e:
            self._logger.error("SkillRouterService initialization failed: %s", e)
            self._initialized = False
            return False

    async def shutdown(self) -> None:
        """Shut down the skill router service."""
        if self._logger:
            self._logger.info("SkillRouterService shutting down...")
        self._registry = None
        self._router = None
        self._initialized = False

    async def health(self) -> Dict[str, Any]:
        """Return service health status."""
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        status = "healthy" if self._initialized else "unhealthy"
        return {
            "status": status,
            "service_name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
        }

    async def stats(self) -> Dict[str, Any]:
        """Return service statistics and metrics."""
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        registry_count = self._registry.count if self._registry else 0
        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            "initialized": self._initialized,
            "registry": {
                "skills_count": registry_count,
                "max_skills": self.config.max_skills,
                "enable_versioning": self.config.enable_versioning,
                "enable_fallback": self.config.enable_fallback,
            },
            "metrics": self._metrics.snapshot(),
        }

    def register_skill(self, definition: SkillDefinition) -> bool:
        """Register a skill.

        Args:
            definition: The SkillDefinition to register.

        Returns:
            True if registration succeeded.
        """
        if not self._registry:
            return False
        result = self._registry.register(definition)
        if result:
            self._metrics.counter("skills_registered")
        return result

    def unregister_skill(self, skill_id: str) -> bool:
        """Unregister a skill by ID.

        Args:
            skill_id: The ID of the skill to unregister.

        Returns:
            True if the skill was removed.
        """
        if not self._registry:
            return False
        result = self._registry.unregister(skill_id)
        if result:
            self._metrics.counter("skills_unregistered")
        return result

    def route(
        self,
        intent: str,
        entities: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[SkillResult]:
        """Route an intent to matching skills.

        Args:
            intent: The intent to route.
            entities: Optional extracted entities.
            context: Optional routing context.

        Returns:
            List of SkillResult objects.
        """
        if not self._router:
            return []
        self._metrics.counter("routes")
        return self._router.route(intent, entities, context)

    def list_skills(self) -> List[SkillDefinition]:
        """List all registered skills.

        Returns:
            List of SkillDefinition objects.
        """
        if not self._registry:
            return []
        return self._registry.list()
