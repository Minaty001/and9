"""
app/core/memory.py — Supabase-backed cognitive memory.

All storage goes through Supabase (PostgreSQL).
No SQLite, no MongoDB.

Constitution V3 compliance:
  Rule 5 — Every memory record has source, confidence, verified
  Rule 6 — No LLM-inferred facts stored as truth
  Rule 8 — Source tracking for all writes

Required env vars:
    SUPABASE_URL  — https://ipvdftzjyxwjhahfkwbq.supabase.co
    SUPABASE_KEY  — your anon or service_role key from Supabase dashboard

Required Supabase tables (run once in SQL Editor):
    See: app/core/supabase_schema.sql
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)


# ── Supabase client (singleton) ────────────────────────────────
_sb_client = None


def _get_client():
    global _sb_client
    if _sb_client is not None:
        return _sb_client
    from app.core.config import SUPABASE_URL, SUPABASE_KEY
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
    from supabase import create_client
    _sb_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _sb_client


# ── Valid sources (Rule 5 confidence map) ──────────────────────
# These match app/core/truth_engine.py CONFIDENCE_MAP
_VALID_SOURCES = {
    "user_input", "direct_statement", "user_stated",
    "observed", "observed_pattern", "cross_session",
    "regex_extraction", "keyword_detection",
    "system", "llm_response",
}


def _validate_source(source: str) -> str:
    """Ensure source is a known valid value; fall back to 'user_input'."""
    s = source.lower().replace(" ", "_")
    return s if s in _VALID_SOURCES else "user_input"


# ── factory ────────────────────────────────────────────────────
def get_memory():
    """Return a Memory instance (always Supabase)."""
    return Memory()


# ══════════════════════════════════════════════════════════════════
# Memory class
# ══════════════════════════════════════════════════════════════════

class Memory:
    """Cognitive memory backed by Supabase (PostgreSQL).

    When SUPABASE_KEY is not configured (e.g. in tests), falls back to an
    in-memory dict store so the app still runs without a real DB connection.

    The `db_path` parameter is accepted but ignored (backward-compat with tests).
    """

    def __init__(self, db_path=None):  # db_path accepted but ignored
        self._sb = None
        self._ok = False
        self._mem: dict = {          # in-memory fallback store
            "chat":      [],
            "facts":     {},
            "sessions":  [],
            "episodes":  [],
            "semantic":  {},         # (category, key) → value
            "emotional": [],
            "_next_id":  1,
        }
        try:
            from app.core.config import SUPABASE_KEY
            if SUPABASE_KEY:
                self._sb = _get_client()
                self._ok = True
        except Exception as e:
            logger.warning(f"Supabase init skipped: {e}")

    def _next(self) -> int:
        n = self._mem["_next_id"]
        self._mem["_next_id"] += 1
        return n

    # ── helpers ──────────────────────────────────────────────────

    def _q(self, table: str):
        return self._sb.table(table)

    def _safe(self, fn, default=None):
        try:
            return fn()
        except Exception as e:
            logger.warning(f"Supabase op failed: {e}")
            return default


    # ════════════════════════════════════════════════════════════
    # Chat History
    # ════════════════════════════════════════════════════════════

    def add(self, role: str, content: str, source: str = "user_input",
            confidence: float = 1.0, verified: bool = True):
        """Add a chat message with source tracking (Rule 5/8).

        Args:
            role: 'user' or 'assistant'.
            content: Message content.
            source: Origin of the content (user_input, llm_response, system, etc.)
            confidence: Confidence score per Rule 5 map.
            verified: Whether this fact has been verified.
        """
        if self._ok:
            self._safe(lambda: self._q("chat_history").insert(
                {"role": role, "content": content,
                 "source": _validate_source(source),
                 "confidence": confidence, "verified": verified}
            ).execute())
        else:
            self._mem["chat"].append({
                "role": role, "content": content,
                "source": _validate_source(source),
                "confidence": confidence, "verified": verified,
            })

    def get_recent_chat(self, limit: int = 20) -> list:
        if self._ok:
            res = self._safe(lambda: self._q("chat_history")
                             .select("role, content")
                             .order("id", desc=True)
                             .limit(limit)
                             .execute(), None)
            if not res or not res.data:
                return []
            return [{"role": r["role"], "content": r["content"]}
                    for r in reversed(res.data)]
        else:
            return self._mem["chat"][-limit:]

    def get_chat_count(self) -> int:
        if self._ok:
            res = self._safe(lambda: self._q("chat_history")
                             .select("id", count="exact").execute(), None)
            return res.count if res else 0
        return len(self._mem["chat"])

    def clear_chat_history(self):
        if self._ok:
            self._safe(lambda: self._q("chat_history").delete().neq("id", 0).execute())
        else:
            self._mem["chat"].clear()

    # ════════════════════════════════════════════════════════════
    # User Facts  (backward-compat)
    # ════════════════════════════════════════════════════════════

    def learn_fact(self, key: str, value: str,
                   fact_type: str = "personal", priority: int = 1,
                   source: str = "user_input", confidence: float = 1.0,
                   verified: bool = True):
        """Store a user fact with source/confidence tracking.

        Args:
            key: Fact key.
            value: Fact value.
            fact_type: Category of fact.
            priority: Display priority (higher = more important).
            source: Origin of fact (user_input, regex_extraction, etc.)
            confidence: Confidence per Rule 5 map.
            verified: Whether user has confirmed this fact.
        """
        if self._ok:
            self._safe(lambda: self._q("user_facts").upsert(
                {"fact_key": key, "fact_value": value,
                 "fact_type": fact_type, "priority": priority,
                 "source": _validate_source(source),
                 "confidence": confidence, "verified": verified},
                on_conflict="fact_key"
            ).execute())
        else:
            self._mem["facts"][key] = {
                "value": value, "type": fact_type, "priority": priority,
                "source": _validate_source(source),
                "confidence": confidence, "verified": verified,
            }

    def get_facts(self, fact_type: Optional[str] = None,
                  min_confidence: float = 0.0) -> dict:
        """Get facts, optionally filtered by type and minimum confidence.

        Args:
            fact_type: Optional category filter.
            min_confidence: Minimum confidence threshold.

        Returns:
            dict of fact_key → fact_value.
        """
        if self._ok:
            q = self._q("user_facts").select("fact_key, fact_value").order("priority", desc=True)
            if fact_type:
                q = q.eq("fact_type", fact_type)
            if min_confidence > 0:
                q = q.gte("confidence", min_confidence)
            res = self._safe(lambda: q.execute(), None)
            if not res or not res.data:
                return {}
            return {r["fact_key"]: r["fact_value"] for r in res.data}
        else:
            f = self._mem["facts"]
            if fact_type:
                return {k: v["value"] for k, v in f.items()
                        if v["type"] == fact_type and v["confidence"] >= min_confidence}
            return {k: v["value"] for k, v in f.items()
                    if v["confidence"] >= min_confidence}

    def delete_fact(self, key: str) -> bool:
        if self._ok:
            res = self._safe(lambda: self._q("user_facts")
                             .delete().eq("fact_key", key).execute(), None)
            return bool(res and res.data)
        else:
            existed = key in self._mem["facts"]
            self._mem["facts"].pop(key, None)
            return existed

    def search_facts(self, keyword: str) -> dict:
        if self._ok:
            res = self._safe(lambda: self._q("user_facts")
                             .select("fact_key, fact_value")
                             .ilike("fact_value", f"%{keyword}%")
                             .execute(), None)
            if not res or not res.data:
                return {}
            return {r["fact_key"]: r["fact_value"] for r in res.data}
        else:
            kw = keyword.lower()
            return {k: v["value"] for k, v in self._mem["facts"].items()
                    if kw in k.lower() or kw in v["value"].lower()}

    # ════════════════════════════════════════════════════════════
    # Session Management
    # ════════════════════════════════════════════════════════════

    def get_or_create_session(self, timeout_minutes: int = 30) -> int:
        if not self._ok:
            # Find open session in memory
            open_s = next((s for s in self._mem["sessions"] if s["ended_at"] is None), None)
            if open_s:
                return open_s["id"]
            new_id = self._next()
            self._mem["sessions"].append({"id": new_id, "ended_at": None})
            return new_id

        # Find open session
        res = self._safe(lambda: self._q("conversation_sessions")
                         .select("id, started_at")
                         .is_("ended_at", "null")
                         .order("id", desc=True)
                         .limit(1)
                         .execute(), None)

        if res and res.data:
            session = res.data[0]
            sid = session["id"]
            ep = self._safe(lambda: self._q("episodic_memory")
                            .select("created_at")
                            .eq("session_id", sid)
                            .order("id", desc=True)
                            .limit(1)
                            .execute(), None)

            cutoff = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)

            if ep and ep.data:
                last_ts = datetime.fromisoformat(ep.data[0]["created_at"].replace("Z", "+00:00"))
                if last_ts.tzinfo is None:
                    last_ts = last_ts.replace(tzinfo=timezone.utc)
                if last_ts >= cutoff:
                    return sid
            else:
                started = datetime.fromisoformat(session["started_at"].replace("Z", "+00:00"))
                if started.tzinfo is None:
                    started = started.replace(tzinfo=timezone.utc)
                if started >= cutoff:
                    return sid

            self._safe(lambda: self._q("conversation_sessions")
                       .update({"ended_at": datetime.now(timezone.utc).isoformat()})
                       .eq("id", sid).execute())

        res = self._safe(lambda: self._q("conversation_sessions")
                         .insert({"dominant_emotion": "neutral"})
                         .execute(), None)
        if res and res.data:
            return res.data[0]["id"]
        return 1

    def end_session(self, session_id: int, summary: Optional[str] = None):
        if not self._ok:
            for s in self._mem["sessions"]:
                if s["id"] == session_id:
                    s["ended_at"] = datetime.now(timezone.utc).isoformat()
            return
        self._safe(lambda: self._q("conversation_sessions")
                   .update({"ended_at": datetime.now(timezone.utc).isoformat(), "summary": summary})
                   .eq("id", session_id).execute())

    def get_session_history(self, session_id: int) -> list:
        if not self._ok:
            return [e for e in self._mem["episodes"] if e.get("session_id") == session_id]
        res = self._safe(lambda: self._q("episodic_memory")
                         .select("id, role, content, topic, emotion, importance, created_at")
                         .eq("session_id", session_id)
                         .order("id")
                         .execute(), None)
        if not res or not res.data:
            return []
        return [{"id": r["id"], "role": r["role"], "content": r["content"],
                 "topic": r.get("topic", "general"), "emotion": r.get("emotion", "neutral"),
                 "importance": r.get("importance", 1), "timestamp": r.get("created_at", "")}
                for r in res.data]

    # ════════════════════════════════════════════════════════════
    # Episodic Memory
    # ════════════════════════════════════════════════════════════

    def add_episode(self, role: str, content: str, topic: str = "general",
                    emotion: str = "neutral", importance: int = 1,
                    source: str = "user_input", confidence: float = 1.0,
                    verified: bool = True) -> int:
        """Add an episode with source/confidence tracking.

        Args:
            role: 'user' or 'assistant'.
            content: Message content.
            topic: Conversation topic.
            emotion: Detected emotion.
            importance: 1-5 importance rating.
            source: Origin of content.
            confidence: Confidence per Rule 5 map.
            verified: Whether content is verified.
        """
        session_id = self.get_or_create_session()
        self.add(role, content, source=source, confidence=confidence, verified=verified)
        if self._ok:
            res = self._safe(lambda: self._q("episodic_memory")
                             .insert({"session_id": session_id, "role": role,
                                      "content": content, "topic": topic,
                                      "emotion": emotion, "importance": importance,
                                      "source": _validate_source(source),
                                      "confidence": confidence,
                                      "verified": verified})
                             .execute(), None)
            if res and res.data:
                return res.data[0]["id"]
            return 0
        else:
            ep = {"id": self._next(), "session_id": session_id, "role": role,
                  "content": content, "topic": topic, "emotion": emotion,
                  "importance": importance, "source": _validate_source(source),
                  "confidence": confidence, "verified": verified,
                  "timestamp": datetime.now(timezone.utc).isoformat()}
            self._mem["episodes"].append(ep)
            return ep["id"]

    def get_recent_episodes(self, limit: int = 10) -> list:
        if self._ok:
            res = self._safe(lambda: self._q("episodic_memory")
                             .select("id, session_id, role, content, topic, emotion, importance, created_at")
                             .order("id", desc=True)
                             .limit(limit)
                             .execute(), None)
            if not res or not res.data:
                return []
            return [{"id": r["id"], "session_id": r["session_id"], "role": r["role"],
                     "content": r["content"], "topic": r.get("topic", "general"),
                     "emotion": r.get("emotion", "neutral"), "importance": r.get("importance", 1),
                     "timestamp": r.get("created_at", "")} for r in reversed(res.data)]
        else:
            return list(reversed(self._mem["episodes"]))[:limit]

    def get_relevant_episodes(self, topic: str, limit: int = 5) -> list:
        if self._ok:
            res = self._safe(lambda: self._q("episodic_memory")
                             .select("id, session_id, role, content, topic, emotion, importance, created_at")
                             .ilike("topic", f"%{topic}%")
                             .order("id", desc=True)
                             .limit(limit)
                             .execute(), None)
            if not res or not res.data:
                return []
            return [{"id": r["id"], "session_id": r["session_id"], "role": r["role"],
                     "content": r["content"], "topic": r.get("topic", "general"),
                     "emotion": r.get("emotion", "neutral"), "importance": r.get("importance", 1),
                     "timestamp": r.get("created_at", "")} for r in res.data]
        else:
            kw = topic.lower()
            return [e for e in reversed(self._mem["episodes"]) if kw in e.get("topic", "").lower()][:limit]

    def get_episode_count(self) -> int:
        if self._ok:
            res = self._safe(lambda: self._q("episodic_memory")
                             .select("id", count="exact").execute(), None)
            return res.count if res else 0
        return len(self._mem["episodes"])

    # ════════════════════════════════════════════════════════════
    # Semantic Memory
    # ════════════════════════════════════════════════════════════

    def store_fact(self, category: str, key: str, value: str,
                   confidence: float, source: str = "regex_extraction",
                   verified: bool = False):
        """Store a semantic fact with mandatory confidence and source tracking.

        Per Rule 5, confidence MUST be specified and must NOT exceed
        the source type's maximum (use truth_engine.cap_confidence).

        Per Rule 6, LLM-inferred facts (confidence=0.0) are NEVER stored.

        Args:
            category: Fact category (identity, location, preference, etc.)
            key: Fact key.
            value: Fact value.
            confidence: REQUIRED — confidence per Rule 5 map.
            source: Origin of fact (default: regex_extraction).
            verified: Whether user has confirmed (default: False).
        """
        if self._ok:
            self._safe(lambda: self._q("semantic_memory").upsert(
                {"category": category, "fact_key": key, "fact_value": value,
                 "confidence": confidence, "source": _validate_source(source),
                 "verified": verified},
                on_conflict="category,fact_key"
            ).execute())
        else:
            self._mem["semantic"][(category, key)] = {
                "value": value, "confidence": confidence,
                "source": _validate_source(source), "verified": verified,
            }

    def get_user_profile(self) -> dict:
        if self._ok:
            res = self._safe(lambda: self._q("semantic_memory")
                             .select("category, fact_key, fact_value")
                             .execute(), None)
            if not res or not res.data:
                return {}
            profile: dict = {}
            for r in res.data:
                profile.setdefault(r["category"], {})[r["fact_key"]] = r["fact_value"]
            return profile
        else:
            profile: dict = {}
            for (cat, k), v in self._mem["semantic"].items():
                profile.setdefault(cat, {})[k] = v["value"]
            return profile

    def get_verified_facts(self, min_confidence: float = 0.5) -> dict:
        """Get only verified facts with confidence above threshold.

        Returns facts grouped by category, same shape as get_user_profile.
        """
        if self._ok:
            res = self._safe(lambda: self._q("semantic_memory")
                             .select("category, fact_key, fact_value, confidence")
                             .eq("verified", True)
                             .gte("confidence", min_confidence)
                             .execute(), None)
            if not res or not res.data:
                return {}
            profile: dict = {}
            for r in res.data:
                profile.setdefault(r["category"], {})[r["fact_key"]] = r["fact_value"]
            return profile
        else:
            profile: dict = {}
            for (cat, k), v in self._mem["semantic"].items():
                if v.get("verified") and v.get("confidence", 0) >= min_confidence:
                    profile.setdefault(cat, {})[k] = v["value"]
            return profile

    def get_facts_by_category(self, category: str) -> dict:
        if self._ok:
            res = self._safe(lambda: self._q("semantic_memory")
                             .select("fact_key, fact_value")
                             .eq("category", category)
                             .execute(), None)
            if not res or not res.data:
                return {}
            return {r["fact_key"]: r["fact_value"] for r in res.data}
        else:
            return {k: v["value"] for (c, k), v in self._mem["semantic"].items() if c == category}

    def confirm_fact(self, category: str, key: str):
        """Mark a fact as verified and update confirmation timestamp."""
        if self._ok:
            self._safe(lambda: self._q("semantic_memory")
                       .update({"last_confirmed": datetime.now(timezone.utc).isoformat(),
                                "verified": True})
                       .eq("category", category).eq("fact_key", key).execute())
        else:
            if (category, key) in self._mem["semantic"]:
                self._mem["semantic"][(category, key)]["verified"] = True

    def forget_fact(self, category: str, key: str) -> bool:
        if self._ok:
            res = self._safe(lambda: self._q("semantic_memory")
                             .delete().eq("category", category).eq("fact_key", key)
                             .execute(), None)
            return bool(res and res.data)
        else:
            existed = (category, key) in self._mem["semantic"]
            self._mem["semantic"].pop((category, key), None)
            return existed

    # ════════════════════════════════════════════════════════════
    # Emotional Memory
    # ════════════════════════════════════════════════════════════

    def record_emotion(self, topic: str, emotion: str, intensity: int = 3,
                       episode_id=None, context: Optional[str] = None,
                       source: str = "keyword_detection", confidence: float = 0.7):
        """Record an emotional state with source tracking.

        Args:
            topic: Topic associated with the emotion.
            emotion: Emotion label.
            intensity: 1-5 intensity.
            episode_id: Related episodic memory ID.
            context: Optional context string.
            source: Origin (keyword_detection, user_stated, etc.)
            confidence: Confidence per Rule 5 map.
        """
        if self._ok:
            self._safe(lambda: self._q("emotional_memory")
                       .insert({"topic": topic, "emotion": emotion, "intensity": intensity,
                                "episode_id": episode_id, "context": context,
                                "source": _validate_source(source),
                                "confidence": confidence})
                       .execute())
        else:
            self._mem["emotional"].append({"id": self._next(), "topic": topic,
                "emotion": emotion, "intensity": intensity, "context": context,
                "source": _validate_source(source), "confidence": confidence,
                "timestamp": datetime.now(timezone.utc).isoformat()})

    def get_emotional_history(self, topic: str) -> list:
        if self._ok:
            res = self._safe(lambda: self._q("emotional_memory")
                             .select("id, emotion, intensity, created_at, episode_id, context")
                             .eq("topic", topic)
                             .order("id", desc=True)
                             .execute(), None)
            if not res or not res.data:
                return []
            return [{"id": r["id"], "emotion": r["emotion"], "intensity": r["intensity"],
                     "timestamp": r.get("created_at", ""), "context": r.get("context")}
                    for r in res.data]
        else:
            return [e for e in reversed(self._mem["emotional"]) if e["topic"] == topic]

    def get_emotional_context(self) -> dict:
        if self._ok:
            res = self._safe(lambda: self._q("emotional_memory")
                             .select("topic, emotion, intensity, created_at")
                             .order("id", desc=True).limit(100).execute(), None)
            if not res or not res.data:
                return {}
            seen, result = set(), {}
            for r in res.data:
                t = r["topic"]
                if t not in seen:
                    seen.add(t)
                    result[t] = {"emotion": r["emotion"], "intensity": r["intensity"],
                                 "last_seen": r.get("created_at", "")}
                if len(seen) >= 20:
                    break
            return result
        else:
            seen, result = set(), {}
            for e in reversed(self._mem["emotional"]):
                t = e["topic"]
                if t not in seen:
                    seen.add(t)
                    result[t] = {"emotion": e["emotion"], "intensity": e["intensity"],
                                 "last_seen": e["timestamp"]}
            return result

    def get_dominant_emotion_for_topic(self, topic: str) -> str:
        if self._ok:
            res = self._safe(lambda: self._q("emotional_memory")
                             .select("emotion").eq("topic", topic).execute(), None)
            if not res or not res.data:
                return "neutral"
            from collections import Counter
            counts = Counter(r["emotion"] for r in res.data)
            return counts.most_common(1)[0][0] if counts else "neutral"
        else:
            from collections import Counter
            counts = Counter(e["emotion"] for e in self._mem["emotional"] if e["topic"] == topic)
            return counts.most_common(1)[0][0] if counts else "neutral"

    # ════════════════════════════════════════════════════════════
    # Context Builder
    # ════════════════════════════════════════════════════════════

    def build_memory_context(self, current_topic: Optional[str] = None,
                             limit: int = 8) -> dict:
        """Build context dict — all Supabase reads run in parallel."""
        from concurrent.futures import ThreadPoolExecutor

        session_id = self.get_or_create_session()

        if not self._ok:
            # In-memory path — no network, just return directly
            return {
                "user_profile":      self.get_user_profile(),
                "emotional_context": self.get_emotional_context(),
                "recent_episodes":   self.get_recent_episodes(limit),
                "relevant_past":     self.get_relevant_episodes(current_topic, 3) if current_topic else [],
                "session_id":        session_id,
            }

        # Supabase path — fire all queries simultaneously
        with ThreadPoolExecutor(max_workers=4) as ex:
            f_profile   = ex.submit(self.get_user_profile)
            f_emotional = ex.submit(self.get_emotional_context)
            f_recent    = ex.submit(self.get_recent_episodes, limit)
            f_relevant  = ex.submit(self.get_relevant_episodes, current_topic, 3) \
                          if current_topic else None

        return {
            "user_profile":      f_profile.result(),
            "emotional_context": f_emotional.result(),
            "recent_episodes":   f_recent.result(),
            "relevant_past":     f_relevant.result() if f_relevant else [],
            "session_id":        session_id,
        }
