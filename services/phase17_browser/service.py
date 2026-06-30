"""
Phase 17 — Browser Controller Service.

Wraps SearchEngine, PageInteractor, ContentExtractor, and PageSummarizer
in a ServiceBase interface with lifecycle management, metrics, and health checks.
"""

import time
import logging
from typing import Any, Dict, List, Optional

from services.base.service_base import ServiceBase
from .config import BrowserConfig
from .models import BrowserActionResult
from .browser_controller import SearchEngine, PageInteractor, ContentExtractor, PageSummarizer

logger = logging.getLogger(__name__)


class BrowserControllerService(ServiceBase):
    """Service for browser automation: search, page opening, extraction, summarization.

    Orchestrates SearchEngine, PageInteractor, ContentExtractor, and PageSummarizer
    with full lifecycle management.
    """

    def __init__(self, config: Optional[BrowserConfig] = None):
        super().__init__(name="jarvis_browser", version="1.0.0")
        self.config = config or BrowserConfig()
        self._start_time = 0.0
        self._search_engine: Optional[SearchEngine] = None
        self._interactor: Optional[PageInteractor] = None
        self._extractor: Optional[ContentExtractor] = None
        self._summarizer: Optional[PageSummarizer] = None

    # ── Lifecycle ───────────────────────────────────────────────

    async def initialize(self) -> bool:
        """Initialize the browser controller service."""
        self._start_time = time.time()
        try:
            self._search_engine = SearchEngine(name=self.config.default_search_engine)
            self._interactor = PageInteractor(
                enable_history=self.config.enable_navigation_history,
                max_history=self.config.max_history,
            )
            self._extractor = ContentExtractor()
            self._summarizer = PageSummarizer()

            self._metrics.reset()
            self._initialized = True
            logger.info("BrowserControllerService initialized")
            return True
        except Exception as e:
            logger.error("BrowserControllerService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        """Shut down the browser controller service."""
        logger.info("BrowserControllerService shutting down...")
        self._initialized = False

    # ── Health / Stats ──────────────────────────────────────────

    async def health(self) -> Dict[str, Any]:
        """Return service health status."""
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service_name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
        }

    async def stats(self) -> Dict[str, Any]:
        """Return service statistics."""
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        history_count = len(self._interactor.get_history()) if self._interactor else 0
        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            "search_engine": self.config.default_search_engine,
            "history_size": history_count,
            "metrics": self._metrics.snapshot(),
        }

    # ── Browser Actions ─────────────────────────────────────────

    async def search(self, query: str, num_results: int = 5) -> BrowserActionResult:
        """Perform a web search.

        Args:
            query: Search query string.
            num_results: Maximum number of results.

        Returns:
            BrowserActionResult with action_type='search'.
        """
        start = time.perf_counter()

        if not self._initialized:
            return BrowserActionResult(
                success=False,
                action_type="search",
                error="Service not initialized",
            )

        if not query or not query.strip():
            return BrowserActionResult(
                success=False,
                action_type="search",
                error="Search query cannot be empty",
            )

        try:
            results = self._search_engine.search(query, num_results=num_results)
            self._metrics.counter("searches_performed")

            duration = (time.perf_counter() - start) * 1000
            return BrowserActionResult(
                success=True,
                action_type="search",
                title=f"Search results for: {query}",
                content_preview=str(results)[:500] if results else "No results found",
                summary=None,
                captcha_detected=False,
                duration_ms=round(duration, 2),
                metadata={
                    "query": query,
                    "num_results": len(results),
                    "results": results,
                },
            )
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            return BrowserActionResult(
                success=False,
                action_type="search",
                error=str(e),
                duration_ms=round(duration, 2),
            )

    async def open(self, url: str) -> BrowserActionResult:
        """Open a web page.

        Args:
            url: The URL to open.

        Returns:
            BrowserActionResult with action_type='open_page'.
        """
        start = time.perf_counter()

        if not self._initialized:
            return BrowserActionResult(
                success=False,
                action_type="open_page",
                error="Service not initialized",
            )

        if not url or not url.strip():
            return BrowserActionResult(
                success=False,
                action_type="open_page",
                error="URL cannot be empty",
            )

        try:
            result = self._interactor.open_page(url, user_agent=self.config.user_agent)
            self._metrics.counter("pages_opened")

            # Check for CAPTCHA
            if self.config.enable_captcha_detection and result.extracted_text:
                result.captcha_detected = self._extractor.detect_captcha(result.extracted_text)

            return result
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            return BrowserActionResult(
                success=False,
                action_type="open_page",
                error=str(e),
                duration_ms=round(duration, 2),
            )

    async def extract(self, url: Optional[str] = None) -> BrowserActionResult:
        """Extract text content from the current page or a specified URL.

        Args:
            url: Optional URL to open before extracting. If None, uses current page.

        Returns:
            BrowserActionResult with action_type='extract'.
        """
        start = time.perf_counter()

        if not self._initialized:
            return BrowserActionResult(
                success=False,
                action_type="extract",
                error="Service not initialized",
            )

        try:
            # Open the URL if provided
            if url:
                open_result = await self.open(url)
                if not open_result.success:
                    return BrowserActionResult(
                        success=False,
                        action_type="extract",
                        error=f"Failed to open URL: {open_result.error}",
                        duration_ms=(time.perf_counter() - start) * 1000,
                    )

            # Get the current page content
            current_url = self._interactor.current_url
            if not current_url:
                return BrowserActionResult(
                    success=False,
                    action_type="extract",
                    error="No page currently open",
                    duration_ms=(time.perf_counter() - start) * 1000,
                )

            # Re-open to get content (in real impl, would use cached content)
            page_result = self._interactor.open_page(current_url)
            if not page_result.success or not page_result.extracted_text:
                return BrowserActionResult(
                    success=False,
                    action_type="extract",
                    error="Failed to retrieve page content",
                    duration_ms=(time.perf_counter() - start) * 1000,
                )

            extracted = self._extractor.extract_text(page_result.extracted_text)
            links = self._extractor.extract_links(page_result.extracted_text)
            captcha = self._extractor.detect_captcha(page_result.extracted_text)

            self._metrics.counter("extractions_performed")
            duration = (time.perf_counter() - start) * 1000

            return BrowserActionResult(
                success=True,
                action_type="extract",
                url=current_url,
                title=page_result.title,
                content_preview=extracted[:500],
                extracted_text=extracted,
                summary=None,
                captcha_detected=captcha,
                duration_ms=round(duration, 2),
                metadata={"links_found": len(links)},
            )
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            return BrowserActionResult(
                success=False,
                action_type="extract",
                error=str(e),
                duration_ms=round(duration, 2),
            )

    async def summarize(self, url_or_text: Optional[str] = None, max_words: int = 200) -> BrowserActionResult:
        """Summarize a page or text.

        Args:
            url_or_text: URL to open and summarize, or raw text. If None, summarizes
                         the current page.
            max_words: Maximum number of words in the summary.

        Returns:
            BrowserActionResult with action_type='summarize'.
        """
        start = time.perf_counter()

        if not self._initialized:
            return BrowserActionResult(
                success=False,
                action_type="summarize",
                error="Service not initialized",
            )

        if not self.config.enable_summarization:
            return BrowserActionResult(
                success=False,
                action_type="summarize",
                error="Summarization is disabled in config",
            )

        try:
            text_to_summarize = None
            result_url = None
            result_title = None

            if url_or_text and (url_or_text.startswith("http://") or url_or_text.startswith("https://")):
                # Treat as URL
                extract_result = await self.extract(url_or_text)
                if extract_result.success and extract_result.extracted_text:
                    text_to_summarize = extract_result.extracted_text
                    result_url = extract_result.url
                    result_title = extract_result.title
            elif url_or_text:
                # Treat as raw text
                text_to_summarize = url_or_text
            else:
                # Use current page
                current_url = self._interactor.current_url
                if current_url:
                    page_result = self._interactor.open_page(current_url)
                    if page_result.extracted_text:
                        text_to_summarize = self._extractor.extract_text(page_result.extracted_text)
                        result_url = current_url
                        result_title = page_result.title

            if not text_to_summarize:
                return BrowserActionResult(
                    success=False,
                    action_type="summarize",
                    error="No content available to summarize",
                    duration_ms=(time.perf_counter() - start) * 1000,
                )

            summary = self._summarizer.summarize(text_to_summarize, max_words=max_words)

            self._metrics.counter("summarizations_performed")
            duration = (time.perf_counter() - start) * 1000

            return BrowserActionResult(
                success=True,
                action_type="summarize",
                url=result_url,
                title=result_title,
                content_preview=text_to_summarize[:500],
                summary=summary,
                duration_ms=round(duration, 2),
                metadata={"original_length": len(text_to_summarize), "summary_length": len(summary)},
            )
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            return BrowserActionResult(
                success=False,
                action_type="summarize",
                error=str(e),
                duration_ms=round(duration, 2),
            )

    async def back(self) -> BrowserActionResult:
        """Navigate to the previous page.

        Returns:
            BrowserActionResult with action_type='navigate'.
        """
        if not self._initialized:
            return BrowserActionResult(
                success=False,
                action_type="navigate",
                error="Service not initialized",
            )
        result = self._interactor.navigate_back()
        if result.success:
            self._metrics.counter("navigations_back")
        return result

    async def forward(self) -> BrowserActionResult:
        """Navigate to the next page.

        Returns:
            BrowserActionResult with action_type='navigate'.
        """
        if not self._initialized:
            return BrowserActionResult(
                success=False,
                action_type="navigate",
                error="Service not initialized",
            )
        result = self._interactor.navigate_forward()
        if result.success:
            self._metrics.counter("navigations_forward")
        return result

    async def history(self) -> List[str]:
        """Return the navigation history.

        Returns:
            List of URLs in navigation history.
        """
        if not self._initialized:
            return []
        return self._interactor.get_history()

    async def get_current_url(self) -> Optional[str]:
        """Return the currently active URL.

        Returns:
            Current URL string, or None if no page is open.
        """
        if not self._initialized:
            return None
        return self._interactor.current_url
