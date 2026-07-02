"""
AND9 — Working Memory & Memory Layers.

Provides three layers of conversational memory:

  1. WorkingMemory — Recent turn buffer (deque, max N turns).
     Stores complete user-assistant exchanges with metadata.

  2. ShortTermMemory — Ephemeral entity store with TTL.
     Remembers facts mentioned in the current session for
     quick reference resolution (e.g., "that song").

  3. ActiveTaskMemory — Lightweight tracker of the active task
     and paused task queue.

Designed to be lightweight, thread-safe, and suitable for Termux.
"""

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class TurnRecord:
    """A single user-assistant exchange turn."""
    user_message: str
    assistant_message: str
    intent: str = ""
    task_id: str = ""
    timestamp: float = field(default_factory=time.time)
    entities: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "user_message": self.user_message,
            "assistant_message": self.assistant_message,
            "intent": self.intent,
            "task_id": self.task_id,
            "timestamp": self.timestamp,
            "entities": self.entities,
        }


@dataclass
class DialogueConfig:
    """Configuration for the Dialogue Manager.

    Attributes:
        max_history: Maximum conversation turns to keep in working memory.
        max_active_tasks: Maximum concurrent active tasks (0 = unlimited).
        auto_cleanup_interval: Seconds between auto-cleanup of old tasks.
        entity_ttl: Seconds before short-term memory entities expire.
        persist_path: Optional file path for state persistence.
        debug_mode: Enable verbose logging.
    """
    max_history: int = 100
    max_active_tasks: int = 10
    auto_cleanup_interval: int = 300
    entity_ttl: int = 300  # 5 minutes
    persist_path: Optional[str] = None
    debug_mode: bool = False


class ShortTermMemory:
    """Ephemeral key-value store with TTL.

    Remembers entities mentioned in the current conversation session.
    Each entity has a configurable TTL (default 5 minutes).

    Thread-safe.
    """

    def __init__(self, default_ttl: int = 300):
        self._lock = threading.Lock()
        self._data: dict[str, tuple[Any, float]] = {}  # key -> (value, expiry)
        self._default_ttl = default_ttl

    def remember(self, key: str, value: Any, ttl: Optional[int] = None):
        """Store a value with TTL.

        Args:
            key: Entity key (e.g., "last_song", "last_app").
            value: The value to remember.
            ttl: Time-to-live in seconds (default: self._default_ttl).
        """
        with self._lock:
            expiry = time.time() + (ttl if ttl is not None else self._default_ttl)
            self._data[key] = (value, expiry)
            logger.debug("STM: remembered '%s' = '%s' (ttl=%ds)",
                         key, value, ttl or self._default_ttl)

    def recall(self, key: str) -> Optional[Any]:
        """Recall a value by key.

        Returns None if the key doesn't exist or has expired.
        """
        with self._lock:
            entry = self._data.get(key)
            if not entry:
                return None
            value, expiry = entry
            if time.time() > expiry:
                del self._data[key]
                return None
            return value

    def forget(self, key: str):
        """Explicitly remove a key."""
        with self._lock:
            self._data.pop(key, None)

    def get_all(self) -> dict[str, Any]:
        """Get all non-expired entries as a plain dict."""
        with self._lock:
            now = time.time()
            result = {}
            expired = []
            for key, (value, expiry) in self._data.items():
                if now > expiry:
                    expired.append(key)
                else:
                    result[key] = value
            for key in expired:
                del self._data[key]
            return result

    def clear(self):
        """Clear all entries."""
        with self._lock:
            self._data.clear()

    @property
    def size(self) -> int:
        """Number of non-expired entries."""
        return len(self.get_all())


class WorkingMemory:
    """Conversation turn buffer.

    Stores the most recent N user-assistant exchanges with full
    intent and entity metadata. Used by the Context Manager for
    context assembly and by the Reference Resolver for anaphora
    resolution.
    """

    def __init__(self, max_history: int = 100):
        self._lock = threading.Lock()
        self._turns: deque[TurnRecord] = deque(maxlen=max_history)
        self._max_history = max_history

    def add_turn(self, user_message: str, assistant_message: str,
                 intent: str = "", task_id: str = "",
                 entities: Optional[dict[str, str]] = None) -> TurnRecord:
        """Record a conversation turn.

        Args:
            user_message: The user's input.
            assistant_message: The assistant's response.
            intent: Detected intent name.
            task_id: Active task ID.
            entities: Entities extracted from this turn.

        Returns:
            The created TurnRecord.
        """
        record = TurnRecord(
            user_message=user_message,
            assistant_message=assistant_message,
            intent=intent,
            task_id=task_id,
            entities=entities or {},
        )
        with self._lock:
            self._turns.append(record)
        return record

    def get_recent_turns(self, n: int = 10) -> list[TurnRecord]:
        """Get the N most recent turns.

        Args:
            n: Number of turns to return.

        Returns:
            List of TurnRecord, most recent last.
        """
        with self._lock:
            all_turns = list(self._turns)
            return all_turns[-n:] if len(all_turns) > n else all_turns

    def get_last_n(self, n: int = 5) -> list[TurnRecord]:
        """Get the last N turns (for context assembly)."""
        return self.get_recent_turns(n)

    def get_last_user_message(self) -> Optional[str]:
        """Get the most recent user message."""
        with self._lock:
            if self._turns:
                return self._turns[-1].user_message
            return None

    def get_last_assistant_message(self) -> Optional[str]:
        """Get the most recent assistant response."""
        with self._lock:
            if self._turns:
                return self._turns[-1].assistant_message
            return None

    def get_turn_count(self) -> int:
        """Total number of turns recorded (session total)."""
        with self._lock:
            return len(self._turns)

    def get_active_intents(self) -> list[str]:
        """Get unique intents from recent turns (last 20)."""
        with self._lock:
            recent = list(self._turns)[-20:]
            seen = set()
            intents = []
            for t in recent:
                if t.intent and t.intent not in seen:
                    seen.add(t.intent)
                    intents.append(t.intent)
            return intents

    def get_last_entity(self, key: str) -> Optional[str]:
        """Get the most recently mentioned value for an entity key.

        Searches backward through turns to find the last mention.
        """
        with self._lock:
            for turn in reversed(self._turns):
                if key in turn.entities:
                    return turn.entities[key]
            return None

    def get_all_entities(self) -> dict[str, str]:
        """Aggregate all entities from recent turns."""
        with self._lock:
            entities = {}
            for turn in self._turns:
                entities.update(turn.entities)
            return entities

    def clear(self):
        """Clear all turns."""
        with self._lock:
            self._turns.clear()

    def to_dict_list(self, n: int = 20) -> list[dict]:
        """Serialize recent turns to dict list (for API)."""
        return [t.to_dict() for t in self.get_recent_turns(n)]

    def get_turns_for_task(self, task_id: str) -> list[TurnRecord]:
        """Get all turns belonging to a specific task."""
        with self._lock:
            return [t for t in self._turns if t.task_id == task_id]


class ActiveTaskMemory:
    """Lightweight tracker for the active task and paused queue.

    This is a thin wrapper around the state tracker's concept of
    "active" vs "paused" for quick access without going through
    the full DST.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._active_task_id: Optional[str] = None
        self._paused_queue: list[str] = []

    def set_active(self, task_id: Optional[str]):
        with self._lock:
            self._active_task_id = task_id

    def get_active(self) -> Optional[str]:
        with self._lock:
            return self._active_task_id

    def push_paused(self, task_id: str):
        with self._lock:
            if task_id not in self._paused_queue:
                self._paused_queue.append(task_id)

    def pop_paused(self) -> Optional[str]:
        with self._lock:
            if self._paused_queue:
                return self._paused_queue.pop()
            return None

    def peek_paused(self) -> Optional[str]:
        with self._lock:
            if self._paused_queue:
                return self._paused_queue[-1]
            return None

    def remove_paused(self, task_id: str):
        with self._lock:
            self._paused_queue = [t for t in self._paused_queue if t != task_id]

    def get_paused_count(self) -> int:
        with self._lock:
            return len(self._paused_queue)
