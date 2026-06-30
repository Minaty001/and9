"""
Phase 24 — Conversation Manager.

Track dialogue state, active topic, user goals, pending questions.
Reference resolution, session boundaries.

Components:
    - ConversationConfig: Configuration for conversation manager
    - DialogueState: Dialogue state data model
    - Session: Session data model
    - SessionManager: Manage conversation sessions
    - DialogueTracker: Track dialogue state and topics
    - ReferenceResolver: Resolve references using context
    - ConversationManagerService: ServiceBase wrapper
"""

from .config import ConversationConfig
from .models import DialogueState, Session
from .session import SessionManager
from .dialogue import DialogueTracker
from .reference import ReferenceResolver
from .service import ConversationManagerService

__all__ = [
    "ConversationConfig",
    "DialogueState",
    "Session",
    "SessionManager",
    "DialogueTracker",
    "ReferenceResolver",
    "ConversationManagerService",
]
