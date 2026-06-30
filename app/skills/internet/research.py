"""
app/skills/research.py — Research tool functions (web fetching, summarization).

LLM-free: uses DuckDuckGo for search, extractive text for summarization.
"""
import re
import logging
import requests

logger = logging.getLogger(__name__)

_http = requests.Session()
_http.headers.update({"User-Agent": "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36"})


def search_sources(query: str, num: int = 5) -> list:
    """Search web using DuckDuckGo and return list of {title, link, snippet}."""
    try:
        from app.integrations.duckduckgo import search_sources as ddg_sources
        return ddg_sources(query, num=num)
    except Exception as e:
        logger.warning(f"DuckDuckGo search failed: {e}")
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
            soup = BeautifulSoup(resp.text, "html.parser")
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
    """Extractively summarize web page content (no LLM).

    Returns the first portion of the text that contains query-relevant keywords.
    Falls back to first 400 chars.
    """
    if not content:
        return ""
    # Try to find sentences containing query keywords
    keywords = re.findall(r'\w+', query.lower())
    sentences = re.split(r'(?<=[.!?])\s+', content)
    relevant = []
    for s in sentences:
        s_lower = s.lower()
        if any(kw in s_lower for kw in keywords if len(kw) > 3):
            relevant.append(s.strip())
        if len(relevant) >= 5:
            break
    if relevant:
        return " | ".join(relevant)[:600]
    return content[:400]


def synthesize_answer(query: str, sources_data: list) -> str:
    """Synthesize a final answer from multiple sources using extractive summaries.

    Returns concatenated source excerpts with inline source numbering.
    No LLM involved.
    """
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
    source_lines = "\n".join([f"  [{s['num']}] {s['title']} — {s['url']}" for s in sources])
    return f"Research findings for: {query}\n\n{combined}\n\nSources:\n{source_lines}"
