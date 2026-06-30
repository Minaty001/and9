# Phase 19 — YouTube Controller

Search, play, pause, and manage YouTube video playback.

## Components

### YouTubeConfig
Configuration for the YouTube controller service. Uses environment variable prefix `JARVIS_PHASE19_`.

| Field | Default | Description |
|---|---|---|
| service_name | `jarvis_youtube` | Service name |
| api_key_env | `JARVIS_YOUTUBE_API_KEY` | Env var for API key |
| max_search_results | `10` | Max search results |
| enable_history | `True` | Enable playback history |
| max_history | `100` | Max history entries |
| enable_autoplay | `False` | Enable autoplay |
| default_quality | `auto` | Default video quality |
| supported_qualities | `["auto","144p","360p","480p","720p","1080p"]` | Supported qualities |

### YouTubeVideo
Pydantic model representing a YouTube video with fields: `id`, `title`, `url`, `duration_seconds`, `channel`, `thumbnail_url`, `description`, `view_count`, `published_at`, `metadata`.

### YouTubePlaybackState
Pydantic model for current playback state: `status` (stopped/playing/paused/buffering), `current_video`, `position_seconds`, `quality`, `volume`, `playlist`, `autoplay`, `timestamp`.

### YouTubeSearcher
Simulated video search engine. Supports:
- `search(query, max_results)` — Search by title/channel keyword
- `get_video_info(video_id)` — Get video details by ID
- `set_custom_results(results)` — Override results for testing

### YouTubePlayer
Manages video playback with methods:
- `play(video_or_id)` — Start playback
- `pause()` / `resume()` / `stop()` — Control playback
- `seek(seconds)` — Seek to position
- `set_quality(level)` / `set_volume(level)` — Adjust settings
- `get_state()` — Get current playback state
- `history()` — Get playback history

### YouTubeControllerService
ServiceBase wrapper providing async access to all YouTube functionality.
