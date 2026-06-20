"""
app/core/orchestrator.py — Central orchestrator with cognitive processing pipeline.

Processing flow:
  1. Understand — analyze intent, emotion, entities
  2. Memory ops — handle explicit memory store/recall requests
  3. Context — build rich prompt from all memory layers
  4. Route & Execute — dispatch to appropriate agent
  5. Post-process — extract facts, tag emotions, update session
"""
import re
import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from app.core.memory import Memory, get_memory
from app.core.understanding import UnderstandingEngine, MessageAnalysis
from app.core.context_builder import ContextBuilder
from app.core.goal_tracker import GoalTracker
from app.core.events import EventSystem, is_event_request
from app.core.reflection import ReflectionEngine
from app.core.activity_logger import get_activity_logger
from app.core.intent_router import LLMIntentRouter

logger = logging.getLogger(__name__)


INTENT_AGENT_MAP = {
    # Direct handlers (orchestrator routes these internally)
    "music": None, "goal": None, "reminder": None,
    "reflection": None, "memory": None, "timer": None,
    # Goes to AssistantAgent (search/image/device are tools, not separate agents)
    "search":         "search",
    "image":          "image",
    "device_app":     "device",
    "device_call":    "device",
    "device_control": "device",
    "device_storage": "device",
    # Dedicated agents
    "research": "research",
    "coding":   "coding",
    # Default
    "chat": None,
}


class Orchestrator:
    """Routes user queries through the cognitive pipeline."""

    def __init__(self, memory=None):
        self.memory     = memory or get_memory()
        self.llm_router = LLMIntentRouter(cache_ttl=60)
        self.understanding = UnderstandingEngine()
        self.context_builder = ContextBuilder()
        self.goals      = GoalTracker(self.memory)
        self.events_sys = EventSystem(self.memory)
        self.reflector  = ReflectionEngine(self.memory)
        self._agent_cache = {}
        # ── Speed: TTL cache for expensive reads (60s) ──────────
        self._cache: dict = {}
        self._cache_ttl = 60  # seconds
        self._pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="jarvis")

    def _get_agent(self, name: str):
        """Lazy-load agent instances."""
        if name in self._agent_cache:
            return self._agent_cache[name]
        from app.agents import AGENT_REGISTRY
        cls = AGENT_REGISTRY.get(name)
        if cls:
            agent = cls()
            self._agent_cache[name] = agent
            return agent
        return None

    def _cached(self, key: str, fn):
        """Return cached value if fresh, else call fn() and cache result."""
        now = time.time()
        entry = self._cache.get(key)
        if entry and (now - entry["ts"]) < self._cache_ttl:
            return entry["val"]
        val = fn()
        self._cache[key] = {"val": val, "ts": now}
        return val

    def _invalidate_cache(self, *keys):
        for k in keys:
            self._cache.pop(k, None)

    def list_agents(self):
        return [
            {"name": "chat",           "description": "General conversation and tasks"},
            {"name": "coding",         "description": "Write, debug, and explain code"},
            {"name": "image",          "description": "Generate images from text prompts"},
            {"name": "research",       "description": "Multi-source research with citations"},
            {"name": "search",         "description": "Real-time web search and facts"},
            {"name": "music",          "description": "Search and play songs from YouTube"},
            {"name": "goal",           "description": "Manage goals, tasks, and projects"},
            {"name": "reminder",       "description": "Set and manage reminders and events"},
            {"name": "reflection",     "description": "Daily review and session summaries"},
            {"name": "device_app",     "description": "Open/launch Android apps"},
            {"name": "device_call",    "description": "Make phone calls"},
            {"name": "device_control", "description": "Control Android device features"},
            {"name": "memory",         "description": "Recall past conversations"},
        ]

    def run(self, query: str) -> dict:
        """Process a query through the full cognitive pipeline."""
        start = time.time()
        query = query.strip()

        if not query:
            return {
                "response": "Bol na yaar, kya scene hai?",
                "agent": "orchestrator",
                "success": False,
                "metadata": {},
                "brain": {},
                "time_ms": 0,
            }

        # ── 1. UNDERSTAND ───────────────────────────────────────
        user_profile = self.memory.get_user_profile()
        analysis = self.understanding.analyze(query, user_profile)

        # ── 2. AUTO-STORE ENTITIES ──────────────────────────────
        self._store_entities(analysis.entities)

        # ── 3. HANDLE MEMORY REQUESTS ───────────────────────────
        if analysis.is_memory_store:
            return self._handle_memory_store(query, analysis, start)
        if analysis.is_memory_recall:
            return self._handle_memory_recall(query, analysis, start)

        # ── 4. BUILD CONTEXT — parallel fetch ───────────────────
        # Run memory, goals, events queries simultaneously
        futures = {}
        with ThreadPoolExecutor(max_workers=3) as ex:
            futures["mem"]   = ex.submit(
                lambda: self.memory.build_memory_context(current_topic=analysis.topic, limit=5)
            )
            futures["goals"] = ex.submit(
                lambda: self._cached("goal_ctx", self.goals.build_goal_context)
            )
            futures["evts"]  = ex.submit(
                lambda: self._cached("event_ctx", self.events_sys.build_event_context)
            )

        memory_ctx = futures["mem"].result()
        goal_ctx   = futures["goals"].result()
        event_ctx  = futures["evts"].result()

        context = self.context_builder.build(
            user_profile=memory_ctx.get("user_profile", {}),
            emotional_context=memory_ctx.get("emotional_context", {}),
            recent_episodes=memory_ctx.get("recent_episodes", []),
            relevant_past=memory_ctx.get("relevant_past", []),
            current_analysis=analysis,
            extra_context="\n".join(filter(None, [goal_ctx, event_ctx])),
        )

        # ── 5. ROUTE & EXECUTE ──────────────────────────────────
        llm_result = self.llm_router.classify(query)
        agent_name = llm_result["intent"]
        intent_params = llm_result.get("parameters", {})

        if agent_name == "music":
            return self._handle_music(query, analysis, memory_ctx, context, start, intent_params)
        if agent_name == "goal":
            return self._handle_goal(query, analysis, memory_ctx, context, start, intent_params)
        if agent_name == "reminder":
            return self._handle_reminder(query, analysis, memory_ctx, context, start, intent_params)
        if agent_name == "reflection":
            return self._handle_reflection(query, analysis, memory_ctx, context, start)
        if agent_name == "memory":
            return self._handle_memory_recall(query, analysis, start)
        if agent_name == "timer":
            return self._handle_timer(query, analysis, memory_ctx, start, intent_params)

        agent = self._get_agent(INTENT_AGENT_MAP.get(agent_name))

        if agent:
            try:
                result = agent.run(query, intent_name=agent_name, intent_params=intent_params)
                response = str(result.get("result", ""))
                metadata = result.get("metadata", {})
                success = result.get("success", True)
            except Exception as e:
                logger.exception(f"Agent {agent_name} failed")
                response = f"Arre yaar, ek error aa gaya: {e}"
                metadata = {}
                success = False
        else:
            response = self._chat_response(query, context)
            metadata = {}
            success = True

        # ── 6. POST-PROCESS (background — don't block response) ─
        threading.Thread(
            target=self._post_process,
            args=(query, response, analysis),
            daemon=True,
        ).start()

        elapsed = int((time.time() - start) * 1000)
        return {
            "response": response,
            "agent": agent_name,
            "success": success,
            "metadata": metadata,
            "brain": {
                "intent": analysis.intent,
                "llm_intent": agent_name,
                "llm_confidence": llm_result.get("confidence", 0),
                "emotion_detected": analysis.emotion,
                "emotion_intensity": analysis.emotion_intensity,
                "topic": analysis.topic,
                "entities_found": len(analysis.entities),
                "expertise_level": analysis.expertise_level,
                "session_id": memory_ctx.get("session_id"),
            },
            "time_ms": elapsed,
        }

    # ── Chat Response ───────────────────────────────────────────

    def _chat_response(self, query: str, context: str) -> str:
        """Generate chat response using the enriched context."""
        from app.core.brain import ask_llm
        history = self.memory.get_recent_chat(4)  # 4 turns is enough, saves tokens
        messages = history + [{"role": "user", "content": query}]
        return ask_llm(messages, context=context) or "Yaar, samajh nahi aaya. Thoda aur bata?"

    # ── Music Handler ───────────────────────────────────────────

    def _handle_music(self, query: str, analysis: MessageAnalysis,
                      memory_ctx: dict, context: str, start: float,
                      intent_params: dict | None = None) -> dict:
        """Handle music/song requests via YouTube search."""
        from app.skills.youtube import handle_music_request, is_music_request

        # Check memory for favorite song preference
        profile = memory_ctx.get("user_profile", {})
        prefs = profile.get("preference", {})
        fav_song = prefs.get("favorite_song") or prefs.get("song") or prefs.get("music")

        # Use LLM-extracted song name if available
        llm_song = intent_params.get("song") if intent_params else None
        llm_artist = intent_params.get("artist") if intent_params else None

        # If user is vague ('koi bhi', 'kuch bhi') and we know their fav, use it
        vague_keywords = ["koi bhi", "kuch bhi", "anything", "koi sa", "koi"]
        is_vague = any(kw in query.lower() for kw in vague_keywords)

        effective_query = llm_song or query
        memory_note = ""
        if llm_artist and llm_song:
            effective_query = f"{llm_song} {llm_artist}"
        if is_vague and fav_song:
            effective_query = fav_song
            memory_note = f"(based on your favorite: {fav_song}) "

        result = handle_music_request(effective_query)

        if result and result.get("youtube_url"):
            reply = memory_note + result["reply"]
            metadata = {
                "youtube_url": result["youtube_url"],
                "title":       result.get("title", ""),
                "thumbnail":   result.get("thumbnail", ""),
            }
        else:
            # Fall back to chat — ask which song
            reply = self._chat_response(query, context)
            metadata = {}

        self._post_process(query, reply, analysis)
        elapsed = int((time.time() - start) * 1000)
        return {
            "response": reply,
            "agent":    "music",
            "success":  True,
            "metadata": metadata,
            "brain": {
                "intent":           analysis.intent,
                "emotion_detected": analysis.emotion,
                "topic":            analysis.topic,
                "session_id":       memory_ctx.get("session_id"),
            },
            "time_ms": elapsed,
        }

    # ── Timer Handler ───────────────────────────────────────────

    _DURATION_PATTERNS = [
        (r"(\d+)\s*(hour|hours|ghante|ghanta)s?", lambda n: n * 3600),
        (r"(\d+)\s*(min|minute|mins|minutes)s?", lambda n: n * 60),
        (r"(\d+)\s*(sec|second|seconds)s?", lambda n: n),
    ]

    def _parse_duration(self, query: str) -> tuple[Optional[int], Optional[str]]:
        """Extract duration in seconds from a natural language query.

        Returns:
            (seconds, label) on success, (None, None) on failure.
        """
        q = query.lower()
        # Try direct duration patterns first
        for pattern, multiplier in self._DURATION_PATTERNS:
            m = re.search(pattern, q)
            if m:
                n = int(m.group(1))
                secs = multiplier(n)
                if 1 <= secs <= 86400:
                    # Build a label from the remainder of the query
                    label = re.sub(r"\b(set|alarm|timer|countdown|for|ka|ke|ki|ka alarm|ka timer)\b",
                                   "", query, flags=re.IGNORECASE).strip(" ,.-") or "Alarm"
                    return secs, label[:100]
        return None, None

    def _handle_timer(self, query: str, analysis: MessageAnalysis,
                      memory_ctx: dict, start: float,
                      intent_params: dict | None = None) -> dict:
        """Handle timer/countdown requests via the server-side timer service."""
        # Prefer LLM-extracted duration
        params = intent_params or {}
        llm_secs = params.get("duration_seconds")
        if llm_secs and 1 <= llm_secs <= 86400:
            secs = llm_secs
            label = params.get("label", "Alarm")[:100]
        else:
            secs, label = self._parse_duration(query)

        if secs is None:
            # If the user said something like "set alarm" without a duration,
            # fall back to chat asking for duration
            reply = "Kitne minute ka timer set karna hai boss? 5 min, 30 sec — batao!"
            elapsed = int((time.time() - start) * 1000)
            return {
                "response": reply, "agent": "timer", "success": True,
                "metadata": {}, "brain": {"intent": "timer", "topic": analysis.topic,
                                          "session_id": memory_ctx.get("session_id")},
                "time_ms": elapsed,
            }

        from app.core.timer import get_timer_service
        result = get_timer_service().create_timer(secs, label or "Alarm")

        # Format response in Hinglish
        if secs >= 3600:
            hours = secs // 3600
            mins = (secs % 3600) // 60
            duration_str = f"{hours} ghante {mins} minute" if mins else f"{hours} ghante"
        elif secs >= 60:
            mins = secs // 60
            duration_str = f"{mins} minute"
        else:
            duration_str = f"{secs} seconds"

        reply = f"⏰ {duration_str} ka timer set kar diya! Bolaunga jab time ho jayega! 💪"

        self._post_process(query, reply, analysis)

        elapsed = int((time.time() - start) * 1000)
        return {
            "response": reply,
            "agent": "timer",
            "success": True,
            "metadata": {
                "timer": {
                    "id": result["id"],
                    "remaining": result["remaining"],
                    "label": result["label"],
                }
            },
            "brain": {"intent": "timer", "topic": analysis.topic,
                      "session_id": memory_ctx.get("session_id")},
            "time_ms": elapsed,
        }

    # ── Goal Handler ────────────────────────────────────────────

    def _handle_goal(self, query: str, analysis: MessageAnalysis,
                     memory_ctx: dict, context: str, start: float,
                     intent_params: dict | None = None) -> dict:
        """Handle goal/project management requests."""
        import re
        params = intent_params or {}
        action = params.get("action", "add")

        if action == "complete":
            goals = self.goals.get_active_goals()
            if goals:
                self.goals.complete_goal(goals[0]["id"])
                reply = f"✅ '{goals[0]['title']}' — mark kar diya done! Badhiya kaam kiya boss! 🎉"
            else:
                reply = "Koi active goal nahi mila. Pehle ek goal add karo!"
        elif action == "list":
            goals = self.goals.get_active_goals()
            projects = self.goals.get_active_projects()
            if not goals and not projects:
                reply = "Boss abhi koi active goal nahi hai. Bolo kya karna hai — main add kar deti hoon!"
            else:
                lines = ["📋 **Active Goals:**"]
                for g in goals:
                    pri = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(g.get("priority", "medium"), "•")
                    dl = f" | Due: {g['deadline']}" if g.get("deadline") else ""
                    lines.append(f"  {pri} {g['title']}{dl}")
                if projects:
                    lines.append("\n🗂 **Projects:**")
                    for p in projects:
                        lines.append(f"  • {p['name']}")
                reply = "\n".join(lines)
        else:
            title = params.get("title") or query[:80]
            q = query.lower()
            priority = "high" if any(kw in q for kw in ["important", "urgent", "zaruri", "jaldi"]) else "medium"
            result = self.goals.add_goal(title, priority=priority)
            reply = f"✅ Goal add kar diya: **{title}** [{priority}] 💪" if result else "Goal add nahi ho saka, try again!"

        self._post_process(query, reply, analysis)
        elapsed = int((time.time() - start) * 1000)
        return {"response": reply, "agent": "goal", "success": True, "metadata": {},
                "brain": {"intent": "goal", "topic": analysis.topic,
                           "session_id": memory_ctx.get("session_id")}, "time_ms": elapsed}

    # ── Reminder Handler ────────────────────────────────────────

    def _handle_reminder(self, query: str, analysis: MessageAnalysis,
                         memory_ctx: dict, context: str, start: float,
                         intent_params: dict | None = None) -> dict:
        """Handle reminder/event creation requests."""
        params = intent_params or {}
        action = params.get("action", "create")

        if action == "list":
            events = self.events_sys.get_upcoming_events(hours_ahead=72)
            if not events:
                reply = "Koi upcoming reminder nahi hai. Kuch schedule karein?"
            else:
                lines = ["📅 **Upcoming Reminders:**"]
                for e in events[:8]:
                    t = str(e.get("event_time", ""))[:16].replace("T", " ")
                    lines.append(f"  🔔 {t} — {e['title']}")
                reply = "\n".join(lines)
        else:
            parsed = self.events_sys.parse_event_from_text(query)
            self.events_sys.add_event(title=parsed["title"], event_time=parsed.get("event_time"))
            if parsed.get("event_time"):
                t = parsed["event_time"][:16].replace("T", " ")
                reply = f"🔔 Reminder set! **{parsed['title']}** — {t} pe yaad dilaungi boss! ✅"
            else:
                reply = f"🔔 Note kar liya: **{parsed['title']}**. Time batao toh exact alert set kar dun!"

        self._post_process(query, reply, analysis)
        elapsed = int((time.time() - start) * 1000)
        return {"response": reply, "agent": "reminder", "success": True, "metadata": {},
                "brain": {"intent": "reminder", "topic": analysis.topic,
                           "session_id": memory_ctx.get("session_id")}, "time_ms": elapsed}

    # ── Reflection Handler ──────────────────────────────────────

    def _handle_reflection(self, query: str, analysis: MessageAnalysis,
                           memory_ctx: dict, context: str, start: float) -> dict:
        """Handle daily review and session reflection."""
        from app.core.brain import ask_llm
        q = query.lower()
        if any(kw in q for kw in ["daily", "aaj", "din", "today", "review"]):
            reply = self.reflector.daily_review(ask_llm)
        else:
            session_id = memory_ctx.get("session_id", 1)
            reply = self.reflector.reflect_on_session(int(session_id), ask_llm)

        self._post_process(query, reply, analysis)
        elapsed = int((time.time() - start) * 1000)
        return {"response": reply, "agent": "reflection", "success": True, "metadata": {},
                "brain": {"intent": "reflection", "topic": analysis.topic,
                           "session_id": memory_ctx.get("session_id")}, "time_ms": elapsed}

    # ── Memory Store Handler ────────────────────────────────────

    def _handle_memory_store(self, query: str, analysis: MessageAnalysis, start: float) -> dict:
        """Handle explicit memory storage requests."""
        # Store entities that were extracted
        self._store_entities(analysis.entities)

        # Also try LLM-based extraction for complex facts
        try:
            from app.core.brain import extract_facts_from_text
            facts = extract_facts_from_text(query)
            for f in facts:
                self.memory.store_fact(
                    category=f["category"],
                    key=f["key"],
                    value=f["value"],
                    confidence=0.9,
                )
        except Exception as e:
            logger.warning(f"LLM fact extraction failed: {e}")

        # Record the episode
        self.memory.add_episode(
            role="user", content=query,
            topic=analysis.topic, emotion=analysis.emotion,
            importance=3,
        )

        response = "Yaad rakh liya bhai! 👍 Aage se dhyan rahunga."
        self._log_activity(query, response)
        self.memory.add_episode(
            role="assistant", content=response,
            topic=analysis.topic, emotion="happy",
        )

        elapsed = int((time.time() - start) * 1000)
        return {
            "response": response,
            "agent": "memory",
            "success": True,
            "metadata": {"task": "memory_store"},
            "brain": {
                "intent": analysis.intent,
                "emotion_detected": analysis.emotion,
                "topic": analysis.topic,
                "entities_found": len(analysis.entities),
            },
            "time_ms": elapsed,
        }

    # ── Memory Recall Handler ───────────────────────────────────

    def _handle_memory_recall(self, query: str, analysis: MessageAnalysis, start: float) -> dict:
        """Handle explicit memory recall requests — uses fast_recall() cache first."""
        import time as _time
        t0 = _time.time()

        # ━━ 1. Fast-path: check warm LRU cache (sub-millisecond) ━━━━━━━━━━━━━
        recalled = self.memory.fast_recall(query, limit=8)
        cache_hit = recalled.get("cache_hit", False)

        # ━━ 2. Build LLM context from recalled data ━━━━━━━━━━━━━━━━━━━
        context = self.context_builder.build(
            user_profile=recalled.get("user_profile", {}),
            emotional_context={},
            recent_episodes=recalled.get("recent_chat", []),
            relevant_past=recalled.get("matched_episodes", []),
            current_analysis=analysis,
        )

        # ━━ 3. Inject sessions summary into prompt ━━━━━━━━━━━━━━━━━━━━━
        sessions = recalled.get("sessions_summary", [])
        if sessions:
            sess_lines = ["\n═══ PREVIOUS SESSIONS RECAP ═══"]
            for s in sessions:
                status = s.get("ended_at", "active")
                sess_lines.append(
                    f"  Session {s['session_id']} [{status}]: {s.get('summary', '')[:80]}"
                )
            context += "\n".join(sess_lines)

        from app.core.brain import ask_llm
        messages = [{"role": "user", "content": query}]
        response = ask_llm(messages, context=context)

        # ━━ 4. Record this exchange (background) ━━━━━━━━━━━━━━━━━━━━━━━
        threading.Thread(
            target=self._post_process,
            args=(query, response, analysis),
            daemon=True,
        ).start()

        recall_ms = int((_time.time() - t0) * 1000)
        elapsed   = int((_time.time() - start) * 1000)
        logger.info(f"memory_recall: cache_hit={cache_hit}, recall_ms={recall_ms}, total_ms={elapsed}")

        return {
            "response": response,
            "agent": "memory",
            "success": True,
            "metadata": {
                "task":       "memory_recall",
                "cache_hit":  cache_hit,
                "recall_ms":  recall_ms,
                "matches":    len(recalled.get("matched_episodes", [])),
            },
            "brain": {
                "intent":           analysis.intent,
                "emotion_detected": analysis.emotion,
                "topic":            analysis.topic,
                "entities_found":   len(analysis.entities),
            },
            "time_ms": elapsed,
        }

    # ── Post-Processing ─────────────────────────────────────────

    def _log_activity(self, query: str, response: str):
        """Log conversation to daily activity file (background)."""
        try:
            get_activity_logger().log(query, response)
        except Exception:
            logger.debug("Activity log skipped")

    def _post_process(self, query: str, response: str, analysis: MessageAnalysis):
        """After generating a response: save episodes, extract facts, tag emotions."""
        self._log_activity(query, response)
        try:
            # Save episodes to episodic memory
            episode_id = self.memory.add_episode(
                role="user", content=query,
                topic=analysis.topic,
                emotion=analysis.emotion,
                importance=2 if analysis.entities else 1,
            )
            self.memory.add_episode(
                role="assistant", content=response[:500],
                topic=analysis.topic,
            )

            # Record emotion if not neutral
            if analysis.emotion != "neutral":
                self.memory.record_emotion(
                    topic=analysis.topic,
                    emotion=analysis.emotion,
                    intensity=analysis.emotion_intensity,
                    episode_id=episode_id,
                    context=query[:200],
                )

            # Auto-extract and store entities
            self._store_entities(analysis.entities)

        except Exception:
            logger.exception("Post-processing error")

    # ── Entity Storage Helper ───────────────────────────────────

    _ENTITY_TO_CATEGORY = {
        "name": "identity",
        "age": "identity",
        "location": "location",
        "profession": "profession",
        "project": "project",
        "preference": "preference",
    }

    def _store_entities(self, entities: dict):
        """Store extracted entities into semantic memory."""
        if not entities:
            return
        for entity_type, value in entities.items():
            category = self._ENTITY_TO_CATEGORY.get(entity_type, "personal")
            try:
                self.memory.store_fact(
                    category=category,
                    key=entity_type,
                    value=str(value),
                    confidence=0.9,
                )
                # Also mirror to legacy user_facts for backward compat
                self.memory.learn_fact(
                    key=entity_type,
                    value=str(value),
                    fact_type=category,
                    priority=2,
                )
                logger.info(f"Auto-stored entity: {entity_type}={value}")
            except Exception as e:
                logger.warning(f"Failed to store entity {entity_type}: {e}")
