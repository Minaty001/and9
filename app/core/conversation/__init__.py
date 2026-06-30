"""
app/core/conversation/ — Conversation Manager.

Track dialogue state, active topic, user goals, pending questions.
Reference resolution, session boundaries.

Components:
    - Session: Conversation session data model
    - DialogueState: Dialogue state data model
    - SessionManager: Manage conversation sessions (create/get/end)
    - DialogueTracker: Track dialogue state, topics, and goals
    - ReferenceResolver: Resolve pronouns and references using context
"""

from .session import SessionManager
from .dialogue import DialogueTracker
from .reference import ReferenceResolver
from .models import Session, DialogueState

__all__ = [
    "SessionManager",
    "DialogueTracker",
    "ReferenceResolver",
    "Session",
    "DialogueState",
]
