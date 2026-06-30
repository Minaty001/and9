"""
Phase 20 — Document Searcher.

Simulates searching through stored documents.
"""

import time
from typing import List, Optional

from .models import SearchResult


class DocumentSearcher:
    """Simulates searching through stored documents.

    Uses keyword matching against stored document entries.
    """

    def __init__(self):
        self._documents: List[SearchResult] = [
            SearchResult(
                id="doc_001",
                title="Project README",
                snippet="This project is an AI assistant for home automation.",
                source="document",
                score=0.91,
            ),
            SearchResult(
                id="doc_002",
                title="Installation Guide",
                snippet="Follow these steps to install the JARVIS assistant on your system.",
                source="document",
                score=0.87,
            ),
            SearchResult(
                id="doc_003",
                title="API Documentation",
                snippet="The REST API provides endpoints for querying the assistant.",
                source="document",
                score=0.84,
            ),
            SearchResult(
                id="doc_004",
                title="Configuration Reference",
                snippet="Configuration files use YAML format with predefined schema.",
                source="document",
                score=0.79,
            ),
            SearchResult(
                id="doc_005",
                title="Troubleshooting Guide",
                snippet="Common issues and solutions for the JARVIS assistant.",
                source="document",
                score=0.76,
            ),
        ]

    def search(self, query: str, max_results: Optional[int] = None) -> List[SearchResult]:
        """Search documents for the given query.

        Args:
            query: Search query string.
            max_results: Maximum number of results.

        Returns:
            List of matching SearchResult objects.
        """
        query_lower = query.lower()
        results = [
            doc for doc in self._documents
            if query_lower in doc.title.lower() or query_lower in doc.snippet.lower()
        ]
        return results[:max_results] if max_results else results

    def add_document(self, result: SearchResult) -> None:
        """Add a document."""
        self._documents.append(result)

    def clear_documents(self) -> None:
        """Clear all documents."""
        self._documents.clear()
