"""
Phase 20 — Memory Searcher.

Simulates searching through stored memory items.
"""

import time
from typing import List, Optional

from .models import SearchResult


class MemorySearcher:
    """Simulates searching through stored memory items.

    Uses keyword matching against stored memory entries.
    """

    def __init__(self):
        self._memory_items: List[SearchResult] = [
            SearchResult(
                id="mem_001",
                title="User's name",
                snippet="The user's name is Alex.",
                source="memory",
                score=0.92,
            ),
            SearchResult(
                id="mem_002",
                title="Favorite music",
                snippet="User enjoys listening to jazz and classical music.",
                source="memory",
                score=0.88,
            ),
            SearchResult(
                id="mem_003",
                title="Home address",
                snippet="User's home address is 123 Main Street.",
                source="memory",
                score=0.85,
            ),
            SearchResult(
                id="mem_004",
                title="Email account",
                snippet="User's email is alex@example.com.",
                source="memory",
                score=0.82,
            ),
            SearchResult(
                id="mem_005",
                title="Recent conversation",
                snippet="User asked about weather forecasting last Tuesday.",
                source="memory",
                score=0.78,
            ),
        ]

    def search(self, query: str, max_results: Optional[int] = None) -> List[SearchResult]:
        """Search memory for items matching the query.

        Args:
            query: Search query string.
            max_results: Maximum number of results.

        Returns:
            List of matching SearchResult objects.
        """
        query_lower = query.lower()
        results = [
            item for item in self._memory_items
            if query_lower in item.title.lower() or query_lower in item.snippet.lower()
        ]
        return results[:max_results] if max_results else results

    def add_memory(self, result: SearchResult) -> None:
        """Add a memory item."""
        self._memory_items.append(result)

    def clear_memory(self) -> None:
        """Clear all memory items."""
        self._memory_items.clear()
