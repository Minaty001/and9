"""
Phase 20 — Search Result Merger.

Merges and ranks results from multiple search sources.
"""

from typing import Dict, List

from .models import SearchResult


class SearchMerger:
    """Merges results from web, memory, and document sources.

    Interleaves sources, deduplicates by title/url, and sorts by score.
    """

    def merge(
        self,
        web_results: List[SearchResult],
        memory_results: List[SearchResult],
        doc_results: List[SearchResult],
        max_results: int = 20,
        min_score: float = 0.0,
    ) -> List[SearchResult]:
        """Merge results from multiple sources.

        Deduplicates by title/url, filters by min_score, sorts by score descending.

        Args:
            web_results: Results from web search.
            memory_results: Results from memory search.
            doc_results: Results from document search.
            max_results: Maximum number of results to return.
            min_score: Minimum score threshold (0.0-1.0).

        Returns:
            Merged and ranked list of SearchResult objects.
        """
        seen: Dict[str, SearchResult] = {}  # key = title lowercase
        seen_urls: set = set()  # track seen URLs

        def _add(results):
            for r in results:
                if r.score < min_score:
                    continue
                title_key = r.title.lower().strip()
                url_key = (r.url or "").lower().strip()
                # Check if duplicate by title
                if title_key in seen:
                    existing = seen[title_key]
                    if r.score > existing.score:
                        seen[title_key] = r
                    continue
                # Check if duplicate by URL
                if url_key and url_key in seen_urls:
                    # Find and potentially replace
                    found = None
                    for k, v in seen.items():
                        if (v.url or "").lower().strip() == url_key:
                            found = (k, v)
                            break
                    if found:
                        k, existing = found
                        if r.score > existing.score:
                            del seen[k]
                            seen[title_key] = r
                    continue
                seen[title_key] = r
                if url_key:
                    seen_urls.add(url_key)

        _add(web_results)
        _add(memory_results)
        _add(doc_results)

        merged = sorted(seen.values(), key=lambda r: r.score, reverse=True)
        return merged[:max_results]
