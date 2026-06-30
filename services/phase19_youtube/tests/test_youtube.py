"""
Tests for Phase 19 — YouTube Controller.
"""

import pytest
from services.phase19_youtube import (
    YouTubeConfig,
    YouTubeVideo,
    YouTubePlaybackState,
    YouTubeSearcher,
    YouTubePlayer,
    YouTubeControllerService,
)


class TestYouTubeVideo:
    """Verify YouTubeVideo creation and fields."""

    def test_create_video(self):
        v = YouTubeVideo(
            id="test123",
            title="Test Video",
            url="https://www.youtube.com/watch?v=test123",
            duration_seconds=120,
            channel="Test Channel",
        )
        assert v.id == "test123"
        assert v.title == "Test Video"
        assert v.duration_seconds == 120
        assert v.channel == "Test Channel"
        assert v.view_count == 0

    def test_video_with_all_fields(self):
        v = YouTubeVideo(
            id="abc123",
            title="Full Video",
            url="https://www.youtube.com/watch?v=abc123",
            duration_seconds=300,
            channel="My Channel",
            thumbnail_url="https://i.ytimg.com/vi/abc123/default.jpg",
            description="A full video description.",
            view_count=5000,
            published_at="2023-01-15",
            metadata={"genre": "music"},
        )
        assert v.view_count == 5000
        assert v.metadata["genre"] == "music"

    def test_playback_state_defaults(self):
        state = YouTubePlaybackState()
        assert state.status == "stopped"
        assert state.position_seconds == 0.0
        assert state.volume == 50
        assert state.quality == "auto"
        assert state.current_video is None


class TestYouTubeSearcher:
    """Verify YouTube search functionality."""

    def test_search_with_results(self):
        config = YouTubeConfig()
        searcher = YouTubeSearcher(config)
        results = searcher.search("never gonna")
        assert len(results) >= 1
        assert results[0].id == "dQw4w9WgXcQ"

    def test_search_empty_results(self):
        config = YouTubeConfig()
        searcher = YouTubeSearcher(config)
        results = searcher.search("xyznonexistentvideo999")
        assert len(results) == 0

    def test_search_respects_max_results(self):
        config = YouTubeConfig(max_search_results=2)
        searcher = YouTubeSearcher(config)
        results = searcher.search("a")
        assert len(results) <= 2

    def test_get_video_info_found(self):
        config = YouTubeConfig()
        searcher = YouTubeSearcher(config)
        video = searcher.get_video_info("dQw4w9WgXcQ")
        assert video is not None
        assert video.title == "Rick Astley - Never Gonna Give You Up"

    def test_get_video_info_not_found(self):
        config = YouTubeConfig()
        searcher = YouTubeSearcher(config)
        video = searcher.get_video_info("nonexistent")
        assert video is None

    def test_set_custom_results(self):
        config = YouTubeConfig()
        searcher = YouTubeSearcher(config)
        custom = [
            YouTubeVideo(id="custom1", title="Custom 1", url="https://youtube.com/watch?v=custom1"),
            YouTubeVideo(id="custom2", title="Custom 2", url="https://youtube.com/watch?v=custom2"),
        ]
        searcher.set_custom_results(custom)
        results = searcher.search("anything")
        assert len(results) == 2
        assert results[0].id == "custom1"

    def test_get_video_info_from_custom(self):
        config = YouTubeConfig()
        searcher = YouTubeSearcher(config)
        custom = [YouTubeVideo(id="myvid", title="My Video", url="https://youtube.com/watch?v=myvid")]
        searcher.set_custom_results(custom)
        video = searcher.get_video_info("myvid")
        assert video is not None
        assert video.title == "My Video"


class TestYouTubePlayer:
    """Verify playback management."""

    def test_play_by_id(self):
        config = YouTubeConfig()
        searcher = YouTubeSearcher(config)
        player = YouTubePlayer(config, searcher)
        assert player.play("dQw4w9WgXcQ") is True
        state = player.get_state()
        assert state.status == "playing"
        assert state.current_video is not None
        assert state.current_video.id == "dQw4w9WgXcQ"

    def test_play_by_video_object(self):
        config = YouTubeConfig()
        searcher = YouTubeSearcher(config)
        player = YouTubePlayer(config, searcher)
        video = YouTubeVideo(id="test1", title="Test", url="https://youtube.com/watch?v=test1")
        assert player.play(video) is True
        state = player.get_state()
        assert state.current_video.id == "test1"

    def test_play_invalid_id(self):
        config = YouTubeConfig()
        searcher = YouTubeSearcher(config)
        player = YouTubePlayer(config, searcher)
        assert player.play("nonexistent") is False

    def test_pause(self):
        config = YouTubeConfig()
        searcher = YouTubeSearcher(config)
        player = YouTubePlayer(config, searcher)
        player.play("dQw4w9WgXcQ")
        assert player.pause() is True
        assert player.get_state().status == "paused"

    def test_pause_when_stopped(self):
        config = YouTubeConfig()
        searcher = YouTubeSearcher(config)
        player = YouTubePlayer(config, searcher)
        assert player.pause() is False

    def test_resume(self):
        config = YouTubeConfig()
        searcher = YouTubeSearcher(config)
        player = YouTubePlayer(config, searcher)
        player.play("dQw4w9WgXcQ")
        player.pause()
        assert player.resume() is True
        assert player.get_state().status == "playing"

    def test_resume_when_not_paused(self):
        config = YouTubeConfig()
        searcher = YouTubeSearcher(config)
        player = YouTubePlayer(config, searcher)
        assert player.resume() is False

    def test_stop(self):
        config = YouTubeConfig()
        searcher = YouTubeSearcher(config)
        player = YouTubePlayer(config, searcher)
        player.play("dQw4w9WgXcQ")
        assert player.stop() is True
        state = player.get_state()
        assert state.status == "stopped"
        assert state.current_video is None

    def test_stop_when_stopped(self):
        config = YouTubeConfig()
        searcher = YouTubeSearcher(config)
        player = YouTubePlayer(config, searcher)
        assert player.stop() is False

    def test_seek(self):
        config = YouTubeConfig()
        searcher = YouTubeSearcher(config)
        player = YouTubePlayer(config, searcher)
        player.play("dQw4w9WgXcQ")
        assert player.seek(30.0) is True
        assert player.get_state().position_seconds == 30.0

    def test_seek_beyond_duration(self):
        config = YouTubeConfig()
        searcher = YouTubeSearcher(config)
        player = YouTubePlayer(config, searcher)
        player.play("dQw4w9WgXcQ")
        assert player.seek(9999.0) is True
        assert player.get_state().position_seconds == 212.0

    def test_seek_no_video(self):
        config = YouTubeConfig()
        searcher = YouTubeSearcher(config)
        player = YouTubePlayer(config, searcher)
        assert player.seek(10.0) is False

    def test_set_quality_valid(self):
        config = YouTubeConfig()
        searcher = YouTubeSearcher(config)
        player = YouTubePlayer(config, searcher)
        assert player.set_quality("720p") is True
        assert player.get_state().quality == "720p"

    def test_set_quality_invalid(self):
        config = YouTubeConfig()
        searcher = YouTubeSearcher(config)
        player = YouTubePlayer(config, searcher)
        assert player.set_quality("8k") is False

    def test_set_volume_valid(self):
        config = YouTubeConfig()
        searcher = YouTubeSearcher(config)
        player = YouTubePlayer(config, searcher)
        assert player.set_volume(75) is True
        assert player.get_state().volume == 75

    def test_set_volume_invalid(self):
        config = YouTubeConfig()
        searcher = YouTubeSearcher(config)
        player = YouTubePlayer(config, searcher)
        assert player.set_volume(150) is False
        assert player.set_volume(-1) is False

    def test_history(self):
        config = YouTubeConfig()
        searcher = YouTubeSearcher(config)
        player = YouTubePlayer(config, searcher)
        player.play("dQw4w9WgXcQ")
        player.play("9bZkp7q19f0")
        hist = player.history()
        assert len(hist) == 2
        assert hist[0].id == "dQw4w9WgXcQ"
        assert hist[1].id == "9bZkp7q19f0"

    def test_history_disabled(self):
        config = YouTubeConfig(enable_history=False)
        searcher = YouTubeSearcher(config)
        player = YouTubePlayer(config, searcher)
        player.play("dQw4w9WgXcQ")
        assert len(player.history()) == 0


class TestYouTubeControllerService:
    """Verify service wrapper."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        svc = YouTubeControllerService()
        assert await svc.initialize() is True

    @pytest.mark.asyncio
    async def test_shutdown(self):
        svc = YouTubeControllerService()
        await svc.initialize()
        await svc.shutdown()
        assert not svc.is_initialized()

    @pytest.mark.asyncio
    async def test_health(self):
        svc = YouTubeControllerService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"
        assert health["service_name"] == "jarvis_youtube"
        assert health["uptime_seconds"] >= 0

    @pytest.mark.asyncio
    async def test_stats(self):
        svc = YouTubeControllerService()
        await svc.initialize()
        stats = await svc.stats()
        assert stats["service"] == "jarvis_youtube"
        assert "metrics" in stats

    @pytest.mark.asyncio
    async def test_full_flow(self):
        svc = YouTubeControllerService()
        await svc.initialize()

        # Search
        results = await svc.search("never gonna")
        assert len(results) >= 1

        # Play
        assert await svc.play(results[0]) is True
        state = await svc.get_state()
        assert state.status == "playing"

        # Pause
        assert await svc.pause() is True
        state = await svc.get_state()
        assert state.status == "paused"

        # Resume
        assert await svc.resume() is True

        # Seek
        assert await svc.seek(10.0) is True

        # Quality
        assert await svc.set_quality("720p") is True
        assert await svc.set_quality("8k") is False

        # Volume
        assert await svc.set_volume(80) is True
        assert await svc.set_volume(200) is False

        # Stop
        assert await svc.stop() is True

        # History
        hist = await svc.history()
        assert len(hist) >= 1

        await svc.shutdown()
