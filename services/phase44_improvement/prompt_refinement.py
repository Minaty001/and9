"""
Phase 44 — Prompt Refiner.

Manages versioned prompt templates with support for proposing
refinements, activating versions, rolling back, and comparing.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import PromptVersion
from .config import ImprovementConfig

logger = logging.getLogger(__name__)


class PromptRefiner:
    """Manages prompt template versions and refinements.

    Usage:
        pr = PromptRefiner()
        v1 = pr.register_prompt("greeting", "Hello {{name}}!")
        v2 = pr.propose_refinement("greeting", "Hi {{name}}!", "More casual tone")
        pr.activate_version("greeting", 2)
    """

    def __init__(self, config: Optional[ImprovementConfig] = None):
        self.config = config or ImprovementConfig()
        self._prompts: Dict[str, List[PromptVersion]] = {}

    def register_prompt(self, name: str, content: str) -> PromptVersion:
        """Register a new prompt template.

        Args:
            name: Logical prompt name.
            content: Prompt template content.

        Returns:
            The created PromptVersion (version 1).
        """
        version_id = uuid.uuid4().hex[:12]
        pv = PromptVersion(
            id=version_id,
            prompt_name=name,
            version=1,
            content=content,
            is_active=True,
        )
        self._prompts[name] = [pv]
        logger.info("Registered prompt '%s' (v1)", name)
        return pv

    def get_active_prompt(self, name: str) -> Optional[PromptVersion]:
        """Get the active version of a prompt.

        Args:
            name: Prompt name.

        Returns:
            Active PromptVersion or None.
        """
        versions = self._prompts.get(name, [])
        for v in versions:
            if v.is_active:
                return v
        return None

    def propose_refinement(
        self,
        name: str,
        new_content: str,
        reason: str = "",
    ) -> Optional[PromptVersion]:
        """Create a new version based on an existing prompt.

        The new version is created as inactive; it must be activated
        explicitly.

        Args:
            name: Prompt name.
            new_content: The refined prompt content.
            reason: Reason for the refinement.

        Returns:
            The new PromptVersion, or None if the prompt doesn't exist.
        """
        versions = self._prompts.get(name)
        if not versions:
            logger.warning("Prompt '%s' not found. Register it first.", name)
            return None

        # Enforce max versions
        if len(versions) >= self.config.max_prompt_versions:
            # Remove oldest non-active version
            oldest = sorted(versions, key=lambda v: (v.is_active, v.version))[0]
            if oldest != self.get_active_prompt(name):
                versions.remove(oldest)
                logger.debug("Removed old prompt version %d for '%s'", oldest.version, name)

        active = self.get_active_prompt(name)
        parent_version = active.version if active else versions[-1].version

        version_id = uuid.uuid4().hex[:12]
        new_version = PromptVersion(
            id=version_id,
            prompt_name=name,
            version=len(versions) + 1,
            content=new_content,
            parent_version=parent_version,
            change_reason=reason,
            is_active=False,
        )
        versions.append(new_version)
        logger.info("Proposed refinement for '%s' (v%d): %s", name, new_version.version, reason)
        return new_version

    def activate_version(self, name: str, version: int) -> bool:
        """Switch the active version of a prompt.

        Args:
            name: Prompt name.
            version: Version number to activate.

        Returns:
            True if activated, False if version not found.
        """
        versions = self._prompts.get(name, [])
        target = None
        for v in versions:
            if v.version == version:
                target = v
            # Deactivate all others
            v.is_active = False

        if not target:
            return False

        target.is_active = True
        logger.info("Activated prompt '%s' v%d", name, version)
        return True

    def rollback_prompt(self, name: str) -> bool:
        """Rollback to the previous active version.

        Args:
            name: Prompt name.

        Returns:
            True if rollback succeeded, False if no previous version.
        """
        versions = self._prompts.get(name, [])
        if len(versions) < 2:
            return False

        active = self.get_active_prompt(name)
        if not active:
            return False

        # Find the version right before the active one
        prev = None
        for v in sorted(versions, key=lambda x: x.version):
            if v.version < active.version:
                prev = v

        if prev is None:
            return False

        # Deactivate all, activate the previous
        for v in versions:
            v.is_active = False
        prev.is_active = True
        logger.info("Rolled back prompt '%s' to v%d", name, prev.version)
        return True

    def compare_versions(self, name: str, v1_num: int, v2_num: int) -> Dict[str, Any]:
        """Compare two versions of a prompt.

        Args:
            name: Prompt name.
            v1_num: First version number.
            v2_num: Second version number.

        Returns:
            Dict with comparison data or error.
        """
        versions = self._prompts.get(name, [])
        v1 = next((v for v in versions if v.version == v1_num), None)
        v2 = next((v for v in versions if v.version == v2_num), None)

        if not v1 or not v2:
            missing = "v1" if not v1 else "v2"
            return {"error": f"Version {missing} not found for prompt '{name}'"}

        return {
            "prompt_name": name,
            "v1_version": v1_num,
            "v2_version": v2_num,
            "v1_content": v1.content,
            "v2_content": v2.content,
            "v1_active": v1.is_active,
            "v2_active": v2.is_active,
            "v1_created": v1.created_at.isoformat(),
            "v2_created": v2.created_at.isoformat(),
            "v1_reason": v1.change_reason,
            "v2_reason": v2.change_reason,
            "content_changed": v1.content != v2.content,
        }
