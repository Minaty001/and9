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

