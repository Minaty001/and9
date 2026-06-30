"""
Phase 19 — YouTube Searcher.

Simulates YouTube search functionality. In production this would call
the YouTube Data API v3.
"""

import time
from typing import List, Optional

from .models import YouTubeVideo
from .config import YouTubeConfig

# Mock video data for simulation
_MOCK_VIDEOS = {
    "dQw4w9WgXcQ": YouTubeVideo(
        id="dQw4w9WgXcQ",
        title="Rick Astley - Never Gonna Give You Up",
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        duration_seconds=212,
        channel="Rick Astley",
        thumbnail_url="https://i.ytimg.com/vi/dQw4w9WgXcQ/default.jpg",
        description="The official video for 'Never Gonna Give You Up'.",
        view_count=1500000000,
        published_at="2009-10-25",
    ),
    "9bZkp7q19f0": YouTubeVideo(
        id="9bZkp7q19f0",
        title="PSY - GANGNAM STYLE",
        url="https://www.youtube.com/watch?v=9bZkp7q19f0",
        duration_seconds=253,
        channel="PSY",
        thumbnail_url="https://i.ytimg.com/vi/9bZkp7q19f0/default.jpg",
        description="GANGNAM STYLE music video.",
        view_count=4800000000,
        published_at="2012-07-15",
    ),
    "kJQP7kiw5Fk": YouTubeVideo(
        id="kJQP7kiw5Fk",
        title="Luis Fonsi - Despacito ft. Daddy Yankee",
        url="https://www.youtube.com/watch?v=kJQP7kiw5Fk",
        duration_seconds=282,
        channel="Luis Fonsi",
        thumbnail_url="https://i.ytimg.com/vi/kJQP7kiw5Fk/default.jpg",
        description="Despacito music video.",
        view_count=8300000000,
        published_at="2017-01-13",
    ),
    "fJ9rUzIMcZQ": YouTubeVideo(
        id="fJ9rUzIMcZQ",
        title="Queen – Bohemian Rhapsody",
        url="https://www.youtube.com/watch?v=fJ9rUzIMcZQ",
        duration_seconds=355,
        channel="Queen Official",
        thumbnail_url="https://i.ytimg.com/vi/fJ9rUzIMcZQ/default.jpg",
        description="Queen's Bohemian Rhapsody official video.",
        view_count=1400000000,
        published_at="2008-08-01",
    ),
    "hT_nvWreIhg": YouTubeVideo(
        id="hT_nvWreIhg",
        title="The Beatles - Hey Jude",
        url="https://www.youtube.com/watch?v=hT_nvWreIhg",
        duration_seconds=420,
        channel="The Beatles",
        thumbnail_url="https://i.ytimg.com/vi/hT_nvWreIhg/default.jpg",
        description="The Beatles performing Hey Jude.",
        view_count=900000000,
        published_at="2015-12-11",
    ),
}


class YouTubeSearcher:
    """Simulates YouTube video search."""

    def __init__(self, config: YouTubeConfig):
        self.config = config
        self._custom_results: List[YouTubeVideo] = []

    def search(self, query: str, max_results: Optional[int] = None) -> List[YouTubeVideo]:
        """Search for videos matching the query.

        Args:
            query: Search query string.
            max_results: Maximum number of results (defaults to config).

        Returns:
            List of matching YouTubeVideo objects.
        """
        if self._custom_results:
            return self._custom_results[:max_results or self.config.max_search_results]

        limit = max_results or self.config.max_search_results
        query_lower = query.lower()
        results = [
            v for v in _MOCK_VIDEOS.values()
            if query_lower in v.title.lower() or query_lower in v.channel.lower()
        ]
        return results[:limit]

    def get_video_info(self, video_id: str) -> Optional[YouTubeVideo]:
        """Get detailed info for a specific video.

        Args:
            video_id: The YouTube video ID.

        Returns:
            YouTubeVideo if found, None otherwise.
        """
        if self._custom_results:
            for v in self._custom_results:
                if v.id == video_id:
                    return v
        return _MOCK_VIDEOS.get(video_id)

    def set_custom_results(self, results: List[YouTubeVideo]) -> None:
        """Set custom results for testing."""
        self._custom_results = list(results)
