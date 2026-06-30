"""
Phase 18 — Media Controller Core Logic.

Provides MediaPlayer and QueueManager for media playback control
with queue management, shuffle, and repeat functionality.
"""

import copy
import random
import time
from typing import List, Optional

from .models import Track, PlaybackState


class QueueManager:
    """Manages the playback queue with add, remove, clear, reorder, shuffle, repeat."""

    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self._queue: List[Track] = []
        self._original_order: List[str] = []  # Track IDs in original order for shuffle toggle
        self._shuffled: bool = False
        self._repeat_mode: str = "off"  # off, one, all

    def add(self, track: Track, position: Optional[int] = None) -> bool:
        """Add a track to the queue.

        Args:
            track: The track to add.
            position: Position to insert at (None = end of queue).

        Returns:
            True if added successfully, False if queue is full.
        """
        if len(self._queue) >= self.max_size:
            return False

        if position is not None and 0 <= position <= len(self._queue):
            self._queue.insert(position, track)
            if self._shuffled:
                self._original_order.insert(position, track.id)
            else:
                self._original_order.insert(position, track.id)
        else:
            self._queue.append(track)
            self._original_order.append(track.id)

        return True

    def remove(self, index: int) -> bool:
        """Remove a track from the queue by index.

        Args:
            index: Index of the track to remove.

        Returns:
            True if removed successfully, False if index is out of range.
        """
        if index < 0 or index >= len(self._queue):
            return False

        removed = self._queue.pop(index)
        if self._shuffled:
            # Remove from original order by track ID
            if removed.id in self._original_order:
                self._original_order.remove(removed.id)
        else:
            if index < len(self._original_order):
                self._original_order.pop(index)

        return True

    def clear(self) -> bool:
        """Clear the entire queue.

        Returns:
            True if cleared successfully.
        """
        self._queue.clear()
        self._original_order.clear()
        return True

    def reorder(self, from_idx: int, to_idx: int) -> bool:
        """Reorder a track from one position to another.

        Args:
            from_idx: Current index of the track.
            to_idx: Target index for the track.

        Returns:
            True if reordered successfully, False if indices are invalid.
        """
        if from_idx < 0 or from_idx >= len(self._queue):
            return False
        if to_idx < 0 or to_idx >= len(self._queue):
            return False
        if from_idx == to_idx:
            return True

        track = self._queue.pop(from_idx)
        self._queue.insert(to_idx, track)

        # Also update original order
        orig_track = self._original_order.pop(from_idx)
        self._original_order.insert(to_idx, orig_track)

        return True

    def get_queue(self) -> List[Track]:
        """Return the current queue (shuffled or original).

        Returns:
            List of Track objects.
        """
        return list(self._queue)

    def set_shuffle(self, enabled: bool) -> bool:
        """Enable or disable shuffle.

        Args:
            enabled: True to shuffle, False to restore original order.

        Returns:
            True if successful.
        """
        if enabled == self._shuffled:
            return True

        if enabled:
            # Store original order and shuffle
            self._original_order = [t.id for t in self._queue]
            random.shuffle(self._queue)
        else:
            # Restore original order
            ordered = []
            for tid in self._original_order:
                for track in self._queue:
                    if track.id == tid:
                        ordered.append(track)
                        break
            # Add any tracks not in original order
            for track in self._queue:
                if track.id not in self._original_order:
                    ordered.append(track)
            self._queue = ordered

        self._shuffled = enabled
        return True

    def set_repeat(self, mode: str) -> bool:
        """Set the repeat mode.

        Args:
            mode: One of 'off', 'one', 'all'.

        Returns:
            True if valid mode, False otherwise.
        """
        if mode not in ("off", "one", "all"):
            return False
        self._repeat_mode = mode
        return True

    @property
    def shuffle(self) -> bool:
        """Whether shuffle is currently enabled."""
        return self._shuffled

    @property
    def repeat_mode(self) -> str:
        """Current repeat mode."""
        return self._repeat_mode

    @property
    def size(self) -> int:
        """Current queue size."""
        return len(self._queue)

    @property
    def is_empty(self) -> bool:
        """Whether the queue is empty."""
        return len(self._queue) == 0


class MediaPlayer:
    """Controls media playback: play, pause, resume, stop, seek, next, previous, volume."""

    def __init__(self, default_volume: int = 50):
        self.default_volume = default_volume
        self._state = PlaybackState(
            status="stopped",
            volume=default_volume,
        )
        self._current_track_index: int = -1

    def play(self, track: Optional[Track] = None) -> bool:
        """Start playback, optionally of a specific track.

        Args:
            track: Optional track to play. If None, resumes or plays first in queue.

        Returns:
            True if playback started.
        """
        if track:
            self._state.current_track = track
            self._state.position_seconds = 0.0
        elif self._state.current_track is None:
            return False

        self._state.status = "playing"
        self._state.timestamp = self._timestamp()
        return True

    def pause(self) -> bool:
        """Pause current playback.

        Returns:
            True if paused, False if not playing.
        """
        if self._state.status != "playing":
            return False

        self._state.status = "paused"
        self._state.timestamp = self._timestamp()
        return True

    def resume(self) -> bool:
        """Resume from paused state.

        Returns:
            True if resumed, False if not paused.
        """
        if self._state.status != "paused":
            return False

        self._state.status = "playing"
        self._state.timestamp = self._timestamp()
        return True

    def stop(self) -> bool:
        """Stop playback and reset position.

        Returns:
            True if stopped.
        """
        if self._state.status == "stopped":
            return False

        self._state.status = "stopped"
        self._state.position_seconds = 0.0
        self._state.timestamp = self._timestamp()
        return True

    def seek(self, seconds: float) -> bool:
        """Seek to a position in the current track.

        Args:
            seconds: Target position in seconds.

        Returns:
            True if seek succeeded, False if no track is loaded.
        """
        if self._state.current_track is None:
            return False

        seconds = max(0.0, seconds)
        if seconds > self._state.current_track.duration_seconds:
            seconds = self._state.current_track.duration_seconds

        self._state.position_seconds = seconds
        self._state.timestamp = self._timestamp()
        return True

    def next(self) -> bool:
        """Skip to the next track.

        Returns:
            True if skipped, False if no next track.
        """
        if self._state.status == "stopped":
            return False
        return True  # Delegates to service for queue management

    def previous(self) -> bool:
        """Go to the previous track.

        Returns:
            True if went back, False if at start.
        """
        if self._state.status == "stopped":
            return False
        return True  # Delegates to service for queue management

    def set_volume(self, level: int) -> bool:
        """Set the volume level.

        Args:
            level: Volume level (0-100).

        Returns:
            True if set successfully, False if out of range.
        """
        if level < 0 or level > 100:
            return False

        self._state.volume = level
        self._state.timestamp = self._timestamp()
        return True

    def get_state(self) -> PlaybackState:
        """Return the current playback state.

        Returns:
            PlaybackState with current status, track, position, volume, queue info.
        """
        return self._state.model_copy(deep=True)

    def update_state(self, **kwargs) -> None:
        """Update the internal playback state fields."""
        for key, value in kwargs.items():
            if hasattr(self._state, key):
                setattr(self._state, key, value)
        self._state.timestamp = self._timestamp()

    @staticmethod
    def _timestamp() -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
