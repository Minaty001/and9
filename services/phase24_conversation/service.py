"""
Phase 24 — Conversation Manager Service.

ServiceBase wrapper for conversation management.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Dict, List, Optional

from services.base.service_base import ServiceBase
from .config import ConversationConfig
from .models import DialogueState, Session
from .session import SessionManager
from .dialogue import DialogueTracker
from .reference import ReferenceResolver

logger = logging.getLogger(__name__)


class ConversationManagerService(ServiceBase):
    """Conversation manager service handling dialogue state, sessions, and references.

    Usage:
        svc = ConversationManagerService()
        await svc.initialize()
        session = await svc.create_session()
        state = await svc.process_turn(session.id, "What's the weather?")
    """

    def __init__(self, config: Optional[ConversationConfig] = None):
        super().__init__(name="jarvis_conversation", version="1.0.0")
        self.config = config or ConversationConfig()
        self.session_manager: Optional[SessionManager] = None
        self.dialogue_tracker: Optional[DialogueTracker] = None
        self.reference_resolver: Optional[ReferenceResolver] = None
        self._start_time = 0.0

    async def initialize(self) -> bool:
        """Initialize the conversation manager service."""
        self._start_time = time.time()
        try:
            self.session_manager = SessionManager(
                session_timeout_seconds=self.config.session_timeout_seconds,
            )
            self.dialogue_tracker = DialogueTracker(
                enable_topic_tracking=self.config.enable_topic_tracking,
                enable_goal_tracking=self.config.enable_goal_tracking,
            )
            self.reference_resolver = ReferenceResolver()
            self._metrics.reset()
            self._initialized = True
            logger.info("ConversationManagerService initialized")
            return True
        except Exception as e:
            logger.error("ConversationManagerService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        """Shut down the conversation manager service."""
        logger.info("ConversationManagerService shutting down...")
        self._initialized = False

    async def process_turn(
        self,
        session_id: str,
        query: str,
        intent: Optional[str] = None,
        entities: Optional[Dict[str, Any]] = None,
    ) -> DialogueState:
        """Process a conversation turn.

        Args:
            session_id: Session identifier.
            query: The user's query text.
            intent: Detected intent (optional).
            entities: Extracted entities (optional).

        Returns:
            Updated DialogueState.
        """
        if not self._initialized:
            raise RuntimeError("ConversationManagerService not initialized")

        session = self.session_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found or inactive: {session_id}")

        self._metrics.counter("turns_processed", 1)
        t0 = time.perf_counter()

        # Resolve references in the query
        if self.config.enable_reference_resolution:
            resolved = self._resolve_references_in_query(query, session_id)
        else:
            resolved = query

        # Detect entities if not provided
        if entities is None:
            entities = self.dialogue_tracker.extract_entities(query)

        # Update dialogue state
        state = self.dialogue_tracker.update_state(session_id, resolved, intent, entities)
        state.turn_count = len(session.dialogue_states) + 1

        # Track goal if applicable
        if self.config.enable_goal_tracking and intent and intent != "general":
            self.dialogue_tracker.track_goal(session_id, intent)

        # Add to session
        self.session_manager.add_dialogue_state(session_id, state)

        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.histogram("turn_processing_time_ms", elapsed)

        return state

    async def create_session(self, metadata: Optional[Dict[str, Any]] = None) -> Session:
        """Create a new conversation session.

        Args:
            metadata: Optional session metadata.

        Returns:
            New Session.
        """
        if not self._initialized or not self.session_manager:
            raise RuntimeError("ConversationManagerService not initialized")
        session = self.session_manager.create_session(metadata)
        self._metrics.counter("sessions_created", 1)
        return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID.

        Args:
            session_id: Session identifier.

        Returns:
            Session if found, None otherwise.
        """
        if not self._initialized or not self.session_manager:
            raise RuntimeError("ConversationManagerService not initialized")
        return self.session_manager.get_session(session_id)

    async def end_session(self, session_id: str) -> bool:
        """End a conversation session.

        Args:
            session_id: Session identifier.

        Returns:
            True if ended successfully.
        """
        if not self._initialized or not self.session_manager:
            raise RuntimeError("ConversationManagerService not initialized")
        result = self.session_manager.end_session(session_id)
        if result:
            self._metrics.counter("sessions_ended", 1)
        return result

    async def get_state(self, session_id: str) -> Optional[DialogueState]:
        """Get the current dialogue state for a session.

        Args:
            session_id: Session identifier.

        Returns:
            Current DialogueState or None.
        """
        if not self._initialized or not self.session_manager:
            raise RuntimeError("ConversationManagerService not initialized")
        return self.session_manager.get_dialogue_state(session_id)

    async def resolve_reference(self, reference: str, session_id: str) -> str:
        """Resolve a reference using session context.

        Args:
            reference: Reference text to resolve.
            session_id: Session identifier.

        Returns:
            Resolved reference string.
        """
        if not self._initialized or not self.session_manager:
            raise RuntimeError("ConversationManagerService not initialized")

        session = self.session_manager.get_session(session_id)
        if not session:
            return reference

        return self.reference_resolver.resolve(reference, session_id, session.dialogue_states)

    async def get_active_sessions(self) -> List[Session]:
        """Get all active sessions.

        Returns:
            List of active Session objects.
        """
        if not self._initialized or not self.session_manager:
            raise RuntimeError("ConversationManagerService not initialized")
        return self.session_manager.list_active_sessions()

    async def timeout_check(self) -> int:
        """Check for and expire timed-out sessions.

        Returns:
            Number of sessions expired.
        """
        if not self._initialized or not self.session_manager:
            raise RuntimeError("ConversationManagerService not initialized")
        return self.session_manager.timeout_check()

    async def health(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service_name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
        }

    async def stats(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        active_count = len(self.session_manager.list_active_sessions()) if self.session_manager else 0
        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            "active_sessions": active_count,
            "metrics": self._metrics.snapshot(),
        }

    def _resolve_references_in_query(self, query: str, session_id: str) -> str:
        """Resolve references found in a query string."""
        session = self.session_manager.get_session(session_id)
        if not session:
            return query

        refs = self.reference_resolver.extract_references(query)
        resolved_query = query

        for ref in refs:
            resolved = self.reference_resolver.resolve(ref, session_id, session.dialogue_states)
            if resolved != ref:
                resolved_query = resolved_query.replace(ref, resolved, 1)

        return resolved_query
