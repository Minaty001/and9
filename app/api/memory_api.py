"""
AND9 — Memory API.
REST endpoints for the 4-layer memory system (Working, Episodic, Semantic, Procedural).
"""
import logging
from flask import Blueprint, jsonify, request
from app.api.routes import get_personality

logger = logging.getLogger(__name__)
memory_bp = Blueprint("memory", __name__)

@memory_bp.route("/working", methods=["GET"])
def get_working_memory():
    """GET /api/memory/working — Get current session working memory state."""
    try:
        os = get_personality()
        mem = os.memory_system
        if not mem:
            return jsonify({"error": "Memory system not initialized"}), 500
            
        session_id = mem.get_or_create_session()
        
        # Access working memory
        from app.core.working_memory import WorkingMemory
        wm = WorkingMemory(mem)
        state = wm._get_state(session_id)
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "working_memory": state
        })
    except Exception as e:
        logger.error(f"Error fetching working memory: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@memory_bp.route("/episodic", methods=["GET"])
def get_episodic_memory():
    """GET /api/memory/episodic — Get recent episodic memories."""
    try:
        limit = request.args.get("limit", default=10, type=int)
        os = get_personality()
        mem = os.memory_system
        if not mem:
            return jsonify({"error": "Memory system not initialized"}), 500
            
        episodes = mem.get_recent_episodes(limit=limit)
        return jsonify({
            "success": True,
            "episodes": episodes
        })
    except Exception as e:
        logger.error(f"Error fetching episodic memory: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@memory_bp.route("/semantic", methods=["GET"])
def get_semantic_memory():
    """GET /api/memory/semantic — Get user profile facts and verified semantic data."""
    try:
        os = get_personality()
        mem = os.memory_system
        if not mem:
            return jsonify({"error": "Memory system not initialized"}), 500
            
        profile = mem.get_user_profile()
        facts = mem.get_verified_facts()
        return jsonify({
            "success": True,
            "profile": profile,
            "verified_facts": facts
        })
    except Exception as e:
        logger.error(f"Error fetching semantic memory: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@memory_bp.route("/procedural", methods=["GET"])
def get_procedural_memory():
    """GET /api/memory/procedural — Get learned skills from procedural memory."""
    try:
        os = get_personality()
        pm = os.procedural_memory
        if not pm:
            return jsonify({"error": "Procedural memory not initialized"}), 500
            
        skills = pm.get_all_skills()
        stats = pm.get_stats()
        return jsonify({
            "success": True,
            "skills": skills,
            "stats": stats
        })
    except Exception as e:
        logger.error(f"Error fetching procedural memory: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@memory_bp.route("/consolidate", methods=["POST"])
def consolidate_memory():
    """POST /api/memory/consolidate — Manually trigger working -> episodic -> semantic consolidation."""
    try:
        os = get_personality()
        mc = os.memory_consolidation
        if not mc:
            return jsonify({"error": "Memory consolidation system not initialized"}), 500
            
        stats = mc.consolidate_now()
        return jsonify({
            "success": True,
            "consolidation_stats": stats
        })
    except Exception as e:
        logger.error(f"Error consolidating memory: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500
