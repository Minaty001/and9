# Phase 18: Media Controller

## Purpose
Media playback control with a `MediaPlayer` core engine (play/pause/stop/seek/volume) and `QueueManager` (add/remove/clear/reorder/shuffle/repeat). Provides full `MediaControllerService` for playback, queue management, shuffle, and repeat (off/one/all) modes. Tracks `PlaybackState` with current track, position, volume, and queue.

## Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `JARVIS_MEDIA_SUPPORTED_SERVICES` | `[local, spotify, youtube_music]` | Supported providers |
| `JARVIS_MEDIA_DEFAULT_VOLUME` | 50 | Default volume |
| `JARVIS_MEDIA_MAX_QUEUE_SIZE` | 100 | Max queue entries |
| `JARVIS_MEDIA_ENABLE_CROSSFADE` | false | Crossfade between tracks |
| `JARVIS_MEDIA_HISTORY_SIZE` | 50 | Max history entries |

## Architecture
```
MediaControllerService
  ├── MediaPlayer — play/pause/stop/seek/volume/next/previous
  └── QueueManager — add/remove/clear/reorder/shuffle/repeat
```

## Code
```python
class MediaPlayer:
    def play(self, track: Optional[Track] = None):
        if track: self._state.current_track = track
        self._state.status = "playing"; self._state.position_seconds = 0.0

    def pause(self):
        self._state.status = "paused"
        self._capture_position()

    def seek(self, seconds: float):
        self._state.position_seconds = max(0, min(seconds, self._duration()))

class QueueManager:
    def add(self, track, position=None) -> bool:
        if len(self._queue) >= self.max_size: return False
        self._queue.insert(position or len(self._queue), track); return True

    def set_shuffle(self, enabled: bool):
        if enabled: random.shuffle(self._queue)
        else: self._queue = [t for t in self._queue]
```

## Location
`app/skills/media/` — media playback skill
