"""app/plugins/spotify/plugin.py — Spotify plugin for AND9"""
import logging
import os

from app.plugins.base_plugin import BasePlugin

logger = logging.getLogger(__name__)


class Plugin(BasePlugin):
    name = "SpotifyPlugin"
    version = "1.0"
    intents = ["spotify_play", "spotify_pause", "spotify_next",
               "spotify_search", "spotify"]
    ram_estimate_mb = 3
    lazy = True  # Only load when first requested

    def initialize(self):
        self._client_id = os.environ.get("SPOTIFY_CLIENT_ID", "")
        self._client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET", "")
        self._enabled = bool(self._client_id and self._client_secret)

    def handle(self, intent: str, entities: dict) -> dict:
        if not self._enabled:
            return {
                "success": False,
                "response": "Spotify is not configured. Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET.",
            }

        if intent == "spotify_play":
            return self._play(entities.get("query", ""))
        elif intent == "spotify_pause":
            return self._pause()
        elif intent == "spotify_search":
            return self._search(entities.get("query", ""))

        return {"success": False, "response": f"Spotify: unknown intent '{intent}'"}

    def _play(self, query: str) -> dict:
        return {"success": True, "response": f"Playing '{query}' on Spotify..."}

    def _pause(self) -> dict:
        return {"success": True, "response": "Spotify paused."}

    def _search(self, query: str) -> dict:
        return {"success": True, "response": f"Searching Spotify for '{query}'..."}