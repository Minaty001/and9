"""
Phase 18 — Media Controller
=============================

Media playback control: play/pause/stop/seek, queue management,
volume control, and playback state tracking with support for
local and online streaming services.

Components:
    - MediaPlayer: Playback control (play, pause, resume, stop, seek, next, previous, volume)
    - QueueManager: Track queue with add, remove, clear, reorder, shuffle, repeat
    - MediaControllerService: Service wrapper with full lifecycle
"""

from .service import MediaControllerService
from .config import MediaConfig
from .models import Track, PlaybackState
from .media_controller import MediaPlayer, QueueManager

__all__ = [
    "MediaControllerService",
    "MediaConfig",
    "Track",
    "PlaybackState",
    "MediaPlayer",
    "QueueManager",
]
