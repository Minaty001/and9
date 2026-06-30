"""
Phase 27 — Knowledge Base
==========================

Structured Q&A, facts, user info, domain knowledge with fast retrieval,
import/export, tagging, and confidence scoring.

Components:
    - KnowledgeStore: In-memory storage for knowledge entries
    - KnowledgeBase: Query/retrieve logic with import/export
    - KnowledgeBaseService: ServiceBase wrapper
"""

from .knowledge_store import KnowledgeStore
from .knowledge_base import KnowledgeBase
from .service import KnowledgeBaseService
from .config import KnowledgeConfig
from .models import KnowledgeEntry, KnowledgeQuery, KnowledgeResult

__all__ = [
    "KnowledgeStore",
    "KnowledgeBase",
    "KnowledgeBaseService",
    "KnowledgeConfig",
    "KnowledgeEntry",
    "KnowledgeQuery",
    "KnowledgeResult",
]
