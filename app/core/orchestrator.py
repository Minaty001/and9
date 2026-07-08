"""
app/core/orchestrator.py — Central orchestrator with cognitive processing pipeline.

Constitution V3 processing flow:
  1. Understand — analyze intent, emotion, entities
  2. Truth Engine — validate memory before LLM calls (Rule 5)
  3. Memory ops — handle explicit memory store/recall requests
  4. Context — build rich prompt from all memory layers
  5. Route & Execute — dispatch to appropriate agent
  6. Post-process — save episodes, tag emotions (no auto-entity storage)
"""
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
from app.core.truth_engine import verify_before_llm, cap_confidence

logger = logging.getLogger(__name__)


class IntentRouter:
    """Keyword-based intent router. Fast, zero LLM calls."""

    PATTERNS = {
        "search":   ["find", "look up", "google", "news", "weather", "who is", "what is"],
        "research": ["in-depth", "comprehensive", "tell me everything about", "deep dive", "history of"],
        "coding":   ["code", "python", "javascript", "bug", "fix", "debug", "function", "refactor"],
        "music":    ["song", "gaana", "music", "gana", "sunna", "laga do", "bajao",
                     "play", "baja do", "track", "playlist", "singer", "soft song",
                     "sad song", "romantic", "sunao", "ghazal", "bhajan"],
        "goal":     ["goal", "target", "aim", "objective", "lakshya", "mera goal",
                     "add goal", "new goal", "set goal", "complete goal", "goals kya hain",
                     "project", "kaam", "task", "todo", "to do", "meri list"],
        "reminder": ["remind", "reminder", "yaad dilana", "yaad dila", "mat bhoolna",
                     "event", "meeting", "schedule", "appointment", "alert"],
        "reflection":["daily review", "aaj kya kiya", "session summary", "reflect",
                      "din ka summary", "review karo", "kya kiya aaj"],
        "device":   ["turn on", "turn off", "enable", "disable", "wifi", "wi-fi",
                     "bluetooth", "torch", "flashlight", "volume", "brightness", "battery",
                     "camera", "photo", "youtube", "whatsapp", "chrome", "calculator",
                     "maps", "telegram", "spotify", "instagram", "alarm", "call", "dial",
                     "contact", "contacts", "file", "folder", "directory", "storage"],
        "pc":       ["pc", "computer", "laptop", "desktop", "windows",
                     "shutdown", "restart", "reboot", "screenshot", "lock pc",
                     "open notepad", "open chrome", "type ", "write ",
                     "list windows", "switch to", "system info", "pc info",
                     "lock computer", "sleep", "hibernate"],
        "audio":    ["bluetooth audio", "bluetooth mic", "bluetooth speaker",
                     "auto detect bluetooth", "switch to bluetooth",
                     "reset audio", "system audio", "audio status"],
    }

    def route(self, query: str) -> str:
        q = query.lower().strip()
        if not q:
            return "chat"

        if any(kw in q for kw in self.PATTERNS["reflection"]):
            return "reflection"
        if any(kw in q for kw in self.PATTERNS["audio"]):
            return "audio"
        if any(kw in q for kw in self.PATTERNS["pc"]):
            return "pc"
        if any(kw in q for kw in self.PATTERNS["device"]):
            return "device"
        if any(kw in q for kw in self.PATTERNS["goal"]):
            return "goal"
        if any(kw in q for kw in self.PATTERNS["reminder"]):
            return "reminder"
        if any(kw in q for kw in self.PATTERNS["music"]):
            return "music"
        if q.startswith("search") or q.startswith("find ") or q.startswith("look up") or q.startswith("google"):
            return "search"
        if any(kw in q for kw in self.PATTERNS["coding"]):
            return "coding"
        if q.startswith("research") or any(kw in q for kw in self.PATTERNS["research"]):
            return "research"
        if any(kw in q for kw in self.PATTERNS["search"]):
            return "search"

        return "chat"


class Orchestrator:
    """Routes user queries through the cognitive pipeline."""

    def __init__(self, memory=None):
        self.memory     = memory or get_memory()
        self.router     = IntentRouter()
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
            {"name": "chat",       "description": "General conversation and tasks"},
            {"name": "coding",     "description": "Write, debug, and explain code"},
            {"name": "research",   "description": "Multi-source research with citations"},
            {"name": "search",     "description": "Real-time web search and facts"},
            {"name": "music",      "description": "Search and play songs from YouTube"},
            {"name": "goal",       "description": "Manage goals, tasks, and projects"},
            {"name": "reminder",   "description": "Set and manage reminders and events"},
            {"name": "reflection", "description": "Daily review and session summaries"},
            {"name": "device",     "description": "Control Android device features"},
            {"name": "pc",         "description": "Control PC: volume, brightness, apps, screenshots, system"},
            {"name": "audio",      "description": "Manage Bluetooth audio devices and settings"},
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

        # ── 2. HANDLE MEMORY REQUESTS ───────────────────────────
        if analysis.is_memory_store:
            return self._handle_memory_store(query, analysis, start)
        if analysis.is_memory_recall:
            return self._handle_memory_recall(query, analysis, start)

        # ── 3. BUILD CONTEXT + TRUTH CHECK — parallel fetch ────
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

        # ── 4. TRUTH ENGINE — verify before LLM ──────────────────
        import re
        personal_patterns = [
            r"\bmy\b", r"\bwho am i\b", r"\bwhat is my\b", r"\bwhere do i\b", r"\bfavorite\b",
            r"\bmera\b", r"\bmeri\b", r"\bmujhe\b", r"\bmain kahan\b", r"\byaad hai\b", r"\babout me\b",
            r"\bpreference\b", r"\bhobby\b", r"\bprofession\b", r"\bjob\b", r"\bcity\b",
            r"\blocation\b", r"\bage\b", r"\bnaam\b"
        ]
        is_asking_personal = any(re.search(pat, query.lower()) for pat in personal_patterns)
        
        # Check if "me" is used personally (not as a filler object of tell/show/give/remind)
        if not is_asking_personal and re.search(r"\bme\b", query.lower()):
            if not re.search(r"\b(tell|show|give|play|send|remind|ask|let|help|with)\s+me\b", query.lower()):
                is_asking_personal = True

        if is_asking_personal or analysis.is_memory_recall:
            has_truth, guidance = verify_before_llm(memory_ctx, query)
            if not has_truth:
                # No usable memory — return honest don't-know
                elapsed = int((time.time() - start) * 1000)
                return {
                    "response": guidance,
                    "agent": "orchestrator",
                    "success": True,
                    "metadata": {"truth_engine": "no_memory"},
                    "brain": {
                        "intent": analysis.intent,
                        "emotion_detected": analysis.emotion,
                        "emotion_intensity": analysis.emotion_intensity,
                        "topic": analysis.topic,
                        "entities_found": len(analysis.entities),
                        "expertise_level": analysis.expertise_level,
                        "session_id": memory_ctx.get("session_id"),
                        "truth_engine": "no_verified_memory",
                    },
                    "time_ms": elapsed,
                }

        context = self.context_builder.build(
            user_profile=memory_ctx.get("user_profile", {}),
            emotional_context=memory_ctx.get("emotional_context", {}),
            recent_episodes=memory_ctx.get("recent_episodes", []),
            relevant_past=memory_ctx.get("relevant_past", []),
            current_analysis=analysis,
            extra_context="\n".join(filter(None, [goal_ctx, event_ctx])),
        )

        # ── 5. ROUTE & EXECUTE ──────────────────────────────────
        agent_name = self.router.route(query)

        if agent_name == "music":
            return self._handle_music(query, analysis, memory_ctx, context, start)
        if agent_name == "goal":
            return self._handle_goal(query, analysis, memory_ctx, context, start)
        if agent_name == "reminder":
            return self._handle_reminder(query, analysis, memory_ctx, context, start)
        if agent_name == "reflection":
            return self._handle_reflection(query, analysis, memory_ctx, context, start)

        agent = self._get_agent(agent_name)

        if agent:
            try:
                result = agent.run(query)
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
                      memory_ctx: dict, context: str, start: float) -> dict:
        """Handle music/song requests via YouTube search."""
        from app.skills.youtube import handle_music_request, is_music_request

        # Check memory for favorite song preference
        profile = memory_ctx.get("user_profile", {})
        prefs = profile.get("preference", {})
        fav_song = prefs.get("favorite_song") or prefs.get("song") or prefs.get("music")

        # If user is vague ('koi bhi', 'kuch bhi') and we know their fav, use it
        vague_keywords = ["koi bhi", "kuch bhi", "anything", "koi sa", "koi"]
        is_vague = any(kw in query.lower() for kw in vague_keywords)

        effective_query = query
        memory_note = ""
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

    # ── Goal Handler ────────────────────────────────────────────

    def _handle_goal(self, query: str, analysis: MessageAnalysis,
                     memory_ctx: dict, context: str, start: float) -> dict:
        """Handle goal/project management requests."""
        import re
        q = query.lower()

        if any(kw in q for kw in ["complete", "done", "khatam", "finish", "ho gaya"]):
            goals = self.goals.get_active_goals()
            if goals:
                self.goals.complete_goal(goals[0]["id"])
                reply = f"✅ '{goals[0]['title']}' — mark kar diya done! Badhiya kaam kiya boss! 🎉"
            else:
                reply = "Koi active goal nahi mila. Pehle ek goal add karo!"
        elif any(kw in q for kw in ["list", "show", "kya hain", "batao", "dikhaao", "meri list", "goals kya"]):
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
            title = re.sub(
                r"\b(goal|target|add|set|new|mera|meri|jarvis|please|lagao|daalo|create)\b",
                "", query, flags=re.IGNORECASE
            ).strip(" ,.-") or query[:80]
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
                         memory_ctx: dict, context: str, start: float) -> dict:
        """Handle reminder/event creation requests."""
        q = query.lower()

        if any(kw in q for kw in ["list", "show", "kya hain", "upcoming", "schedule", "batao"]):
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
        """Handle explicit memory storage requests.

        Per Rule 5/6: ONLY store entities extracted via regex (confidence 0.3).
        NEVER use LLM for fact extraction.
        """
        # Store regex-extracted entities at appropriate confidence
        self._store_entities(analysis.entities, source="regex_extraction")

        # Record the episode with source tracking
        self.memory.add_episode(
            role="user", content=query,
            topic=analysis.topic, emotion=analysis.emotion,
            importance=3,
            source="user_input",
        )

        response = "Yaad rakh liya bhai! 👍 Aage se dhyan rahunga."
        self.memory.add_episode(
            role="assistant", content=response,
            topic=analysis.topic, emotion="happy",
            source="llm_response",
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
        """Handle explicit memory recall requests.

        Per Rule 1/4: First check Truth Engine for verified memory.
        If no verified memory exists, return honest "I don't know".
        """
        # Build memory context
        memory_ctx = self.memory.build_memory_context(
            current_topic=analysis.topic, limit=10
        )

        # Truth Engine check — do we actually have verified memory?
        has_truth, guidance = verify_before_llm(memory_ctx, query)
        if not has_truth:
            # No verified memory about this topic
            self.memory.add_episode(
                role="user", content=query,
                topic=analysis.topic, emotion=analysis.emotion,
            )
            self.memory.add_episode(
                role="assistant", content=guidance[:500],
                topic=analysis.topic,
            )
            elapsed = int((time.time() - start) * 1000)
            return {
                "response": guidance,
                "agent": "memory",
                "success": True,
                "metadata": {"task": "memory_recall", "truth_engine": "no_memory"},
                "brain": {
                    "intent": analysis.intent,
                    "emotion_detected": analysis.emotion,
                    "topic": analysis.topic,
                    "entities_found": len(analysis.entities),
                },
                "time_ms": elapsed,
            }

        # We have verified memory — build context and ask LLM
        context = self.context_builder.build(
            user_profile=memory_ctx.get("user_profile", {}),
            emotional_context=memory_ctx.get("emotional_context", {}),
            recent_episodes=memory_ctx.get("recent_episodes", []),
            relevant_past=memory_ctx.get("relevant_past", []),
            current_analysis=analysis,
        )

        from app.core.brain import ask_llm
        messages = [{"role": "user", "content": query}]
        response = ask_llm(messages, context=context)

        # Record this exchange
        self.memory.add_episode(
            role="user", content=query,
            topic=analysis.topic, emotion=analysis.emotion,
        )
        self.memory.add_episode(
            role="assistant", content=response[:500],
            topic=analysis.topic,
        )

        elapsed = int((time.time() - start) * 1000)
        return {
            "response": response,
            "agent": "memory",
            "success": True,
            "metadata": {"task": "memory_recall"},
            "brain": {
                "intent": analysis.intent,
                "emotion_detected": analysis.emotion,
                "topic": analysis.topic,
                "entities_found": len(analysis.entities),
            },
            "time_ms": elapsed,
        }

    # ── Post-Processing ─────────────────────────────────────────

    def _post_process(self, query: str, response: str, analysis: MessageAnalysis):
        """After generating a response: save episodes, tag emotions.

        Per Rule 5/6: Does NOT auto-store entities (removed).
        Entities are only stored during explicit memory_store requests.
        """
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

    def _store_entities(self, entities: dict, source: str = "regex_extraction"):
        """Store extracted entities into semantic memory.

        Per Rule 5: regex_extraction has max confidence of 0.3.
        Per Rule 6: never LLM-inferred facts.
        Entities are only stored with appropriate source and confidence.

        Args:
            entities: Dict of entity_type → value from regex extraction.
            source: Source type (default regex_extraction).
        """
        if not entities:
            return
        confidence = cap_confidence(source)
        for entity_type, value in entities.items():
            category = self._ENTITY_TO_CATEGORY.get(entity_type, "personal")
            try:
                self.memory.store_fact(
                    category=category,
                    key=entity_type,
                    value=str(value),
                    confidence=confidence,
                    source=source,
                    verified=False,  # regex-extracted, not user-confirmed
                )
                # Mirror to user_facts for backward compat
                self.memory.learn_fact(
                    key=entity_type,
                    value=str(value),
                    fact_type=category,
                    priority=2,
                    source=source,
                    confidence=confidence,
                    verified=False,
                )
                logger.info(f"Stored entity: {entity_type}={value} (conf={confidence}, source={source})")
            except Exception as e:
                logger.warning(f"Failed to store entity {entity_type}: {e}")
