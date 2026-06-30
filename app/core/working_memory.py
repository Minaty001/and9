"""
app/core/working_memory.py — Current task/conversation state manager.

Working memory holds the immediate context: what the user is doing,
what the current task is, the active focus area, and transient state
that doesn't need to persist in long-term memory.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


class WorkingMemory:
    """Short-term state for the current session.

    Data is stored in Supabase `working_memory` table and also
    held in-memory for sub-millisecond access within a session.
    """

    def __init__(self, memory):
        self.memory = memory
        self._local: dict = {}          # in-memory cache: session_id → state

    # ── State Management ──────────────────────────────────────────

    def set_focus(self, session_id: int, focus: str) -> bool:
        """Set the current focus area (e.g. 'coding', 'research')."""
        self._set_local(session_id, "focus", focus)
        return self._upsert(session_id, {"focus": focus})

    def get_focus(self, session_id: int) -> str:
        """Get the current focus area."""
        state = self._get_state(session_id)
        return state.get("focus", "")

    def set_current_task(self, session_id: int, task: str) -> bool:
        """Set the current active task description."""
        self._set_local(session_id, "current_task", task)
        return self._upsert(session_id, {"current_task": task})

    def get_current_task(self, session_id: int) -> str:
        """Get the current active task description."""
        state = self._get_state(session_id)
        return state.get("current_task", "")

    def set_state(self, session_id: int, state: str) -> bool:
        """Set the session state (idle, thinking, executing, waiting)."""
        self._set_local(session_id, "state", state)
        return self._upsert(session_id, {"state": state})

    def get_state(self, session_id: int) -> str:
        """Get the session state."""
        s = self._get_state(session_id)
        return s.get("state", "idle")

    def set_metadata(self, session_id: int, key: str, value) -> bool:
        """Store arbitrary metadata key-value pair in working memory."""
        current = self._get_state(session_id)
        meta = current.get("metadata", {})
        meta[key] = value
        self._set_local(session_id, "metadata", meta)
        return self._upsert(session_id, {"metadata": meta})

    def get_metadata(self, session_id: int, key: str, default=None):
        """Retrieve arbitrary metadata by key."""
        state = self._get_state(session_id)
        return state.get("metadata", {}).get(key, default)

    def clear(self, session_id: int) -> bool:
        """Reset working memory for a session to defaults."""
        self._local.pop(session_id, None)
        return self._upsert(session_id, {
            "focus": "", "current_task": "", "state": "idle", "metadata": {},
        })

    # ── Internal ──────────────────────────────────────────────────

    def _set_local(self, session_id: int, key: str, value):
        if session_id not in self._local:
            self._local[session_id] = {}
        self._local[session_id][key] = value

    def _get_state(self, session_id: int) -> dict:
        # Fast in-memory path
        if session_id in self._local:
            return self._local[session_id]

        # Load from DB on first access
        result = self._db_get(session_id)
        if result:
            self._local[session_id] = result
            return result

        # Create default
        default = {"focus": "", "current_task": "", "state": "idle", "metadata": {}}
        self._local[session_id] = default
        self._upsert(session_id, default)
        return default

    def _upsert(self, session_id: int, data: dict) -> bool:
        sb = self.memory._sb
        if not sb:
            return True                     # no-op in fallback mode
        try:
            existing = sb.table("working_memory") \
                .select("id") \
                .eq("session_id", session_id) \
                .limit(1) \
                .execute()
            now = datetime.now(timezone.utc).isoformat()
            data["session_id"] = session_id
            data["updated_at"] = now
            if existing and existing.data:
                sb.table("working_memory") \
                    .update(data) \
                    .eq("session_id", session_id) \
                    .execute()
            else:
                data["created_at"] = now
                sb.table("working_memory") \
                    .insert(data) \
                    .execute()
            return True
        except Exception as e:
            logger.debug(f"WorkingMemory upsert failed: {e}")
            return False

    def _db_get(self, session_id: int) -> Optional[dict]:
        sb = self.memory._sb
        if not sb:
            return None
        try:
            res = sb.table("working_memory") \
                .select("*") \
                .eq("session_id", session_id) \
                .order("id", desc=True) \
                .limit(1) \
                .execute()
            if res and res.data:
                row = res.data[0]
                return {
                    "focus": row.get("focus", ""),
                    "current_task": row.get("current_task", ""),
                    "state": row.get("state", "idle"),
                    "metadata": row.get("metadata", {}),
                }
        except Exception as e:
            logger.debug(f"WorkingMemory DB get failed: {e}")
        return None
