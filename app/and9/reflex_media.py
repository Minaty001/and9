"""
AND9 — Reflex Media Handlers.

Handles YouTube search and music playback via the JARVIS media stack.
These functions prepare YouTube search intents and attempt music
playback through the existing handle_music_request() function.

Music playback is attempted first via the JARVIS music search pipeline
(which requires the `youtube-search-python` package). If that fails,
falls back to a YouTube search intent so the user can at least see
results.

Note: The `youtube-search-python` dependency may not be installed in
the current environment. In that case, music playback falls through
to the search fallback path gracefully.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def handle_youtube_search(search_term: str) -> dict:
    """Prepare a YouTube search intent for the given query.

    Creates an Android Intent that will open the YouTube app with
    the search query pre-filled.

    Args:
        search_term: The search string (can be empty for just opening
                     YouTube).

    Returns:
        Response dict with YOUTUBE_SEARCH action and an Android
        intent payload. If no search term is provided, just opens
        the YouTube app.
    """
    if not search_term or search_term.strip() == "":
        return {
            "response": "YouTube khol raha hoon! ▶️",
            "action": "LAUNCH_APP",
            "payload": {
                "action": "android.intent.action.VIEW",
                "package": "com.google.android.youtube",
                "data": "https://www.youtube.com/",
            },
        }

    # YouTube app supports deep linking to search results
    search_url = f"https://www.youtube.com/results?search_query={search_term.replace(' ', '+')}"
    return {
        "response": f"YouTube pe '{search_term}' search kar raha hoon 🔍▶️",
        "action": "YOUTUBE_SEARCH",
        "payload": {
            "action": "android.intent.action.VIEW",
            "package": "com.google.android.youtube",
            "data": search_url,
        },
    }


def handle_youtube_play(query: str) -> dict:
    """Attempt to play music/songs through YouTube.

    First tries the JARVIS music handler for a rich playback experience.
    Falls back to YouTube search if music services are unavailable.

    Args:
        query: Normalized user query (e.g., "play song despacito").

    Returns:
        Response dict with either a MUSIC_PLAY or YOUTUBE_SEARCH
        action.
    """
    # Extract what the user wants to play
    play_query = query.lower()

    # Remove "play", "song", "music" words for the actual search
    for word in ["play", "song", "music", "bajao", "sunao"]:
        play_query = play_query.replace(word, " ").strip()

    if not play_query:
        play_query = "trending music"

    # Try the JARVIS music handler (requires youtube-search-python)
    try:
        from app.javis.youtube import handler as music_handler

        result = music_handler.handle_music_request(play_query)
        if result and "response" in result:
            return {
                "response": f"Baja raha hoon '{play_query}' 🎵",
                "action": "MUSIC_PLAY",
                "payload": result,
            }
    except ImportError:
        logger.warning("youtube-search-python not available, falling back to search")
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
            "package": "com.google.android.youtube",
            "data": search_url,
        },
    }
