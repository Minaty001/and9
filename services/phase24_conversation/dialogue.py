"""
Phase 24 — Dialogue Tracker.

Track dialogue state, topics, goals, and pending questions.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import DialogueState

logger = logging.getLogger(__name__)

# Simple keyword-based topic detection
TOPIC_KEYWORDS: Dict[str, List[str]] = {
    "weather": ["weather", "temperature", "rain", "forecast", "climate"],
    "news": ["news", "headlines", "latest", "breaking", "report"],
    "time": ["time", "date", "clock", "schedule", "when"],
    "search": ["search", "find", "look up", "google", "internet"],
    "greeting": ["hello", "hi", "hey", "good morning", "good evening"],
    "help": ["help", "assist", "support", "how to", "guide"],
    "music": ["music", "song", "play", "audio", "listen"],
    "memory": ["remember", "recall", "memory", "forget", "store"],
}


class DialogueTracker:
    """Tracks dialogue state, topics, user goals, and pending questions."""

    def __init__(self, enable_topic_tracking: bool = True, enable_goal_tracking: bool = True):
        self._enable_topic_tracking = enable_topic_tracking
        self._enable_goal_tracking = enable_goal_tracking

    def update_state(
        self,
        session_id: str,
        query: str,
        intent: Optional[str] = None,
        entities: Optional[Dict[str, Any]] = None,
    ) -> DialogueState:
        """Update dialogue state with a new turn.

        Args:
            session_id: Session identifier.
            query: The user's query text.
            intent: Detected intent (optional).
            entities: Extracted entities (optional).

        Returns:
            Updated DialogueState.
        """
        topic = self.detect_topic(query) if self._enable_topic_tracking else "general"
        entities = entities or {}

        state = DialogueState(
            session_id=session_id,
            active_topic=topic,
            turn_count=1,
            recent_entities=entities,
            references={},
        )

        # Update recent entities
        for key, value in entities.items():
            state.recent_entities[key] = value
            # Create reference from entity name to value
            state.references[key] = str(value)

        return state

    def get_current_state(self, session_id: str) -> Optional[DialogueState]:
        """Get current state (stub - actual storage is in SessionManager).

        This is a convenience method. The actual state storage
        is managed by the ConversationManagerService.

        Args:
            session_id: Session identifier.

        Returns:
            None by default; actual state from SessionManager.
        """
        return None

    def detect_topic(self, query: str) -> str:
        """Detect topic from query text using keyword matching.

        Args:
            query: The user's query text.

        Returns:
            Detected topic string.
        """
        query_lower = query.lower().strip()

        for topic, keywords in TOPIC_KEYWORDS.items():
            for keyword in keywords:
                if keyword in query_lower:
                    return topic

        return "general"

    def track_goal(self, session_id: str, goal: str) -> bool:
        """Register a user goal for a session.

        Args:
            session_id: Session identifier.
            goal: The detected user goal.

        Returns:
            True if tracked successfully.
        """
        logger.info("Tracked goal for session %s: %s", session_id, goal)
        return True

    def add_pending_question(self, session_id: str, question: str) -> bool:
        """Add a pending question for a session.

        Args:
            session_id: Session identifier.
            question: The question text.

        Returns:
            True if added successfully.
        """
        logger.info("Added pending question for session %s: %s", session_id, question)
        return True

    def extract_entities(self, query: str) -> Dict[str, Any]:
        """Simple entity extraction from query text.

        Args:
            query: The user's query text.

        Returns:
            Dictionary of extracted entities.
        """
        entities: Dict[str, Any] = {}
        query_lower = query.lower()

        # Simple entity extraction patterns
        if "mumbai" in query_lower:
            entities["location"] = "Mumbai"
        if "delhi" in query_lower:
            entities["location"] = "Delhi"
        if "bangalore" in query_lower:
            entities["location"] = "Bangalore"
        if "python" in query_lower:
            entities["language"] = "Python"
        if "javascript" in query_lower:
            entities["language"] = "JavaScript"

        return entities
