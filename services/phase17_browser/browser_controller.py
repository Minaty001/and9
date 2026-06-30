"""
Phase 17 — Browser Controller Core Logic.

Provides SearchEngine, PageInteractor, ContentExtractor, and PageSummarizer
for browser automation capabilities.
"""

import re
import time
from typing import Dict, List, Optional, Tuple
from .models import BrowserActionResult


# ── Mock search database ─────────────────────────────────────────────

MOCK_RESULTS: Dict[str, List[dict]] = {
    "jarvis": [
        {"title": "JARVIS AI Assistant", "url": "https://example.com/jarvis", "snippet": "JARVIS is an AI-powered personal assistant for Android devices."},
        {"title": "JARVIS GitHub Repository", "url": "https://github.com/jarvis-ai", "snippet": "Open source JARVIS implementation on GitHub."},
        {"title": "JARVIS Documentation", "url": "https://docs.jarvis.ai", "snippet": "Complete documentation for the JARVIS AI operating system."},
    ],
    "python tutorial": [
        {"title": "Python Official Tutorial", "url": "https://docs.python.org/3/tutorial/", "snippet": "The official Python 3 tutorial by the Python Software Foundation."},
        {"title": "Learn Python - Free Interactive Tutorial", "url": "https://learnpython.org", "snippet": "Learn Python programming with free interactive tutorials."},
        {"title": "Python for Beginners", "url": "https://pythonforbeginners.com", "snippet": "Python tutorials for absolute beginners covering basics to advanced."},
    ],
    "weather": [
        {"title": "Weather.com", "url": "https://weather.com", "snippet": "Get the latest weather forecasts and conditions."},
        {"title": "AccuWeather", "url": "https://accuweather.com", "snippet": "Accurate weather forecasts for your location."},
        {"title": "OpenWeather API", "url": "https://openweathermap.org", "snippet": "Free weather API with current conditions and forecasts."},
    ],
}


# ── CAPTCHA indicators ───────────────────────────────────────────────

CAPTCHA_INDICATORS = [
    "captcha",
    "recaptcha",
    "i'm not a robot",
    "i am not a robot",
    "verify you are human",
    "are you human",
    "captcha verification",
    "captcha required",
    "security check",
    "bot detection",
    "challenge-response",
    "g-recaptcha",
    "hcaptcha",
    "turnstile",
    "cf-turnstile",
]


class SearchEngine:
    """Simulated search engine with custom result injection for testing."""

    def __init__(self, name: str = "google"):
        self.name = name
        self._custom_results: Dict[str, List[dict]] = {}

    def search(self, query: str, num_results: int = 5) -> List[dict]:
        """Search for a query and return a list of result dicts.

        Args:
            query: Search query string.
            num_results: Maximum number of results to return.

        Returns:
            List of dicts with 'title', 'url', 'snippet' keys.
        """
        query_lower = query.strip().lower()

        # Check custom results first
        if query_lower in self._custom_results:
            results = self._custom_results[query_lower]
        else:
            results = MOCK_RESULTS.get(query_lower, [])

        # Check partial matches in mock DB
        if not results:
            for key, mock_list in MOCK_RESULTS.items():
                if key in query_lower or query_lower in key:
                    results = mock_list
                    break

        return results[:num_results]

    def set_custom_result(self, query: str, results: List[dict]) -> None:
        """Inject custom search results for a given query (useful for testing).

        Args:
            query: The search query to associate results with.
            results: List of result dicts with 'title', 'url', 'snippet'.
        """
        self._custom_results[query.strip().lower()] = results

    def clear_custom_results(self) -> None:
        """Remove all custom injected results."""
        self._custom_results.clear()


class PageInteractor:
    """Simulated page interaction with history management."""

    def __init__(self, enable_history: bool = True, max_history: int = 100):
        self.enable_history = enable_history
        self.max_history = max_history
        self._history: List[str] = []
        self._current_index: int = -1

    def open_page(self, url: str, user_agent: str = "Mozilla/5.0 JARVIS") -> BrowserActionResult:
        """Simulate opening a web page.

        Args:
            url: The URL to open.
            user_agent: User agent string to use.

        Returns:
            BrowserActionResult with action_type='open_page'.
        """
        start = time.perf_counter()

        if not url or not url.strip():
            return BrowserActionResult(
                success=False,
                action_type="open_page",
                error="URL cannot be empty",
                duration_ms=(time.perf_counter() - start) * 1000,
            )

        url = url.strip()

        # Simulate page opening
        title = self._infer_title(url)
        content = self._simulate_page_content(url)

        # Track in history
        if self.enable_history:
            if self._current_index < len(self._history) - 1:
                # We navigated back, so truncate forward history
                self._history = self._history[: self._current_index + 1]
            self._history.append(url)
            if len(self._history) > self.max_history:
                self._history = self._history[-self.max_history :]
            self._current_index = len(self._history) - 1

        duration = (time.perf_counter() - start) * 1000
        return BrowserActionResult(
            success=True,
            action_type="open_page",
            url=url,
            title=title,
            content_preview=content[:500],
            extracted_text=content,
            duration_ms=round(duration, 2),
        )

    def navigate_back(self) -> BrowserActionResult:
        """Navigate to the previous page in history.

        Returns:
            BrowserActionResult with action_type='navigate'.
        """
        start = time.perf_counter()

        if not self.enable_history or self._current_index < 0 or len(self._history) == 0:
            return BrowserActionResult(
                success=False,
                action_type="navigate",
                error="No previous page in history",
                duration_ms=(time.perf_counter() - start) * 1000,
            )

        self._current_index -= 1
        url = self._history[self._current_index]
        title = self._infer_title(url)

        duration = (time.perf_counter() - start) * 1000
        return BrowserActionResult(
            success=True,
            action_type="navigate",
            url=url,
            title=title,
            duration_ms=round(duration, 2),
        )

    def navigate_forward(self) -> BrowserActionResult:
        """Navigate to the next page in history.

        Returns:
            BrowserActionResult with action_type='navigate'.
        """
        start = time.perf_counter()

        if not self.enable_history or self._current_index >= len(self._history) - 1:
            return BrowserActionResult(
                success=False,
                action_type="navigate",
                error="No next page in history",
                duration_ms=(time.perf_counter() - start) * 1000,
            )

        self._current_index += 1
        url = self._history[self._current_index]
        title = self._infer_title(url)

        duration = (time.perf_counter() - start) * 1000
        return BrowserActionResult(
            success=True,
            action_type="navigate",
            url=url,
            title=title,
            duration_ms=round(duration, 2),
        )

    def get_history(self) -> List[str]:
        """Return the full navigation history."""
        return list(self._history)

    def clear_history(self) -> None:
        """Clear navigation history and reset current position."""
        self._history.clear()
        self._current_index = -1

    @property
    def current_url(self) -> Optional[str]:
        """Return the current URL based on navigation position."""
        if 0 <= self._current_index < len(self._history):
            return self._history[self._current_index]
        return None

    def _infer_title(self, url: str) -> str:
        """Infer a page title from a URL."""
        # Remove protocol
        clean = re.sub(r"^https?://", "", url)
        clean = clean.rstrip("/")
        # Use domain/path as title
        if "/" in clean:
            parts = clean.split("/", 1)
            domain = parts[0]
            path = parts[1].replace("/", " - ").replace("-", " ").replace("_", " ")
            return f"{domain} - {path.title()}"
        return f"{clean} - Home"

    def _simulate_page_content(self, url: str) -> str:
        """Simulate page content for a given URL."""
        url_lower = url.lower()

        if "example.com" in url_lower:
            return (
                "<html><body><h1>Welcome to Example</h1>"
                "<p>This is an example page for demonstration purposes.</p>"
                "<p>JARVIS AI can browse the web to find information.</p>"
                "<a href='https://example.com/page1'>Page 1</a>"
                "<a href='https://example.com/page2'>Page 2</a>"
                "</body></html>"
            )
        elif "captcha" in url_lower or "verify" in url_lower:
            return (
                "<html><body><h1>Security Check</h1>"
                "<p>Please verify you are human.</p>"
                "<div class='g-recaptcha' data-sitekey='abc123'></div>"
                "<p>Complete the CAPTCHA verification to proceed.</p>"
                "</body></html>"
            )
        else:
            return (
                "<html><body><h1>Page Content</h1>"
                "<p>This is simulated content for: " + url + "</p>"
                "<p>JARVIS is an AI-powered personal assistant.</p>"
                "<p>It can search and extract information from web pages.</p>"
                "<a href='https://example.com/link1'>Link 1</a>"
                "<a href='https://example.com/link2'>Link 2</a>"
                "</body></html>"
            )


class ContentExtractor:
    """HTML content extraction utilities."""

    @staticmethod
    def extract_text(html_or_text: str) -> str:
        """Strip HTML tags and extract clean text content.

        Args:
            html_or_text: Raw HTML or plain text.

        Returns:
            Clean text with HTML tags removed, whitespace normalized.
        """
        if not html_or_text:
            return ""

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", html_or_text)
        # Decode common HTML entities
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&quot;", "\"")
        text = text.replace("&#39;", "'")
        text = text.replace("&nbsp;", " ")
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @staticmethod
    def extract_links(html_or_text: str) -> List[str]:
        """Extract all href links from HTML content.

        Args:
            html_or_text: HTML content to scan.

        Returns:
            List of URL strings found in href attributes.
        """
        if not html_or_text:
            return []

        links = re.findall(r'href=["\'](https?://[^"\']+)["\']', html_or_text, re.IGNORECASE)
        # Also match relative links starting with /
        relative = re.findall(r'href=["\'](/[^"\']+)["\']', html_or_text, re.IGNORECASE)
        links.extend(relative)
        return links

    @staticmethod
    def detect_captcha(content: str) -> bool:
        """Detect whether the given content contains CAPTCHA challenges.

        Checks for known CAPTCHA indicators in the content (case-insensitive).

        Args:
            content: Page content (HTML or text) to scan.

        Returns:
            True if CAPTCHA indicators are found, False otherwise.
        """
        if not content:
            return False

        content_lower = content.lower()
        for indicator in CAPTCHA_INDICATORS:
            if indicator in content_lower:
                return True
        return False


class PageSummarizer:
    """Simple extractive text summarizer."""

    @staticmethod
    def summarize(text: str, max_words: int = 200) -> str:
        """Generate a simple extractive summary of the given text.

        Uses sentence extraction: picks first meaningful sentences
        up to the max_words limit.

        Args:
            text: Input text to summarize.
            max_words: Maximum number of words in the summary.

        Returns:
            Summarized text.
        """
        if not text or not text.strip():
            return ""

        # Clean text
        text = text.strip()

        # Split into sentences (simple approach)
        sentences = re.split(r"(?<=[.!?])\s+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return text[:max_words * 10]  # fallback

        # Extractive summarization: take first sentences up to max_words
        summary_words: List[str] = []
        for sentence in sentences:
            sentence_words = sentence.split()
            if len(summary_words) + len(sentence_words) <= max_words:
                summary_words.extend(sentence_words)
                if sentence.endswith((".", "!", "?")):
                    summary_words[-1] = summary_words[-1]  # keep punctuation
            else:
                # Add as many words as we can
                remaining = max_words - len(summary_words)
                if remaining > 0:
                    summary_words.extend(sentence_words[:remaining])
                break

        summary = " ".join(summary_words)

        # Ensure summary ends with proper punctuation
        if summary and not summary[-1] in ".!?":
            summary += "."

        return summary

    @staticmethod
    def extract_keywords(text: str, max_keywords: int = 5) -> List[str]:
        """Extract key terms from text using simple frequency analysis.

        Args:
            text: Input text.
            max_keywords: Maximum number of keywords to return.

        Returns:
            List of most frequent meaningful words.
        """
        if not text or not text.strip():
            return []

        # Lowercase and split
        words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())

        # Common stop words to filter
        stop_words = {
            "the", "and", "for", "are", "but", "not", "you", "all", "can",
            "had", "her", "was", "one", "our", "out", "has", "have", "been",
            "its", "that", "this", "with", "from", "they", "what", "when",
            "where", "which", "will", "would", "could", "should", "about",
            "into", "over", "than", "them", "then", "these", "their", "your",
            "also", "how", "just", "more", "some", "than", "very", "were",
        }

        # Count frequencies
        freq = {}
        for word in words:
            if word not in stop_words:
                freq[word] = freq.get(word, 0) + 1

        # Sort by frequency descending
        sorted_words = sorted(freq.items(), key=lambda x: (-x[1], x[0]))
        return [word for word, _ in sorted_words[:max_keywords]]
