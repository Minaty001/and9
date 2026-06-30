"""
Phase 18 — Media Controller Service.

Wraps MediaPlayer and QueueManager in a ServiceBase interface with
lifecycle management, metrics, and health checks.
"""

import time
import logging
from typing import Any, Dict, List, Optional

from services.base.service_base import ServiceBase
from .config import MediaConfig
from .models import Track, PlaybackState
from .media_controller import MediaPlayer, QueueManager

logger = logging.getLogger(__name__)


class MediaControllerService(ServiceBase):
    """Service for media playback control.

    Orchestrates MediaPlayer and QueueManager with full lifecycle management,
    providing play/pause/stop/seek/volume control and queue management.
    """

    def __init__(self, config: Optional[MediaConfig] = None):
        super().__init__(name="jarvis_media", version="1.0.0")
        self.config = config or MediaConfig()
        self._start_time = 0.0
        self._player: Optional[MediaPlayer] = None
        self._queue_manager: Optional[QueueManager] = None
        self._playback_history: List[Dict[str, Any]] = []

    # ── Lifecycle ───────────────────────────────────────────────

    async def initialize(self) -> bool:
        """Initialize the media controller service."""
        self._start_time = time.time()
        try:
            self._player = MediaPlayer(default_volume=self.config.default_volume)
            self._queue_manager = QueueManager(max_size=self.config.max_queue_size)

            self._metrics.reset()
            self._initialized = True
            logger.info("MediaControllerService initialized")
            return True
        except Exception as e:
            logger.error("MediaControllerService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        """Shut down the media controller service."""
        logger.info("MediaControllerService shutting down...")
        self._initialized = False

    # ── Health / Stats ──────────────────────────────────────────

    async def health(self) -> Dict[str, Any]:
        """Return service health status."""
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service_name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
        }

    async def stats(self) -> Dict[str, Any]:
        """Return service statistics."""
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        state = self._player.get_state() if self._player else None
        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            "playback_status": state.status if state else "unavailable",
            "queue_size": self._queue_manager.size if self._queue_manager else 0,
            "playback_history_count": len(self._playback_history),
            "metrics": self._metrics.snapshot(),
        }

    # ── Playback Control ────────────────────────────────────────

    async def play(self, track: Optional[Track] = None) -> bool:
        """Start or resume playback.

        Args:
            track: Optional track to play. If None, plays first in queue or resumes.

        Returns:
            True if playback started successfully.
        """
        if not self._initialized:
            return False

        result = self._player.play(track)
        if result:
            self._metrics.counter("play_actions")
            if track:
                self._record_history("play", track)
        return result

    async def pause(self) -> bool:
        """Pause current playback.

        Returns:
            True if paused successfully.
        """
        if not self._initialized:
            return False
        result = self._player.pause()
        if result:
            self._metrics.counter("pause_actions")
        return result

    async def resume(self) -> bool:
        """Resume from paused state.

        Returns:
            True if resumed successfully.
        """
        if not self._initialized:
            return False
        result = self._player.resume()
        if result:
            self._metrics.counter("resume_actions")
        return result

    async def stop(self) -> bool:
        """Stop playback.

        Returns:
            True if stopped successfully.
        """
        if not self._initialized:
            return False
        result = self._player.stop()
        if result:
            self._metrics.counter("stop_actions")
            self._record_history("stop", self._player.get_state().current_track)
        return result

    async def seek(self, seconds: float) -> bool:
        """Seek to a position in the current track.

        Args:
            seconds: Target position in seconds.

        Returns:
            True if seek succeeded.
        """
        if not self._initialized:
            return False
        result = self._player.seek(seconds)
        if result:
            self._metrics.counter("seek_actions")
        return result

    async def next(self) -> bool:
        """Skip to the next track in the queue.

        Returns:
            True if skipped successfully.
        """
        if not self._initialized:
            return False

        queue = self._queue_manager.get_queue()
        if not queue:
            return False

        state = self._player.get_state()
        current = state.current_track

        if current:
            # Find current track index
            current_idx = -1
            for i, t in enumerate(queue):
                if t.id == current.id:
                    current_idx = i
                    break

            if current_idx >= 0 and current_idx < len(queue) - 1:
                next_track = queue[current_idx + 1]
            else:
                if self._queue_manager.repeat_mode == "all":
                    next_track = queue[0]
                elif self._queue_manager.repeat_mode == "one":
                    next_track = current
                else:
                    return False
        else:
            next_track = queue[0]

        self._player.play(next_track)
        self._metrics.counter("next_actions")
        self._record_history("next", next_track)
        return True

    async def previous(self) -> bool:
        """Go to the previous track in the queue.

        Returns:
            True if went to previous track successfully.
        """
        if not self._initialized:
            return False

        queue = self._queue_manager.get_queue()
        if not queue:
            return False

        state = self._player.get_state()
        current = state.current_track

        if current:
            current_idx = -1
            for i, t in enumerate(queue):
                if t.id == current.id:
                    current_idx = i
                    break

            if current_idx > 0:
                prev_track = queue[current_idx - 1]
            else:
                if self._queue_manager.repeat_mode == "all":
                    prev_track = queue[-1]
                elif self._queue_manager.repeat_mode == "one":
                    prev_track = current
                else:
                    return False
        else:
            prev_track = queue[-1]

        self._player.play(prev_track)
        self._metrics.counter("previous_actions")
        self._record_history("previous", prev_track)
        return True

    async def set_volume(self, level: int) -> bool:
        """Set the volume level.

        Args:
            level: Volume level (0-100).

        Returns:
            True if set successfully.
        """
        if not self._initialized:
            return False
        result = self._player.set_volume(level)
        if result:
            self._metrics.counter("volume_changes")
        return result

    async def get_state(self) -> PlaybackState:
        """Return the current playback state.

        Returns:
            PlaybackState with current playback information.
        """
        if not self._initialized:
            return PlaybackState(status="stopped", volume=self.config.default_volume)

        state = self._player.get_state()
        # Sync queue info
        state.queue = self._queue_manager.get_queue()
        state.shuffle = self._queue_manager.shuffle
        state.repeat_mode = self._queue_manager.repeat_mode
        return state

    # ── Queue Management ────────────────────────────────────────

    async def queue_add(self, track: Track, position: Optional[int] = None) -> bool:
        """Add a track to the queue.

        Args:
            track: Track to add.
            position: Position to insert at (None = end).

        Returns:
            True if added successfully.
        """
        if not self._initialized:
            return False
        result = self._queue_manager.add(track, position)
        if result:
            self._metrics.counter("queue_adds")
        return result

    async def queue_remove(self, index: int) -> bool:
        """Remove a track from the queue.

        Args:
            index: Index of the track to remove.

        Returns:
            True if removed successfully.
        """
        if not self._initialized:
            return False
        result = self._queue_manager.remove(index)
        if result:
            self._metrics.counter("queue_removes")
        return result

    async def queue_clear(self) -> bool:
        """Clear the entire queue.

        Returns:
            True if cleared successfully.
        """
        if not self._initialized:
            return False
        result = self._queue_manager.clear()
        if result:
            self._metrics.counter("queue_clears")
        return result

    async def queue_reorder(self, from_idx: int, to_idx: int) -> bool:
        """Reorder a track in the queue.

        Args:
            from_idx: Current index.
            to_idx: Target index.

        Returns:
            True if reordered successfully.
        """
        if not self._initialized:
            return False
        return self._queue_manager.reorder(from_idx, to_idx)

    async def queue_get(self) -> List[Track]:
        """Return the current queue.

        Returns:
            List of Track objects.
        """
        if not self._initialized:
            return []
        return self._queue_manager.get_queue()

    async def set_shuffle(self, enabled: bool) -> bool:
        """Enable or disable shuffle.

        Args:
            enabled: True to shuffle, False to restore order.

        Returns:
            True if successful.
        """
        if not self._initialized:
            return False
        result = self._queue_manager.set_shuffle(enabled)
        if result:
            self._metrics.counter("shuffle_toggles")
        return result

    async def set_repeat(self, mode: str) -> bool:
        """Set the repeat mode.

        Args:
            mode: One of 'off', 'one', 'all'.

        Returns:
            True if set successfully.
        """
        if not self._initialized:
            return False
        result = self._queue_manager.set_repeat(mode)
        if result:
            self._metrics.counter("repeat_changes")
        return result

    # ── Internal ────────────────────────────────────────────────

    def _record_history(self, action: str, track: Optional[Track]) -> None:
        """Record a playback event in history."""
        entry = {
            "action": action,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        }
        if track:
            entry["track_id"] = track.id
            entry["track_title"] = track.title
        self._playback_history.append(entry)
        if len(self._playback_history) > self.config.history_size:
            self._playback_history = self._playback_history[-self.config.history_size :]
