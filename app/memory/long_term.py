"""
╔══════════════════════════════════════════════════════════════╗
║           PROCEDURAL MEMORY — Learned Skills Repository     ║
║   Stores and retrieves reusable skills as execution plans   ║
╚══════════════════════════════════════════════════════════════╝

Procedural memory is the "know-how" of the AI. It stores:
- Learned skills (how to deploy a server, generate APK, etc.)
- Execution plans (step-by-step procedures)
- Triggers (what activates each skill)
- Success metrics (how reliable each skill is)

When a new task comes in, procedural memory is checked first
to see if there's already a known skill for it.
"""

import logging
import time
import json
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class Skill:
    """A reusable skill in procedural memory."""
    skill_id: str
    name: str
    description: str
    category: str = "general"
    triggers: List[str] = field(default_factory=list)       # Keywords that activate this skill
    trigger_patterns: List[str] = field(default_factory=list)  # Regex patterns
    steps: List[Dict] = field(default_factory=list)          # Execution steps
    parameters: Dict[str, Any] = field(default_factory=dict)  # Required parameters
    success_count: int = 0
    failure_count: int = 0
    confidence: float = 0.5
    created_at: float = 0.0
    last_used: float = 0.0
    average_duration_ms: float = 0.0
    metadata: dict = field(default_factory=dict)


class ProceduralMemory:
    """Stores and manages reusable skills.

    Skills can be:
    - Learned automatically (via SkillLearner)
    - Registered manually (by developer)
    - Composed from existing skills
    """

    def __init__(self):
        """Initialise procedural memory with thread-safe storage for skills, triggers, and handlers."""
        self._lock = threading.RLock()
        self._skills: Dict[str, Skill] = {}          # skill_id → Skill
        self._trigger_index: Dict[str, str] = {}      # keyword → skill_id (for fast lookup)
        self._categories: Dict[str, List[str]] = defaultdict(list)  # category → [skill_ids]
        self._handler_registry: Dict[str, Callable] = {}  # skill_id → handler function

    # ── Skill Management ────────────────────────────────────────

    def store_skill(self, skill: Skill) -> bool:
        """Store a skill in procedural memory.

        Args:
            skill: The Skill to store.

        Returns:
            True if stored successfully.
        """
        with self._lock:
            if skill.skill_id in self._skills:
                # Update existing
                existing = self._skills[skill.skill_id]
                existing.success_count = skill.success_count
                existing.failure_count = skill.failure_count
                existing.confidence = skill.confidence
                existing.last_used = time.time()
                existing.steps = skill.steps or existing.steps
                logger.debug(f"ProceduralMemory: Updated skill '{skill.name}'")
            else:
                # New skill
                skill.created_at = time.time()
                self._skills[skill.skill_id] = skill

                # Index triggers
                for trigger in skill.triggers:
                    self._trigger_index[trigger.lower()] = skill.skill_id
                for pattern in skill.trigger_patterns:
                    self._trigger_index[pattern.lower()] = skill.skill_id

                # Index category
                self._categories[skill.category].append(skill.skill_id)

                logger.info(f"ProceduralMemory: Stored new skill '{skill.name}' in '{skill.category}'")
            return True

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """Retrieve a skill by ID."""
        with self._lock:
            skill = self._skills.get(skill_id)
            if skill:
                skill.last_used = time.time()
            return skill

    def find_skill(self, query: str) -> Optional[Skill]:
        """Find the best matching skill for a query.

        Checks:
        1. Direct trigger match
        2. Keyword match in triggers
        3. Substring match in name/description

        Returns the best matching skill or None.
        """
        q = query.lower().strip()
        with self._lock:
            best_match = None
            best_score = 0.0

            for skill in self._skills.values():
                # Check direct trigger match
                for trigger in skill.triggers:
                    if trigger.lower() == q:
                        return skill  # Exact match = instant return
                    if trigger.lower() in q:
                        score = len(trigger) / len(q)
                        if score > best_score:
                            best_score = score
                            best_match = skill

                # Check name match
                if skill.name.lower() in q:
                    score = len(skill.name) / len(q)
                    if score > best_score:
                        best_score = score
                        best_match = skill

                # Check description match
                if skill.description.lower() in q:
                    score = len(skill.description) / len(q) * 0.8
                    if score > best_score:
                        best_score = score
                        best_match = skill

            if best_match and best_score > 0.3:
                best_match.last_used = time.time()
                return best_match

            return None

    def search_skills(self, query: str, category: Optional[str] = None) -> List[Skill]:
        """Search skills by keyword."""
        q = query.lower()
        results = []

        with self._lock:
            skills_to_search = (
                [self._skills[sid] for sid in self._categories.get(category, [])]
                if category
                else list(self._skills.values())
            )

            for skill in skills_to_search:
                if q in skill.name.lower() or \
                   q in skill.description.lower() or \
                   any(q in t.lower() for t in skill.triggers):
                    results.append(skill)

        return results

    # ── Skill Registration ──────────────────────────────────────

    def register_skill(self, skill_id: str, handler: Callable) -> bool:
        """Register a handler function for a skill.

        This allows skills to have executable implementations.
        """
        with self._lock:
            if skill_id not in self._skills:
                logger.warning(f"ProceduralMemory: Cannot register handler for unknown skill '{skill_id}'")
                return False
            self._handler_registry[skill_id] = handler
            logger.info(f"ProceduralMemory: Registered handler for skill '{skill_id}'")
            return True

    def execute_skill(self, skill_id: str, params: Dict = None) -> Dict:
        """Execute a skill by ID.

        Args:
            skill_id: The skill to execute.
            params: Parameters for execution.

        Returns:
            Dict with execution result.
        """
        skill = self.get_skill(skill_id)
        if not skill:
            return {"success": False, "error": f"Skill '{skill_id}' not found"}

        params = params or {}

        # Check if there's a registered handler
        handler = self._handler_registry.get(skill_id)
        if handler:
            try:
                result = handler(params)
                with self._lock:
                    skill.success_count += 1
                return {"success": True, "result": result}
            except Exception as e:
                with self._lock:
                    skill.failure_count += 1
                return {"success": False, "error": str(e)}

        # No handler — return the steps as an execution plan
        return {
            "success": True,
            "skill_name": skill.name,
            "steps": skill.steps,
            "parameters_required": skill.parameters,
        }

    # ── Bulk Operations ─────────────────────────────────────────

    def get_skills_by_category(self, category: str) -> List[Skill]:
        """Get all skills in a category."""
        with self._lock:
            return [
                self._skills[sid]
                for sid in self._categories.get(category, [])
                if sid in self._skills
            ]

    def get_all_skills(self, min_confidence: float = 0.0) -> List[Dict]:
        """Get all skills as serializable dicts."""
        with self._lock:
            return [
                {
                    "id": s.skill_id,
                    "name": s.name,
                    "description": s.description,
                    "category": s.category,
                    "confidence": round(s.confidence, 3),
                    "success_count": s.success_count,
                    "failure_count": s.failure_count,
                    "triggers": s.triggers[:5],
                    "steps": len(s.steps),
                    "last_used": s.last_used,
                }
                for s in sorted(
                    self._skills.values(),
                    key=lambda x: x.confidence,
                    reverse=True,
                )
                if s.confidence >= min_confidence
            ]

    def remove_skill(self, skill_id: str) -> bool:
        """Remove a skill from procedural memory."""
        with self._lock:
            skill = self._skills.pop(skill_id, None)
            if skill:
                # Clean up indexes
                for trigger in skill.triggers:
                    self._trigger_index.pop(trigger.lower(), None)
                for pattern in skill.trigger_patterns:
                    self._trigger_index.pop(pattern.lower(), None)
                if skill.category in self._categories:
                    self._categories[skill.category] = [
                        sid for sid in self._categories[skill.category] if sid != skill_id
                    ]
                self._handler_registry.pop(skill_id, None)
                logger.info(f"ProceduralMemory: Removed skill '{skill_id}'")
                return True
            return False

    def get_stats(self) -> dict:
        """Return aggregate statistics about stored skills.

        Returns:
            Dict with total_skills, categories breakdown, avg_confidence,
            total_successes, total_failures, and skills_with_handlers count.
        """
        with self._lock:
            total_skills = len(self._skills)
            if total_skills == 0:
                return {"total_skills": 0, "categories": {}, "avg_confidence": 0.0}
            avg_conf = sum(s.confidence for s in self._skills.values()) / total_skills
            return {
                "total_skills": total_skills,
                "categories": {k: len(v) for k, v in self._categories.items()},
                "avg_confidence": round(avg_conf, 3),
                "total_successes": sum(s.success_count for s in self._skills.values()),
                "total_failures": sum(s.failure_count for s in self._skills.values()),
                "skills_with_handlers": len(self._handler_registry),
            }
