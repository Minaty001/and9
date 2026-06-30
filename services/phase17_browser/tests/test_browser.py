"""
Tests for Phase 17 — Browser Controller.

Covers SearchEngine, PageInteractor, ContentExtractor, PageSummarizer,
and BrowserControllerService with 20+ tests.
"""

import pytest
from services.phase17_browser import (
    BrowserControllerService,
    BrowserConfig,
    BrowserActionResult,
    SearchEngine,
    PageInteractor,
    ContentExtractor,
    PageSummarizer,
)


# ── SearchEngine ─────────────────────────────────────────────────────


class TestSearchEngine:
    """Verify the simulated search engine."""

    def test_search_with_results(self):
        engine = SearchEngine()
        results = engine.search("jarvis")
        assert len(results) >= 1
        assert results[0]["title"] == "JARVIS AI Assistant"
        assert results[0]["url"] == "https://example.com/jarvis"

    def test_search_empty_results(self):
        engine = SearchEngine()
        results = engine.search("xyznonexistent12345")
        assert results == []

    def test_search_custom_results(self):
        engine = SearchEngine()
        custom = [
            {"title": "Custom Result", "url": "https://custom.example.com", "snippet": "Custom snippet"},
        ]
        engine.set_custom_result("custom query", custom)
        results = engine.search("custom query")
        assert len(results) == 1
        assert results[0]["title"] == "Custom Result"

    def test_search_respects_num_results(self):
        engine = SearchEngine()
        results = engine.search("jarvis", num_results=2)
        assert len(results) == 2

    def test_search_case_insensitive(self):
        engine = SearchEngine()
        results = engine.search("JARVIS")
        assert len(results) >= 1

    def test_search_partial_match(self):
        engine = SearchEngine()
        results = engine.search("python")
        assert len(results) >= 1
        assert "python" in results[0]["title"].lower()

    def test_clear_custom_results(self):
        engine = SearchEngine()
        engine.set_custom_result("test", [{"title": "T", "url": "https://t.com", "snippet": "t"}])
        engine.clear_custom_results()
        results = engine.search("test")
        assert results == []


# ── PageInteractor ───────────────────────────────────────────────────


class TestPageInteractor:
    """Verify page interaction and navigation."""

    async def test_open_page_success(self):
        interactor = PageInteractor()
        result = interactor.open_page("https://example.com")
        assert result.success is True
        assert result.action_type == "open_page"
        assert result.url == "https://example.com"
        assert result.title is not None

    async def test_open_page_empty_url(self):
        interactor = PageInteractor()
        result = interactor.open_page("")
        assert result.success is False
        assert "empty" in result.error.lower()

    async def test_navigate_back(self):
        interactor = PageInteractor()
        interactor.open_page("https://example.com/page1")
        interactor.open_page("https://example.com/page2")
        result = interactor.navigate_back()
        assert result.success is True
        assert result.url == "https://example.com/page1"

    async def test_navigate_back_no_history(self):
        interactor = PageInteractor()
        result = interactor.navigate_back()
        assert result.success is False

    async def test_navigate_forward(self):
        interactor = PageInteractor()
        interactor.open_page("https://example.com/page1")
        interactor.open_page("https://example.com/page2")
        interactor.navigate_back()
        result = interactor.navigate_forward()
        assert result.success is True
        assert result.url == "https://example.com/page2"

    async def test_navigate_forward_no_future(self):
        interactor = PageInteractor()
        interactor.open_page("https://example.com")
        result = interactor.navigate_forward()
        assert result.success is False

    async def test_history_tracking(self):
        interactor = PageInteractor()
        interactor.open_page("https://example.com/a")
        interactor.open_page("https://example.com/b")
        history = interactor.get_history()
        assert len(history) == 2
        assert history[0] == "https://example.com/a"
        assert history[1] == "https://example.com/b"

    async def test_clear_history(self):
        interactor = PageInteractor()
        interactor.open_page("https://example.com")
        interactor.clear_history()
        assert interactor.get_history() == []
        assert interactor.current_url is None

    async def test_current_url(self):
        interactor = PageInteractor()
        assert interactor.current_url is None
        interactor.open_page("https://example.com")
        assert interactor.current_url == "https://example.com"
        interactor.navigate_back()
        assert interactor.current_url is None

    async def test_back_truncates_forward_history(self):
        interactor = PageInteractor()
        interactor.open_page("https://example.com/a")
        interactor.open_page("https://example.com/b")
        interactor.open_page("https://example.com/c")
        interactor.navigate_back()  # now at b
        interactor.open_page("https://example.com/d")  # should truncate c
        assert interactor.current_url == "https://example.com/d"
        # forward should only go to d
        result = interactor.navigate_forward()
        assert result.success is False  # no forward after d


# ── ContentExtractor ─────────────────────────────────────────────────


class TestContentExtractor:
    """Verify text extraction, link extraction, and CAPTCHA detection."""

    def test_extract_text_strips_html(self):
        html = "<html><body><h1>Title</h1><p>Paragraph text.</p></body></html>"
        text = ContentExtractor.extract_text(html)
        assert "Title" in text
        assert "Paragraph text" in text
        assert "<" not in text

    def test_extract_text_plain_text(self):
        text = ContentExtractor.extract_text("Just plain text, no HTML.")
        assert text == "Just plain text, no HTML."

    def test_extract_text_empty(self):
        assert ContentExtractor.extract_text("") == ""
        assert ContentExtractor.extract_text(None) == ""

    def test_extract_text_normalizes_whitespace(self):
        html = "<p>  Lots   of   spaces  </p>"
        text = ContentExtractor.extract_text(html)
        assert text == "Lots of spaces"

    def test_extract_links(self):
        html = '<a href="https://example.com/page1">Link 1</a><a href="https://example.com/page2">Link 2</a>'
        links = ContentExtractor.extract_links(html)
        assert len(links) == 2
        assert "https://example.com/page1" in links

    def test_extract_links_empty(self):
        assert ContentExtractor.extract_links("") == []
        assert ContentExtractor.extract_links(None) == []

    def test_extract_links_no_href(self):
        html = "<p>No links here</p>"
        assert ContentExtractor.extract_links(html) == []

    def test_detect_captcha_positive(self):
        content = "Please complete the reCAPTCHA to verify you are human."
        assert ContentExtractor.detect_captcha(content) is True

    def test_detect_captcha_negative(self):
        content = "Welcome to the homepage. Enjoy your visit!"
        assert ContentExtractor.detect_captcha(content) is False

    def test_detect_captcha_empty(self):
        assert ContentExtractor.detect_captcha("") is False
        assert ContentExtractor.detect_captcha(None) is False

    def test_detect_captcha_via_html(self):
        html = '<div class="g-recaptcha" data-sitekey="abc"></div>'
        assert ContentExtractor.detect_captcha(html) is True


# ── PageSummarizer ───────────────────────────────────────────────────


class TestPageSummarizer:
    """Verify the extractive summarizer."""

    def test_summarize_short_text(self):
        text = "JARVIS is an AI assistant. It runs on Android devices. It works offline."
        summary = PageSummarizer.summarize(text, max_words=50)
        assert len(summary) > 0
        assert "JARVIS" in summary

    def test_summarize_long_text(self):
        sentences = " ".join(["This is sentence number " + str(i) + "." for i in range(100)])
        summary = PageSummarizer.summarize(sentences, max_words=20)
        word_count = len(summary.split())
        assert word_count <= 25  # allow small margin
        assert word_count > 0

    def test_summarize_empty_text(self):
        assert PageSummarizer.summarize("") == ""
        assert PageSummarizer.summarize("   ") == ""
        assert PageSummarizer.summarize(None) == ""

    def test_summarize_respects_max_words(self):
        text = "One. Two. Three. Four. Five. Six. Seven. Eight. Nine. Ten."
        summary = PageSummarizer.summarize(text, max_words=3)
        assert len(summary.split()) <= 5  # allow punctuation

    def test_extract_keywords(self):
        text = "JARVIS is an AI assistant for Android devices. JARVIS runs locally on Android."
        keywords = PageSummarizer.extract_keywords(text)
        assert len(keywords) >= 1
        assert "jarvis" in keywords

    def test_extract_keywords_empty(self):
        assert PageSummarizer.extract_keywords("") == []


# ── BrowserControllerService ─────────────────────────────────────────


class TestBrowserControllerService:
    """Verify the service wrapper lifecycle and browser actions."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        svc = BrowserControllerService()
        result = await svc.initialize()
        assert result is True
        assert svc.is_initialized() is True

    @pytest.mark.asyncio
    async def test_health_uninitialized(self):
        svc = BrowserControllerService()
        health = await svc.health()
        assert health["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_health_healthy(self):
        svc = BrowserControllerService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"
        assert health["service_name"] == "jarvis_browser"

    @pytest.mark.asyncio
    async def test_stats(self):
        svc = BrowserControllerService()
        await svc.initialize()
        stats = await svc.stats()
        assert stats["service"] == "jarvis_browser"
        assert "metrics" in stats
        assert "history_size" in stats

    @pytest.mark.asyncio
    async def test_search(self):
        svc = BrowserControllerService()
        await svc.initialize()
        result = await svc.search("jarvis")
        assert result.success is True
        assert result.action_type == "search"
        assert len(result.metadata.get("results", [])) >= 1

    @pytest.mark.asyncio
    async def test_search_empty_query(self):
        svc = BrowserControllerService()
        await svc.initialize()
        result = await svc.search("")
        assert result.success is False
        assert "empty" in result.error.lower()

    @pytest.mark.asyncio
    async def test_open_page(self):
        svc = BrowserControllerService()
        await svc.initialize()
        result = await svc.open("https://example.com")
        assert result.success is True
        assert result.action_type == "open_page"
        assert result.url == "https://example.com"

    @pytest.mark.asyncio
    async def test_open_page_empty_url(self):
        svc = BrowserControllerService()
        await svc.initialize()
        result = await svc.open("")
        assert result.success is False

    @pytest.mark.asyncio
    async def test_extract(self):
        svc = BrowserControllerService()
        await svc.initialize()
        result = await svc.extract("https://example.com")
        assert result.success is True
        assert result.action_type == "extract"
        assert result.extracted_text is not None

    @pytest.mark.asyncio
    async def test_summarize_from_text(self):
        svc = BrowserControllerService()
        await svc.initialize()
        result = await svc.summarize("JARVIS is an AI assistant. It works offline. It is very useful.")
        assert result.success is True
        assert result.action_type == "summarize"
        assert result.summary is not None

    @pytest.mark.asyncio
    async def test_navigation_back_and_forward(self):
        svc = BrowserControllerService()
        await svc.initialize()
        await svc.open("https://example.com/page1")
        await svc.open("https://example.com/page2")
        back = await svc.back()
        assert back.success is True
        assert back.url == "https://example.com/page1"
        fwd = await svc.forward()
        assert fwd.success is True
        assert fwd.url == "https://example.com/page2"

    @pytest.mark.asyncio
    async def test_history(self):
        svc = BrowserControllerService()
        await svc.initialize()
        await svc.open("https://example.com/a")
        await svc.open("https://example.com/b")
        history = await svc.history()
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_get_current_url(self):
        svc = BrowserControllerService()
        await svc.initialize()
        assert await svc.get_current_url() is None
        await svc.open("https://example.com")
        assert await svc.get_current_url() == "https://example.com"

    @pytest.mark.asyncio
    async def test_shutdown(self):
        svc = BrowserControllerService()
        await svc.initialize()
        await svc.shutdown()
        assert svc.is_initialized() is False

    @pytest.mark.asyncio
    async def test_search_uninitialized(self):
        svc = BrowserControllerService()
        result = await svc.search("test")
        assert result.success is False
        assert "not initialized" in result.error.lower()

    @pytest.mark.asyncio
    async def test_full_flow(self):
        """Test a complete browser flow: search -> open -> extract -> summarize -> navigate."""
        svc = BrowserControllerService()
        await svc.initialize()

        # Search
        search_result = await svc.search("jarvis")
        assert search_result.success is True

        # Open a page
        open_result = await svc.open("https://example.com/jarvis")
        assert open_result.success is True

        # Extract
        extract_result = await svc.extract()
        assert extract_result.success is True
        assert extract_result.extracted_text is not None

        # Summarize
        summarize_result = await svc.summarize(max_words=50)
        assert summarize_result.success is True

        # Health check
        health = await svc.health()
        assert health["status"] == "healthy"

        # Shutdown
        await svc.shutdown()
        assert svc.is_initialized() is False
