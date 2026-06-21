"""
AND9 — YouTube Actions (Phase 7 of Refactor).

Handles YouTube search, play, and open commands.
Always sends intents to the YouTube app — NEVER to Chrome.

Supports:
    youtube kholo                   → open YouTube app
    search cooking on youtube       → YouTube search
    play song despacito             → YouTube play/search
    gaana chalao                     → song search
"""
import logging
from typing import Optional

from app.and9.core.config import YOUTUBE_PACKAGE

logger = logging.getLogger(__name__)


def execute_youtube_search(query: str = "") -> dict:
    """Search YouTube for a query.

    If query is empty, just opens the YouTube app.

    Args:
        query: Search terms.

    Returns:
        Dict with response, action, payload.
        Payload always targets YouTube package — never Chrome.
    """
    if not query or query.strip() == "":
        return {
            "response": "YouTube khol raha hoon! ▶️",
            "action": "YOUTUBE_SEARCH",
            "payload": {
                "action": "android.intent.action.VIEW",
                "package": YOUTUBE_PACKAGE,
                "data": "https://www.youtube.com/",
            },
        }

    search_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
    return {
        "response": f"YouTube pe '{query}' search kar raha hoon 🔍▶️",
        "action": "YOUTUBE_SEARCH",
        "payload": {
            "action": "android.intent.action.VIEW",
            "package": YOUTUBE_PACKAGE,
            "data": search_url,
        },
    }


def execute_youtube_play(query: str = "") -> dict:
    """Play/search music or video on YouTube.

    First tries the JARVIS music handler for rich playback.
    Falls back to YouTube search.

    Args:
        query: Song/video name or search terms.

    Returns:
        Dict with response, action, payload.
    """
    if not query or query.strip() == "":
        return execute_youtube_search("trending music")

    # Clean query: remove action words
    play_query = query.lower()
    for word in ["play", "song", "music", "bajao", "sunao", "chalao"]:
        play_query = play_query.replace(word, " ").strip()
    if not play_query:
        play_query = query.strip()

    # Try JARVIS music handler first
    try:
        from app.skills.youtube import handle_music_request
        result = handle_music_request(play_query)
        if result and "response" in result:
            return {
                "response": f"Baja raha hoon '{play_query}' 🎵",
                "action": "MUSIC_PLAY",
                "payload": result,
            }
    except ImportError:
        logger.debug("youtube-search-python not available, using search fallback")
    except Exception as e:
        logger.error("Music handler error: %s", e)

    # Fallback: YouTube search
    search_url = (
        f"https://www.youtube.com/results?"
        f"search_query={play_query.replace(' ', '+')}+music"
    )
    return {
        "response": f"YouTube pe '{play_query}' dhundh raha hoon 🎵🔍",
        "action": "YOUTUBE_SEARCH",
        "payload": {
            "action": "android.intent.action.VIEW",
            "package": YOUTUBE_PACKAGE,
            "data": search_url,
        },
    }
