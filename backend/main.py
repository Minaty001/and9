"""
app/main.py — Flask Application Factory

Creates and configures the Flask app with:
- Rate limiting (in-memory, no external deps)
- Request ID tracking
- Graceful error handlers (404, 405, 429, 500)
- Structured logging

Entry point for both development and production (gunicorn).
"""
import os
import time
import uuid
import logging
from functools import wraps
from backend.utils._flask_compat import Flask, g, request, jsonify, render_template

from backend.api.routes.routes import api_bp
from backend.api.routes.web_routes import web_bp
from backend.api.admin.admin_routes import admin_bp
from backend.api.routes.memory_api import memory_bp


# ── Rate Limiter (in-memory, per-IP sliding window) ───────────

class RateLimiter:
    """Simple sliding-window rate limiter per IP."""

    def __init__(self, limit: int = 30, window_sec: int = 60):
        self.limit = limit
        self.window_sec = window_sec
        self._buckets: dict[str, list[float]] = {}

    def check(self, key: str) -> tuple[bool, int]:
        """Returns (allowed, retry_after_seconds)."""
        now = time.time()
        window_start = now - self.window_sec
        bucket = self._buckets.get(key, [])

        # Prune old entries
        bucket = [t for t in bucket if t > window_start]

        if len(bucket) >= self.limit:
            retry_after = int(bucket[0] + self.window_sec - now) if bucket else self.window_sec
            return False, max(1, retry_after)

        bucket.append(now)
        self._buckets[key] = bucket
        return True, 0


_limiter = RateLimiter(limit=30, window_sec=60)


# ── Flask Factory ─────────────────────────────────────────────

_startup_logger = logging.getLogger("and9.startup")


def _init_and9(app: Flask) -> None:
    """Run AND9 startup initialization sequence.

    Called once when the Flask app is created.
    Phases executed:
        Phase 12 — Validate action registry (assert all actions registered)
        Phase 8  — Start reminder scheduler background thread
        Phase 4  — Load installed_apps.json dynamic cache
        Phase 15 — Intent trace DB auto-initialized on import
    """
    # Phase 12: validate action registry
    try:
        from backend.skills.android.action_registry import validate_registry
        validate_registry()
        _startup_logger.info("AND9 Action Registry validated.")
    except AssertionError as e:
        _startup_logger.critical("AND9 Action Registry FAILED: %s", e)
        raise  # Fatal
    except Exception as e:
        _startup_logger.error("AND9 registry check error: %s", e)

    # Priority 1: validate Android handler coverage
    try:
        from backend.skills.android.validate_handlers import validate_android_handlers
        validate_android_handlers()
        _startup_logger.info("AND9 Android Handler Coverage validated.")
    except RuntimeError as e:
        _startup_logger.critical("AND9 Handler Coverage FAILED: %s", e)
        # Non-fatal in dev — fatal in production
        import os
        if os.environ.get("AND9_STRICT_VALIDATION", "0") == "1":
            raise
    except Exception as e:
        _startup_logger.warning("AND9 handler coverage check error: %s", e)

    # Priority 3: start standalone reminder worker
    try:
        from backend.services.reminder.worker import start_worker
        start_worker()
        _startup_logger.info("AND9 Reminder Worker started.")
    except Exception as e:
        _startup_logger.error("Failed to start AND9 reminder worker: %s", e)

    # Phase 4: preload dynamic package cache
    try:
        from backend.services.automation.package_resolver import PackageResolver
        PackageResolver()
        _startup_logger.info("AND9 PackageResolver initialized.")
    except Exception as e:
        _startup_logger.warning("AND9 PackageResolver error: %s", e)

    # Validate database (Priority: self diagnostics)
    try:
        from backend.core.activity_db import validate_database
        validate_database()
        _startup_logger.info("AND9 Activity Database validated.")
    except Exception as e:
        _startup_logger.critical("AND9 Activity Database validation FAILED: %s", e)
        raise

    # Phase 0: ensure legacy data directory
    try:
        from backend.core.config import _ensure_notes_dir
        _ensure_notes_dir()
        _startup_logger.info("AND9 data directory ready.")
    except Exception as e:
        _startup_logger.warning("AND9 data directory setup: %s", e)

    _startup_logger.info("AND9 initialized. Three-Brain Architecture ACTIVE.")


def _init_personality(app: Flask) -> None:
    """Initialize the PersonalOS cognitive architecture.

    This is the NEW unified cognitive layer that wraps the existing
    AND9 three-brain system with:
    - Agent Loop (continuous Observe→Think→Act→Reflect→Learn)
    - Cognitive Engine (Reflex + Habit + Reasoning)
    - Learning System (Pattern, Skill, Preference)
    - Procedural Memory
    - Memory Consolidation (Working→Episodic→Semantic)
    - Automation System (Goals, Habits, Scheduled Actions)
    - Self-Reflection

    The PersonalOS instance is stored on app.personality_os for
    access from API routes.
    """
    try:
        from backend.core.personality_os import PersonalOS

        personality_os = PersonalOS()
        personality_os.initialize()
        app.personality_os = personality_os

        _startup_logger.info("PersonalOS initialized — Full cognitive architecture ACTIVE.")
        _startup_logger.info(
            "Systems: Reflex | Habit | Reasoning | Memory | Learning | Automation | Reflection"
        )
    except Exception as e:
        _startup_logger.warning("PersonalOS initialization deferred: %s", e)
        app.personality_os = None


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__, template_folder="templates", static_folder="static", static_url_path="")

    # ── Configuration ───────────────────────────────────────────
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", uuid.uuid4().hex)
    app.config["JSONIFY_PRETTYPRINT_REGULAR"] = False
    app.config["JSON_SORT_KEYS"] = False

    # ── Logging ─────────────────────────────────────────────────
    log_level = logging.DEBUG if os.environ.get("FLASK_DEBUG") == "1" else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    # ── AND9 Startup Initialization (Phase 12, 15) ───────────────
    _init_and9(app)

    # ── PersonalOS Cognitive Architecture (Phase 16) ────────────
    _init_personality(app)

    # ── Request ID ──────────────────────────────────────────────
    @app.before_request
    def set_request_id():
        g.request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex[:12])
        g.start_time = time.time()

    @app.after_request
    def add_headers(response):
        response.headers["X-Request-ID"] = getattr(g, "request_id", "unknown")
        response.headers["X-Runtime-Ms"] = str(int((time.time() - getattr(g, "start_time", time.time())) * 1000))
        return response

    # ── Rate limiting ───────────────────────────────────────────
    @app.before_request
    def rate_limit():
        # Skip rate limiting for static files and health checks
        if request.path in ("/health", "/api/health") or request.path.startswith("/static/"):
            return None

        client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown")
        allowed, retry_after = _limiter.check(client_ip)
        if not allowed:
            return jsonify({
                "error": "rate_limit_exceeded",
                "message": f"Too many requests. Try again in {retry_after} seconds.",
                "retry_after": retry_after,
            }), 429, {"Retry-After": str(retry_after)}

    # ── Register blueprints ─────────────────────────────────────
    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(memory_bp, url_prefix="/api/memory")

    # ── Health check ────────────────────────────────────────────
    @app.route("/health")
    def health():
        return {"status": "ok", "request_id": getattr(g, "request_id", "none")}

    # ── Error handlers ──────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "not_found", "message": "The requested resource was not found."}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "method_not_allowed", "message": "Method not allowed for this endpoint."}), 405

    @app.errorhandler(429)
    def too_many_requests(e):
        return jsonify({"error": "rate_limit_exceeded", "message": "Too many requests. Slow down."}), 429

    @app.errorhandler(500)
    def server_error(e):
        app.logger.exception("Internal server error")
        return jsonify({"error": "internal_error", "message": "An unexpected error occurred."}), 500

    app.logger.info("JARVIS v4 app created")
    return app


# Expose module-level app for gunicorn
app = create_app()


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8000))
    debug = os.environ.get("FLASK_DEBUG") == "1"
    app.run(host=host, port=port, debug=debug)
