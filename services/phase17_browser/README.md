# Phase 17 — Browser Controller

Browser automation capabilities for the JARVIS AI operating system.

## Components

### SearchEngine
Simulated web search engine with:
- Predefined mock results for common queries (`jarvis`, `python tutorial`, `weather`)
- Custom result injection for testing
- Case-insensitive and partial matching
- Configurable result count

### PageInteractor
Page interaction and navigation management:
- `open_page(url)` — Simulate opening a URL with content generation
- `navigate_back()` / `navigate_forward()` — History-based navigation
- `get_history()` / `clear_history()` — History tracking
- `current_url` property — Current page position
- Forward history truncation on new navigation after going back

### ContentExtractor
HTML content processing utilities:
- `extract_text(html)` — Strip HTML tags, decode entities, normalize whitespace
- `extract_links(html)` — Extract all `href` URLs (absolute and relative)
- `detect_captcha(content)` — Detect CAPTCHA challenges using known indicators (reCAPTCHA, hCaptcha, Turnstile, etc.)

### PageSummarizer
Simple extractive text summarization:
- `summarize(text, max_words)` — Extract first sentences up to word limit
- `extract_keywords(text)` — Frequency-based keyword extraction with stop word filtering

### BrowserControllerService
Service wrapper with full lifecycle management:
- `search(query)` — Search the web
- `open(url)` — Open a web page
- `extract(url)` — Extract text content from a page
- `summarize(url_or_text)` — Summarize content
- `back()` / `forward()` / `history()` / `get_current_url()` — Navigation

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `service_name` | `jarvis_browser` | Service name |
| `default_search_engine` | `google` | Default search engine |
| `enable_captcha_detection` | `True` | Enable CAPTCHA detection |
| `max_page_size_chars` | `50000` | Max page size to process |
| `extract_timeout_ms` | `10000` | Extraction timeout |
| `enable_summarization` | `True` | Enable page summarization |
| `user_agent` | `Mozilla/5.0 JARVIS` | User agent string |
| `enable_navigation_history` | `True` | Enable history tracking |
| `max_history` | `100` | Max history entries |

## Usage

```python
from services.phase17_browser import BrowserControllerService, BrowserConfig

config = BrowserConfig()
service = BrowserControllerService(config)
await service.initialize()

# Search
result = await service.search("jarvis")

# Open a page
result = await service.open("https://example.com")

# Extract text
result = await service.extract()

# Summarize
result = await service.summarize(max_words=100)

# Navigate
await service.back()
await service.forward()

# Shutdown
await service.shutdown()
```

## Testing

```bash
cd /root/github/and9 && python -m pytest services/phase17_browser/tests/ -v
```

20+ tests covering all components and the full service lifecycle.
