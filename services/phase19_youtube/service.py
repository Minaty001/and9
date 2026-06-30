"""
Phase 19 — YouTube Controller Service.

ServiceBase wrapper for YouTube search and playback.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Dict, List, Optional

from services.base.service_base import ServiceBase
from .config import YouTubeConfig
from .models import YouTubeVideo, YouTubePlaybackState
from .searcher import YouTubeSearcher
from .player import YouTubePlayer

logger = logging.getLogger(__name__)


class YouTubeControllerService(ServiceBase):
    """YouTube controller service for searching and managing video playback.

    Usage:
        svc = YouTubeControllerService()
        await svc.initialize()
        results = await svc.search("never gonna give you up")
        await svc.play(results[0])
        state = await svc.get_state()
    """

    def __init__(self, config: Optional[YouTubeConfig] = None):
        super().__init__(name="jarvis_youtube", version="1.0.0")
        self.config = config or YouTubeConfig()
        self.searcher: Optional[YouTubeSearcher] = None
        self.player: Optional[YouTubePlayer] = None
        self._start_time = 0.0

    async def initialize(self) -> bool:
        self._start_time = time.time()
        try:
            self.searcher = YouTubeSearcher(self.config)
            self.player = YouTubePlayer(self.config, self.searcher)
            self._metrics.reset()
            self._initialized = True
            logger.info("YouTubeControllerService initialized")
            return True
        except Exception as e:
            logger.error("YouTubeControllerService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        logger.info("YouTubeControllerService shutting down...")
        self._initialized = False

    async def search(self, query: str, max_results: Optional[int] = None) -> List[YouTubeVideo]:
        """Search for YouTube videos.

        Args:
            query: Search query string.
            max_results: Maximum number of results.

        Returns:
            List of matching YouTubeVideo objects.
        """
        if not self.searcher:
            raise RuntimeError("YouTubeControllerService not initialized")
        t0 = time.perf_counter()
        results = self.searcher.search(query, max_results)
        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.counter("searches", 1)
        self._metrics.histogram("search_time_ms", elapsed)
        return results

    async def play(self, video: YouTubeVideo) -> bool:
        """Play a video.

        Args:
            video: The YouTubeVideo to play.

        Returns:
            True if playback started.
        """
        if not self.player:
            raise RuntimeError("YouTubeControllerService not initialized")
        t0 = time.perf_counter()
        result = self.player.play(video)
        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.counter("play_actions", 1)
        self._metrics.histogram("play_time_ms", elapsed)
        return result

    async def pause(self) -> bool:
        """Pause playback."""
        if not self.player:
            raise RuntimeError("YouTubeControllerService not initialized")
        result = self.player.pause()
        self._metrics.counter("pause_actions", 1)
        return result

    async def resume(self) -> bool:
        """Resume playback."""
        if not self.player:
            raise RuntimeError("YouTubeControllerService not initialized")
        result = self.player.resume()
        self._metrics.counter("resume_actions", 1)
        return result

    async def stop(self) -> bool:
        """Stop playback."""
        if not self.player:
            raise RuntimeError("YouTubeControllerService not initialized")
        result = self.player.stop()
        self._metrics.counter("stop_actions", 1)
        return result

    async def seek(self, seconds: float) -> bool:
        """Seek to a position."""
        if not self.player:
            raise RuntimeError("YouTubeControllerService not initialized")
        result = self.player.seek(seconds)
        self._metrics.counter("seek_actions", 1)
        return result

    async def set_quality(self, level: str) -> bool:
        """Set video quality."""
        if not self.player:
            raise RuntimeError("YouTubeControllerService not initialized")
        result = self.player.set_quality(level)
        self._metrics.counter("quality_changes", 1)
        return result

    async def set_volume(self, level: int) -> bool:
        """Set volume level."""
        if not self.player:
            raise RuntimeError("YouTubeControllerService not initialized")
        result = self.player.set_volume(level)
        self._metrics.counter("volume_changes", 1)
        return result

    async def get_state(self) -> YouTubePlaybackState:
        """Get current playback state."""
        if not self.player:
            raise RuntimeError("YouTubeControllerService not initialized")
        return self.player.get_state()

    async def history(self) -> List[YouTubeVideo]:
        """Get playback history."""
        if not self.player:
            raise RuntimeError("YouTubeControllerService not initialized")
        return self.player.history()

    async def health(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service_name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
        }

    async def stats(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        state = self.player.get_state() if self.player else None
        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            "playback_status": state.status if state else "unknown",
            "metrics": self._metrics.snapshot(),
        }
