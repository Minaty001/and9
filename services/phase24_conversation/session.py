"""
Phase 24 — Session Manager.

Manage conversation sessions with creation, retrieval, and lifecycle.
"""

import time
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import Session, DialogueState

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages conversation session lifecycle."""

    def __init__(self, session_timeout_seconds: int = 1800):
        self._session_timeout = session_timeout_seconds
        self._sessions: Dict[str, Session] = {}

    def create_session(self, metadata: Optional[Dict[str, Any]] = None) -> Session:
        """Create a new conversation session.

        Args:
            metadata: Optional metadata to attach to the session.

        Returns:
            The newly created Session.
        """
        session_id = str(uuid.uuid4())
        session = Session(
            id=session_id,
            metadata=metadata or {},
        )
        self._sessions[session_id] = session
        logger.info("Created session: %s", session_id)
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID.

        Args:
            session_id: Session identifier.

        Returns:
            Session if found and active, None otherwise.
        """
        session = self._sessions.get(session_id)
        if not session:
            return None
        if not session.active:
            return None
        return session

    def end_session(self, session_id: str) -> bool:
        """End a session.

        Args:
            session_id: Session identifier.

        Returns:
            True if session was ended successfully.
        """
        session = self._sessions.get(session_id)
        if not session:
            return False
        session.active = False
        logger.info("Ended session: %s", session_id)
        return True

    def list_active_sessions(self) -> List[Session]:
        """List all active sessions.

        Returns:
            List of active Session objects.
        """
        return [s for s in self._sessions.values() if s.active]

    def timeout_check(self) -> int:
        """Check for and expire timed-out sessions.

        Returns:
            Number of sessions expired.
        """
        now = datetime.now(timezone.utc)
        expired = 0

        for session_id, session in list(self._sessions.items()):
            if not session.active:
                continue

            # Check last dialogue state
            if session.dialogue_states:
                last = session.dialogue_states[-1].last_active
                elapsed = (now - last).total_seconds()
                if elapsed > self._session_timeout:
                    session.active = False
                    expired += 1
                    logger.info("Session %s timed out after %.0fs", session_id, elapsed)
            else:
                # No dialogue states yet, check session creation time
                elapsed = (now - session.created_at).total_seconds()
                if elapsed > self._session_timeout:
                    session.active = False
                    expired += 1

        return expired

    def add_dialogue_state(self, session_id: str, state: DialogueState) -> bool:
        """Add a dialogue state to a session.

        Args:
            session_id: Session identifier.
            state: DialogueState to add.

        Returns:
            True if added successfully.
        """
        session = self._sessions.get(session_id)
        if not session or not session.active:
            return False
        session.dialogue_states.append(state)
        return True

    def get_dialogue_state(self, session_id: str) -> Optional[DialogueState]:
        """Get the most recent dialogue state for a session.

        Args:
            session_id: Session identifier.

        Returns:
            Most recent DialogueState or None.
        """
        session = self._sessions.get(session_id)
        if not session or not session.dialogue_states:
            return None
        return session.dialogue_states[-1]
