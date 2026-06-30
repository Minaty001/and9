# Phase 19: YouTube Controller

## Purpose
Search, play, pause, and manage YouTube video playback. `YouTubeSearcher` provides simulated search against a mock video database with custom result injection. `YouTubePlayer` manages playback state (playing/paused/stopped/buffering), quality settings, volume, seek, and playback history. `YouTubeControllerService` wraps both in an async ServiceBase.

## Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `JARVIS_PHASE19_API_KEY_ENV` | `JARVIS_YOUTUBE_API_KEY` | API key env var |
| `JARVIS_PHASE19_MAX_SEARCH_RESULTS` | 10 | Max search results |
| `JARVIS_PHASE19_ENABLE_HISTORY` | true | Enable playback history |
| `JARVIS_PHASE19_ENABLE_AUTOPLAY` | false | Enable autoplay |
| `JARVIS_PHASE19_DEFAULT_QUALITY` | `auto` | Default video quality |

## Architecture
```
YouTubeControllerService
  ├── YouTubeSearcher — search(query)/get_video_info/set_custom_results
  └── YouTubePlayer — play/pause/resume/stop/seek/set_quality/set_volume/get_state/history
```

## Code
```python
class YouTubeSearcher:
    def search(self, query, max_results=10) -> List[YouTubeVideo]:
        results = []
        for vid in self._videos.values():
            if query.lower() in vid.title.lower() or query.lower() in vid.channel.lower():
                results.append(vid)
        return results[:max_results]

class YouTubePlayer:
    def play(self, video_or_id) -> bool:
        video = self._resolve_video(video_or_id)
        if not video: return False
        self._state.current_video = video
        self._state.status = "playing"; self._state.position_seconds = 0.0
        self._add_to_history(video); return True

    def seek(self, seconds: float):
        self._state.position_seconds = max(0, min(seconds, self._state.current_video.duration_seconds))
```

## Location
`app/services/youtube/` — YouTube integration service
