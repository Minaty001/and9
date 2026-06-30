"""
Phase 20 — Search Engine.

Unified web, memory, and document search with merging, caching, and telemetry.

Components:
    - SearchConfig: Configuration for search engine
    - SearchResult: Search result data model
    - SearchQuery: Search query with filters
    - WebSearcher: Simulated web search
    - MemorySearcher: Simulated memory search
    - DocumentSearcher: Simulated document search
    - SearchMerger: Merge and rank results
    - SearchCache: LRU cache with TTL
    - SearchEngineService: ServiceBase wrapper
"""

from .config import SearchConfig
from .models import SearchResult, SearchQuery
from .web_searcher import WebSearcher
from .memory_searcher import MemorySearcher
from .document_searcher import DocumentSearcher
from .merger import SearchMerger
from .cache import SearchCache
from .service import SearchEngineService

__all__ = [
    "SearchConfig",
    "SearchResult",
    "SearchQuery",
    "WebSearcher",
    "MemorySearcher",
    "DocumentSearcher",
    "SearchMerger",
    "SearchCache",
    "SearchEngineService",
]
