"""
Phase 19 — YouTube Controller.

Search, play, pause, and manage YouTube video playback.
Simulates YouTube Data API integration.

Components:
    - YouTubeConfig: Configuration for YouTube controller
    - YouTubeVideo: Video data model
    - YouTubePlaybackState: Playback state model
    - YouTubeSearcher: Search for videos
    - YouTubePlayer: Manage video playback
    - YouTubeControllerService: ServiceBase wrapper
"""

from .config import YouTubeConfig
from .models import YouTubeVideo, YouTubePlaybackState
from .searcher import YouTubeSearcher
from .player import YouTubePlayer
from .service import YouTubeControllerService

__all__ = [
    "YouTubeConfig",
    "YouTubeVideo",
    "YouTubePlaybackState",
    "YouTubeSearcher",
    "YouTubePlayer",
    "YouTubeControllerService",
]
