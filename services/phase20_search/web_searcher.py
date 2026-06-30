"""
Phase 20 — Web Searcher.

Simulates web search functionality.
"""

import time
from typing import List, Optional

from .models import SearchResult

# Mock web search data
_MOCK_WEB_RESULTS = [
    SearchResult(
        id="web_001",
        title="Python Programming Language",
        snippet="Python is a high-level, general-purpose programming language.",
        url="https://www.python.org",
        source="web",
        score=0.95,
    ),
    SearchResult(
        id="web_002",
        title="JARVIS AI Assistant",
        snippet="JARVIS is an AI-powered voice assistant for home automation.",
        url="https://github.com/jarvis",
        source="web",
        score=0.90,
    ),
    SearchResult(
        id="web_003",
        title="Machine Learning Guide",
        snippet="A comprehensive guide to machine learning algorithms and techniques.",
        url="https://example.com/ml-guide",
        source="web",
        score=0.85,
    ),
    SearchResult(
        id="web_004",
        title="Open Source Projects",
        snippet="Explore open source projects on GitHub and contribute to the community.",
        url="https://github.com",
        source="web",
        score=0.80,
    ),
    SearchResult(
        id="web_005",
        title="Web Development Tutorial",
        snippet="Learn web development with HTML, CSS, and JavaScript.",
        url="https://example.com/web-dev",
        source="web",
        score=0.75,
    ),
]


class WebSearcher:
    """Simulates web search using mock data."""

    def __init__(self):
        self._custom_results: List[SearchResult] = []

    def search(self, query: str, max_results: Optional[int] = None) -> List[SearchResult]:
        """Search the web for the given query.

        Args:
            query: Search query string.
            max_results: Maximum number of results.

        Returns:
            List of SearchResult objects.
        """
        if self._custom_results:
            return self._custom_results[:max_results]

        query_lower = query.lower()
        results = [
            r for r in _MOCK_WEB_RESULTS
            if query_lower in r.title.lower() or query_lower in r.snippet.lower()
        ]
        return results[:max_results] if max_results else results

    def set_custom_results(self, results: List[SearchResult]) -> None:
        """Set custom results for testing."""
        self._custom_results = list(results)
