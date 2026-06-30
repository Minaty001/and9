"""
Tests for Phase 18 — Media Controller.

Covers Track, PlaybackState, MediaPlayer, QueueManager,
and MediaControllerService with 18+ tests.
"""

import pytest
from services.phase18_media import (
    MediaControllerService,
    MediaConfig,
    Track,
    PlaybackState,
    MediaPlayer,
    QueueManager,
)


SAMPLE_TRACK_1 = Track(
    id="track_1",
    title="Test Song 1",
    artist="Test Artist",
    album="Test Album",
    duration_seconds=240.0,
    url="https://example.com/song1",
    service="local",
)

SAMPLE_TRACK_2 = Track(
    id="track_2",
    title="Test Song 2",
    artist="Test Artist",
    duration_seconds=180.0,
    url="https://example.com/song2",
    service="spotify",
)

SAMPLE_TRACK_3 = Track(
    id="track_3",
    title="Test Song 3",
    artist="Another Artist",
    duration_seconds=300.0,
    url="https://example.com/song3",
    service="youtube_music",
)


# ── Track Model ──────────────────────────────────────────────────────


class TestTrackModel:
    """Verify the Track model."""

    def test_track_creation(self):
        track = Track(id="1", title="Song")
        assert track.id == "1"
        assert track.title == "Song"
        assert track.artist == "Unknown Artist"
        assert track.duration_seconds == 0.0
        assert track.service == "local"

    def test_track_full(self):
        assert SAMPLE_TRACK_1.artist == "Test Artist"
        assert SAMPLE_TRACK_1.album == "Test Album"
        assert SAMPLE_TRACK_1.duration_seconds == 240.0

    def test_track_serde(self):
        data = SAMPLE_TRACK_1.model_dump()
        assert data["id"] == "track_1"
        restored = Track(**data)
        assert restored.id == SAMPLE_TRACK_1.id
        assert restored.title == SAMPLE_TRACK_1.title


# ── PlaybackState Model ──────────────────────────────────────────────


class TestPlaybackStateModel:
    """Verify the PlaybackState model."""

    def test_playback_state_defaults(self):
        state = PlaybackState()
        assert state.status == "stopped"
        assert state.current_track is None
        assert state.position_seconds == 0.0
        assert state.volume == 50
        assert state.queue == []
        assert state.shuffle is False
        assert state.repeat_mode == "off"

    def test_playback_state_with_track(self):
        state = PlaybackState(
            status="playing",
            current_track=SAMPLE_TRACK_1,
            position_seconds=30.0,
            volume=75,
        )
        assert state.status == "playing"
        assert state.current_track.id == "track_1"
        assert state.position_seconds == 30.0
        assert state.volume == 75


# ── MediaPlayer ──────────────────────────────────────────────────────


class TestMediaPlayer:
    """Verify playback control."""

    def test_play_with_track(self):
        player = MediaPlayer()
        result = player.play(SAMPLE_TRACK_1)
        assert result is True
        state = player.get_state()
        assert state.status == "playing"
        assert state.current_track.id == "track_1"

    def test_play_without_track_no_current(self):
        player = MediaPlayer()
        result = player.play()
        assert result is False  # No track loaded, no queue

    def test_pause(self):
        player = MediaPlayer()
        player.play(SAMPLE_TRACK_1)
        result = player.pause()
        assert result is True
        state = player.get_state()
        assert state.status == "paused"

    def test_pause_when_stopped(self):
        player = MediaPlayer()
        result = player.pause()
        assert result is False

    def test_resume(self):
        player = MediaPlayer()
        player.play(SAMPLE_TRACK_1)
        player.pause()
        result = player.resume()
        assert result is True
        state = player.get_state()
        assert state.status == "playing"

    def test_resume_when_not_paused(self):
        player = MediaPlayer()
        result = player.resume()
        assert result is False

    def test_stop(self):
        player = MediaPlayer()
        player.play(SAMPLE_TRACK_1)
        result = player.stop()
        assert result is True
        state = player.get_state()
        assert state.status == "stopped"
        assert state.position_seconds == 0.0

    def test_stop_when_stopped(self):
        player = MediaPlayer()
        result = player.stop()
        assert result is False

    def test_seek(self):
        player = MediaPlayer()
        player.play(SAMPLE_TRACK_1)
        result = player.seek(60.0)
        assert result is True
        state = player.get_state()
        assert state.position_seconds == 60.0

    def test_seek_beyond_duration(self):
        player = MediaPlayer()
        player.play(SAMPLE_TRACK_1)
        result = player.seek(9999.0)
        assert result is True
        state = player.get_state()
        assert state.position_seconds == SAMPLE_TRACK_1.duration_seconds

    def test_seek_no_track(self):
        player = MediaPlayer()
        result = player.seek(10.0)
        assert result is False

    def test_seek_negative_clamps_to_zero(self):
        player = MediaPlayer()
        player.play(SAMPLE_TRACK_1)
        player.seek(-10.0)
        state = player.get_state()
        assert state.position_seconds == 0.0

    def test_set_volume(self):
        player = MediaPlayer()
        result = player.set_volume(75)
        assert result is True
        assert player.get_state().volume == 75

    def test_set_volume_out_of_range(self):
        player = MediaPlayer()
        assert player.set_volume(-1) is False
        assert player.set_volume(101) is False
        assert player.get_state().volume == 50  # unchanged

    def test_get_state_returns_copy(self):
        player = MediaPlayer()
        player.play(SAMPLE_TRACK_1)
        state1 = player.get_state()
        state2 = player.get_state()
        assert state1.current_track.id == state2.current_track.id
        # Modifying copy shouldn't affect original
        state1.volume = 99
        assert player.get_state().volume == 50

    def test_next_always_succeeds_when_playing(self):
        player = MediaPlayer()
        player.play(SAMPLE_TRACK_1)
        assert player.next() is True

    def test_previous_always_succeeds_when_playing(self):
        player = MediaPlayer()
        player.play(SAMPLE_TRACK_1)
        assert player.previous() is True


# ── QueueManager ─────────────────────────────────────────────────────


class TestQueueManager:
    """Verify queue management."""

    def test_add_to_queue(self):
        qm = QueueManager()
        assert qm.add(SAMPLE_TRACK_1) is True
        assert qm.size == 1

    def test_add_at_position(self):
        qm = QueueManager()
        qm.add(SAMPLE_TRACK_1)
        qm.add(SAMPLE_TRACK_2, position=0)
        queue = qm.get_queue()
        assert queue[0].id == "track_2"
        assert queue[1].id == "track_1"

    def test_add_to_full_queue(self):
        qm = QueueManager(max_size=2)
        qm.add(SAMPLE_TRACK_1)
        qm.add(SAMPLE_TRACK_2)
        assert qm.add(SAMPLE_TRACK_3) is False

    def test_remove_by_index(self):
        qm = QueueManager()
        qm.add(SAMPLE_TRACK_1)
        qm.add(SAMPLE_TRACK_2)
        assert qm.remove(0) is True
        assert qm.size == 1

    def test_remove_invalid_index(self):
        qm = QueueManager()
        assert qm.remove(0) is False
        assert qm.remove(-1) is False

    def test_clear_queue(self):
        qm = QueueManager()
        qm.add(SAMPLE_TRACK_1)
        qm.add(SAMPLE_TRACK_2)
        assert qm.clear() is True
        assert qm.size == 0
        assert qm.is_empty is True

    def test_reorder(self):
        qm = QueueManager()
        qm.add(SAMPLE_TRACK_1)
        qm.add(SAMPLE_TRACK_2)
        qm.add(SAMPLE_TRACK_3)
        assert qm.reorder(0, 2) is True
        queue = qm.get_queue()
        assert queue[0].id == "track_2"
        assert queue[2].id == "track_1"

    def test_reorder_invalid_indices(self):
        qm = QueueManager()
        qm.add(SAMPLE_TRACK_1)
        assert qm.reorder(-1, 0) is False
        assert qm.reorder(0, 5) is False

    def test_set_shuffle(self):
        qm = QueueManager()
        qm.add(SAMPLE_TRACK_1)
        qm.add(SAMPLE_TRACK_2)
        qm.add(SAMPLE_TRACK_3)
        assert qm.set_shuffle(True) is True
        assert qm.shuffle is True

    def test_set_shuffle_restores_order(self):
        qm = QueueManager()
        qm.add(SAMPLE_TRACK_1)
        qm.add(SAMPLE_TRACK_2)
        qm.add(SAMPLE_TRACK_3)
        original_ids = [t.id for t in qm.get_queue()]
        qm.set_shuffle(True)
        qm.set_shuffle(False)
        restored_ids = [t.id for t in qm.get_queue()]
        assert restored_ids == original_ids

    def test_set_repeat_valid(self):
        qm = QueueManager()
        assert qm.set_repeat("one") is True
        assert qm.repeat_mode == "one"
        assert qm.set_repeat("all") is True
        assert qm.set_repeat("off") is True

    def test_set_repeat_invalid(self):
        qm = QueueManager()
        assert qm.set_repeat("invalid") is False
        assert qm.repeat_mode == "off"

    def test_get_queue_returns_copy(self):
        qm = QueueManager()
        qm.add(SAMPLE_TRACK_1)
        queue = qm.get_queue()
        queue.append(SAMPLE_TRACK_2)
        assert qm.size == 1  # Original unchanged


# ── MediaControllerService ───────────────────────────────────────────


class TestMediaControllerService:
    """Verify the service wrapper lifecycle and playback actions."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        svc = MediaControllerService()
        result = await svc.initialize()
        assert result is True
        assert svc.is_initialized() is True

    @pytest.mark.asyncio
    async def test_health_uninitialized(self):
        svc = MediaControllerService()
        health = await svc.health()
        assert health["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_health_healthy(self):
        svc = MediaControllerService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"
        assert health["service_name"] == "jarvis_media"

    @pytest.mark.asyncio
    async def test_stats(self):
        svc = MediaControllerService()
        await svc.initialize()
        stats = await svc.stats()
        assert stats["service"] == "jarvis_media"
        assert "metrics" in stats
        assert "queue_size" in stats

    @pytest.mark.asyncio
    async def test_play_with_track(self):
        svc = MediaControllerService()
        await svc.initialize()
        result = await svc.play(SAMPLE_TRACK_1)
        assert result is True
        state = await svc.get_state()
        assert state.status == "playing"
        assert state.current_track.id == "track_1"

    @pytest.mark.asyncio
    async def test_pause_resume(self):
        svc = MediaControllerService()
        await svc.initialize()
        await svc.play(SAMPLE_TRACK_1)
        pause_result = await svc.pause()
        assert pause_result is True
        state = await svc.get_state()
        assert state.status == "paused"
        resume_result = await svc.resume()
        assert resume_result is True
        state = await svc.get_state()
        assert state.status == "playing"

    @pytest.mark.asyncio
    async def test_stop(self):
        svc = MediaControllerService()
        await svc.initialize()
        await svc.play(SAMPLE_TRACK_1)
        result = await svc.stop()
        assert result is True
        state = await svc.get_state()
        assert state.status == "stopped"

    @pytest.mark.asyncio
    async def test_seek(self):
        svc = MediaControllerService()
        await svc.initialize()
        await svc.play(SAMPLE_TRACK_1)
        result = await svc.seek(45.0)
        assert result is True
        state = await svc.get_state()
        assert state.position_seconds == 45.0

    @pytest.mark.asyncio
    async def test_set_volume(self):
        svc = MediaControllerService()
        await svc.initialize()
        result = await svc.set_volume(80)
        assert result is True
        state = await svc.get_state()
        assert state.volume == 80

    @pytest.mark.asyncio
    async def test_queue_add_and_remove(self):
        svc = MediaControllerService()
        await svc.initialize()
        assert await svc.queue_add(SAMPLE_TRACK_1) is True
        assert await svc.queue_add(SAMPLE_TRACK_2) is True
        queue = await svc.queue_get()
        assert len(queue) == 2
        assert await svc.queue_remove(0) is True
        queue = await svc.queue_get()
        assert len(queue) == 1

    @pytest.mark.asyncio
    async def test_queue_clear(self):
        svc = MediaControllerService()
        await svc.initialize()
        await svc.queue_add(SAMPLE_TRACK_1)
        await svc.queue_add(SAMPLE_TRACK_2)
        assert await svc.queue_clear() is True
        queue = await svc.queue_get()
        assert queue == []

    @pytest.mark.asyncio
    async def test_queue_reorder(self):
        svc = MediaControllerService()
        await svc.initialize()
        await svc.queue_add(SAMPLE_TRACK_1)
        await svc.queue_add(SAMPLE_TRACK_2)
        await svc.queue_add(SAMPLE_TRACK_3)
        assert await svc.queue_reorder(0, 2) is True
        queue = await svc.queue_get()
        assert queue[0].id == "track_2"
        assert queue[2].id == "track_1"

    @pytest.mark.asyncio
    async def test_shuffle_and_repeat(self):
        svc = MediaControllerService()
        await svc.initialize()
        assert await svc.set_shuffle(True) is True
        state = await svc.get_state()
        assert state.shuffle is True
        assert await svc.set_repeat("all") is True
        state = await svc.get_state()
        assert state.repeat_mode == "all"

    @pytest.mark.asyncio
    async def test_full_playback_cycle(self):
        """Test a complete media playback cycle."""
        svc = MediaControllerService()
        await svc.initialize()

        # Add tracks to queue
        await svc.queue_add(SAMPLE_TRACK_1)
        await svc.queue_add(SAMPLE_TRACK_2)
        await svc.queue_add(SAMPLE_TRACK_3)

        # Play
        assert await svc.play(SAMPLE_TRACK_1) is True
        state = await svc.get_state()
        assert state.status == "playing"

        # Seek
        assert await svc.seek(30.0) is True

        # Pause
        assert await svc.pause() is True
        assert await svc.resume() is True

        # Volume
        assert await svc.set_volume(60) is True

        # Next / Previous
        assert await svc.next() is True
        assert await svc.previous() is True

        # Stop
        assert await svc.stop() is True

        # Health
        health = await svc.health()
        assert health["status"] == "healthy"

        # Shutdown
        await svc.shutdown()
        assert svc.is_initialized() is False
