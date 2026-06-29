"""
app/api/admin_routes.py — Admin panel API endpoints.

Password-protected admin access for file browsing, editing, and data viewing.
Accepts passwords: "code10" or "codeten"
"""
import os
import hashlib
import logging
from functools import wraps
from backend.utils._flask_compat import Blueprint, request, jsonify, session, render_template

from backend.core.config import NOTES_DIR

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__)

import time

# ── Password hashes (loaded dynamically from environment, or fallback to default hashes with a warning) ──
_env_hash = os.environ.get("JARVIS_ADMIN_HASH")
if _env_hash:
    VALID_HASHES = {_env_hash}
else:
    _env_password = os.environ.get("JARVIS_ADMIN_PASSWORD")
    if _env_password:
        VALID_HASHES = {hashlib.sha256(_env_password.encode()).hexdigest()}
    else:
        logger.warning("No JARVIS_ADMIN_HASH or JARVIS_ADMIN_PASSWORD configured. Using default passwords!")
        VALID_HASHES = {
            hashlib.sha256("code10".encode()).hexdigest(),
            hashlib.sha256("codeten".encode()).hexdigest(),
        }

# IP-based failed login lockout: client_ip -> (fail_count, lockout_until_timestamp)
FAILED_LOGINS = {}

def _get_client_ip():
    """Securely get client IP address, trusting X-Forwarded-For only if proxy is configured."""
    trust_proxy = os.environ.get("TRUST_PROXY", "").lower() in ("true", "1") or os.environ.get("RENDER", "").lower() in ("true", "1")
    if trust_proxy:
        ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown")
        if "," in ip:
            ip = ip.split(",")[0].strip()
        return ip
    return request.remote_addr or "unknown"

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
    client_ip = _get_client_ip()
    now = time.time()

    # Check if locked out
    lockout_info = FAILED_LOGINS.get(client_ip)
    if lockout_info:
        fail_count, lockout_until = lockout_info
        if now < lockout_until:
            retry_after = int(lockout_until - now)
            return jsonify({
                "error": f"Too many failed attempts. Locked out. Try again in {retry_after} seconds."
            }), 429

    data = request.get_json(silent=True) or {}
    password = (data.get("password") or "").strip()

    if not password:
        return jsonify({"error": "Password required."}), 400

    pw_hash = hashlib.sha256(password.encode()).hexdigest()

    if pw_hash in VALID_HASHES:
        # Reset failed login count
        FAILED_LOGINS.pop(client_ip, None)
        session["admin_authenticated"] = True
        try:
            session.permanent = True
        except AttributeError:
            pass
        logger.info(f"Admin access granted to IP: {client_ip}")
        return jsonify({"status": "authenticated", "message": "Welcome, Admin."})
    else:
        # Increment failed login count
        fail_count = 0
        if lockout_info:
            fail_count = lockout_info[0]
        fail_count += 1

        # Lockout for 15 minutes after 5 failures
        if fail_count >= 5:
            lockout_until = now + 900
            FAILED_LOGINS[client_ip] = (fail_count, lockout_until)
            logger.warning(f"Admin login lockout triggered for IP: {client_ip}")
            return jsonify({"error": "Invalid password. Too many failures, locked out for 15 minutes."}), 429
        else:
            FAILED_LOGINS[client_ip] = (fail_count, 0)
            logger.warning(f"Failed admin login attempt from IP: {client_ip} (Attempt {fail_count}/5)")
            return jsonify({"error": f"Invalid password. Attempt {fail_count}/5."}), 403


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
    from backend.api.routes.routes import get_mem
    mem = get_mem()

    chat_history = []
    user_facts = []

    # Chat history (last 100)
    try:
        if mem._ok:
            res = mem._safe(lambda: mem._q("chat_history")
                             .select("id, created_at, role, content")
                             .order("id", desc=True)
                             .limit(100)
                             .execute(), None)
            if res and res.data:
                chat_history = [
                    {"id": r["id"], "timestamp": r.get("created_at"), "role": r["role"], "content": r["content"]}
                    for r in res.data
                ]
        else:
            chat_history = [
                {"id": i, "timestamp": msg.get("timestamp", ""), "role": msg["role"], "content": msg["content"]}
                for i, msg in enumerate(mem._mem["chat"])
            ]
    except Exception as e:
        logger.warning(f"Failed to fetch chat history for admin: {e}")

    # User facts
    try:
        if mem._ok:
            res = mem._safe(lambda: mem._q("user_facts")
                             .select("fact_key, fact_value, fact_type, priority, last_updated")
                             .order("priority", desc=True)
                             .execute(), None)
            if res and res.data:
                user_facts = [
                    {"key": r["fact_key"], "value": r["fact_value"], "type": r["fact_type"], "priority": r["priority"], "updated": r.get("last_updated")}
                    for r in res.data
                ]
        else:
            user_facts = [
                {"key": k, "value": v["value"], "type": v["type"], "priority": v["priority"], "updated": v.get("timestamp", "")}
                for k, v in mem._mem["facts"].items()
            ]
    except Exception as e:
        logger.warning(f"Failed to fetch user facts for admin: {e}")

    result = {
        "chat_history": chat_history,
        "user_facts": user_facts,
        "system": {
            "project_root": PROJECT_ROOT,
            "data_dir": NOTES_DIR,
            "memory_db": "Supabase (PostgreSQL)",
            "db_exists": mem._ok,
        }
    }
    return jsonify(result)


@admin_bp.route("/data/clear", methods=["POST"])
@admin_required
def clear_data():
    """Clear chat history or facts."""
    data = request.get_json(silent=True) or {}
    target = data.get("target", "")

    from backend.api.routes.routes import get_mem
    mem = get_mem()

    try:
        if target == "chat":
            if mem._ok:
                mem._safe(lambda: mem._q("chat_history").delete().neq("id", 0).execute())
            else:
                mem._mem["chat"].clear()
            logger.info("Admin cleared chat history")
        elif target == "facts":
            if mem._ok:
                mem._safe(lambda: mem._q("user_facts").delete().neq("priority", -999).execute())
            else:
                mem._mem["facts"].clear()
            logger.info("Admin cleared user facts")
        elif target == "all":
            if mem._ok:
                mem._safe(lambda: mem._q("chat_history").delete().neq("id", 0).execute())
                mem._safe(lambda: mem._q("user_facts").delete().neq("priority", -999).execute())
            else:
                mem._mem["chat"].clear()
                mem._mem["facts"].clear()
            logger.info("Admin cleared all data")
        else:
            return jsonify({"error": "Target must be 'chat', 'facts', or 'all'."}), 400

        return jsonify({"status": "cleared", "target": target})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/images", methods=["GET"])
@admin_required
def list_images():
    """List all generated images."""
    try:
        from backend.skills.media.img import list_generated_images
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
    from backend.core.activity_logger import get_activity_logger
    files = get_activity_logger().list_files()
    return jsonify({"files": files, "count": len(files)})


@admin_bp.route("/activity", methods=["GET"])
@admin_required
def read_activity():
    """GET /api/admin/activity?date=2026-06-20 — read a day's activity."""
    date_str = (request.args.get("date") or "").strip()
    if not date_str:
        return jsonify({"error": "date parameter required (YYYY-MM-DD)"}), 400

    from backend.core.activity_logger import get_activity_logger
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

    from backend.core.activity_logger import get_activity_logger
    ok = get_activity_logger().write_file(date_str, content)
    if not ok:
        return jsonify({"error": "Failed to write activity file."}), 500

    return jsonify({"status": "saved", "date": date_str, "size": len(content)})
