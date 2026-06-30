"""
Phase 15 — Skill Registry.

Manages registration, unregistration, lookup, and versioning of skills.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from .models import SkillDefinition, SkillResult


class VersionHistory:
    """Tracks version history for a skill."""

    def __init__(self):
        self._history: Dict[str, List[SkillDefinition]] = {}

    def add_version(self, skill: SkillDefinition) -> None:
        """Record a version entry for a skill."""
        sid = skill.id
        if sid not in self._history:
            self._history[sid] = []
        self._history[sid].append(skill)

    def get_history(self, skill_id: str) -> List[SkillDefinition]:
        """Return version history for a skill."""
        return list(self._history.get(skill_id, []))

    def clear(self, skill_id: str) -> None:
        """Clear version history for a skill."""
        self._history.pop(skill_id, None)


class SkillRegistry:
    """Registry for managing skill definitions.

    Supports registration, unregistration, lookup by ID, and
    intent-based discovery with entity matching and priority sorting.
    """

    def __init__(self, max_skills: int = 100, enable_versioning: bool = True):
        self._max_skills = max_skills
        self._enable_versioning = enable_versioning
        self._skills: Dict[str, SkillDefinition] = {}
        self._version_history = VersionHistory() if enable_versioning else None
        self._logger = logging.getLogger("skill_registry")

    def register(self, definition: SkillDefinition) -> bool:
        """Register a skill definition.

        Args:
            definition: The SkillDefinition to register.

        Returns:
            True if registration succeeded, False otherwise.
        """
        if len(self._skills) >= self._max_skills:
            self._logger.warning("Skill registry full (%d max)", self._max_skills)
            return False

        sid = definition.id
        if sid in self._skills:
            self._logger.warning("Skill '%s' already registered, overwriting", sid)

        self._skills[sid] = definition

        if self._enable_versioning and self._version_history:
            self._version_history.add_version(definition)

        self._logger.info("Registered skill '%s' (v%s)", definition.name, definition.version)
        return True

    def unregister(self, skill_id: str) -> bool:
        """Unregister a skill by ID.

        Args:
            skill_id: The ID of the skill to remove.

        Returns:
            True if the skill was removed, False if not found.
        """
        if skill_id not in self._skills:
            self._logger.warning("Skill '%s' not found for unregistration", skill_id)
            return False

        removed = self._skills.pop(skill_id)
        if self._enable_versioning and self._version_history:
            self._version_history.clear(skill_id)

        self._logger.info("Unregistered skill '%s' (v%s)", removed.name, removed.version)
        return True

    def get(self, skill_id: str) -> Optional[SkillDefinition]:
        """Retrieve a skill definition by ID.

        Args:
            skill_id: The ID of the skill.

        Returns:
            SkillDefinition or None if not found.
        """
        return self._skills.get(skill_id)

    def find_by_intent(
        self,
        intent: str,
        entities: Optional[Dict[str, Any]] = None,
    ) -> List[SkillDefinition]:
        """Find skills matching an intent, sorted by priority and entity match count.

        Args:
            intent: The intent to match.
            entities: Optional dict of extracted entities.

        Returns:
            List of matching SkillDefinitions sorted by priority (descending),
            then by matching entity count (descending).
        """
        entities = entities or {}
        entity_keys = set(entities.keys())

        matches = []
        for skill in self._skills.values():
            if not skill.enabled:
                continue
            if intent not in skill.intents:
                continue

            # Count how many required entities are satisfied
            required_set = set(skill.required_entities)
            matched_entities = len(required_set & entity_keys)

            # Only include if all required entities are present
            if required_set and not required_set.issubset(entity_keys):
                continue

            matches.append((skill, matched_entities))

        # Sort by priority (desc), then matched entity count (desc)
        matches.sort(key=lambda x: (-x[0].priority, -x[1]))

        return [m[0] for m in matches]

    def list(self) -> List[SkillDefinition]:
        """List all registered skill definitions.

        Returns:
            List of all SkillDefinition objects.
        """
        return list(self._skills.values())

    def get_version_history(self, skill_id: str) -> List[SkillDefinition]:
        """Retrieve version history for a skill.

        Args:
            skill_id: The ID of the skill.

        Returns:
            List of SkillDefinition versions, newest first.
        """
        if not self._enable_versioning or not self._version_history:
            return []
        return list(reversed(self._version_history.get_history(skill_id)))

    @property
    def count(self) -> int:
        """Return the number of registered skills."""
        return len(self._skills)
