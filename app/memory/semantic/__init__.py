"""
app/memory/semantic/ — Semantic memory subsystem.

Stores and retrieves structured knowledge and entity-relationship graphs.

Components:
    - KnowledgeGraph: Entity-relationship knowledge graph
    - KnowledgeStore: In-memory store for knowledge entries
    - KnowledgeBase: Query/retrieve logic for structured Q&A
"""

from .knowledge_graph import KnowledgeGraph
from .knowledge_base import KnowledgeStore, KnowledgeBase, KnowledgeEntry, KnowledgeQuery, KnowledgeResult

__all__ = [
    "KnowledgeGraph",
    "KnowledgeStore",
    "KnowledgeBase",
    "KnowledgeEntry",
    "KnowledgeQuery",
    "KnowledgeResult",
]
