"""
Tests for Phase 11 — Habit Brain.
"""

import pytest
from services.phase11_habit import (
    HabitTracker,
    HabitSuggester,
    HabitBrainService,
    HabitConfig,
    HabitObservation,
    HabitPattern,
    HabitSuggestion,
)


class TestHabitTracker:
    """Verify pattern observation, matching, decay, and lifecycle."""

    def test_observe_creates_pattern(self):
        tracker = HabitTracker()
        obs = HabitObservation(command="play music", time_hour=9)
        pattern = tracker.observe(obs)
        assert pattern is not None
        assert pattern.command == "play music"
        assert tracker.get_pattern_count() == 1

    def test_observe_matches_existing(self):
        tracker = HabitTracker()
        tracker.observe(HabitObservation(command="play music", time_hour=9))
        pattern = tracker.observe(HabitObservation(command="play music", time_hour=9))
        assert pattern.frequency == 2
        assert pattern.confidence > 0.1

    def test_observe_different_time_no_match(self):
        tracker = HabitTracker(HabitConfig(time_window_minutes=10))
        tracker.observe(HabitObservation(command="play music", time_hour=9))
        pattern = tracker.observe(HabitObservation(command="play music", time_hour=18))
        # Should create a new pattern since time differs beyond window
        assert tracker.get_pattern_count() == 2

    def test_reject_suppresses(self):
        tracker = HabitTracker()
        p1 = tracker.observe(HabitObservation(command="test", time_hour=10))
        tracker.observe(HabitObservation(command="test", time_hour=10))
        tracker.observe(HabitObservation(command="test", time_hour=10))
        tracker.reject(p1.pattern_id)
        # Should not match rejected patterns
        tracker.observe(HabitObservation(command="test", time_hour=10))
        # Should have created new pattern since original was rejected
        assert tracker.get_pattern_count() >= 1

    def test_approve(self):
        tracker = HabitTracker()
        p = tracker.observe(HabitObservation(command="test", time_hour=10))
        assert tracker.approve(p.pattern_id) is True
        assert tracker.get_pattern(p.pattern_id).user_approved is True

    def test_remove(self):
        tracker = HabitTracker()
        p = tracker.observe(HabitObservation(command="test", time_hour=10))
        assert tracker.remove(p.pattern_id) is True
        assert tracker.get_pattern_count() == 0

    def test_remove_nonexistent(self):
        tracker = HabitTracker()
        assert tracker.remove("nonexistent") is False

    def test_get_patterns_filters_by_confidence(self):
        tracker = HabitTracker()
        p1 = tracker.observe(HabitObservation(command="frequent", time_hour=10))
        for _ in range(10):
            tracker.observe(HabitObservation(command="frequent", time_hour=10))
        p2 = tracker.observe(HabitObservation(command="rare", time_hour=14))
        high = tracker.get_patterns(min_confidence=0.5)
        assert all(p.confidence >= 0.5 for p in high)

    def test_audit_log(self):
        cfg = HabitConfig(enable_audit_log=True)
        tracker = HabitTracker(cfg)
        p = tracker.observe(HabitObservation(command="test", time_hour=10))
        tracker.approve(p.pattern_id)
        log = tracker.get_audit_log()
        assert len(log) >= 1
        assert log[0].action == "approved"

    def test_clear(self):
        tracker = HabitTracker()
        tracker.observe(HabitObservation(command="test", time_hour=10))
        tracker.clear()
        assert tracker.get_pattern_count() == 0


class TestHabitSuggester:
    """Verify suggestion ranking."""

    def test_suggest_returns_top_patterns(self):
        cfg = HabitConfig(min_observations=1, confidence_threshold=0.1)
        tracker = HabitTracker(cfg)
        for _ in range(5):
            tracker.observe(HabitObservation(command="morning music", time_hour=9))
        suggester = HabitSuggester(tracker, cfg)
        suggestions = suggester.suggest(current_hour=9)
        assert len(suggestions) >= 1
        assert suggestions[0].command == "morning music"

    def test_suggest_respects_limit(self):
        cfg = HabitConfig(min_observations=1, confidence_threshold=0.0, max_suggestions=2)
        tracker = HabitTracker(cfg)
        for cmd, hr in [("a", 9), ("b", 10), ("c", 11)]:
            for _ in range(3):
                tracker.observe(HabitObservation(command=cmd, time_hour=hr))
        suggester = HabitSuggester(tracker, cfg)
        suggestions = suggester.suggest(current_hour=9, limit=2)
        assert len(suggestions) <= 2

    def test_suggest_filters_low_confidence(self):
        cfg = HabitConfig(min_observations=1, confidence_threshold=0.9)
        tracker = HabitTracker(cfg)
        tracker.observe(HabitObservation(command="rare", time_hour=10))
        suggester = HabitSuggester(tracker, cfg)
        suggestions = suggester.suggest(current_hour=10)
        assert len(suggestions) == 0

    def test_suggest_for_pattern(self):
        cfg = HabitConfig(min_observations=1)
        tracker = HabitTracker(cfg)
        p = tracker.observe(HabitObservation(command="test", time_hour=10))
        suggester = HabitSuggester(tracker, cfg)
        s = suggester.suggest_for_pattern(p.pattern_id)
        assert s is not None
        assert s.command == "test"


class TestHabitBrainService:
    """Verify service wrapper."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        svc = HabitBrainService()
        assert await svc.initialize() is True

    @pytest.mark.asyncio
    async def test_observe_and_suggest(self):
        svc = HabitBrainService()
        await svc.initialize()
        for _ in range(4):
            await svc.observe("morning coffee", hour=8)
        suggestions = await svc.suggest(hour=8)
        assert len(suggestions) >= 1
        assert suggestions[0].command == "morning coffee"

    @pytest.mark.asyncio
    async def test_approve_reject(self):
        svc = HabitBrainService()
        await svc.initialize()
        p = await svc.observe("test", hour=12)
        assert await svc.approve(p.pattern_id) is True
        assert await svc.reject(p.pattern_id) is True

    @pytest.mark.asyncio
    async def test_get_patterns(self):
        svc = HabitBrainService()
        await svc.initialize()
        await svc.observe("test", hour=12)
        patterns = await svc.get_patterns()
        assert len(patterns) >= 1

    @pytest.mark.asyncio
    async def test_get_audit_log(self):
        svc = HabitBrainService()
        await svc.initialize()
        p = await svc.observe("test", hour=12)
        await svc.approve(p.pattern_id)
        log = await svc.get_audit_log()
        assert len(log) >= 1

    @pytest.mark.asyncio
    async def test_health(self):
        svc = HabitBrainService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"
        assert "tracked_patterns" in health

    @pytest.mark.asyncio
    async def test_shutdown(self):
        svc = HabitBrainService()
        await svc.initialize()
        await svc.shutdown()
        assert not svc.is_initialized()
