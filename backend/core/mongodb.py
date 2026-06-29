"""
AND9 — MongoDB Logger.

Persists every user chat turn (input + response) and every system
output to MongoDB Atlas for durable, queryable history.

Design:
  - Singleton pattern: one MongoClient per process
  - Lazy connection: connects on first write, not at import time
  - Fire-and-forget: all writes are wrapped in try/except — failures
    log a warning but NEVER crash the main pipeline
  - Reconnect-safe: on connection error, retry on next write

Environment:
  MONGO_URI — MongoDB Atlas connection string (with user/password)
              Defaults to the project's production cluster.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.core.config import MONGO_URI

logger = logging.getLogger(__name__)

# ── Singleton state ──────────────────────────────────────────────
_client = None
_db = None
_chats = None
_outputs = None
_last_attempt = 0.0       # timestamp of last connection attempt (cooldown)
_RETRY_COOLDOWN = 60.0    # seconds between reconnection attempts

DB_NAME = "and9"
COLL_CHATS = "chats"
COLL_OUTPUTS = "outputs"


def _get_client():
    """Get or create the cached MongoClient (lazy, singleton).

    Returns:
        pymongo.MongoClient or None if connection failed.
    """
    global _client, _last_attempt
    if _client is not None:
        return _client

    if not MONGO_URI:
        logger.debug("MongoLogger: MONGO_URI not configured")
        return None

    # Cooldown: don't retry more than once per _RETRY_COOLDOWN seconds
    now = __import__("time").time()
    if now - _last_attempt < _RETRY_COOLDOWN:
        return None
    _last_attempt = now

    try:
        from pymongo import MongoClient
        _client = MongoClient(
            MONGO_URI,
            serverSelectionTimeoutMS=5000,  # 5s connect timeout
            connectTimeoutMS=5000,
            socketTimeoutMS=5000,
            maxPoolSize=2,
            tls=True,
            tlsAllowInvalidCertificates=True,
        )
        logger.info("MongoLogger: connected to MongoDB Atlas")
        return _client
    except Exception as e:
        logger.debug("MongoLogger: connection failed: %s", e)
        _client = None
        return None


def _get_db():
    """Get the cached database handle."""
    global _db
    client = _get_client()
    if client is None:
        return None
    if _db is None:
        _db = client[DB_NAME]
    return _db


def _get_chats():
    """Get the cached chats collection handle."""
    global _chats
    db = _get_db()
    if db is None:
        return None
    if _chats is None:
        _chats = db[COLL_CHATS]
    return _chats


def _get_outputs():
    """Get the cached outputs collection handle."""
    global _outputs
    db = _get_db()
    if db is None:
        return None
    if _outputs is None:
        _outputs = db[COLL_OUTPUTS]
    return _outputs


def log_chat(
    user_input: str,
    response: str,
    intent: str = "",
    action: str = "chat",
    brain_type: str = "",
    confidence: float = 0.0,
    emotion: str = "neutral",
    topic: str = "general",
    time_ms: float = 0.0,
    success: bool = True,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Log one user → AI chat turn to MongoDB.

    This is fire-and-forget: any failure is logged as a warning
    and silently swallowed. The main pipeline is NEVER blocked
    by MongoDB.

    Args:
        user_input: The raw user query.
        response: The AI response text.
        intent: Classified intent string (e.g. "PYTHON_CODING").
        action: Action type (e.g. "chat", "open_app", "search").
        brain_type: Which brain handled it ("reflex", "neural", etc.).
        confidence: Classification confidence (0-1).
        emotion: Detected emotion.
        topic: Detected topic.
        time_ms: Processing time in milliseconds.
        success: Whether processing was successful.
        metadata: Additional key-value data.
    """
    col = _get_chats()
    if col is None:
        return

    doc = {
        "user_input": user_input[:1000],
        "response": response[:2000],
        "intent": intent or "",
        "action": action or "chat",
        "brain_type": brain_type or "",
        "confidence": round(float(confidence), 4),
        "emotion": emotion or "neutral",
        "topic": topic or "general",
        "time_ms": round(float(time_ms), 1),
        "success": bool(success),
        "metadata": metadata or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        col.insert_one(doc)
    except Exception as e:
        logger.debug("MongoLogger: log_chat failed: %s", e)
        # Reset connection on error — next write will retry
        _reset()


def log_output(
    source: str,
    content: str,
    output_type: str = "unknown",
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Log a system processing output to MongoDB.

    Args:
        source: Origin module (e.g. "brain/neural", "brain/reflex").
        content: The output content (response, log, etc.).
        output_type: Category (e.g. "PYTHON_CODING", "search_result").
        metadata: Additional context.
    """
    col = _get_outputs()
    if col is None:
        return

    doc = {
        "source": source[:200],
        "content": content[:2000],
        "output_type": output_type or "unknown",
        "metadata": metadata or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        col.insert_one(doc)
    except Exception as e:
        logger.debug("MongoLogger: log_output failed: %s", e)
        _reset()


def get_recent_chats(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve the most recent chat logs from MongoDB.

    Args:
        limit: Max number of entries to return (default 50).

    Returns:
        List of chat documents (sorted newest-first), or empty list
        on error.
    """
    col = _get_chats()
    if col is None:
        return []
    try:
        cursor = col.find().sort("timestamp", -1).limit(limit)
        return list(cursor)
    except Exception as e:
        logger.warning("MongoLogger: get_recent_chats failed: %s", e)
        return []


def get_recent_outputs(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve the most recent system output logs from MongoDB.

    Args:
        limit: Max number of entries to return (default 50).

    Returns:
        List of output documents (sorted newest-first), or empty list
        on error.
    """
    col = _get_outputs()
    if col is None:
        return []
    try:
        cursor = col.find().sort("timestamp", -1).limit(limit)
        return list(cursor)
    except Exception as e:
        logger.warning("MongoLogger: get_recent_outputs failed: %s", e)
        return []


def is_connected() -> bool:
    """Check whether MongoDB is currently connected and responsive.

    Only checks an already-established connection. Does NOT attempt
    a new connection — use _get_client() for that.
    
    Returns True if a connection exists and is responsive, False otherwise.
    """
    global _client
    if _client is None:
        return False
    try:
        _client.admin.command("ping")
        return True
    except Exception:
        return False


def close():
    """Close the MongoDB connection gracefully.

    Call this during application shutdown to release resources.
    """
    global _client, _db, _chats, _outputs
    if _client is not None:
        try:
            _client.close()
        except Exception as e:
            logger.debug("MongoLogger: close error: %s", e)
    _client = None
    _db = None
    _chats = None
    _outputs = None


def _reset():
    """Reset connection state after an error so next write retries."""
    global _client, _db, _chats, _outputs
    if _client is not None:
        try:
            _client.close()
        except Exception:
            pass
    _client = None
    _db = None
    _chats = None
    _outputs = None
