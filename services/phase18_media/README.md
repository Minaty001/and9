# Phase 18 — Media Controller

Media playback control for the JARVIS AI operating system.

## Components

### MediaPlayer
Core playback engine with:
- `play(track)` — Start playback of a specific track, or resume
- `pause()` / `resume()` — Pause and resume playback
- `stop()` — Stop playback and reset position
- `seek(seconds)` — Seek to a position in the current track
- `set_volume(level)` — Set volume (0-100)
- `get_state()` — Return current playback state as PlaybackState
- `next()` / `previous()` — Track navigation (delegates to service for queue integration)

### QueueManager
Track queue management:
- `add(track, position)` — Add track to queue (default: end)
- `remove(index)` — Remove track by index
- `clear()` — Clear entire queue
- `reorder(from_idx, to_idx)` — Reorder tracks
- `get_queue()` — Return current queue
- `set_shuffle(enabled)` — Toggle shuffle (preserves original order when disabled)
- `set_repeat(mode)` — Set repeat mode: `off`, `one`, `all`

### MediaControllerService
Service wrapper with full lifecycle management:
- Playback: `play()`, `pause()`, `resume()`, `stop()`, `seek()`, `next()`, `previous()`
- Volume: `set_volume(level)`
- State: `get_state()`
- Queue: `queue_add()`, `queue_remove()`, `queue_clear()`, `queue_reorder()`, `queue_get()`
- Shuffle/Repeat: `set_shuffle()`, `set_repeat()`

## Models

### Track
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | str | required | Unique identifier |
| `title` | str | required | Track title |
| `artist` | str | `Unknown Artist` | Artist name |
| `album` | str? | None | Album name |
| `duration_seconds` | float | 0.0 | Track duration |
| `url` | str? | None | Track URL |
| `service` | str | `local` | Source service |
| `metadata` | dict | {} | Additional metadata |

### PlaybackState
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `status` | str | `stopped` | stopped, playing, paused |
| `current_track` | Track? | None | Currently playing track |
| `position_seconds` | float | 0.0 | Current position |
| `volume` | int | 50 | Volume (0-100) |
| `queue` | List[Track] | [] | Current queue |
| `shuffle` | bool | False | Shuffle enabled |
| `repeat_mode` | str | `off` | off, one, all |

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `service_name` | `jarvis_media` | Service name |
| `supported_services` | `["local", "spotify", "youtube_music"]` | Supported services |
| `default_volume` | `50` | Default volume |
| `max_queue_size` | `100` | Max queue entries |
| `enable_crossfade` | `False` | Crossfade between tracks |
| `enable_eq` | `False` | Equalizer support |
| `history_size` | `50` | Max playback history entries |

## Usage

```python
from services.phase18_media import MediaControllerService, MediaConfig, Track

config = MediaConfig()
service = MediaControllerService(config)
await service.initialize()

# Create a track
track = Track(
    id="song_1",
    title="My Song",
    artist="My Artist",
    duration_seconds=240.0,
)

# Play
await service.play(track)

# Queue management
await service.queue_add(track)
await service.set_shuffle(True)
await service.set_repeat("all")

# Control
await service.pause()
await service.resume()
await service.seek(60.0)
await service.set_volume(75)

# Get state
state = await service.get_state()

# Shutdown
await service.shutdown()
```

## Testing

```bash
cd /root/github/and9 && python -m pytest services/phase18_media/tests/ -v
```

18+ tests covering all models, components, and the full service lifecycle.
