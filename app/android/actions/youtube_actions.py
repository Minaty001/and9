"""
AND9 — YouTube Actions (Phase 10 Rebuild).

Handles YouTube open, search, and play commands.
Priority: YOUTUBE_SEARCH > SEARCH.
NEVER routes to Chrome. ALWAYS uses YouTube app.

Supported commands:
    youtube kholo / youtube open karo
    youtube search <query> / search <query> on youtube
    youtube pe search karo / youtube par search karo
    youtube kholo aur search karo <query>
    youtube pe video search karo / youtube pe song search karo
    play <song> on youtube / <song> youtube pe bajao
    play song / play music / gaana chalao / song bajao
"""
import logging
from typing import Optional
from urllib.parse import quote_plus

from app.core.config import YOUTUBE_PACKAGE, YOUTUBE_COMPONENT

logger = logging.getLogger(__name__)

# YouTube Intent constants
_YOUTUBE_VIEW_ACTION = "android.intent.action.VIEW"
_YOUTUBE_SEARCH_BASE = "https://www.youtube.com/results?search_query="
_YOUTUBE_HOME_URL = "https://www.youtube.com/"


def execute_youtube_search(query: str = "", action: str = "search") -> dict:
    """Search or open YouTube. Never opens Chrome.

    Args:
        query:  Search query. Empty string = open YouTube home.
        action: "search", "play", or "open".

    Returns:
        Dict with response, action, payload targeting YouTube only.

    Examples:
        >>> execute_youtube_search("despacito")
        {'response': "YouTube pe 'despacito' search kar raha hoon 🔍▶️", ...}

        >>> execute_youtube_search("")
        {'response': 'YouTube khol raha hoon! ▶️', ...}
    """
    # ── Open YouTube home ─────────────────────────────────────────
    if not query or not query.strip():
        return _open_youtube_home()

    clean_query = query.strip()
    search_url = _YOUTUBE_SEARCH_BASE + quote_plus(clean_query)

    if action == "play":
        # Play intent: same URL but different response tone
        return {
            "response": f"YouTube pe '{clean_query}' baja raha hoon 🎵▶️",
            "action": "YOUTUBE_PLAY",
            "payload": {
                "action": _YOUTUBE_VIEW_ACTION,
                "package": YOUTUBE_PACKAGE,
                "component": YOUTUBE_COMPONENT,
                "data": search_url,
                "query": clean_query,
            },
        }

    return {
        "response": f"YouTube pe '{clean_query}' search kar raha hoon 🔍▶️",
        "action": "YOUTUBE_SEARCH",
        "payload": {
            "action": _YOUTUBE_VIEW_ACTION,
            "package": YOUTUBE_PACKAGE,
            "component": YOUTUBE_COMPONENT,
            "data": search_url,
            "query": clean_query,
        },
    }


def execute_youtube_play(query: str = "") -> dict:
    """Play a song or video on YouTube. Never opens Chrome.

    Cleans action words from the query, then searches YouTube.

    Args:
        query: Song/video name or raw search terms.

    Returns:
        Dict with response, action, payload targeting YouTube only.

    Examples:
        >>> execute_youtube_play("tum hi ho sunao")
        {'response': "YouTube pe 'tum hi ho' baja raha hoon 🎵▶️", ...}
    """
    if not query or not query.strip():
        return _open_youtube_home()

    # Clean media action words from query
    clean_query = _clean_media_query(query)
    if not clean_query:
        clean_query = query.strip()

    return execute_youtube_search(clean_query, action="play")


def _open_youtube_home() -> dict:
    """Open YouTube app home page."""
    return {
        "response": "YouTube khol raha hoon! ▶️",
        "action": "YOUTUBE_SEARCH",
        "payload": {
            "action": _YOUTUBE_VIEW_ACTION,
            "package": YOUTUBE_PACKAGE,
            "component": YOUTUBE_COMPONENT,
            "data": _YOUTUBE_HOME_URL,
        },
    }


def _clean_media_query(q: str) -> str:
    """Strip YouTube/media action words to get the actual search query.

    Examples:
        "tum hi ho sunao"   → "tum hi ho"
        "song bajao despacito" → "despacito"
        "play despacito on youtube" → "despacito"
    """
    import re
    noise_words = [
        r"\byoutube\b", r"\bpe\b", r"\bpar\b", r"\baur\b",
        r"\bsearch\b", r"\bkaro\b", r"\bplay\b", r"\bon\b",
        r"\bsunao\b", r"\bbajao\b", r"\bchalao\b", r"\blaga\b", r"\bdo\b",
        r"\bsong\b", r"\bgaana\b", r"\bgana\b", r"\bmusic\b",
        r"\bvideo\b", r"\bkholo\b", r"\bopen\b",
    ]
    result = q.lower().strip()
    for pattern in noise_words:
        result = re.sub(pattern, " ", result, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", result).strip()
