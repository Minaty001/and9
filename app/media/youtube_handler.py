"""
AND9 — YouTube Handler (Phase 7 of Refactor).

Provides search, play, and open operations against YouTube.
All commands target the YouTube Android app using direct
YouTube URLs and intents.

NEVER sends YouTube commands to Chrome or any browser.
"""
import logging

from app.core.config import YOUTUBE_PACKAGE

logger = logging.getLogger(__name__)


class YouTubeHandler:
    """Handles YouTube-related operations.

    All methods produce Android Intent payloads that target
    the YouTube app package directly.
    """

    @staticmethod
    def open() -> dict:
        """Open the YouTube app to the home page."""
        return {
            "response": "YouTube khol raha hoon! ▶️",
            "action": "YOUTUBE_SEARCH",
            "payload": {
                "action": "android.intent.action.VIEW",
                "package": YOUTUBE_PACKAGE,
                "data": "https://www.youtube.com/",
            },
        }

    @staticmethod
    def search(query: str) -> dict:
        """Search YouTube for a query string."""
        if not query or not query.strip():
            return YouTubeHandler.open()

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

    @staticmethod
    def play(query: str) -> dict:
        """Play a song/video on YouTube via search."""
        if not query or not query.strip():
            return YouTubeHandler.open()

        search_url = (
            f"https://www.youtube.com/results?"
            f"search_query={query.replace(' ', '+')}"
        )
        return {
            "response": f"YouTube pe '{query}' play kar raha hoon ▶️🎵",
            "action": "YOUTUBE_PLAY",
            "payload": {
                "action": "android.intent.action.VIEW",
                "package": YOUTUBE_PACKAGE,
                "data": search_url,
            },
        }

    @staticmethod
    def play_music(query: str) -> dict:
        """Attempt music playback via JARVIS handler, fallback to search."""
        try:
            from app.skills.youtube import handle_music_request
            result = handle_music_request(query)
            if result and "response" in result:
                return {
                    "response": f"Baja raha hoon '{query}' 🎵",
                    "action": "MUSIC_PLAY",
                    "payload": result,
                }
        except ImportError:
            logger.debug("youtube-search-python not available")
        except Exception as e:
            logger.error("Music handler error: %s", e)

        return YouTubeHandler.play(f"{query} music")
