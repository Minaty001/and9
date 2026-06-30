"""
Phase 15 — Skill Router.

Plugin registry for skills, route by intent+entities, versioning, fallbacks.
"""

from .config import SkillConfig
from .models import SkillDefinition, SkillResult
from .skill_registry import SkillRegistry
from .skill_router import SkillRouter
from .service import SkillRouterService

__all__ = [
    "SkillConfig",
    "SkillDefinition",
    "SkillResult",
    "SkillRegistry",
    "SkillRouter",
    "SkillRouterService",
]
