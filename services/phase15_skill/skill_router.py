"""
Phase 15 — Skill Router.

Routes intents to registered skills, executes them in priority order,
and provides fallback support when a skill fails.
"""

import time
import logging
import asyncio
from typing import Any, Dict, List, Optional

from .models import SkillDefinition, SkillResult
from .skill_registry import SkillRegistry


class SkillRouter:
    """Routes intents to registered skills with fallback support.

    Finds matching skills via the registry, executes them in priority
    order, and falls back to the next matching skill if a primary skill
    fails.
    """

    def __init__(
        self,
        registry: SkillRegistry,
        enable_fallback: bool = True,
        fallback_timeout_ms: int = 5000,
    ):
        self._registry = registry
        self._enable_fallback = enable_fallback
        self._fallback_timeout_ms = fallback_timeout_ms
        self._logger = logging.getLogger("skill_router")

    def route(
        self,
        intent: str,
        entities: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[SkillResult]:
        """Route an intent to matching skills and execute them.

        Skills are executed in priority order. If the primary skill fails
        and fallback is enabled, the next matching skill is tried.

        Args:
            intent: The intent to route.
            entities: Optional extracted entities dict.
            context: Optional routing context dict.

        Returns:
            List of SkillResult objects from all executed skills.
        """
        entities = entities or {}
        context = context or {}

        # Find matching skills sorted by priority
        matches = self._registry.find_by_intent(intent, entities)

        if not matches:
            self._logger.info("No skills found for intent '%s'", intent)
            return []

        results: List[SkillResult] = []
        primary_failed = True

        for skill in matches:
            if not skill.enabled:
                continue

            # Execute the skill
            result = self._execute_skill(skill, intent, entities, context)
            results.append(result)

            if result.success:
                primary_failed = False
                # Primary skill succeeded, only execute other high-priority ones
                # if this is the first success or we're collecting all
                # For simplicity, we stop at first success by default
                if not context.get("collect_all", False):
                    break
            else:
                # Skill failed — if fallback is enabled, continue to next
                if not self._enable_fallback:
                    break
                self._logger.info(
                    "Skill '%s' failed, attempting fallback (timeout=%dms)",
                    skill.name,
                    self._fallback_timeout_ms,
                )

        return results

    def _execute_skill(
        self,
        skill: SkillDefinition,
        intent: str,
        entities: Dict[str, Any],
        context: Dict[str, Any],
    ) -> SkillResult:
        """Execute a single skill and return the result.

        In a real implementation, this would call the skill's registered
        handler. For now, it simulates execution based on skill config.
        """
        start = time.perf_counter()

        try:
            # Simulated execution — in production, this dispatches to the
            # actual skill plugin registered with the system.
            simulated_fail = skill.config.get("simulate_failure", False)

            if simulated_fail:
                duration_ms = (time.perf_counter() - start) * 1000
                return SkillResult(
                    skill_id=skill.id,
                    success=False,
                    output="",
                    confidence=0.0,
                    duration_ms=duration_ms,
                    error=f"Simulated failure for skill '{skill.name}'",
                )

            # Simulate a small processing delay
            delay_ms = skill.config.get("execution_delay_ms", 10)
            if delay_ms > 0:
                time.sleep(delay_ms / 1000.0)

            duration_ms = (time.perf_counter() - start) * 1000
            return SkillResult(
                skill_id=skill.id,
                success=True,
                output=f"Skill '{skill.name}' executed successfully for intent '{intent}'",
                confidence=0.95,
                duration_ms=duration_ms,
                error=None,
            )

        except Exception as e:
            duration_ms = (time.perf_counter() - start) * 1000
            return SkillResult(
                skill_id=skill.id,
                success=False,
                output="",
                confidence=0.0,
                duration_ms=duration_ms,
                error=str(e),
            )
