"""
app/api — Flask API blueprints.

Chat, memory, goals, events, TTS, AND9 multi-brain, dialogue manager,
proactive intelligence, admin panel, and dependency graph endpoints.
"""

# Flask blueprints — lazy-loaded via getter functions so the package
# can be imported even when Flask is not installed.
_api_bp = None
_web_bp = None
_admin_bp = None


def get_api_bp():
    """Lazy-load and return the main API blueprint."""
    global _api_bp
    if _api_bp is None:
        from app.api.routes import api_bp as _api_bp
    return _api_bp


def get_web_bp():
    """Lazy-load and return the web blueprint."""
    global _web_bp
    if _web_bp is None:
        from app.api.web_routes import web_bp as _web_bp
    return _web_bp


def get_admin_bp():
    """Lazy-load and return the admin blueprint."""
    global _admin_bp
    if _admin_bp is None:
        from app.api.admin_routes import admin_bp as _admin_bp
    return _admin_bp


__all__ = [
    "get_api_bp",
    "get_web_bp",
    "get_admin_bp",
]
