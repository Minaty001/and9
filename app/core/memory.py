"""
app/core/memory.py — Supabase-backed cognitive memory.

All storage goes through Supabase (PostgreSQL).
No SQLite, no MongoDB.

Required env vars:
    SUPABASE_URL  — https://ipvdftzjyxwjhahfkwbq.supabase.co
    SUPABASE_KEY  — your anon or service_role key from Supabase dashboard

Required Supabase tables (run once in SQL Editor):
    See: app/core/supabase_schema.sql
"""
import logging
import os
import time
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)


# ── Fast Recall Cache (module-level, survives Memory re-instantiation) ─
# LRU cache: key → {"data": ..., "ts": float, "hits": int}
_RECALL_CACHE: OrderedDict = OrderedDict()
_RECALL_CACHE_MAX  = 128   # max entries
_RECALL_CACHE_TTL  = 300   # seconds (5 min)


def _cache_put(key: str, value):
    """Insert/update an entry in the recall cache (LRU eviction)."""
    _RECALL_CACHE.pop(key, None)          # move to end if exists
    _RECALL_CACHE[key] = {"data": value, "ts": time.time(), "hits": 0}
    if len(_RECALL_CACHE) > _RECALL_CACHE_MAX:
        _RECALL_CACHE.popitem(last=False)  # evict oldest


def _cache_get(key: str):
    """Return cached value if still fresh, else None."""
    entry = _RECALL_CACHE.get(key)
    if not entry:
        return None
    if time.time() - entry["ts"] > _RECALL_CACHE_TTL:
        _RECALL_CACHE.pop(key, None)
        return None
    entry["hits"] += 1
    _RECALL_CACHE.move_to_end(key)        # LRU: mark as recently used
    return entry["data"]


def _cache_invalidate(*keys: str):
    """Remove one or more keys from the recall cache."""
    for k in keys:
        _RECALL_CACHE.pop(k, None)


def get_recall_cache_stats() -> dict:
    """Return cache statistics for monitoring."""
    now = time.time()
    entries = list(_RECALL_CACHE.values())
    return {
        "size":     len(entries),
        "max_size": _RECALL_CACHE_MAX,
        "ttl_sec":  _RECALL_CACHE_TTL,
        "total_hits": sum(e["hits"] for e in entries),
        "oldest_age_sec": int(now - entries[0]["ts"]) if entries else 0,
    }


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

    def add(self, role: str, content: str):
        if self._ok:
            self._safe(lambda: self._q("chat_history").insert(
                {"role": role, "content": content}
            ).execute())
        else:
            self._mem["chat"].append({"role": role, "content": content})
        # Warm the in-memory cache so get_recent_chat is instant for next caller
        _cache_invalidate("recent_chat")

    def get_recent_chat(self, limit: int = 20) -> list:
        cache_key = f"recent_chat_{limit}"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached
        if self._ok:
            res = self._safe(lambda: self._q("chat_history")
                             .select("role, content")
                             .order("id", desc=True)
                             .limit(limit)
                             .execute(), None)
            if not res or not res.data:
                return []
            result = [{"role": r["role"], "content": r["content"]}
                      for r in reversed(res.data)]
        else:
            result = self._mem["chat"][-limit:]
        _cache_put(cache_key, result)
        return result

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
        _cache_invalidate("recent_chat", "memory_ctx_None")

    # ════════════════════════════════════════════════════════════
    # User Facts  (backward-compat)
    # ════════════════════════════════════════════════════════════

    def learn_fact(self, key: str, value: str,
                   fact_type: str = "personal", priority: int = 1):
        if self._ok:
            self._safe(lambda: self._q("user_facts").upsert(
                {"fact_key": key, "fact_value": value,
                 "fact_type": fact_type, "priority": priority},
                on_conflict="fact_key"
            ).execute())
        else:
            self._mem["facts"][key] = {"value": value, "type": fact_type, "priority": priority}

    def get_facts(self, fact_type: Optional[str] = None) -> dict:
        if self._ok:
            q = self._q("user_facts").select("fact_key, fact_value").order("priority", desc=True)
            if fact_type:
                q = q.eq("fact_type", fact_type)
            res = self._safe(lambda: q.execute(), None)
            if not res or not res.data:
                return {}
            return {r["fact_key"]: r["fact_value"] for r in res.data}
        else:
            f = self._mem["facts"]
            if fact_type:
                return {k: v["value"] for k, v in f.items() if v["type"] == fact_type}
            return {k: v["value"] for k, v in f.items()}

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
                    emotion: str = "neutral", importance: int = 1) -> int:
        session_id = self.get_or_create_session()
        self.add(role, content)
        if self._ok:
            res = self._safe(lambda: self._q("episodic_memory")
                             .insert({"session_id": session_id, "role": role,
                                      "content": content, "topic": topic,
                                      "emotion": emotion, "importance": importance})
                             .execute(), None)
            if res and res.data:
                return res.data[0]["id"]
            return 0
        else:
            ep = {"id": self._next(), "session_id": session_id, "role": role,
                  "content": content, "topic": topic, "emotion": emotion,
                  "importance": importance, "timestamp": datetime.now(timezone.utc).isoformat()}
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
                   confidence: float = 0.8, source_episode_id=None):
        if self._ok:
            self._safe(lambda: self._q("semantic_memory").upsert(
                {"category": category, "fact_key": key, "fact_value": value,
                 "confidence": confidence},
                on_conflict="category,fact_key"
            ).execute())
        else:
            self._mem["semantic"][(category, key)] = {"value": value, "confidence": confidence}

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
        if not self._ok: return
        self._safe(lambda: self._q("semantic_memory")
                   .update({"last_confirmed": datetime.now(timezone.utc).isoformat()})
                   .eq("category", category).eq("fact_key", key).execute())

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
                       episode_id=None, context: Optional[str] = None):
        if self._ok:
            self._safe(lambda: self._q("emotional_memory")
                       .insert({"topic": topic, "emotion": emotion, "intensity": intensity,
                                "episode_id": episode_id, "context": context})
                       .execute())
        else:
            self._mem["emotional"].append({"id": self._next(), "topic": topic,
                "emotion": emotion, "intensity": intensity, "context": context,
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
    # Episode Search (cross-session keyword recall)
    # ════════════════════════════════════════════════════════════

    def search_episodes(self, keyword: str, limit: int = 10) -> list:
        """Full-text keyword search across all episodic memory entries.

        Results are cached so repeated queries for the same keyword are
        returned from memory without hitting the database.
        """
        if not keyword:
            return []
        cache_key = f"ep_search_{keyword.lower()}_{limit}"
        cached = _cache_get(cache_key)
        if cached is not None:
            logger.debug(f"fast_recall cache HIT for '{keyword}'")
            return cached

        if self._ok:
            # Search across content AND topic columns
            res_c = self._safe(lambda: self._q("episodic_memory")
                               .select("id, session_id, role, content, topic, emotion, importance, created_at")
                               .ilike("content", f"%{keyword}%")
                               .order("id", desc=True)
                               .limit(limit)
                               .execute(), None)
            res_t = self._safe(lambda: self._q("episodic_memory")
                               .select("id, session_id, role, content, topic, emotion, importance, created_at")
                               .ilike("topic", f"%{keyword}%")
                               .order("id", desc=True)
                               .limit(limit)
                               .execute(), None)
            seen, results = set(), []
            for res in [res_c, res_t]:
                if res and res.data:
                    for r in res.data:
                        if r["id"] not in seen:
                            seen.add(r["id"])
                            results.append({
                                "id":         r["id"],
                                "session_id": r["session_id"],
                                "role":        r["role"],
                                "content":     r["content"],
                                "topic":       r.get("topic", "general"),
                                "emotion":     r.get("emotion", "neutral"),
                                "importance":  r.get("importance", 1),
                                "timestamp":   r.get("created_at", ""),
                            })
            # Sort by id desc, cap at limit
            results = sorted(results, key=lambda x: x["id"], reverse=True)[:limit]
        else:
            kw = keyword.lower()
            results = [
                e for e in reversed(self._mem["episodes"])
                if kw in e.get("content", "").lower() or kw in e.get("topic", "").lower()
            ][:limit]

        _cache_put(cache_key, results)
        return results

    def get_sessions_summary(self, limit: int = 5) -> list:
        """Return a brief summary of the most recent conversation sessions.

        Each entry contains session_id, episode count, dominant emotion,
        and a short snippet of the last message — useful for a 'memory recap'.
        Cached with TTL so repeated front-end polls don't hit the DB.
        """
        cache_key = f"sessions_summary_{limit}"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        summaries = []
        if self._ok:
            # Fetch recent closed + open sessions
            res = self._safe(lambda: self._q("conversation_sessions")
                             .select("id, started_at, ended_at, dominant_emotion, summary")
                             .order("id", desc=True)
                             .limit(limit)
                             .execute(), None)
            sessions = res.data if res and res.data else []
            for s in sessions:
                ep_res = self._safe(lambda sid=s["id"]: self._q("episodic_memory")
                                    .select("id, content, role")
                                    .eq("session_id", sid)
                                    .order("id", desc=True)
                                    .limit(3)
                                    .execute(), None)
                episodes = ep_res.data if ep_res and ep_res.data else []
                last_msg = episodes[0]["content"][:120] if episodes else ""
                summaries.append({
                    "session_id":   s["id"],
                    "started_at":   str(s.get("started_at", ""))[:16],
                    "ended_at":     str(s.get("ended_at", ""))[:16] if s.get("ended_at") else "active",
                    "emotion":      s.get("dominant_emotion", "neutral"),
                    "summary":      s.get("summary") or last_msg,
                    "episode_count": len(episodes),
                })
        else:
            # in-memory fallback
            session_ids = list({e.get("session_id") for e in self._mem["episodes"]})[-limit:]
            for sid in reversed(session_ids):
                eps = [e for e in self._mem["episodes"] if e.get("session_id") == sid]
                last_msg = eps[-1]["content"][:120] if eps else ""
                summaries.append({
                    "session_id": sid,
                    "started_at": "",
                    "ended_at":   "active",
                    "emotion":    "neutral",
                    "summary":    last_msg,
                    "episode_count": len(eps),
                })

        _cache_put(cache_key, summaries)
        return summaries

    def fast_recall(self, query: str, limit: int = 8) -> dict:
        """Unified fast memory recall — checks cache first, then searches.

        Returns a structured dict with:
          - matched_episodes: keyword-matched past conversations
          - user_profile:     known facts about the user
          - recent_chat:      last few chat turns (from cache)
          - sessions_summary: overview of recent sessions
          - cache_hit:        True if all data came from cache
        """
        cache_key = f"fast_recall_{query.lower().strip()[:64]}_{limit}"
        cached = _cache_get(cache_key)
        if cached is not None:
            cached["cache_hit"] = True
            return cached

        from concurrent.futures import ThreadPoolExecutor

        keywords = [w for w in query.lower().split() if len(w) > 3]
        primary_kw = keywords[0] if keywords else query[:20]

        if not self._ok:
            result = {
                "matched_episodes":  self.search_episodes(primary_kw, limit),
                "user_profile":      self.get_user_profile(),
                "recent_chat":       self.get_recent_chat(6),
                "sessions_summary":  self.get_sessions_summary(3),
                "cache_hit":         False,
            }
            _cache_put(cache_key, result)
            return result

        with ThreadPoolExecutor(max_workers=4) as ex:
            f_ep      = ex.submit(self.search_episodes, primary_kw, limit)
            f_profile = ex.submit(self.get_user_profile)
            f_chat    = ex.submit(self.get_recent_chat, 6)
            f_sess    = ex.submit(self.get_sessions_summary, 3)

        result = {
            "matched_episodes":  f_ep.result(),
            "user_profile":      f_profile.result(),
            "recent_chat":       f_chat.result(),
            "sessions_summary":  f_sess.result(),
            "cache_hit":         False,
        }
        _cache_put(cache_key, result)
        return result

    # ════════════════════════════════════════════════════════════
    # Context Builder
    # ════════════════════════════════════════════════════════════

    def build_memory_context(self, current_topic: Optional[str] = None,
                             limit: int = 8) -> dict:
        """Build context dict — all Supabase reads run in parallel.

        Results for static data (user profile, emotional context) are
        served from the recall cache when fresh to avoid redundant DB hits.
        """
        from concurrent.futures import ThreadPoolExecutor

        cache_key = f"memory_ctx_{current_topic}_{limit}"
        cached = _cache_get(cache_key)
        if cached is not None:
            logger.debug("build_memory_context: cache HIT")
            return cached

        session_id = self.get_or_create_session()

        if not self._ok:
            # In-memory path — no network, just return directly
            result = {
                "user_profile":      self.get_user_profile(),
                "emotional_context": self.get_emotional_context(),
                "recent_episodes":   self.get_recent_episodes(limit),
                "relevant_past":     self.get_relevant_episodes(current_topic, 3) if current_topic else [],
                "session_id":        session_id,
            }
            _cache_put(cache_key, result)
            return result

        # Supabase path — fire all queries simultaneously
        with ThreadPoolExecutor(max_workers=4) as ex:
            f_profile   = ex.submit(self.get_user_profile)
            f_emotional = ex.submit(self.get_emotional_context)
            f_recent    = ex.submit(self.get_recent_episodes, limit)
            f_relevant  = ex.submit(self.get_relevant_episodes, current_topic, 3) \
                          if current_topic else None

        result = {
            "user_profile":      f_profile.result(),
            "emotional_context": f_emotional.result(),
            "recent_episodes":   f_recent.result(),
            "relevant_past":     f_relevant.result() if f_relevant else [],
            "session_id":        session_id,
        }
        _cache_put(cache_key, result)
        return result

    # ════════════════════════════════════════════════════════════
    # v2 NEW TABLES — Procedural Memory
    # ════════════════════════════════════════════════════════════

    def store_procedure(self, name: str, description: str = "",
                        workflow_steps: Optional[list] = None,
                        trigger_phrase: Optional[str] = None) -> Optional[int]:
        if not self._ok:
            return None
        res = self._safe(lambda: self._q("procedural_memory").insert({
            "name": name, "description": description,
            "workflow_steps": workflow_steps or [],
            "trigger_phrase": trigger_phrase,
        }).execute(), None)
        return res.data[0]["id"] if res and res.data else None

    def get_procedure(self, name: str) -> Optional[dict]:
        if not self._ok:
            return None
        res = self._safe(lambda: self._q("procedural_memory")
                         .select("*").eq("name", name)
                         .limit(1).execute(), None)
        return res.data[0] if res and res.data else None

    def record_procedure_use(self, proc_id: int, success: bool, duration_ms: int):
        if not self._ok:
            return
        col = "success_count" if success else "failure_count"
        self._safe(lambda: self._q("procedural_memory")
                   .update({
                       col: self._sb.raw(f"{col} + 1"),
                       "last_used_at": datetime.now(timezone.utc).isoformat(),
                       "avg_duration_ms": self._sb.raw(
                           f"(avg_duration_ms * (success_count + failure_count) + {duration_ms})"
                           f" / (success_count + failure_count + 1)"
                       ),
                   }).eq("id", proc_id).execute())

    def search_procedures(self, keyword: str, limit: int = 10) -> list:
        if not self._ok:
            return []
        res = self._safe(lambda: self._q("procedural_memory")
                         .select("*")
                         .ilike("name", f"%{keyword}%")
                         .order("success_count", desc=True)
                         .limit(limit).execute(), None)
        return res.data if res and res.data else []

    # ════════════════════════════════════════════════════════════
    # v2 NEW TABLES — Habit Memory
    # ════════════════════════════════════════════════════════════

    def record_habit(self, pattern_name: str, pattern_type: str = "daily",
                     trigger: Optional[str] = None, action: str = "",
                     confidence: float = 0.5) -> Optional[int]:
        if not self._ok:
            return None
        existing = self._safe(lambda: self._q("habit_memory")
                              .select("id, frequency")
                              .eq("pattern_name", pattern_name)
                              .limit(1).execute(), None)
        now = datetime.now(timezone.utc).isoformat()
        if existing and existing.data:
            hid = existing.data[0]["id"]
            freq = existing.data[0].get("frequency", 0) + 1
            self._safe(lambda: self._q("habit_memory")
                       .update({
                           "frequency": freq,
                           "confidence": min(1.0, confidence + freq * 0.05),
                           "last_observed": now,
                       }).eq("id", hid).execute())
            return hid
        res = self._safe(lambda: self._q("habit_memory").insert({
            "pattern_name": pattern_name, "pattern_type": pattern_type,
            "trigger": trigger, "action": action,
            "confidence": confidence, "frequency": 1,
            "last_observed": now,
        }).execute(), None)
        return res.data[0]["id"] if res and res.data else None

    def get_habits(self, pattern_type: Optional[str] = None,
                   min_confidence: float = 0.3, limit: int = 20) -> list:
        if not self._ok:
            return []
        q = self._q("habit_memory").select("*") \
            .gte("confidence", min_confidence) \
            .order("frequency", desc=True).limit(limit)
        if pattern_type:
            q = q.eq("pattern_type", pattern_type)
        res = self._safe(lambda: q.execute(), None)
        return res.data if res and res.data else []

    # ════════════════════════════════════════════════════════════
    # v2 NEW TABLES — Reflections
    # ════════════════════════════════════════════════════════════

    def store_reflection(self, task_type: str, what_happened: str,
                         what_succeeded: str = "", what_failed: str = "",
                         why: str = "", improvement: str = "",
                         can_be_skill: bool = False,
                         new_skill_name: Optional[str] = None,
                         session_id: Optional[int] = None,
                         task_id: Optional[int] = None) -> Optional[int]:
        if not self._ok:
            return None
        res = self._safe(lambda: self._q("reflections").insert({
            "task_type": task_type, "what_happened": what_happened,
            "what_succeeded": what_succeeded, "what_failed": what_failed,
            "why": why, "improvement": improvement,
            "can_be_skill": can_be_skill, "new_skill_name": new_skill_name,
            "session_id": session_id, "task_id": task_id,
        }).execute(), None)
        return res.data[0]["id"] if res and res.data else None

    def get_recent_reflections(self, limit: int = 10) -> list:
        if not self._ok:
            return []
        res = self._safe(lambda: self._q("reflections")
                         .select("*")
                         .order("id", desc=True).limit(limit)
                         .execute(), None)
        return res.data if res and res.data else []

    # ════════════════════════════════════════════════════════════
    # v2 NEW TABLES — Skills
    # ════════════════════════════════════════════════════════════

    def register_skill(self, name: str, description: str = "",
                       triggers: Optional[list] = None,
                       parameters: Optional[list] = None) -> Optional[int]:
        if not self._ok:
            return None
        res = self._safe(lambda: self._q("skills").insert({
            "name": name, "description": description,
            "triggers": triggers or [], "parameters": parameters or [],
        }).execute(), None)
        return res.data[0]["id"] if res and res.data else None

    def update_skill(self, skill_id: int, **kwargs) -> bool:
        if not self._ok:
            return False
        kwargs["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._safe(lambda: self._q("skills")
                   .update(kwargs).eq("id", skill_id).execute())
        return True

    def get_skill(self, skill_id_or_name) -> Optional[dict]:
        if not self._ok:
            return None
        q = self._q("skills").select("*")
        if isinstance(skill_id_or_name, int):
            q = q.eq("id", skill_id_or_name)
        else:
            q = q.eq("name", skill_id_or_name)
        res = self._safe(lambda: q.limit(1).execute(), None)
        return res.data[0] if res and res.data else None

    def list_skills(self, status: str = "active") -> list:
        if not self._ok:
            return []
        res = self._safe(lambda: self._q("skills")
                         .select("*").eq("status", status)
                         .order("name").execute(), None)
        return res.data if res and res.data else []

    def store_skill_version(self, skill_id: int, version: int,
                            code: str, changelog: str = "") -> Optional[int]:
        if not self._ok:
            return None
        import hashlib
        code_hash = hashlib.sha256(code.encode()).hexdigest()[:16]
        res = self._safe(lambda: self._q("skill_versions").insert({
            "skill_id": skill_id, "version": version,
            "code": code, "hash": code_hash, "changelog": changelog,
        }).execute(), None)
        return res.data[0]["id"] if res and res.data else None

    # ════════════════════════════════════════════════════════════
    # v2 NEW TABLES — Tasks
    # ════════════════════════════════════════════════════════════

    def create_task(self, title: str, description: str = "",
                    task_type: str = "general", priority: str = "medium",
                    goal_id: Optional[int] = None,
                    depends_on: Optional[list] = None,
                    scheduled_at: Optional[str] = None) -> Optional[int]:
        if not self._ok:
            return None
        res = self._safe(lambda: self._q("tasks").insert({
            "title": title, "description": description,
            "task_type": task_type, "priority": priority,
            "goal_id": goal_id, "depends_on": depends_on or [],
            "scheduled_at": scheduled_at,
        }).execute(), None)
        return res.data[0]["id"] if res and res.data else None

    def update_task(self, task_id: int, **kwargs) -> bool:
        if not self._ok:
            return False
        if "completed_at" in kwargs or kwargs.get("status") in ("done", "failed", "cancelled"):
            if "completed_at" not in kwargs:
                kwargs["completed_at"] = datetime.now(timezone.utc).isoformat()
        self._safe(lambda: self._q("tasks")
                   .update(kwargs).eq("id", task_id).execute())
        return True

    def get_task(self, task_id: int) -> Optional[dict]:
        if not self._ok:
            return None
        res = self._safe(lambda: self._q("tasks")
                         .select("*").eq("id", task_id)
                         .limit(1).execute(), None)
        return res.data[0] if res and res.data else None

    def get_pending_tasks(self, limit: int = 20) -> list:
        if not self._ok:
            return []
        res = self._safe(lambda: self._q("tasks")
                         .select("*")
                         .in_("status", ("pending", "in_progress", "waiting"))
                         .order("priority", desc=True)
                         .order("id").limit(limit)
                         .execute(), None)
        return res.data if res and res.data else []

    def add_task_history(self, task_id: int, attempt: int, status: str,
                         duration_ms: int = 0, error: Optional[str] = None,
                         input_data: Optional[dict] = None,
                         output_data: Optional[dict] = None) -> Optional[int]:
        if not self._ok:
            return None
        now = datetime.now(timezone.utc).isoformat()
        res = self._safe(lambda: self._q("task_history").insert({
            "task_id": task_id, "attempt": attempt,
            "status": status, "duration_ms": duration_ms,
            "error": error,
            "input_snapshot": input_data or {},
            "output_snapshot": output_data or {},
            "started_at": now, "completed_at": now,
        }).execute(), None)
        return res.data[0]["id"] if res and res.data else None

    # ════════════════════════════════════════════════════════════
    # v2 NEW TABLES — Decisions
    # ════════════════════════════════════════════════════════════

    def record_decision(self, title: str, context_summary: str = "",
                        options: Optional[list] = None,
                        selected_option: Optional[int] = None,
                        selection_reason: str = "",
                        goal_id: Optional[int] = None,
                        session_id: Optional[int] = None) -> Optional[int]:
        if not self._ok:
            return None
        res = self._safe(lambda: self._q("decisions").insert({
            "title": title, "context_summary": context_summary,
            "options": options or [],
            "selected_option": selected_option,
            "selection_reason": selection_reason,
            "goal_id": goal_id, "session_id": session_id,
        }).execute(), None)
        return res.data[0]["id"] if res and res.data else None

    def update_decision_outcome(self, decision_id: int, outcome: str,
                                success: bool, execution_time_ms: int = 0) -> bool:
        if not self._ok:
            return False
        self._safe(lambda: self._q("decisions")
                   .update({
                       "outcome": outcome, "success": success,
                       "execution_time_ms": execution_time_ms,
                   }).eq("id", decision_id).execute())
        return True

    def add_decision_step(self, decision_id: int, step: str,
                          detail: str = "", data: Optional[dict] = None) -> Optional[int]:
        if not self._ok:
            return None
        res = self._safe(lambda: self._q("decision_history").insert({
            "decision_id": decision_id, "step": step,
            "detail": detail, "data": data or {},
        }).execute(), None)
        return res.data[0]["id"] if res and res.data else None

    # ════════════════════════════════════════════════════════════
    # v2 NEW TABLES — Tool Usage
    # ════════════════════════════════════════════════════════════

    def record_tool_usage(self, tool_name: str, success: bool = True,
                          latency_ms: int = 0, tokens_used: int = 0,
                          error_type: Optional[str] = None,
                          query_type: str = "general",
                          session_id: Optional[int] = None) -> Optional[int]:
        if not self._ok:
            return None
        res = self._safe(lambda: self._q("tool_usage").insert({
            "tool_name": tool_name, "success": success,
            "latency_ms": latency_ms, "tokens_used": tokens_used,
            "error_type": error_type, "query_type": query_type,
            "session_id": session_id,
        }).execute(), None)
        return res.data[0]["id"] if res and res.data else None

    def get_tool_stats(self, tool_name: Optional[str] = None) -> list:
        if not self._ok:
            return []
        q = self._q("tool_usage").select(
            "tool_name, count(*) as calls, "
            "avg(latency_ms) as avg_latency, "
            "sum(case when success then 1 else 0 end) as successes"
        )
        if tool_name:
            q = q.eq("tool_name", tool_name)
        res = self._safe(lambda: q.order("tool_name").execute(), None)
        return res.data if res and res.data else []

    # ════════════════════════════════════════════════════════════
    # v2 NEW TABLES — Learning Events
    # ════════════════════════════════════════════════════════════

    def record_learning_event(self, event_type: str, title: str = "",
                              description: str = "",
                              confidence: float = 0.5,
                              metadata: Optional[dict] = None) -> Optional[int]:
        if not self._ok:
            return None
        res = self._safe(lambda: self._q("learning_events").insert({
            "event_type": event_type, "title": title,
            "description": description, "confidence": confidence,
            "metadata": metadata or {},
        }).execute(), None)
        return res.data[0]["id"] if res and res.data else None

    def get_learning_events(self, event_type: Optional[str] = None,
                            limit: int = 20) -> list:
        if not self._ok:
            return []
        q = self._q("learning_events").select("*") \
            .order("id", desc=True).limit(limit)
        if event_type:
            q = q.eq("event_type", event_type)
        res = self._safe(lambda: q.execute(), None)
        return res.data if res and res.data else []

    # ════════════════════════════════════════════════════════════
    # v2 NEW TABLES — Behavior Patterns
    # ════════════════════════════════════════════════════════════

    def record_behavior_pattern(self, pattern_name: str,
                                trigger_query: Optional[str] = None,
                                action_taken: Optional[str] = None,
                                confidence: float = 0.3) -> Optional[int]:
        if not self._ok:
            return None
        now = datetime.now(timezone.utc).isoformat()
        existing = self._safe(lambda: self._q("behavior_patterns")
                              .select("id, pattern_name")
                              .eq("pattern_name", pattern_name)
                              .limit(1).execute(), None)
        if existing and existing.data:
            pid = existing.data[0]["id"]
            self._safe(lambda: self._q("behavior_patterns")
                       .update({
                           "sample_count": self._sb.raw("sample_count + 1"),
                           "last_observed": now,
                           "confidence": self._sb.raw("least(1.0, confidence + 0.05)"),
                       }).eq("id", pid).execute())
            return pid
        res = self._safe(lambda: self._q("behavior_patterns").insert({
            "pattern_name": pattern_name, "trigger_query": trigger_query,
            "action_taken": action_taken, "confidence": confidence,
            "sample_count": 1, "last_observed": now,
        }).execute(), None)
        return res.data[0]["id"] if res and res.data else None

    def get_behavior_patterns(self, min_confidence: float = 0.2,
                              limit: int = 20) -> list:
        if not self._ok:
            return []
        res = self._safe(lambda: self._q("behavior_patterns")
                         .select("*")
                         .gte("confidence", min_confidence)
                         .order("sample_count", desc=True)
                         .limit(limit).execute(), None)
        return res.data if res and res.data else []

    # ════════════════════════════════════════════════════════════
    # v2 NEW TABLES — Automation Rules
    # ════════════════════════════════════════════════════════════

    def create_automation_rule(self, name: str, description: str,
                               trigger_type: str, trigger_config: dict,
                               action_type: str, action_config: dict,
                               priority: int = 5) -> Optional[int]:
        if not self._ok:
            return None
        res = self._safe(lambda: self._q("automation_rules").insert({
            "name": name, "description": description,
            "trigger_type": trigger_type, "trigger_config": trigger_config,
            "action_type": action_type, "action_config": action_config,
            "priority": priority,
        }).execute(), None)
        return res.data[0]["id"] if res and res.data else None

    def get_automation_rules(self, enabled_only: bool = True) -> list:
        if not self._ok:
            return []
        q = self._q("automation_rules").select("*") \
            .order("priority").order("id")
        if enabled_only:
            q = q.eq("enabled", True)
        res = self._safe(lambda: q.execute(), None)
        return res.data if res and res.data else []

    # ════════════════════════════════════════════════════════════
    # v2 NEW TABLES — System Metrics
    # ════════════════════════════════════════════════════════════

    def record_metric(self, metric_name: str, metric_value: float,
                      metric_unit: str = "count",
                      labels: Optional[dict] = None,
                      session_id: Optional[int] = None) -> Optional[int]:
        if not self._ok:
            return None
        res = self._safe(lambda: self._q("system_metrics").insert({
            "metric_name": metric_name, "metric_value": metric_value,
            "metric_unit": metric_unit, "labels": labels or {},
            "session_id": session_id,
        }).execute(), None)
        return res.data[0]["id"] if res and res.data else None

    def get_metrics(self, metric_name: Optional[str] = None,
                    since: Optional[str] = None, limit: int = 100) -> list:
        if not self._ok:
            return []
        q = self._q("system_metrics").select("*") \
            .order("id", desc=True).limit(limit)
        if metric_name:
            q = q.eq("metric_name", metric_name)
        if since:
            q = q.gte("recorded_at", since)
        res = self._safe(lambda: q.execute(), None)
        return res.data if res and res.data else []

    # ════════════════════════════════════════════════════════════
    # v2 — Embedding / Vector Search
    # ════════════════════════════════════════════════════════════

    def _get_embedding(self, text: str) -> Optional[list]:
        """Generate embedding vector for text using configured provider.

        Returns a list of floats, or None on failure.
        """
        from app.core.config import (
            ENABLE_VECTOR_SEARCH, EMBEDDING_MODEL,
            EMBEDDING_DIMENSIONS, GROQ_API_KEY,
        )

        if not ENABLE_VECTOR_SEARCH or not GROQ_API_KEY:
            return None

        try:
            import requests
            resp = requests.post(
                "https://api.groq.com/openai/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": EMBEDDING_MODEL,
                    "input": text[:8000],
                    "dimensions": EMBEDDING_DIMENSIONS,
                },
                timeout=10,
            )
            if resp.status_code == 200:
                return resp.json()["data"][0]["embedding"]
        except Exception as e:
            logger.debug(f"Embedding failed: {e}")
        return None

    def store_with_embedding(self, table: str, data: dict,
                             text_for_embedding: str) -> Optional[dict]:
        """Insert a row with an embedding vector computed from text_for_embedding."""
        embedding = self._get_embedding(text_for_embedding)
        if embedding:
            data["embedding"] = embedding
        return self._safe(
            lambda: self._q(table).insert(data).execute(),
            None,
        )

    def search_by_vector(self, table: str, query_text: str,
                         threshold: float = 0.7, limit: int = 10) -> list:
        """Search a table by embedding similarity to query_text.

        Uses the Supabase pgvector search function for the specified table.
        Falls back to ilike keyword search if vector search is disabled or fails.
        """
        from app.core.config import ENABLE_VECTOR_SEARCH

        embedding = self._get_embedding(query_text) if ENABLE_VECTOR_SEARCH else None

        if embedding and self._ok:
            try:
                func_map = {
                    "episodic_memory": "search_episodic_memory",
                    "semantic_memory": "search_semantic_memory",
                }
                func_name = func_map.get(table)
                if func_name:
                    res = self._sb.rpc(func_name, {
                        "query_embedding": embedding,
                        "match_threshold": threshold,
                        "match_count": limit,
                    }).execute()
                    if res and res.data:
                        return res.data
            except Exception as e:
                logger.debug(f"Vector search failed for {table}: {e}")

        # Fallback: keyword search
        kw = query_text.lower()
        if table == "episodic_memory":
            return self.search_episodes(kw, limit=limit)
        elif table == "semantic_memory":
            if self._ok:
                res = self._safe(lambda: self._q("semantic_memory")
                                 .select("*")
                                 .ilike("fact_value", f"%{kw}%")
                                 .limit(limit).execute(), None)
                return res.data if res and res.data else []
        return []

