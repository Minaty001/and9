"""
AND9 — Activity Database Logger.
Manages the activities.db SQLite database for tracking executed actions.
"""
import sqlite3
import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
# Dynamic DB path resolution for local dev vs Render deploy
if os.environ.get("RENDER") or os.path.exists("/app/.jarvis_data"):
    _default_db = "/app/.jarvis_data/activities.db"
else:
    _default_db = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "activities.db"))

DB_PATH = os.environ.get("AND9_ACTIVITIES_DB", _default_db)

try:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
except Exception as _mkdir_err:
    logger.warning("Could not create activities DB directory '%s': %s", os.path.dirname(DB_PATH), _mkdir_err)

def init_activity_db():
    """Initialize activities.db schema."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                query TEXT NOT NULL,
                intent TEXT NOT NULL,
                action TEXT NOT NULL,
                result TEXT NOT NULL,
                details TEXT
            )
        """)
        conn.commit()
        conn.close()
        logger.info("Activity DB initialized successfully at %s", DB_PATH)
    except Exception as e:
        logger.error("Failed to initialize activity database: %s", e)

def validate_database() -> bool:
    """Validate database schema and writability."""
    try:
        init_activity_db()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Check table structure
        cursor.execute("PRAGMA table_info(activities)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        required_cols = {"id", "timestamp", "query", "intent", "action", "result", "details"}
        for col in required_cols:
            if col not in columns:
                raise RuntimeError(f"Database validation failed: missing column {col}")
        # Check if writable
        cursor.execute("INSERT INTO activities (timestamp, query, intent, action, result, details) VALUES (?, ?, ?, ?, ?, ?)",
                       (datetime.now().isoformat(), "test_startup", "test", "test", "test", "{}"))
        conn.commit()
        # Delete test entry
        cursor.execute("DELETE FROM activities WHERE query = 'test_startup'")
        conn.commit()
        conn.close()
        logger.info("Database validation PASSED.")
        return True
    except Exception as e:
        logger.critical("Database validation FAILED: %s", e)
        raise RuntimeError(f"Database validation failed: {e}")

def format_action_result(action: str, query: str, response: str, success: bool) -> str:
    """Format a human-readable action result summary matching AGENTS.md constitutional examples."""
    if not success:
        return f"failure: {response}"
    
    action_lower = action.lower() if action else ""
    query_lower = query.lower()
    
    if "youtube" in action_lower or "youtube" in query_lower:
        return "opened youtube"
    elif "call" in action_lower or "call" in query_lower:
        name = "contact"
        for word in ["mummy", "papa", "amit"]:
            if word in query_lower:
                name = word
                break
        return f"called {name}"
    elif "whatsapp" in action_lower or "whatsapp" in query_lower:
        return "opened whatsapp"
    elif "alarm" in action_lower or "alarm" in query_lower:
        return "alarm set"
    elif "timer" in action_lower or "timer" in query_lower:
        return "timer started"
    elif "flashlight" in action_lower or "torch" in action_lower:
        if "off" in query_lower or "band" in query_lower:
            return "flashlight off"
        return "flashlight on"
    
    return response.strip() if response else "success"

def log_activity(query: str, intent: str, action: str, result_summary: str, details_dict: dict = None):
    """Log an action execution to the activities table."""
    try:
        init_activity_db()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        timestamp = datetime.now().isoformat()
        details_json = json.dumps(details_dict or {})
        cursor.execute("""
            INSERT INTO activities (timestamp, query, intent, action, result, details)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (timestamp, query, intent, action, result_summary, details_json))
        conn.commit()
        conn.close()
        logger.info("Logged activity: %s | Result: %s", query, result_summary)
    except Exception as e:
        logger.error("Failed to log activity: %s", e)
