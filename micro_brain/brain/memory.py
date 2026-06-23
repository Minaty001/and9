"""
╔══════════════════════════════════════════════════╗
║           BRAIN 2: MEMORY BRAIN                  ║
║   SQLite-based multi-layer memory system         ║
╚══════════════════════════════════════════════════╝

Purpose:
    Store and manage memories across multiple time scales.

Memory Types:
    Working Memory   - Current context (volatile, small)
    Episodic Memory  - Personal experiences
    Semantic Memory  - Facts and knowledge
    User Preferences - User settings and likes
    Skills           - Learned capabilities
    Habits           - Patterned behaviors
    Goals            - User objectives
"""

import os
import json
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from config import MEMORY_CONFIG, DB_SCHEMA
from utils.logger import get_logger

logger = get_logger()


class MemoryBrain:
    """
    Memory Brain - Multi-layer memory with SQLite persistence.

    Features:
    - Working, episodic, semantic, preference, skill, habit, goal storage
    - Importance scoring (0.0 → 1.0)
    - Automatic forgetting of low-importance memories
    - Promotion of high-importance memories
    - Thread-safe with connection pooling
    """

    def __init__(self):
        self.db_path = MEMORY_CONFIG["db_path"]
        self._local = threading.local()
        self._cache = {}
        self._init_database()

    @contextmanager
    def _get_conn(self):
        """Get a thread-local database connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, timeout=10)
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn.execute("PRAGMA cache_size=-4000")  # ~4MB cache
            self._local.conn.execute("PRAGMA temp_store=MEMORY")
            self._local.conn.row_factory = sqlite3.Row
        yield self._local.conn

    def _init_database(self):
        """Initialize database schema."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._get_conn() as conn:
            for table_name, schema in DB_SCHEMA.items():
                conn.execute(schema)
            conn.commit()
        logger.info(f"MemoryBrain: Database initialized at {self.db_path}")

    # ═══════════════════════════════════════════════════════════
    # WORKING MEMORY
    # ═══════════════════════════════════════════════════════════

    def save_working_memory(self, content: str, context: str = "",
                            importance: float = 0.5) -> int:
        """Save to working memory."""
        with self._get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO working_memory (content, context, importance) VALUES (?, ?, ?)",
                (content, context, importance),
            )
            conn.commit()
            # Enforce working memory size limit
            self._trim_table("working_memory", MEMORY_CONFIG["working_memory_size"])
            return cur.lastrowid

    def get_working_memory(self, limit: int = 10) -> List[Dict]:
        """Get recent working memory items."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM working_memory ORDER BY last_accessed DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    # ═══════════════════════════════════════════════════════════
    # EPISODIC MEMORY
    # ═══════════════════════════════════════════════════════════

    def save_episodic_memory(self, event: str, emotion: str = "",
                             importance: float = 0.5, context: str = "") -> int:
        """Save an episodic memory (personal experience)."""
        with self._get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO episodic_memory (event, emotion, importance, context) VALUES (?, ?, ?, ?)",
                (event, emotion, importance, context),
            )
            conn.commit()
            self._auto_forget()
            return cur.lastrowid

    def recall_episodic_memory(self, query: str, limit: int = 10) -> List[Dict]:
        """Recall episodic memories matching a query."""
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT *, CASE
                    WHEN event LIKE ? THEN 1.0
                    WHEN context LIKE ? THEN 0.8
                    ELSE 0.5
                END as relevance
                FROM episodic_memory
                WHERE event LIKE ? OR context LIKE ?
                ORDER BY relevance DESC, importance DESC, timestamp DESC
                LIMIT ?""",
                (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%", limit),
            ).fetchall()
            self._update_access_count(conn, "episodic_memory", [r["id"] for r in rows])
            return [dict(r) for r in rows]

    # ═══════════════════════════════════════════════════════════
    # SEMANTIC MEMORY
    # ═══════════════════════════════════════════════════════════

    def save_semantic_memory(self, key: str, value: str, category: str = "",
                             confidence: float = 1.0) -> int:
        """Save a semantic memory (fact/knowledge)."""
        with self._get_conn() as conn:
            cur = conn.execute(
                """INSERT INTO semantic_memory (key, value, category, confidence)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(key) DO UPDATE SET
                       value = excluded.value,
                       confidence = excluded.confidence,
                       timestamp = CURRENT_TIMESTAMP""",
                (key, value, category, confidence),
            )
            conn.commit()
            return cur.lastrowid

    def recall_semantic_memory(self, key: str) -> Optional[Dict]:
        """Recall a semantic memory by key."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM semantic_memory WHERE key = ?", (key,)
            ).fetchone()
            return dict(row) if row else None

    def search_semantic_memory(self, query: str, category: str = "",
                               limit: int = 20) -> List[Dict]:
        """Search semantic memories."""
        with self._get_conn() as conn:
            if category:
                rows = conn.execute(
                    """SELECT * FROM semantic_memory
                       WHERE (key LIKE ? OR value LIKE ?) AND category = ?
                       ORDER BY confidence DESC LIMIT ?""",
                    (f"%{query}%", f"%{query}%", category, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM semantic_memory
                       WHERE key LIKE ? OR value LIKE ?
                       ORDER BY confidence DESC LIMIT ?""",
                    (f"%{query}%", f"%{query}%", limit),
                ).fetchall()
            return [dict(r) for r in rows]

    # ═══════════════════════════════════════════════════════════
    # USER PREFERENCES
    # ═══════════════════════════════════════════════════════════

    def save_preference(self, key: str, value: str, category: str = "",
                        confidence: float = 1.0) -> int:
        """Save a user preference."""
        with self._get_conn() as conn:
            cur = conn.execute(
                """INSERT INTO user_preferences (pref_key, pref_value, category, confidence)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(pref_key) DO UPDATE SET
                       pref_value = excluded.pref_value,
                       confidence = excluded.confidence,
                       timestamp = CURRENT_TIMESTAMP""",
                (key, value, category, confidence),
            )
            conn.commit()
            return cur.lastrowid

    def get_preference(self, key: str) -> Optional[str]:
        """Get a user preference."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT pref_value FROM user_preferences WHERE pref_key = ?", (key,)
            ).fetchone()
            return row["pref_value"] if row else None

    def get_all_preferences(self) -> List[Dict]:
        """Get all user preferences."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM user_preferences ORDER BY category, pref_key"
            ).fetchall()
            return [dict(r) for r in rows]

    # ═══════════════════════════════════════════════════════════
    # SKILLS
    # ═══════════════════════════════════════════════════════════

    def save_skill(self, name: str, description: str = "", pattern: str = "",
                   proficiency: float = 0.0) -> int:
        """Save or update a learned skill."""
        with self._get_conn() as conn:
            cur = conn.execute(
                """INSERT INTO skills (name, description, pattern, proficiency)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(name) DO UPDATE SET
                       proficiency = excluded.proficiency,
                       pattern = excluded.pattern""",
                (name, description, pattern, proficiency),
            )
            conn.commit()
            return cur.lastrowid

    def get_skill(self, name: str) -> Optional[Dict]:
        """Get a skill by name."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM skills WHERE name = ?", (name,)
            ).fetchone()
            return dict(row) if row else None

    def get_all_skills(self) -> List[Dict]:
        """Get all skills."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM skills ORDER BY proficiency DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    # ═══════════════════════════════════════════════════════════
    # HABITS
    # ═══════════════════════════════════════════════════════════

    def save_habit(self, name: str, pattern: str, frequency: str = "",
                   time_of_day: str = "", day_of_week: str = "",
                   confidence: float = 0.5) -> int:
        """Save or update a learned habit."""
        with self._get_conn() as conn:
            # Check if habit exists
            existing = conn.execute(
                "SELECT id, occurrences FROM habits WHERE name = ? AND pattern = ?",
                (name, pattern),
            ).fetchone()
            if existing:
                conn.execute(
                    """UPDATE habits SET frequency = ?, time_of_day = ?,
                       day_of_week = ?, confidence = ?, occurrences = occurrences + 1,
                       last_triggered = CURRENT_TIMESTAMP
                       WHERE id = ?""",
                    (frequency, time_of_day, day_of_week, confidence, existing["id"]),
                )
                cur = existing["id"]
            else:
                cur = conn.execute(
                    """INSERT INTO habits (name, pattern, frequency, time_of_day,
                       day_of_week, confidence, occurrences, last_triggered)
                       VALUES (?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)""",
                    (name, pattern, frequency, time_of_day, day_of_week, confidence),
                ).lastrowid
            conn.commit()
            return cur

    def get_habits(self, enabled_only: bool = True) -> List[Dict]:
        """Get all learned habits."""
        with self._get_conn() as conn:
            if enabled_only:
                rows = conn.execute(
                    "SELECT * FROM habits WHERE enabled = 1 ORDER BY confidence DESC"
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM habits ORDER BY confidence DESC"
                ).fetchall()
            return [dict(r) for r in rows]

    def predict_habit(self, current_hour: int, current_day: int) -> Optional[Dict]:
        """Predict a habit based on current time context."""
        with self._get_conn() as conn:
            # Check habits for this time of day and day of week
            hour_str = f"{current_hour:02d}"
            day_names = ["monday", "tuesday", "wednesday", "thursday",
                         "friday", "saturday", "sunday"]
            day_name = day_names[current_day]
            rows = conn.execute(
                """SELECT * FROM habits
                   WHERE enabled = 1
                   AND (time_of_day = ? OR time_of_day LIKE ?)
                   AND (day_of_week = ? OR day_of_week = '')
                   AND confidence > ?
                   ORDER BY confidence DESC LIMIT 1""",
                (hour_str, f"{hour_str}:%", day_name,
                 MEMORY_CONFIG.get("forget_threshold", 0.1)),
            ).fetchall()
            return dict(rows[0]) if rows else None

    # ═══════════════════════════════════════════════════════════
    # GOALS
    # ═══════════════════════════════════════════════════════════

    def save_goal(self, goal: str, deadline: str = "") -> int:
        """Save a new goal."""
        with self._get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO goals (goal, deadline) VALUES (?, ?)",
                (goal, deadline if deadline else None),
            )
            conn.commit()
            return cur.lastrowid

    def update_goal_progress(self, goal_id: int, progress: float,
                             status: str = "active") -> None:
        """Update goal progress."""
        with self._get_conn() as conn:
            completed_dt = datetime.now().isoformat() if status == "completed" else None
            conn.execute(
                """UPDATE goals SET progress = ?, status = ?, completed = ?
                   WHERE id = ?""",
                (progress, status, completed_dt, goal_id),
            )
            conn.commit()

    def get_active_goals(self) -> List[Dict]:
        """Get all active goals."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM goals WHERE status = 'active' ORDER BY created DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    # ═══════════════════════════════════════════════════════════
    # ACTIVITY LOG
    # ═══════════════════════════════════════════════════════════

    def log_activity(self, query: str, intent: str, action: str = "",
                     result: str = "", duration: float = 0.0,
                     success: int = 1) -> int:
        """Log an activity."""
        with self._get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO activities (query, intent, action, result, duration, success) VALUES (?, ?, ?, ?, ?, ?)",
                (query, intent, action, result, duration, success),
            )
            conn.commit()
            return cur.lastrowid

    def get_recent_activities(self, limit: int = 20) -> List[Dict]:
        """Get recent activities."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM activities ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    # ═══════════════════════════════════════════════════════════
    # GENERAL MEMORY OPERATIONS
    # ═══════════════════════════════════════════════════════════

    def save_memory(self, content: str, memory_type: str = "episodic",
                    context: str = "", importance: float = 0.5) -> int:
        """Generic save across memory types."""
        if memory_type == "working":
            return self.save_working_memory(content, context, importance)
        elif memory_type == "semantic":
            key = content.split(":")[0].strip() if ":" in content else content
            value = content.split(":", 1)[1].strip() if ":" in content else content
            return self.save_semantic_memory(key, value, context, importance)
        else:
            return self.save_episodic_memory(content, "", importance, context)

    def recall_memory(self, query: str, memory_type: str = "all",
                      limit: int = 10) -> Dict[str, List[Dict]]:
        """Recall memories across types."""
        results = {}
        if memory_type in ("all", "episodic"):
            results["episodic"] = self.recall_episodic_memory(query, limit)
        if memory_type in ("all", "semantic"):
            results["semantic"] = self.search_semantic_memory(query, limit=limit)
        if memory_type in ("all", "working"):
            results["working"] = self.get_working_memory(limit)
        return results

    def search_memory(self, query: str, limit: int = 20) -> List[Dict]:
        """Search across all memory types."""
        results = []
        with self._get_conn() as conn:
            for table in ["episodic_memory", "semantic_memory", "working_memory"]:
                try:
                    if table == "semantic_memory":
                        rows = conn.execute(
                            f"SELECT *, '{table}' as source FROM {table} WHERE key LIKE ? OR value LIKE ? LIMIT ?",
                            (f"%{query}%", f"%{query}%", limit),
                        ).fetchall()
                    else:
                        rows = conn.execute(
                            f"SELECT *, '{table}' as source FROM {table} WHERE content LIKE ? OR context LIKE ? LIMIT ?",
                            (f"%{query}%", f"%{query}%", limit),
                        ).fetchall()
                    results.extend([dict(r) for r in rows])
                except Exception:
                    continue
        return results

    def delete_memory(self, memory_id: int, table: str = "episodic_memory") -> bool:
        """Delete a specific memory."""
        valid_tables = ["working_memory", "episodic_memory", "semantic_memory"]
        if table not in valid_tables:
            return False
        with self._get_conn() as conn:
            conn.execute(f"DELETE FROM {table} WHERE id = ?", (memory_id,))
            conn.commit()
            return conn.total_changes > 0

    def promote_memory(self, memory_id: int, table: str = "episodic_memory") -> bool:
        """Promote a memory's importance."""
        valid_tables = ["working_memory", "episodic_memory"]
        if table not in valid_tables:
            return False
        with self._get_conn() as conn:
            conn.execute(
                f"UPDATE {table} SET importance = MIN(1.0, importance + 0.1) WHERE id = ?",
                (memory_id,),
            )
            conn.commit()
            return True

    # ═══════════════════════════════════════════════════════════
    # AUTOMATIC FORGETTING & MAINTENANCE
    # ═══════════════════════════════════════════════════════════

    def _auto_forget(self):
        """Automatically forget low-importance old memories."""
        with self._get_conn() as conn:
            threshold = MEMORY_CONFIG["forget_threshold"]
            # Forget low-importance episodic memories older than 30 days
            conn.execute(
                """DELETE FROM episodic_memory
                   WHERE importance < ? AND timestamp < datetime('now', '-30 days')""",
                (threshold,),
            )
            # Forget low-importance working memories
            conn.execute(
                "DELETE FROM working_memory WHERE importance < ?",
                (threshold,),
            )
            conn.commit()

    def _trim_table(self, table: str, max_size: int):
        """Trim a table to max_size rows, keeping highest importance."""
        with self._get_conn() as conn:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            if count > max_size:
                conn.execute(
                    f"""DELETE FROM {table} WHERE id IN (
                        SELECT id FROM {table} ORDER BY importance ASC, last_accessed ASC
                        LIMIT ?
                    )""",
                    (count - max_size,),
                )
                conn.commit()

    def _update_access_count(self, conn, table: str, ids: List[int]):
        """Update access count for memories."""
        if not ids:
            return
        placeholders = ",".join("?" for _ in ids)
        conn.execute(
            f"""UPDATE {table} SET access_count = access_count + 1,
                last_accessed = CURRENT_TIMESTAMP WHERE id IN ({placeholders})""",
            ids,
        )
        conn.commit()

    def get_memory_count(self) -> int:
        """Get total count of memories across all tables."""
        with self._get_conn() as conn:
            total = 0
            for table in ["working_memory", "episodic_memory", "semantic_memory"]:
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                total += count
            return total

    def get_database_size_mb(self) -> float:
        """Get the database file size in MB."""
        try:
            return os.path.getsize(self.db_path) / (1024 * 1024)
        except OSError:
            return 0.0

    def get_stats(self) -> dict:
        """Get memory brain statistics."""
        with self._get_conn() as conn:
            stats = {
                "working_memory": conn.execute("SELECT COUNT(*) FROM working_memory").fetchone()[0],
                "episodic_memory": conn.execute("SELECT COUNT(*) FROM episodic_memory").fetchone()[0],
                "semantic_memory": conn.execute("SELECT COUNT(*) FROM semantic_memory").fetchone()[0],
                "preferences": conn.execute("SELECT COUNT(*) FROM user_preferences").fetchone()[0],
                "skills": conn.execute("SELECT COUNT(*) FROM skills").fetchone()[0],
                "habits": conn.execute("SELECT COUNT(*) FROM habits").fetchone()[0],
                "goals": conn.execute("SELECT COUNT(*) FROM goals").fetchone()[0],
                "activities": conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0],
                "db_size_mb": round(self.get_database_size_mb(), 2),
            }
            return stats
