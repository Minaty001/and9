# Phase 17: Browser Controller

## Purpose
Browser automation capabilities including simulated web search (`SearchEngine`), page navigation with history (`PageInteractor`), HTML content extraction and CAPTCHA detection (`ContentExtractor`), and extractive text summarization (`PageSummarizer`). Provides a unified `BrowserControllerService` for search, open, extract, summarize, and navigation operations.

## Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `JARVIS_BROWSER_DEFAULT_SEARCH_ENGINE` | `google` | Default search engine |
| `JARVIS_BROWSER_ENABLE_CAPTCHA_DETECTION` | true | Enable CAPTCHA detection |
| `JARVIS_BROWSER_MAX_PAGE_SIZE_CHARS` | 50000 | Max page size |
| `JARVIS_BROWSER_EXTRACT_TIMEOUT_MS` | 10000 | Extraction timeout |
| `JARVIS_BROWSER_ENABLE_SUMMARIZATION` | true | Enable summarization |

## Architecture
```
BrowserControllerService
  ├── SearchEngine       — Mock search with custom result injection
  ├── PageInteractor     — open_page/navigate_back/forward/history
  ├── ContentExtractor   — extract_text(html)/extract_links/detect_captcha
  └── PageSummarizer     — summarize(text, max_words)/extract_keywords
```

## Code
```python
class SearchEngine:
    def search(self, query, max_results=10) -> List[dict]:
        query_lower = query.lower()
        results = copy.deepcopy(self._custom_results or MOCK_RESULTS.get(...))
        return [r for r in results if query_lower in r["title"].lower()
                or query_lower in r["snippet"].lower()][:max_results]

class ContentExtractor:
    @staticmethod
    def extract_text(html: str) -> str:
        text = re.sub(r'<[^>]+>', ' ', html)
        text = html.unescape(text)
        return re.sub(r'\s+', ' ', text).strip()

    @staticmethod
    def detect_captcha(content: str) -> bool:
        return any(indicator in content.lower() for indicator in CAPTCHA_INDICATORS)
```

## Location
`app/services/browser/` — browser automation service
