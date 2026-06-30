"""
app/core/goal_tracker.py — Goal & Project tracking layer.

Part of the JARVIS Cognitive Architecture:
  Conscious Brain → sets/updates goals
  Subconscious Brain → retrieves active goals for context
  Reflection Engine → marks goals complete, generates reviews

Supabase tables required (see supabase_schema.sql):
  - goals
  - projects
"""
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class GoalTracker:
    """Manages user goals, tasks, and projects via Supabase."""

    STATUS_ACTIVE    = "active"
    STATUS_DONE      = "done"
    STATUS_PAUSED    = "paused"
    STATUS_CANCELLED = "cancelled"

    PRIORITY_HIGH   = "high"
    PRIORITY_MEDIUM = "medium"
    PRIORITY_LOW    = "low"

    def __init__(self, memory):
        """Pass the Memory instance — shares same Supabase client."""
        self._mem = memory

    def _q(self, table):
        if not self._mem._ok:
            return None
        return self._mem._sb.table(table)

    def _safe(self, fn, default=None):
        try:
            return fn()
        except Exception as e:
            logger.warning(f"GoalTracker error: {e}")
            return default

    # ════════════════════════════════════════════════════════════
    # Goals
    # ════════════════════════════════════════════════════════════

    def add_goal(self, title: str, description: str = "",
                 priority: str = "medium", deadline: Optional[str] = None,
                 project_id: Optional[int] = None) -> Optional[dict]:
        """Create a new goal. Returns the created record."""
        q = self._q("goals")
        if q is None:
            # in-memory fallback
            g = {"id": len(self._mem._mem.get("goals", [])) + 1,
                 "title": title, "description": description,
                 "priority": priority, "status": self.STATUS_ACTIVE,
                 "deadline": deadline, "project_id": project_id,
                 "created_at": datetime.utcnow().isoformat()}
            self._mem._mem.setdefault("goals", []).append(g)
            return g
        res = self._safe(lambda: q.insert({
            "title": title, "description": description,
            "priority": priority, "status": self.STATUS_ACTIVE,
            "deadline": deadline, "project_id": project_id,
        }).execute(), None)
        return res.data[0] if res and res.data else None

    def get_active_goals(self, limit: int = 10) -> list:
        """Fetch active goals ordered by priority."""
        q = self._q("goals")
        if q is None:
            return [g for g in self._mem._mem.get("goals", [])
                    if g.get("status") == self.STATUS_ACTIVE][:limit]
        res = self._safe(lambda: q.select("*")
                         .eq("status", self.STATUS_ACTIVE)
                         .order("created_at", desc=False)
                         .limit(limit).execute(), None)
        return res.data if res and res.data else []

    def complete_goal(self, goal_id: int) -> bool:
        """Mark a goal as done."""
        q = self._q("goals")
        if q is None:
            for g in self._mem._mem.get("goals", []):
                if g["id"] == goal_id:
                    g["status"] = self.STATUS_DONE
                    return True
            return False
        res = self._safe(lambda: q.update({
            "status": self.STATUS_DONE,
            "completed_at": datetime.utcnow().isoformat()
        }).eq("id", goal_id).execute(), None)
        return bool(res and res.data)

    def update_goal_status(self, goal_id: int, status: str) -> bool:
        q = self._q("goals")
        if q is None:
            for g in self._mem._mem.get("goals", []):
                if g["id"] == goal_id:
                    g["status"] = status
                    return True
            return False
        res = self._safe(lambda: q.update({"status": status})
                         .eq("id", goal_id).execute(), None)
        return bool(res and res.data)

    def get_all_goals(self) -> list:
        q = self._q("goals")
        if q is None:
            return self._mem._mem.get("goals", [])
        res = self._safe(lambda: q.select("*")
                         .order("created_at", desc=True).execute(), None)
        return res.data if res and res.data else []

    def delete_goal(self, goal_id: int) -> bool:
        q = self._q("goals")
        if q is None:
            goals = self._mem._mem.get("goals", [])
            before = len(goals)
            self._mem._mem["goals"] = [g for g in goals if g["id"] != goal_id]
            return len(self._mem._mem["goals"]) < before
        res = self._safe(lambda: q.delete().eq("id", goal_id).execute(), None)
        return bool(res and res.data)

    # ════════════════════════════════════════════════════════════
    # Projects
    # ════════════════════════════════════════════════════════════

    def add_project(self, name: str, description: str = "",
                    status: str = "active") -> Optional[dict]:
        q = self._q("projects")
        if q is None:
            p = {"id": len(self._mem._mem.get("projects", [])) + 1,
                 "name": name, "description": description, "status": status,
                 "created_at": datetime.utcnow().isoformat()}
            self._mem._mem.setdefault("projects", []).append(p)
            return p
        res = self._safe(lambda: q.insert({
            "name": name, "description": description, "status": status
        }).execute(), None)
        return res.data[0] if res and res.data else None

    def get_active_projects(self) -> list:
        q = self._q("projects")
        if q is None:
            return [p for p in self._mem._mem.get("projects", [])
                    if p.get("status") == "active"]
        res = self._safe(lambda: q.select("*").eq("status", "active")
                         .order("created_at", desc=True).execute(), None)
        return res.data if res and res.data else []

    # ════════════════════════════════════════════════════════════
    # Context Summary for LLM
    # ════════════════════════════════════════════════════════════

    def build_goal_context(self) -> str:
        """Return a compact string for injecting into LLM system prompt."""
        goals = self.get_active_goals(5)
        projects = self.get_active_projects()
        if not goals and not projects:
            return ""

        lines = ["═══ ACTIVE GOALS & PROJECTS ═══"]
        for g in goals:
            dl = f" (deadline: {g['deadline']})" if g.get("deadline") else ""
            lines.append(f"  • [{g.get('priority','med').upper()}] {g['title']}{dl}")
        for p in projects:
            lines.append(f"  🗂 Project: {p['name']} — {p.get('description','')}")
        lines.append("Jab relevant ho toh in goals ko naturally conversation mein reference karo.")
        return "\n".join(lines)
