"""
Phase 19 — YouTube Player.

Simulates video playback management.
"""

import time
from datetime import datetime, timezone
from typing import List, Optional

from .models import YouTubeVideo, YouTubePlaybackState
from .config import YouTubeConfig
from .searcher import YouTubeSearcher


class YouTubePlayer:
    """Manages video playback state and operations."""

    def __init__(self, config: YouTubeConfig, searcher: YouTubeSearcher):
        self.config = config
        self._searcher = searcher
        self._state = YouTubePlaybackState(
            quality=config.default_quality,
            autoplay=config.enable_autoplay,
        )
        self._playback_history: List[YouTubeVideo] = []
        self._last_update_time = 0.0

    def play(self, video_or_id) -> bool:
        """Play a video by ID or YouTubeVideo object.

        Args:
            video_or_id: A video ID string or YouTubeVideo instance.

        Returns:
            True if playback started successfully.
        """
        video = self._resolve_video(video_or_id)
        if video is None:
            return False

        # If already playing something, stop it first
        if self._state.status == "playing":
            self._capture_position()

        self._state.current_video = video
        self._state.status = "playing"
        self._state.position_seconds = 0.0
        self._last_update_time = time.time()

        # Add to history
        self._add_to_history(video)
        return True

    def pause(self) -> bool:
        """Pause the current video.

        Returns:
            True if paused successfully.
        """
        if self._state.status != "playing":
            return False
        self._capture_position()
        self._state.status = "paused"
        return True

    def resume(self) -> bool:
        """Resume from paused state.

        Returns:
            True if resumed successfully.
        """
        if self._state.status != "paused":
            return False
        self._state.status = "playing"
        self._last_update_time = time.time()
        return True

    def stop(self) -> bool:
        """Stop playback.

        Returns:
            True if stopped successfully.
        """
        if self._state.status == "stopped":
            return False
        self._capture_position()
        self._state.status = "stopped"
        self._state.current_video = None
        self._state.position_seconds = 0.0
        return True

    def seek(self, seconds: float) -> bool:
        """Seek to a position in the current video.

        Args:
            seconds: Position to seek to in seconds.

        Returns:
            True if seek succeeded.
        """
        if self._state.current_video is None:
            return False
        if seconds < 0:
            seconds = 0.0
        max_duration = float(self._state.current_video.duration_seconds)
        if seconds > max_duration:
            seconds = max_duration
        self._capture_position()
        self._state.position_seconds = seconds
        self._last_update_time = time.time()
        return True

    def set_quality(self, level: str) -> bool:
        """Set video quality.

        Args:
            level: Quality level (auto, 144p, 360p, 480p, 720p, 1080p).

        Returns:
            True if quality was set.
        """
        if level not in self.config.supported_qualities:
            return False
        self._state.quality = level
        return True

    def set_volume(self, level: int) -> bool:
        """Set volume level.

        Args:
            level: Volume 0-100.

        Returns:
            True if volume was set.
        """
        if level < 0 or level > 100:
            return False
        self._state.volume = level
        return True

    def get_state(self) -> YouTubePlaybackState:
        """Get current playback state with simulated time progression."""
        self._update_position()
        return self._state

    def history(self) -> List[YouTubeVideo]:
        """Get playback history."""
        return list(self._playback_history)

    # ── Internal ────────────────────────────────────────────────

    def _resolve_video(self, video_or_id) -> Optional[YouTubeVideo]:
        """Resolve a video ID or YouTubeVideo to a YouTubeVideo."""
        if isinstance(video_or_id, YouTubeVideo):
            return video_or_id
        if isinstance(video_or_id, str):
            return self._searcher.get_video_info(video_or_id)
        return None

    def _capture_position(self) -> None:
        """Capture the current playback position based on elapsed time."""
        if self._state.status == "playing" and self._last_update_time > 0:
            elapsed = time.time() - self._last_update_time
            new_pos = self._state.position_seconds + elapsed
            max_dur = float(self._state.current_video.duration_seconds) if self._state.current_video else 0.0
            if max_dur > 0 and new_pos >= max_dur:
                new_pos = max_dur
                self._state.status = "stopped"
            self._state.position_seconds = new_pos

    def _update_position(self) -> None:
        """Update position if currently playing."""
        if self._state.status == "playing" and self._last_update_time > 0:
            elapsed = time.time() - self._last_update_time
            if elapsed > 1.0:
                self._capture_position()
                self._last_update_time = time.time()

    def _add_to_history(self, video: YouTubeVideo) -> None:
        """Add a video to playback history."""
        if self.config.enable_history:
            self._playback_history.append(video)
            if len(self._playback_history) > self.config.max_history:
                self._playback_history.pop(0)
