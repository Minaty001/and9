"""
AND9 — DuckDuckGo Web Search Integration.

Free, API-key-free web search using duckduckgo-search (or ddgs).
Replaces the SerpAPI dependency for basic web search needs.

Usage:
    from app.integrations.duckduckgo import web_search
    results = web_search("latest AI news")
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Try ddgs (the modern, maintained fork) first,
# fall back to the original duckduckgo-search package.
try:
    from ddgs import DDGS  # pip install ddgs
except ImportError:
    try:
        from duckduckgo_search import DDGS  # pip install duckduckgo-search
    except ImportError:
        DDGS = None  # type: ignore


def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Search the web using DuckDuckGo.

    Args:
        query: Search term.
        max_results: Max results to return (default 5).

    Returns:
        List of dicts with keys: title, href, body.
        Empty list on error or if DDGS is not installed.
    """
    if DDGS is None:
        logger.warning("DuckDuckGo search not available — install 'ddgs' or 'duckduckgo-search'.")
        return []

    try:
        with DDGS() as ddgs:
            raw = list(ddgs.text(query, max_results=max_results))
        logger.info("DuckDuckGo returned %d results for '%s'", len(raw), query)
        return [
            {
                "title": item.get("title", ""),
                "href": item.get("href", ""),
                "body": item.get("body", ""),
            }
            for item in raw
        ]
    except Exception as e:
        logger.warning("DuckDuckGo search failed: %s", e)
        return []


def search_sources(query: str, num: int = 5) -> list[dict]:
    """Drop-in replacement for research.search_sources() — same signature.

    Args:
        query: Search term.
        num: Number of results (default 5).

    Returns:
        List of dicts with keys: title, link, snippet.
    """
    raw = web_search(query, max_results=num)
    return [
        {
            "title": item["title"],
            "link": item["href"],
            "snippet": item["body"],
        }
        for item in raw
    ]
