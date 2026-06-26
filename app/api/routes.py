"""
app/api/routes.py — JSON API endpoints for the chat interface.
"""
import io
import asyncio
import logging
from app._flask_compat import Blueprint, request, jsonify, Response

from app.core.orchestrator import Orchestrator
from app.core.memory import Memory
from app.core.goal_tracker import GoalTracker
from app.core.events import EventSystem
from app.core.reflection import ReflectionEngine
from app.core.proactive import ProactiveEngine

logger = logging.getLogger(__name__)
api_bp = Blueprint("api", __name__)

# Module-level singletons (lazy init to avoid import-time side effects)
_orchestrator = None
_memory       = None
_goals        = None
_events       = None
_reflector    = None


def get_orch():
    """Get or create the singleton Orchestrator instance.

    Lazy-initializes the orchestrator on first call and caches it
    in the module-level ``_orchestrator`` variable.

    Returns:
        Orchestrator: The global orchestrator instance.
    """
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator


def get_mem():
    """Get or create the singleton Memory instance.

    Lazy-initializes the memory subsystem on first call and caches it
    in the module-level ``_memory`` variable.

    Returns:
        Memory: The global memory instance.
    """
    global _memory
    if _memory is None:
        _memory = Memory()
    return _memory


def get_goals():
    """Get or create the singleton GoalTracker instance.

    Lazy-initializes the goal tracker backed by the memory subsystem
    and caches it in the module-level ``_goals`` variable.

    Returns:
        GoalTracker: The global goal tracker instance.
    """
    global _goals
    if _goals is None:
        _goals = GoalTracker(get_mem())
    return _goals


def get_events():
    """Get or create the singleton EventSystem instance.

    Lazy-initializes the event system backed by the memory subsystem
    and caches it in the module-level ``_events`` variable.

    Returns:
        EventSystem: The global event system instance.
    """
    global _events
    if _events is None:
        _events = EventSystem(get_mem())
    return _events


def get_reflector():
    """Get or create the singleton ReflectionEngine instance.

    Lazy-initializes the reflection engine backed by the memory subsystem
    and caches it in the module-level ``_reflector`` variable.

    Returns:
        ReflectionEngine: The global reflection engine instance.
    """
    global _reflector
    if _reflector is None:
        _reflector = ReflectionEngine(get_mem())
    return _reflector



@api_bp.route("/chat", methods=["POST"])
def chat():
    """POST /api/chat — Process a user message through the orchestrator.

    Accepts a JSON body with a ``message`` field, routes it through the
    orchestrator pipeline, and returns the AI response along with any
    device intents, media URLs, sources, and brain metadata.

    Returns:
        JSON response with keys: reply, agent, time_ms, image_url,
        youtube_url, sources, status, brain, metadata, intent.
        500 on server error.
    """
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"reply": "Please provide a message."})

    try:
        result = get_orch().run(message)
        
        # Extract intent from metadata if device action
        intent = None
        metadata = result.get("metadata", {})
        if metadata.get("task") == "device" and (metadata.get("action") in ["PLAY_VIDEO", "LAUNCH_APP", "SET_ALARM", "CREATE_EVENT", "CALL"] or "intent" in metadata):
            intent = metadata.get("intent") or metadata.get("payload")

        return jsonify({
            "reply":       result.get("response", ""),
            "agent":       result.get("agent", "chat"),
            "time_ms":     result.get("time_ms", 0),
            "image_url":   result.get("metadata", {}).get("image_url"),
            "youtube_url": result.get("metadata", {}).get("youtube_url"),
            "sources":     result.get("metadata", {}).get("sources"),
            "status":      "success" if result.get("success", True) else "error",
            "brain":       result.get("brain", {}),
            "metadata":    result.get("metadata", {}),
            "intent":      intent,  # NEW: Device intent for frontend execution
        })
    except Exception as e:
        logger.exception("Chat endpoint error")
        return jsonify({"reply": f"I encountered an error: {e}", "status": "error"}), 500


@api_bp.route("/agents", methods=["GET"])
def list_agents():
    """GET /api/agents — List all available agent names from the orchestrator.

    Returns:
        JSON list of agent name strings.
    """
    return jsonify(get_orch().list_agents())


@api_bp.route("/history", methods=["GET"])
def get_history():
    """GET /api/history — Return the 20 most recent chat turns from memory.

    Returns:
        JSON list of recent chat history entries.
    """
    return jsonify(get_mem().get_recent_chat(20))


@api_bp.route("/memory/facts", methods=["GET"])
def get_facts():
    """GET /api/memory/facts — Retrieve all stored facts from semantic memory.

    Returns:
        JSON list of fact objects.
    """
    return jsonify(get_mem().get_facts())


@api_bp.route("/memory/learn", methods=["POST"])
def learn_fact():
    """POST /api/memory/learn — Store a new fact into semantic memory.

    Accepts JSON body with ``key``, ``value``, and optional ``fact_type``.

    Returns:
        JSON ``{"status": "learned", "key": key}`` on success.
        400 if key or value is missing.
    """
    data = request.get_json(silent=True) or {}
    key = data.get("key", "").strip()
    value = data.get("value", "").strip()
    if key and value:
        get_mem().learn_fact(key, value, data.get("fact_type", "personal"))
        return jsonify({"status": "learned", "key": key})
    return jsonify({"error": "key and value required"}), 400


@api_bp.route("/memory/fact", methods=["DELETE"])
def delete_fact():
    """DELETE /api/memory/fact — Remove a fact from semantic memory by key.

    Accepts JSON body with ``key`` specifying which fact to delete.

    Returns:
        JSON ``{"status": "deleted", "key": key}`` on success.
        400 if key is missing; 404 if the fact is not found.
    """
    data = request.get_json(silent=True) or {}
    key = data.get("key", "").strip()
    if not key:
        return jsonify({"error": "key is required"}), 400
    deleted = get_mem().delete_fact(key)
    if deleted:
        return jsonify({"status": "deleted", "key": key})
    return jsonify({"error": "fact not found", "key": key}), 404


@api_bp.route("/memory/search", methods=["GET"])
def search_facts():
    """GET /api/memory/search — Search facts by keyword.

    Accepts a query parameter ``q`` and returns matching facts from semantic memory.

    Returns:
        JSON list of matching fact objects.
        400 if ``q`` parameter is missing.
    """
    keyword = request.args.get("q", "").strip()
    if not keyword:
        return jsonify({"error": "query parameter 'q' is required"}), 400
    results = get_mem().search_facts(keyword)
    return jsonify(results)


@api_bp.route("/memory/recall", methods=["GET"])
def fast_recall():
    """GET /api/memory/recall?q=<query>[&limit=8]

    Fast cross-session memory recall backed by an LRU cache.
    Returns matched past episodes, user profile, recent chat turns,
    and a sessions summary in a single response.

    Query params:
        q     (str) — search keywords (required)
        limit (int) — max episode matches to return (default: 8)
    """
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "query parameter 'q' is required"}), 400
    limit = min(int(request.args.get("limit", 8)), 50)
    try:
        result = get_mem().fast_recall(query, limit=limit)
        return jsonify({
            "query":             query,
            "cache_hit":         result.get("cache_hit", False),
            "matched_episodes":  result.get("matched_episodes", []),
            "user_profile":      result.get("user_profile", {}),
            "recent_chat":       result.get("recent_chat", []),
            "sessions_summary":  result.get("sessions_summary", []),
        })
    except Exception as e:
        logger.exception("fast_recall endpoint error")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/memory/cache/stats", methods=["GET"])
def recall_cache_stats():
    """GET /api/memory/cache/stats — live cache statistics (size, TTL, hit count)."""
    from app.core.memory import get_recall_cache_stats
    return jsonify(get_recall_cache_stats())


@api_bp.route("/memory/episodes/search", methods=["GET"])
def search_episodes():
    """GET /api/memory/episodes/search?q=<keyword>[&limit=10]

    Keyword search across all stored episodic memory entries.
    """
    keyword = request.args.get("q", "").strip()
    if not keyword:
        return jsonify({"error": "query parameter 'q' is required"}), 400
    limit = min(int(request.args.get("limit", 10)), 50)
    results = get_mem().search_episodes(keyword, limit=limit)
    return jsonify({"keyword": keyword, "results": results, "count": len(results)})


@api_bp.route("/memory/sessions", methods=["GET"])
def sessions_summary():
    """GET /api/memory/sessions[?limit=5] — summary of recent conversation sessions."""
    limit = min(int(request.args.get("limit", 5)), 20)
    summaries = get_mem().get_sessions_summary(limit=limit)
    return jsonify({"sessions": summaries, "count": len(summaries)})


@api_bp.route("/brain/profile", methods=["GET"])
def brain_profile():
    """Return the full user profile from semantic memory."""
    return jsonify(get_mem().get_user_profile())


@api_bp.route("/brain/emotions", methods=["GET"])
def brain_emotions():
    """Return the emotional context from emotional memory."""
    return jsonify(get_mem().get_emotional_context())


@api_bp.route("/brain/sessions", methods=["GET"])
def brain_sessions():
    """Return the current session info."""
    session_id = get_mem().get_or_create_session()
    history = get_mem().get_session_history(session_id)
    return jsonify({
        "session_id": session_id,
        "episode_count": len(history),
        "episodes": history[-20:],  # Last 20 episodes
    })


@api_bp.route("/understanding/analyze", methods=["POST"])
def analyze_query():
    """POST /api/understanding/analyze — analyze user query using UnderstandingEngine."""
    data = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()
    if not query:
        return jsonify({"error": "query is required"}), 400

    try:
        user_profile = get_mem().get_user_profile()
        analysis = get_orch().understanding.analyze(query, user_profile)
        
        result = {
            "intent": analysis.intent,
            "emotion": analysis.emotion,
            "emotion_intensity": analysis.emotion_intensity,
            "entities": analysis.entities,
            "is_memory_store": analysis.is_memory_store,
            "is_memory_recall": analysis.is_memory_recall,
            "topic": analysis.topic,
            "expertise_level": analysis.expertise_level,
            "nlp_confidence": analysis.nlp_confidence,
        }
        
        if analysis.nlp_result:
            nlp = analysis.nlp_result
            result["nlp_details"] = {
                "sentiment_score": getattr(nlp, "sentiment_score", 0.0),
                "sentence_complexity": getattr(nlp, "sentence_complexity", 0.0),
                "tokens": getattr(nlp, "tokens", []),
                "lemmas": getattr(nlp, "lemmas", []),
                "pos_tags": getattr(nlp, "pos_tags", []),
                "noun_chunks": getattr(nlp, "noun_chunks", []),
                "root_verbs": getattr(nlp, "root_verbs", []),
                "pipeline_active": getattr(nlp, "pipeline_active", False),
                "word_count": getattr(nlp, "word_count", 0),
            }
            
        return jsonify(result)
    except Exception as e:
        logger.exception("Error in /api/understanding/analyze")
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════
# Goals API
# ═══════════════════════════════════════════════════════════════

@api_bp.route("/goals", methods=["GET"])
def list_goals():
    """GET /api/goals — returns all goals (filter ?status=active)."""
    status = request.args.get("status")
    goals = get_goals().get_active_goals(20) if status == "active" else get_goals().get_all_goals()
    return jsonify({"goals": goals, "count": len(goals)})


@api_bp.route("/goals", methods=["POST"])
def add_goal():
    """POST /api/goals — { title, description?, priority?, deadline? }"""
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400
    result = get_goals().add_goal(
        title=title,
        description=data.get("description", ""),
        priority=data.get("priority", "medium"),
        deadline=data.get("deadline"),
    )
    return jsonify({"status": "created", "goal": result}), 201


@api_bp.route("/goals/<int:goal_id>", methods=["PATCH"])
def update_goal(goal_id):
    """PATCH /api/goals/<id> — { status: 'done'|'active'|'paused' }"""
    data = request.get_json(silent=True) or {}
    status = data.get("status", "").strip()
    if status == "done":
        ok = get_goals().complete_goal(goal_id)
    elif status:
        ok = get_goals().update_goal_status(goal_id, status)
    else:
        return jsonify({"error": "status is required"}), 400
    return jsonify({"status": "updated" if ok else "not_found", "id": goal_id})


@api_bp.route("/goals/<int:goal_id>", methods=["DELETE"])
def delete_goal(goal_id):
    """DELETE /api/goals/<id>"""
    ok = get_goals().delete_goal(goal_id)
    return jsonify({"status": "deleted" if ok else "not_found", "id": goal_id})


# ═══════════════════════════════════════════════════════════════
# Events / Reminders API
# ═══════════════════════════════════════════════════════════════

@api_bp.route("/events", methods=["GET"])
def list_events():
    """GET /api/events — returns upcoming events (?hours=48)."""
    hours = int(request.args.get("hours", 48))
    events = get_events().get_upcoming_events(hours_ahead=hours)
    due    = get_events().get_due_events()
    return jsonify({"events": events, "due": due, "count": len(events)})


@api_bp.route("/events", methods=["POST"])
def add_event():
    """POST /api/events — { title, event_time?, notes?, repeat? }"""
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400
    result = get_events().add_event(
        title=title,
        event_time=data.get("event_time"),
        notes=data.get("notes", ""),
        repeat=data.get("repeat", "none"),
    )
    return jsonify({"status": "created", "event": result}), 201


@api_bp.route("/events/<int:event_id>/done", methods=["PATCH"])
def mark_event_done(event_id):
    """PATCH /api/events/<id>/done — mark reminder as done."""
    ok = get_events().mark_done(event_id)
    return jsonify({"status": "done" if ok else "not_found", "id": event_id})


@api_bp.route("/reminder/alerts", methods=["GET"])
def reminder_alerts():
    """GET /api/reminder/alerts — polled by frontend for in-app reminder notifications.

    Returns reminders that just fired. Each reminder appears in
    exactly one response (claim-based queue).
    """
    from app.reminders.worker import get_alerts
    alerts = get_alerts()
    return jsonify({"alerts": alerts})


# ═══════════════════════════════════════════════════════════════
# Reflection API
# ═══════════════════════════════════════════════════════════════

@api_bp.route("/reflect", methods=["GET"])
def reflect():
    """GET /api/reflect?type=daily|session"""
    from app.core.brain import ask_llm
    reflect_type = request.args.get("type", "daily")
    if reflect_type == "session":
        session_id = get_mem().get_or_create_session()
        summary = get_reflector().reflect_on_session(session_id, ask_llm)
        return jsonify({"type": "session", "session_id": session_id, "summary": summary})
    else:
        review = get_reflector().daily_review(ask_llm)
        return jsonify({"type": "daily", "review": review})


@api_bp.route("/health", methods=["GET"])
def health():
    """GET /api/health — Simple health check endpoint.

    Returns:
        JSON ``{"status": "ok"}`` indicating the service is alive.
    """
    return jsonify({"status": "ok"})


# ═══════════════════════════════════════════════════════════════
# Proactive Intelligence API
# ═══════════════════════════════════════════════════════════════

_proactive = None

def get_proactive():
    """Get or create the singleton ProactiveEngine instance.

    Lazy-initializes the proactive engine backed by the memory subsystem
    and caches it in the module-level ``_proactive`` variable.

    Returns:
        ProactiveEngine: The global proactive engine instance.
    """
    global _proactive
    if _proactive is None:
        _proactive = ProactiveEngine(get_mem())
    return _proactive


@api_bp.route("/proactive/briefing", methods=["GET"])
def proactive_briefing():
    """GET /api/proactive/briefing — Time-aware greeting, suggestions, quick actions.

    Returns everything the Android home screen needs in one call:
    - greeting, time, date, tip
    - proactive suggestion based on time/emotion
    - dynamic quick action chips
    - productivity streak from episodic memory
    """
    try:
        eng = get_proactive()
        mem = get_mem()

        # Get user profile for personalized greeting
        profile = mem.get_user_profile()
        briefing = eng.get_daily_briefing()

        # Suggestion based on time context
        suggestion = eng.get_proactive_suggestion()

        # Streak from recent episodes
        recent = mem.get_recent_episodes(limit=50)
        streak = eng.analyze_productivity_streak(recent)

        # Quick actions
        quick_actions = eng.get_android_quick_actions(profile)

        return jsonify({
            **briefing,
            "suggestion":    suggestion,
            "streak":        streak,
            "quick_actions": quick_actions,
        })
    except Exception:
        logger.exception("Proactive briefing error")
        return jsonify({
            "greeting":  "Hey! JARVIS ready! 🤖",
            "time":      "",
            "date":      "",
            "tip":       "",
            "suggestion": None,
            "streak":     {"streak_days": 0, "message": ""},
            "quick_actions": [],
        })


@api_bp.route("/proactive/suggestion", methods=["GET"])
def proactive_suggestion():
    """GET /api/proactive/suggestion?emotion=neutral&topic=general — Single suggestion."""
    emotion = request.args.get("emotion", "neutral")
    topic   = request.args.get("topic", "general")
    eng     = get_proactive()
    eng._last_suggestion_ts = 0  # force fresh suggestion
    suggestion = eng.get_proactive_suggestion(emotion=emotion, topic=topic)
    return jsonify({"suggestion": suggestion})


# ═══════════════════════════════════════════════════════════════
# TTS — Microsoft Edge TTS (server-side, works on Render.com)
# ═══════════════════════════════════════════════════════════════

# Voice selection:
#   Hinglish / English → en-IN-NeerjaNeural  (Indian English, female, warm)
#   Hindi (Devanagari) → hi-IN-SwaraNeural   (native Hindi, female, clear)
# Both are free neural voices from Microsoft Edge TTS.

_VOICE_EN_IN = "en-IN-NeerjaNeural"
_VOICE_HI_IN = "hi-IN-SwaraNeural"


def _has_devanagari(text: str) -> bool:
    """Check whether the given text contains any Devanagari Unicode characters.

    Uses the Devanagari Unicode block U+0900–U+097F to detect Hindi text.

    Args:
        text: The input string to inspect.

    Returns:
        True if at least one Devanagari character is found, False otherwise.
    """
    return any("\u0900" <= ch <= "\u097F" for ch in text)


def _run_async(coro):
    """Run async coroutine safely in synchronous contexts."""
    try:
        asyncio.get_running_loop()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(asyncio.run, coro).result()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


async def _synthesize(text: str, voice: str, rate: str, pitch: str) -> bytes:
    """Run edge-tts and collect all audio bytes in memory."""
    import edge_tts
    buf = io.BytesIO()
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    return buf.getvalue()


@api_bp.route("/tts", methods=["POST"])
def tts():
    """Convert text to speech using Microsoft Edge TTS.

    Body JSON:
        text   (str)  — required, max 3000 chars
        voice  (str)  — optional, overrides auto-detection
        rate   (str)  — optional, e.g. '+0%' '+10%' '-5%' (default: '+0%')
        pitch  (str)  — optional, e.g. '+0Hz' '-5Hz'      (default: '+0Hz')

    Returns:
        audio/mpeg stream (MP3)
    """
    try:
        import edge_tts  # noqa: F401 — just checking it's available
    except ImportError:
        return jsonify({"error": "edge-tts not installed"}), 503

    data  = request.get_json(silent=True) or {}
    text  = (data.get("text") or "").strip()[:3000]
    if not text:
        return jsonify({"error": "text is required"}), 400

    # Auto-detect voice from script
    if _has_devanagari(text):
        voice = data.get("voice", _VOICE_HI_IN)
    else:
        voice = data.get("voice", _VOICE_EN_IN)

    rate  = data.get("rate",  "+20%")
    pitch = data.get("pitch", "+0Hz")

    try:
        audio_bytes = _run_async(_synthesize(text, voice, rate, pitch))
    except Exception as e:
        logger.exception("TTS synthesis failed")
        return jsonify({"error": f"TTS failed: {e}"}), 500

    if not audio_bytes:
        return jsonify({"error": "TTS produced no audio"}), 500

    return Response(
        audio_bytes,
        mimetype="audio/mpeg",
        headers={
            "Content-Length": str(len(audio_bytes)),
            "Cache-Control":  "no-store",
            "X-TTS-Voice":    voice,
        },
    )


@api_bp.route("/tts/voices", methods=["GET"])
def tts_voices():
    """Return available edge-tts voices filtered for Indian languages."""
    try:
        import edge_tts

        async def _get_voices():
            """Fetch available edge-tts voices filtered for Indian languages.

            Returns:
                list[dict]: Voice info dicts with name, short, gender, and lang keys
                for Indian language locales (en-IN, hi-IN, ta-IN, te-IN, mr-IN).
            """
            voices = await edge_tts.list_voices()
            indian = [
                {"name": v["Name"], "short": v["ShortName"],
                 "gender": v["Gender"], "lang": v["Locale"]}
                for v in voices
                if v["Locale"] in ("en-IN", "hi-IN", "ta-IN", "te-IN", "mr-IN")
            ]
            return indian

        voices = _run_async(_get_voices())
        return jsonify({"voices": voices, "default_hinglish": _VOICE_EN_IN, "default_hindi": _VOICE_HI_IN})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════
# Timer / Countdown API
# ═══════════════════════════════════════════════════════════════

_MAX_TIMER_SECS = 86400  # 24 hours


@api_bp.route("/timer", methods=["POST"])
def create_timer():
    """POST /api/timer — { duration: int (seconds), label?: str }

    Creates a new server-side countdown timer.
    Returns the timer id, remaining, label, and end_time.
    """
    data = request.get_json(silent=True) or {}
    duration = data.get("duration", 0)
    label = (data.get("label") or "Alarm").strip()[:100]
    try:
        duration = int(duration)
    except (TypeError, ValueError):
        return jsonify({"error": "duration must be an integer"}), 400
    if duration <= 0:
        return jsonify({"error": "duration must be positive"}), 400
    if duration > _MAX_TIMER_SECS:
        return jsonify({"error": f"duration cannot exceed {_MAX_TIMER_SECS}s (24h)"}), 400

    from app.core.timer import get_timer_service
    result = get_timer_service().create_timer(duration, label)
    return jsonify(result), 201


@api_bp.route("/timer/alerts", methods=["GET"])
def timer_alerts():
    """GET /api/timer/alerts — polled by frontend every ~1s.

    Returns timers that have just expired. Each timer appears in
    exactly one response and then must be acknowledged.
    """
    from app.core.timer import get_timer_service
    alerts = get_timer_service().get_alerts()
    return jsonify({"alerts": alerts})


@api_bp.route("/timer/<int:timer_id>", methods=["GET"])
def timer_status(timer_id):
    """GET /api/timer/<id> — current status of a timer."""
    from app.core.timer import get_timer_service
    status = get_timer_service().get(timer_id)
    if status is None:
        return jsonify({"error": "timer not found"}), 404
    return jsonify(status)


@api_bp.route("/timer/<int:timer_id>", methods=["DELETE"])
def cancel_timer(timer_id):
    """DELETE /api/timer/<id> — cancel a running timer."""
    from app.core.timer import get_timer_service
    ok = get_timer_service().cancel(timer_id)
    return jsonify({"cancelled": ok})


@api_bp.route("/timer/<int:timer_id>/pause", methods=["POST"])
def pause_timer(timer_id):
    """POST /api/timer/<id>/pause — pause a running timer."""
    from app.core.timer import get_timer_service
    result = get_timer_service().pause(timer_id)
    if result is None:
        return jsonify({"error": "timer not found or not active"}), 404
    return jsonify(result)


@api_bp.route("/timer/<int:timer_id>/resume", methods=["POST"])
def resume_timer(timer_id):
    """POST /api/timer/<id>/resume — resume a paused timer."""
    from app.core.timer import get_timer_service
    result = get_timer_service().resume(timer_id)
    if result is None:
        return jsonify({"error": "timer not found or not paused"}), 404
    return jsonify(result)


@api_bp.route("/timers", methods=["GET"])
def list_timers():
    """GET /api/timers — list all active (non-terminal) timers."""
    from app.core.timer import get_timer_service
    timers = get_timer_service().get_all_active()
    return jsonify({"timers": timers, "count": len(timers)})


# ═══════════════════════════════════════════════════════════════
# AND9 API — Multi-brain AI Operating System
# ═══════════════════════════════════════════════════════════════

_and9_instance = None


def get_and9():
    """Get or create the singleton AND9 multi-brain instance.

    Lazy-initializes the AND9 system wired to the event system and
    caches it in the module-level ``_and9_instance`` variable.

    Returns:
        AND9: The global AND9 multi-brain operating system instance.
    """
    global _and9_instance
    if _and9_instance is None:
        from app.and9 import AND9
        from app.core.events import EventSystem
        _and9_instance = AND9(events_sys=get_events())
    return _and9_instance


@api_bp.route("/and9", methods=["POST"])
def and9_process():
    """POST /api/and9 — Process query through AND9 multi-brain system.

    Body JSON:
        query (str) — User input (Hindi, Hinglish, or English).

    Returns JSON:
        response (str)        — Natural language reply
        action (str|null)     — Action type (e.g., "LAUNCH_APP", "CALL")
        payload (dict|null)   — Action payload/Android intent
        brain (str)           — Which brain handled it ("reflex"/"conscious")
        intent (str|null)     — Detected intent type
        time_ms (float)       — Execution time
        success (bool)        — Whether execution succeeded
    """
    data = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()

    if not query:
        return jsonify({
            "response": "Kya karna hai? Kuch batao na!",
            "action": None,
            "payload": None,
            "brain": "conscious",
            "intent": None,
            "time_ms": 0,
            "success": False,
        }), 400

    try:
        result = get_and9().process(query)
        return jsonify(result)
    except Exception as e:
        logger.exception("AND9 endpoint error")
        return jsonify({
            "response": f"AND9 error: {e}",
            "action": None,
            "payload": None,
            "brain": "conscious",
            "intent": None,
            "time_ms": 0,
            "success": False,
        }), 500


@api_bp.route("/and9/apps", methods=["POST"])
def and9_sync_apps():
    """POST /api/and9/apps — sync installed apps from Android.

    Body JSON:
        Dict of package_name -> label
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Expected JSON dict"}), 400

    from app.and9.apps.package_resolver import get_resolver
    get_resolver().update_dynamic_cache(data)
    return jsonify({"status": "synced", "count": len(data)})

@api_bp.route("/and9/stats", methods=["GET"])
def and9_stats():
    """GET /api/and9/stats — Get AND9 system statistics."""
    try:
        stats = get_and9().get_stats()
        return jsonify(stats)
    except Exception as e:
        logger.exception("AND9 stats error")
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════
# PersonalOS API — Full Cognitive Architecture
# ═══════════════════════════════════════════════════════════════

_personality = None


def get_personality():
    """Get or create the PersonalOS singleton.

    Falls back to getting it from the Flask app if already initialized
    during startup, or creates a new instance on-demand.
    """
    global _personality
    if _personality is not None:
        return _personality

    # Try to get from Flask app (initialized during startup)
    try:
        from app._flask_compat import current_app
        if current_app and hasattr(current_app, "personality_os"):
            _personality = current_app.personality_os
            if _personality is not None:
                return _personality
    except Exception:
        logger.debug("No PersonalityOS found in current_app, creating on-demand")

    # Create on-demand (cold start)
    from app.core.personality_os import PersonalOS
    _personality = PersonalOS()
    _personality.initialize()
    return _personality


@api_bp.route("/personality/process", methods=["POST"])
def personality_process():
    """POST /api/personality/process — Process input through full cognitive architecture.

    Body JSON:
        query  (str)  — User input (Hindi, Hinglish, or English)
        source (str)  — Optional: "user" | "notification" | "screen" | "system"
        **context     — Additional context keys

    Returns JSON:
        response (str)        — Natural language reply
        brain (str)           — Which brain handled it ("reflex"/"conscious")
        time_ms (float)       — Processing time
        success (bool)        — Whether execution succeeded
        learning (dict|null)  — Any learning that occurred
        metadata (dict)       — Full processing metadata
    """
    data = request.get_json(silent=True) or {}
    query = (data.get("query") or data.get("message") or "").strip()

    if not query:
        return jsonify({
            "response": "Kya karna hai? Kuch batao na!",
            "brain": "conscious",
            "time_ms": 0,
            "success": False,
            "learning": None,
            "metadata": {},
        }), 400

    try:
        source = data.get("source", "user")
        context = {k: v for k, v in data.items() if k not in ("query", "message", "source")}

        result = get_personality().process(query, source=source, **context)
        return jsonify(result)
    except Exception as e:
        logger.exception("PersonalityOS process error")
        return jsonify({
            "response": f"Personality OS error: {e}",
            "brain": "conscious",
            "time_ms": 0,
            "success": False,
            "learning": None,
            "metadata": {"error": str(e)},
        }), 500


@api_bp.route("/personality/stats", methods=["GET"])
def personality_stats():
    """GET /api/personality/stats — Full system statistics."""
    try:
        stats = get_personality().get_stats()
        return jsonify(stats)
    except Exception as e:
        logger.exception("Personality stats error")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/personality/reflection", methods=["GET"])
def personality_reflection():
    """GET /api/personality/reflection — Daily reflection summary."""
    try:
        reflection = get_personality().get_daily_reflection()
        return jsonify(reflection)
    except Exception as e:
        logger.exception("Personality reflection error")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/personality/learnings", methods=["GET"])
def personality_learnings():
    """GET /api/personality/learnings — All accumulated learnings.

    Returns patterns, skills, and preferences learned over time.
    """
    try:
        learnings = get_personality().get_all_learnings()
        return jsonify(learnings)
    except Exception as e:
        logger.exception("Personality learnings error")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/personality/goals", methods=["GET"])
def personality_goals():
    """GET /api/personality/goals — List all goals."""
    try:
        summary = get_personality().get_goal_summary()
        return jsonify({"summary": summary})
    except Exception as e:
        logger.exception("Personality goals error")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/personality/health", methods=["GET"])
def personality_health():
    """GET /api/personality/health — Get detailed health status of all cognitive architecture subsystems."""
    try:
        os = get_personality()
        health_status = {
            "status": "healthy" if os._initialized else "uninitialized",
            "initialized": os._initialized,
            "started": os._started,
            "subsystems": {
                "procedural_memory": os.procedural_memory is not None,
                "memory_consolidation": os.memory_consolidation is not None,
                "learning_system": os.learning_system is not None,
                "memory_system": os.memory_system is not None,
                "knowledge_graph": os.knowledge_graph is not None,
                "reflection_engine": os.reflection_engine is not None,
                "automation_system": os.automation_system is not None,
                "cognitive_engine": os.cognitive_engine is not None,
                "agent_loop": os.agent_loop is not None,
            }
        }
        return jsonify(health_status)
    except Exception as e:
        logger.error(f"Error checking personality health: {e}", exc_info=True)
        return jsonify({"status": "error", "error": str(e)}), 500


@api_bp.route("/personality/goals", methods=["POST"])
def personality_add_goal():
    """POST /api/personality/goals — Add a new goal.

    Body JSON:
        title    (str)  — Goal title (required)
        category (str)  — "personal" | "work" | "health" | "learning"
        priority (str)  — "low" | "medium" | "high"
    """
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400

    result = get_personality().add_goal(
        title=title,
        category=data.get("category", "personal"),
        priority=data.get("priority", "medium"),
    )
    if result.get("success"):
        return jsonify(result), 201
    return jsonify(result), 500


@api_bp.route("/personality/habits", methods=["POST"])
def personality_add_habit():
    """POST /api/personality/habits — Add a new habit to track.

    Body JSON:
        name      (str)  — Habit name (required)
        frequency (str)  — "daily" | "weekly" | "weekday"
    """
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400

    result = get_personality().add_habit(
        name=name,
        frequency=data.get("frequency", "daily"),
    )
    if result.get("success"):
        return jsonify(result), 201
    return jsonify(result), 500


@api_bp.route("/and9/pipeline-status", methods=["GET"])
def pipeline_status():
    """Server-Sent Events endpoint to stream real-time pipeline status updates."""
    from app.and9.core.pipeline_status import status_manager
    import json
    import queue

    def event_stream():
        """Generator yielding SSE events for real-time pipeline status updates.

        Registers a callback on the status manager, yields the current
        pipeline status immediately, then streams subsequent updates as
        they arrive. Sends heartbeat pings every 10 seconds to prevent
        client-side timeout.

        Yields:
            str: Server-Sent Event formatted data lines (status or ping).
        """
        q = queue.Queue()
        
        def listener(status):
            """Callback that enqueues a status update into the SSE event queue.

            Args:
                status: Status dict received from the pipeline status manager.
            """
            q.put(status)
            
        status_manager.register_listener(listener)
        
        try:
            # Yield initial status
            yield f"data: {json.dumps(status_manager.get_status())}\n\n"
            
            while True:
                try:
                    status = q.get(timeout=10.0)
                    yield f"data: {json.dumps(status)}\n\n"
                except queue.Empty:
                    # Heartbeat ping to prevent client timeout
                    yield ": ping\n\n"
        except GeneratorExit:
            pass
        finally:
            status_manager.unregister_listener(listener)

    return Response(event_stream(), mimetype="text/event-stream")
