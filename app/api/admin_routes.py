"""
app/api/admin_routes.py — Admin panel API endpoints.

Password-protected admin access for file browsing, editing, and data viewing.
Accepts passwords: "code10" or "codeten"
"""
import os
import hashlib
import logging
import sqlite3
from functools import wraps
from flask import Blueprint, request, jsonify, session, render_template

from app.core.config import NOTES_DIR, MEMORY_DB

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__)

# ── Password hashes (code10 and codeten) ──────────────────────
VALID_HASHES = {
    hashlib.sha256("code10".encode()).hexdigest(),
    hashlib.sha256("codeten".encode()).hexdigest(),
}

# ── Project root (where app code lives) ───────────────────────
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


# ── Auth decorator ────────────────────────────────────────────

def admin_required(f):
    """Require admin session for a route."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_authenticated"):
            return jsonify({"error": "unauthorized", "message": "Admin access required."}), 401
        return f(*args, **kwargs)
    return decorated


# ── Auth endpoints ────────────────────────────────────────────

@admin_bp.route("/auth", methods=["POST"])
def admin_auth():
    """Authenticate with admin password."""
    data = request.get_json(silent=True) or {}
    password = (data.get("password") or "").strip().lower()

    if not password:
        return jsonify({"error": "Password required."}), 400

    pw_hash = hashlib.sha256(password.encode()).hexdigest()

    if pw_hash in VALID_HASHES:
        session["admin_authenticated"] = True
        session.permanent = True
        logger.info("Admin access granted")
        return jsonify({"status": "authenticated", "message": "Welcome, Admin."})
    else:
        logger.warning("Failed admin login attempt")
        return jsonify({"error": "Invalid password."}), 403


@admin_bp.route("/logout", methods=["POST"])
def admin_logout():
    """Revoke admin session."""
    session.pop("admin_authenticated", None)
    return jsonify({"status": "logged_out"})


@admin_bp.route("/check", methods=["GET"])
def admin_check():
    """Check if currently authenticated."""
    return jsonify({"authenticated": bool(session.get("admin_authenticated"))})


# ── Admin panel page ──────────────────────────────────────────

@admin_bp.route("/panel", methods=["GET"])
def admin_panel():
    """Serve the admin panel HTML."""
    return render_template("admin.html")


# ── File system endpoints ─────────────────────────────────────

def _safe_path(rel_path):
    """Resolve a relative path within PROJECT_ROOT. Prevent directory traversal."""
    if not rel_path:
        rel_path = "."
    # Remove leading slashes
    rel_path = rel_path.lstrip("/")
    full = os.path.normpath(os.path.join(PROJECT_ROOT, rel_path))
    # Security: must stay within project root
    if not full.startswith(PROJECT_ROOT):
        return None
    return full


@admin_bp.route("/files", methods=["GET"])
@admin_required
def list_files():
    """List files and folders at a given path."""
    rel_path = request.args.get("path", ".")
    full_path = _safe_path(rel_path)

    if not full_path or not os.path.exists(full_path):
        return jsonify({"error": "Path not found."}), 404

    if not os.path.isdir(full_path):
        return jsonify({"error": "Not a directory."}), 400

    items = []
    try:
        for name in sorted(os.listdir(full_path)):
            # Skip hidden/cache dirs
            if name in ("__pycache__", ".git", ".pytest_cache", "node_modules"):
                continue
            item_path = os.path.join(full_path, name)
            rel = os.path.relpath(item_path, PROJECT_ROOT)
            is_dir = os.path.isdir(item_path)
            size = 0 if is_dir else os.path.getsize(item_path)
            items.append({
                "name": name,
                "path": rel,
                "is_dir": is_dir,
                "size": size,
            })
    except PermissionError:
        return jsonify({"error": "Permission denied."}), 403

    return jsonify({
        "path": os.path.relpath(full_path, PROJECT_ROOT),
        "items": items,
    })


@admin_bp.route("/file", methods=["GET"])
@admin_required
def read_file():
    """Read the content of a file."""
    rel_path = request.args.get("path", "")
    full_path = _safe_path(rel_path)

    if not full_path or not os.path.exists(full_path):
        return jsonify({"error": "File not found."}), 404

    if os.path.isdir(full_path):
        return jsonify({"error": "Cannot read a directory."}), 400

    # Reject known binary file extensions
    binary_exts = {".pyc", ".pyo", ".so", ".dll", ".exe", ".apk", ".jar",
                   ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar",
                   ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".bmp",
                   ".mp3", ".mp4", ".wav", ".avi", ".mkv", ".webm",
                   ".db", ".sqlite", ".sqlite3", ".woff", ".woff2", ".ttf", ".otf"}
    _, ext = os.path.splitext(full_path)
    if ext.lower() in binary_exts:
        return jsonify({
            "error": f"Cannot display binary file ({ext}). Download it instead.",
            "is_binary": True,
            "path": os.path.relpath(full_path, PROJECT_ROOT),
            "size": os.path.getsize(full_path),
        }), 415

    # Limit file size (500KB)
    if os.path.getsize(full_path) > 512000:
        return jsonify({"error": "File too large (max 500KB)."}), 413

    try:
        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return jsonify({
            "path": os.path.relpath(full_path, PROJECT_ROOT),
            "content": content,
            "size": len(content),
        })
    except Exception as e:
        return jsonify({"error": f"Cannot read file: {e}"}), 500


@admin_bp.route("/file", methods=["PUT"])
@admin_required
def write_file():
    """Write/update a file's content."""
    data = request.get_json(silent=True) or {}
    rel_path = data.get("path", "")
    content = data.get("content", "")

    if not rel_path:
        return jsonify({"error": "Path required."}), 400

    full_path = _safe_path(rel_path)
    if not full_path:
        return jsonify({"error": "Invalid path."}), 400

    # Don't allow editing outside project
    if not full_path.startswith(PROJECT_ROOT):
        return jsonify({"error": "Access denied."}), 403

    try:
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Admin edited file: {rel_path}")
        return jsonify({"status": "saved", "path": rel_path, "size": len(content)})
    except Exception as e:
        return jsonify({"error": f"Cannot write file: {e}"}), 500


# ── Stored data endpoints ─────────────────────────────────────

@admin_bp.route("/data", methods=["GET"])
@admin_required
def view_data():
    """View all stored data: chat history, facts, and system info."""
    result = {
        "chat_history": [],
        "user_facts": [],
        "system": {
            "project_root": PROJECT_ROOT,
            "data_dir": NOTES_DIR,
            "memory_db": MEMORY_DB,
            "db_exists": os.path.exists(MEMORY_DB),
        }
    }

    if not os.path.exists(MEMORY_DB):
        return jsonify(result)

    try:
        conn = sqlite3.connect(MEMORY_DB)

        # Chat history (last 100)
        try:
            rows = conn.execute(
                "SELECT id, timestamp, role, content FROM chat_history ORDER BY id DESC LIMIT 100"
            ).fetchall()
            result["chat_history"] = [
                {"id": r[0], "timestamp": r[1], "role": r[2], "content": r[3]}
                for r in rows
            ]
        except sqlite3.OperationalError:
            pass

        # User facts
        try:
            rows = conn.execute(
                "SELECT fact_key, fact_value, fact_type, priority, last_updated FROM user_facts ORDER BY priority DESC"
            ).fetchall()
            result["user_facts"] = [
                {"key": r[0], "value": r[1], "type": r[2], "priority": r[3], "updated": r[4]}
                for r in rows
            ]
        except sqlite3.OperationalError:
            pass

        conn.close()
    except Exception as e:
        result["error"] = str(e)

    return jsonify(result)


@admin_bp.route("/data/clear", methods=["POST"])
@admin_required
def clear_data():
    """Clear chat history or facts."""
    data = request.get_json(silent=True) or {}
    target = data.get("target", "")

    if not os.path.exists(MEMORY_DB):
        return jsonify({"error": "No database found."}), 404

    try:
        conn = sqlite3.connect(MEMORY_DB)
        if target == "chat":
            conn.execute("DELETE FROM chat_history")
            conn.commit()
            logger.info("Admin cleared chat history")
        elif target == "facts":
            conn.execute("DELETE FROM user_facts")
            conn.commit()
            logger.info("Admin cleared user facts")
        elif target == "all":
            conn.execute("DELETE FROM chat_history")
            conn.execute("DELETE FROM user_facts")
            conn.commit()
            logger.info("Admin cleared all data")
        else:
            conn.close()
            return jsonify({"error": "Target must be 'chat', 'facts', or 'all'."}), 400
        conn.close()
        return jsonify({"status": "cleared", "target": target})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/images", methods=["GET"])
@admin_required
def list_images():
    """List all generated images."""
    try:
        from app.skills.img import list_generated_images
        images = list_generated_images()
        return jsonify({"images": images})
    except Exception as e:
        logger.error(f"Failed to list images: {e}")
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════
# Daily Activity Log Endpoints
# ═══════════════════════════════════════════════════════════════

@admin_bp.route("/activities", methods=["GET"])
@admin_required
def list_activities():
    """GET /api/admin/activities — list all daily activity files."""
    from app.core.activity_logger import get_activity_logger
    files = get_activity_logger().list_files()
    return jsonify({"files": files, "count": len(files)})


@admin_bp.route("/activity", methods=["GET"])
@admin_required
def read_activity():
    """GET /api/admin/activity?date=2026-06-20 — read a day's activity."""
    date_str = (request.args.get("date") or "").strip()
    if not date_str:
        return jsonify({"error": "date parameter required (YYYY-MM-DD)"}), 400

    from app.core.activity_logger import get_activity_logger
    content = get_activity_logger().read_file(date_str)
    if content is None:
        return jsonify({"error": "Activity file not found."}), 404

    return jsonify({"date": date_str, "content": content, "size": len(content)})


@admin_bp.route("/activity", methods=["PUT"])
@admin_required
def write_activity():
    """PUT /api/admin/activity — { date: "2026-06-20", content: "..." }"""
    data = request.get_json(silent=True) or {}
    date_str = (data.get("date") or "").strip()
    content = data.get("content", "")

    if not date_str:
        return jsonify({"error": "date field required"}), 400

    from app.core.activity_logger import get_activity_logger
    ok = get_activity_logger().write_file(date_str, content)
    if not ok:
        return jsonify({"error": "Failed to write activity file."}), 500

    return jsonify({"status": "saved", "date": date_str, "size": len(content)})

