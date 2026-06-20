"""
app/skills/research.py — Research tool functions (web fetching, summarization).

These are used by ResearchAgent but are callable independently as tools.
"""
import re
import logging
import requests

from app.core.config import SERP_API_KEY
from app.core.brain import ask_llm

logger = logging.getLogger(__name__)

_http = requests.Session()
_http.headers.update({"User-Agent": "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36"})


def search_sources(query: str, num: int = 5) -> list:
    """Search web and return list of {title, link, snippet}."""
    if not SERP_API_KEY:
        logger.warning("SERP_API_KEY not set")
        return []
    try:
        resp = _http.get(
            "https://serpapi.com/search",
            params={"q": query, "api_key": SERP_API_KEY, "num": num},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            return [
                {"title": item.get("title", ""), "link": item.get("link", ""), "snippet": item.get("snippet", "")}
                for item in data.get("organic_results", [])
            ]
    except Exception as e:
        logger.warning(f"Search failed: {e}")
    return []


def fetch_page(url: str, max_chars: int = 4000) -> str:
    """Fetch and clean web page text."""
    if not url or not url.startswith("http"):
        return ""
    try:
        resp = _http.get(url, timeout=8)
        if resp.status_code != 200:
            return ""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "lxml")
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            text = soup.get_text(separator=" ", strip=True)
        except ImportError:
            text = re.sub(r"<[^>]+>", " ", resp.text)
        return re.sub(r"\s+", " ", text).strip()[:max_chars]
    except Exception as e:
        logger.warning(f"Fetch failed: {url[:50]}... {e}")
        return ""


def summarize_source(content: str, query: str, source_num: int = 1) -> str:
    """Summarize web page content for research synthesis."""
    try:
        summary = ask_llm(
            [{"role": "user", "content": f"Topic: {query}\n\nContent to summarize:\n{content[:3000]}"}],
            system="Summarize this web page content in 3-5 sentences relevant to the research topic.",
            max_tokens=300,
            temperature=0.1,
        )
        if summary and not summary.startswith("["):
            return summary
    except Exception:
        pass
    return content[:400]


def synthesize_answer(query: str, sources_data: list) -> str:
    """Synthesize a final answer from multiple sources."""
    summaries = []
    sources = []
    for i, item in enumerate(sources_data[:4], 1):
        url = item.get("link", "")
        title = item.get("title", f"Source {i}")
        content = fetch_page(url)
        if content:
            summary = summarize_source(content, query, source_num=i)
            summaries.append(f"[Source {i}] {title}:\n{summary}")
            sources.append({"num": i, "title": title, "url": url})

    if not summaries:
        return "Could not retrieve content from any sources."

    combined = "\n\n".join(summaries)
    final = ask_llm(
        [{"role": "user", "content": f"Research question: {query}\n\nSource summaries:\n{combined}\n\nProvide a comprehensive answer with citations."}],
        system="You are a research analyst. Synthesize sources into a clear, factual answer with inline citations.",
        max_tokens=4096,
    )
    source_lines = "\n".join([f"  [{s['num']}] {s['title']} — {s['url']}" for s in sources])
    return f"{final}\n\nSources:\n{source_lines}"
