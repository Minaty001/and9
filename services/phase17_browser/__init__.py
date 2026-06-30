"""
Phase 17 — Browser Controller
==============================

Browser automation capabilities: search, page opening, content
extraction, summarization, and navigation history management
with CAPTCHA detection.

Components:
    - SearchEngine: Simulated web search with custom result injection
    - PageInteractor: Page opening, back/forward navigation, history
    - ContentExtractor: HTML tag stripping, link extraction, CAPTCHA detection
    - PageSummarizer: Extractive text summarization
    - BrowserControllerService: Service wrapper with full lifecycle
"""

from .service import BrowserControllerService
from .config import BrowserConfig
from .models import BrowserActionResult
from .browser_controller import SearchEngine, PageInteractor, ContentExtractor, PageSummarizer

__all__ = [
    "BrowserControllerService",
    "BrowserConfig",
    "BrowserActionResult",
    "SearchEngine",
    "PageInteractor",
    "ContentExtractor",
    "PageSummarizer",
]
