"""
app/api/routes.py — JSON API endpoints for the chat interface.
"""
import io
import asyncio
import logging
import os
import threading
import time
from flask import Blueprint, request, jsonify, Response

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
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator


def get_mem():
    global _memory
    if _memory is None:
        _memory = Memory()
    return _memory


def get_goals():
    global _goals
    if _goals is None:
        _goals = GoalTracker(get_mem())
    return _goals


def get_events():
    global _events
    if _events is None:
        _events = EventSystem(get_mem())
    return _events


def get_reflector():
    global _reflector
    if _reflector is None:
        _reflector = ReflectionEngine(get_mem())
    return _reflector



@api_bp.route("/chat", methods=["POST"])
def chat():
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
    return jsonify(get_orch().list_agents())


@api_bp.route("/history", methods=["GET"])
def get_history():
    return jsonify(get_mem().get_recent_chat(20))


@api_bp.route("/memory/facts", methods=["GET"])
def get_facts():
    return jsonify(get_mem().get_facts())


@api_bp.route("/memory/learn", methods=["POST"])
def learn_fact():
    data = request.get_json(silent=True) or {}
    key = data.get("key", "").strip()
    value = data.get("value", "").strip()
    if key and value:
        get_mem().learn_fact(key, value, data.get("fact_type", "personal"))
        return jsonify({"status": "learned", "key": key})
    return jsonify({"error": "key and value required"}), 400


@api_bp.route("/memory/fact", methods=["DELETE"])
def delete_fact():
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


@api_bp.route("/v5/chat", methods=["POST"])
def v5_chat():
    """POST /api/v5/chat — Route through the AND9 Kernel (v5.0).

    Body JSON:
        message (str) — User input.

    Returns JSON with Kernel-processed response.
    """
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"reply": "Please provide a message.", "status": "error"})

    try:
        from app.core.kernel import get_kernel
        kernel = get_kernel()
        if not hasattr(kernel, '_initialized') or not kernel._initialized:
            kernel.boot()
        result = kernel.handle_request(message)
        return jsonify({
            "reply":   result.get("response", ""),
            "brain":   result.get("brain", "unknown"),
            "success": result.get("success", True),
            "status":  "ok",
        })
    except Exception as e:
        logger.exception("v5 chat error")
        return jsonify({"reply": f"Kernel error: {e}", "status": "error"}), 500


@api_bp.route("/v5/health", methods=["GET"])
def v5_health():
    """GET /api/v5/health — Kernel health endpoint."""
    try:
        from app.core.kernel import _kernel as _global_kernel
        kernel = _global_kernel
        if kernel is None or not kernel._initialized:
            return jsonify({"status": "not booted"})
        health_data = kernel.health()
        return jsonify(health_data)
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})


@api_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


# ═══════════════════════════════════════════════════════════════
# Proactive Intelligence API
# ═══════════════════════════════════════════════════════════════

_proactive = None

def get_proactive():
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
    except Exception as e:
        logger.exception("Proactive briefing error: %s", e)
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
            voices = await edge_tts.list_voices()
            indian = [
                {"name": v["Name"], "short": v["ShortName"],
                 "gender": v["Gender"], "lang": v["Locale"]}
                for v in voices
                if v["Locale"] in ("en-IN", "hi-IN", "ta-IN", "te-IN", "mr-IN")
            ]
            return indian

        voices = asyncio.run(_get_voices())
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


# ═══════════════════════════════════════════════════════════════
# AND9 API — Multi-brain AI Operating System
# ═══════════════════════════════════════════════════════════════

_and9_instance = None


def get_and9():
    global _and9_instance
    if _and9_instance is None:
        from app.brain import AND9
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

    from app.android.apps.package_resolver import get_resolver
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
# Dialogue Manager API — Multi-Turn Conversation
# ═══════════════════════════════════════════════════════════════

_dialogue_manager = None
_dialogue_lock = threading.Lock()


def get_dialogue_manager():
    """Lazy-init singleton DialogueManager instance."""
    global _dialogue_manager
    if _dialogue_manager is None:
        with _dialogue_lock:
            if _dialogue_manager is None:
                from app.dialogue_manager import DialogueManager, DialogueConfig
                import os
                config = DialogueConfig(
                    persist_path=os.path.join(
                        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        "data", "dialogue_state.json",
                    ),
                )
                # Wrap AND9's process for action execution
                and9 = get_and9()
                _dialogue_manager = DialogueManager(
                    config=config,
                    and9_orchestrator=and9.orchestrator._execute,
                )
    return _dialogue_manager


@api_bp.route("/dialogue", methods=["POST"])
def dialogue_process():
    """POST /api/dialogue — Process a message through the Dialogue Manager.

    Body JSON:
        message (str) — User input (required).

    Returns JSON with dialogue state and response.
    """
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()

    if not message:
        return jsonify({
            "response": "Kya karna hai? Kuch batao na!",
            "intent": None,
            "status": "error",
            "error": "empty_message",
        }), 400

    try:
        dm = get_dialogue_manager()
        result = dm.process(message)
        return jsonify(result)
    except Exception as e:
        logger.exception("Dialogue endpoint error")
        return jsonify({
            "response": f"Dialogue error: {e}",
            "intent": None,
            "status": "error",
            "error": str(e),
        }), 500


@api_bp.route("/dialogue/state", methods=["GET"])
def dialogue_state():
    """GET /api/dialogue/state — Get full dialogue manager state.

    Returns active tasks, paused tasks, stats, and memory info.
    """
    try:
        dm = get_dialogue_manager()
        state = dm.get_state()
        return jsonify(state)
    except Exception as e:
        logger.exception("Dialogue state error")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/dialogue/tasks", methods=["GET"])
def dialogue_tasks():
    """GET /api/dialogue/tasks — List all active dialogue tasks.

    Query params:
        all (bool) — If true, also show completed/cancelled tasks.
    """
    try:
        dm = get_dialogue_manager()
        all_tasks = request.args.get("all", "").lower() in ("true", "1", "yes")
        tasks = dm.get_tasks(active_only=not all_tasks)
        return jsonify({
            "tasks": tasks,
            "count": len(tasks),
        })
    except Exception as e:
        logger.exception("Dialogue tasks error")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/dialogue/tasks/<task_id>", methods=["GET"])
def dialogue_task_detail(task_id):
    """GET /api/dialogue/tasks/<id> — Get a specific task's state."""
    try:
        dm = get_dialogue_manager()
        task = dm.get_task(task_id)
        if task:
            return jsonify(task)
        return jsonify({"error": "task_not_found", "task_id": task_id}), 404
    except Exception as e:
        logger.exception("Dialogue task detail error")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/dialogue/tasks/<task_id>", methods=["DELETE"])
def dialogue_task_cancel(task_id):
    """DELETE /api/dialogue/tasks/<id> — Cancel a specific task."""
    try:
        dm = get_dialogue_manager()
        ok = dm.cancel_task(task_id)
        if ok:
            return jsonify({"status": "cancelled", "task_id": task_id})
        return jsonify({"error": "task_not_found", "task_id": task_id}), 404
    except Exception as e:
        logger.exception("Dialogue task cancel error")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/dialogue/history", methods=["GET"])
def dialogue_history():
    """GET /api/dialogue/history[?n=20] — Recent conversation history.

    Query params:
        n (int) — Number of recent turns to return (max 100).
    """
    try:
        dm = get_dialogue_manager()
        n = min(int(request.args.get("n", 20)), 100)
        history = dm.get_conversation_history(n)
        return jsonify({
            "history": history,
            "count": len(history),
        })
    except Exception as e:
        logger.exception("Dialogue history error")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/dialogue/reset", methods=["POST"])
def dialogue_reset():
    """POST /api/dialogue/reset — Reset all dialogue state."""
    try:
        dm = get_dialogue_manager()
        dm.reset()
        return jsonify({"status": "reset"})
    except Exception as e:
        logger.exception("Dialogue reset error")
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════
# Dependency Graph API — Code Analysis & MCP Tools
# ═══════════════════════════════════════════════════════════════

_depgraph_server = None
_depgraph_lock = threading.Lock()


def get_depgraph_server():
    """Lazy-init singleton DependencyGraphMCPServer instance."""
    global _depgraph_server
    if _depgraph_server is None:
        with _depgraph_lock:
            if _depgraph_server is None:
                from app.dependency_graph.mcp_server import DependencyGraphMCPServer
                _depgraph_server = DependencyGraphMCPServer(
                    root_path=os.path.abspath(
                        os.path.join(os.path.dirname(__file__), "..", "..")
                    ),
                )
    return _depgraph_server


@api_bp.route("/depgraph/analyze", methods=["GET"])
def depgraph_analyze():
    """GET /api/depgraph/analyze?reanalyze=true — Build/rebuild dependency graph."""
    try:
        server = get_depgraph_server()
        reanalyze = request.args.get("reanalyze", "").lower() in ("true", "1", "yes")
        graph = server.ensure_graph(reanalyze=reanalyze)
        return jsonify({
            "node_count": graph.node_count,
            "edge_count": graph.edge_count,
            "status": "ok",
        })
    except Exception as e:
        logger.exception("Depgraph analyze error")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/depgraph/graph", methods=["GET"])
def depgraph_graph():
    """GET /api/depgraph/graph — Get the full dependency graph."""
    try:
        server = get_depgraph_server()
        result = server.handle_tool_call("get_dependency_graph", {})
        return jsonify(result)
    except Exception as e:
        logger.exception("Depgraph graph error")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/depgraph/callers", methods=["POST"])
def depgraph_callers():
    """POST /api/depgraph/callers — {"filepath": "..."} — Get callers."""
    try:
        data = request.get_json(silent=True) or {}
        filepath = data.get("filepath", "").strip()
        if not filepath:
            return jsonify({"error": "filepath is required"}), 400
        server = get_depgraph_server()
        result = server.handle_tool_call("get_callers", {"filepath": filepath})
        return jsonify(result)
    except Exception as e:
        logger.exception("Depgraph callers error")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/depgraph/callees", methods=["POST"])
def depgraph_callees():
    """POST /api/depgraph/callees — {"filepath": "..."} — Get callees."""
    try:
        data = request.get_json(silent=True) or {}
        filepath = data.get("filepath", "").strip()
        if not filepath:
            return jsonify({"error": "filepath is required"}), 400
        server = get_depgraph_server()
        result = server.handle_tool_call("get_callees", {"filepath": filepath})
        return jsonify(result)
    except Exception as e:
        logger.exception("Depgraph callees error")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/depgraph/impact", methods=["POST"])
def depgraph_impact():
    """POST /api/depgraph/impact — {"filepath": "...", "max_depth": 10} — Impact analysis."""
    try:
        data = request.get_json(silent=True) or {}
        filepath = data.get("filepath", "").strip()
        if not filepath:
            return jsonify({"error": "filepath is required"}), 400
        max_depth = int(data.get("max_depth", 10))
        server = get_depgraph_server()
        result = server.handle_tool_call("impact_analysis", {
            "filepath": filepath, "max_depth": max_depth,
        })
        return jsonify(result)
    except Exception as e:
        logger.exception("Depgraph impact error")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/depgraph/orphans", methods=["GET"])
def depgraph_orphans():
    """GET /api/depgraph/orphans — Find files with no dependents."""
    try:
        server = get_depgraph_server()
        result = server.handle_tool_call("find_orphans", {})
        return jsonify(result)
    except Exception as e:
        logger.exception("Depgraph orphans error")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/depgraph/leaves", methods=["GET"])
def depgraph_leaves():
    """GET /api/depgraph/leaves — Find files with no dependencies."""
    try:
        server = get_depgraph_server()
        result = server.handle_tool_call("find_leaves", {})
        return jsonify(result)
    except Exception as e:
        logger.exception("Depgraph leaves error")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/depgraph/pagerank", methods=["GET"])
def depgraph_pagerank():
    """GET /api/depgraph/pagerank?top_n=20 — PageRank scores."""
    try:
        top_n = int(request.args.get("top_n", 20))
        server = get_depgraph_server()
        result = server.handle_tool_call("pagerank", {"top_n": top_n})
        return jsonify(result)
    except Exception as e:
        logger.exception("Depgraph pagerank error")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/depgraph/mermaid", methods=["GET"])
def depgraph_mermaid():
    """GET /api/depgraph/mermaid — Export as Mermaid.js flowchart."""
    try:
        server = get_depgraph_server()
        mermaid = server.handle_tool_call("export_mermaid", {})
        return mermaid, 200, {"Content-Type": "text/plain; charset=utf-8"}
    except Exception as e:
        logger.exception("Depgraph mermaid error")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/depgraph/d3", methods=["GET"])
def depgraph_d3():
    """GET /api/depgraph/d3 — Export as D3.js force-directed graph JSON."""
    try:
        server = get_depgraph_server()
        result = server.handle_tool_call("export_d3", {})
        return jsonify(result)
    except Exception as e:
        logger.exception("Depgraph d3 error")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/depgraph/module", methods=["POST"])
def depgraph_module():
    """POST /api/depgraph/module — {"filepath": "..."} — Module info."""
    try:
        data = request.get_json(silent=True) or {}
        filepath = data.get("filepath", "").strip()
        if not filepath:
            return jsonify({"error": "filepath is required"}), 400
        server = get_depgraph_server()
        result = server.handle_tool_call("module_info", {"filepath": filepath})
        return jsonify(result)
    except Exception as e:
        logger.exception("Depgraph module error")
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════
# Multi-Agent System API (AND9 Phase 3 — Agent Swarm)
# ═══════════════════════════════════════════════════════════════

_multi_agent_system = None
_multi_agent_lock = threading.Lock()


def get_multi_agent_system():
    """Lazy-init singleton for the AND9 multi-agent system.

    Creates all 20 agents, links the AgentOrchestrator to the
    ExecutiveAgent, and initializes them for use.
    """
    global _multi_agent_system
    if _multi_agent_system is None:
        with _multi_agent_lock:
            if _multi_agent_system is None:
                from app.agents import create_agent_system
                _multi_agent_system = create_agent_system(
                    auto_init=True,
                    create_orchestrator=True,
                )
                logger.info(
                    "Multi-agent system initialised with %d agents",
                    len(_multi_agent_system.list_agents()),
                )
    return _multi_agent_system


@api_bp.route("/multi-agent", methods=["POST"])
def multi_agent_process():
    """POST /api/multi-agent — Process a message through the multi-agent swarm.

    Body JSON:
        message (str)  — User input (required).
        agent   (str)  — Optional: target a specific agent by name.
        mode    (str)  — "auto" (default) = orchestrator routes it,
                         "direct" = send directly to specified agent.

    Returns JSON with the response and full agent execution breakdown.
    """
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    agent_name = (data.get("agent") or "").strip() or None
    mode = (data.get("mode") or "auto").strip()

    if not message:
        return jsonify({
            "response": "Please provide a message.",
            "agent": None,
            "sub_agents": [],
            "agent_results": [],
            "total_time_ms": 0,
            "status": "error",
        }), 400

    start_time = time.perf_counter()

    try:
        registry = get_multi_agent_system()

        # Direct mode: send to a specific agent
        if mode == "direct" and agent_name:
            agent = registry.get(agent_name)
            if not agent:
                return jsonify({
                    "response": f"Agent '{agent_name}' not found. Use GET /api/multi-agent/agents to see available agents.",
                    "agent": agent_name,
                    "sub_agents": [],
                    "agent_results": [],
                    "total_time_ms": 0,
                    "status": "error",
                }), 404

            agent_result = agent(message)
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            return jsonify({
                "response": agent_result.response,
                "agent": agent_name,
                "sub_agents": [agent_name],
                "agent_results": [{
                    "agent": agent_name,
                    "success": agent_result.success,
                    "response": agent_result.response,
                    "confidence": agent_result.confidence,
                    "latency_ms": agent_result.latency_ms,
                    "error": agent_result.error,
                }],
                "total_time_ms": elapsed_ms,
                "status": "success" if agent_result.success else "error",
            })

        # Auto mode: use the orchestrator / executive agent
        executive = registry.get("executive")
        if not executive:
            return jsonify({
                "response": "Executive agent not available.",
                "agent": None,
                "sub_agents": [],
                "agent_results": [],
                "total_time_ms": 0,
                "status": "error",
            }), 500

        # If the executive has an orchestrator, use it
        orch = getattr(executive, "_orchestrator", None)
        if orch is not None:
            result = orch.run(message)
        else:
            result = executive(message)

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        # Build sub_agent breakdown
        sub_agents = []
        agent_results = []

        if result.data and isinstance(result.data, dict):
            meta = result.data
            sub_agent_data = meta.get("sub_agents") or meta.get("agent_results") or []
            if isinstance(sub_agent_data, list):
                for sr in sub_agent_data:
                    if isinstance(sr, dict):
                        agent_results.append({
                            "agent": sr.get("agent_name") or sr.get("agent", "unknown"),
                            "success": sr.get("success", True),
                            "response": (sr.get("response") or "")[:200],
                            "confidence": sr.get("confidence", 0.0),
                            "latency_ms": sr.get("latency_ms", 0),
                            "error": sr.get("error"),
                        })
                        sub_agents.append(agent_results[-1]["agent"])

        if not sub_agents:
            sub_agents = [result.agent_name or "executive"]
            agent_results = [{
                "agent": result.agent_name or "executive",
                "success": result.success,
                "response": (result.response or "")[:500],
                "confidence": result.confidence,
                "latency_ms": result.latency_ms,
                "error": result.error,
            }]

        return jsonify({
            "response": result.response,
            "agent": result.agent_name or "executive",
            "sub_agents": sub_agents,
            "agent_results": agent_results,
            "total_time_ms": elapsed_ms,
            "status": "success" if result.success else "error",
        })

    except Exception as e:
        logger.exception("Multi-agent endpoint error")
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        return jsonify({
            "response": f"Multi-agent system error: {e}",
            "agent": None,
            "sub_agents": [],
            "agent_results": [],
            "total_time_ms": elapsed_ms,
            "status": "error",
        }), 500


@api_bp.route("/multi-agent/agents", methods=["GET"])
def multi_agent_list():
    """GET /api/multi-agent/agents — List all registered agents.

    Returns each agent's name, role, status, and basic metrics
    (invocations, success rate, average latency).
    """
    try:
        registry = get_multi_agent_system()
        agents = registry.list_agents()
        return jsonify({
            "agents": agents,
            "count": len(agents),
        })
    except Exception as e:
        logger.exception("Multi-agent list error")
        return jsonify({"error": str(e)}), 500

