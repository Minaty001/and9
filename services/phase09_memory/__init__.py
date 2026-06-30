"""
Phase 9 — Memory System
========================

Long-term and working memory management for the JARVIS assistant.
Supports storing, retrieving, consolidating, and forgetting memories.

Components:
    - MemoryStore: In-memory storage with CRUD and threshold-aware eviction
    - MemoryManager: Consolidation, retrieval, and lifecycle management
    - MemoryService: ServiceBase wrapper

Usage:
    svc = MemoryService()
    await svc.initialize()
    await svc.store("user_name", "Alice", memory_type="long_term", importance=0.9)
    results = await svc.recall("name")
    await svc.consolidate()
"""

from .memory_store import MemoryStore, MemoryItem
from .memory_manager import MemoryManager, MemoryType
from .service import MemoryService
from .config import MemoryConfig
from .models import MemoryQuery, MemoryStats

__all__ = [
    "MemoryStore",
    "MemoryItem",
    "MemoryManager",
    "MemoryType",
    "MemoryService",
    "MemoryConfig",
    "MemoryQuery",
    "MemoryStats",
]
