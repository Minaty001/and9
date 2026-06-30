"""
Tests for Phase 26 — Learning Engine.
"""

import pytest
from services.phase26_learning import (
    PreferenceLearner,
    PatternLearner,
    ActivitySummarizer,
    LearningEngineService,
    LearningConfig,
    LearningObservation,
    LearnedPreference,
    LearnedPattern,
    ActivitySummary,
)


class TestPreferenceLearner:
    """Verify preference observation, retrieval, and management."""

    def test_observe_creates_preference(self):
        learner = PreferenceLearner()
        pref = learner.observe("theme", "color", "dark")
        assert pref.category == "theme"
        assert pref.key == "color"
        assert pref.preferred_value == "dark"
        assert pref.confidence == 1.0

    def test_observe_updates_existing(self):
        learner = PreferenceLearner()
        learner.observe("theme", "color", "dark", confidence=0.8)
        pref = learner.observe("theme", "color", "dark", confidence=1.0)
        assert pref.observation_count == 2
        assert 0.8 < pref.confidence < 1.0  # moved due to EMA

    def test_get_preference_found(self):
        learner = PreferenceLearner()
        learner.observe("notifications", "sound", True)
        pref = learner.get_preference("notifications", "sound")
        assert pref is not None
        assert pref.preferred_value is True

    def test_get_preference_not_found(self):
        learner = PreferenceLearner()
        pref = learner.get_preference("nonexistent", "key")
        assert pref is None

    def test_get_all_preferences(self):
        learner = PreferenceLearner()
        learner.observe("a", "k1", "v1")
        learner.observe("a", "k2", "v2")
        learner.observe("b", "k3", "v3")
        all_prefs = learner.get_all_preferences()
        assert len(all_prefs) == 3
        cat_prefs = learner.get_all_preferences("a")
        assert len(cat_prefs) == 2

    def test_forget_preference(self):
        learner = PreferenceLearner()
        learner.observe("test", "key", "val")
        assert learner.forget_preference("test", "key") is True
        assert learner.get_preference("test", "key") is None

    def test_forget_preference_nonexistent(self):
        learner = PreferenceLearner()
        assert learner.forget_preference("x", "y") is False

    def test_clear(self):
        learner = PreferenceLearner()
        learner.observe("a", "b", "c")
        learner.clear()
        assert learner.get_observation_count() == 0

    def test_observations_context(self):
        learner = PreferenceLearner()
        pref = learner.observe("test", "key", "val", {"time": "morning"})
        assert pref.context_conditions.get("time") == "morning"


class TestPatternLearner:
    """Verify pattern recording, matching, and success tracking."""

    def test_record_creates_pattern(self):
        learner = PatternLearner()
        pattern = learner.record("morning", "play music")
        assert pattern.trigger == "morning"
        assert pattern.action == "play music"
        assert pattern.frequency == 1

    def test_record_updates_existing(self):
        learner = PatternLearner()
        learner.record("morning", "play music")
        pattern = learner.record("morning", "play music")
        assert pattern.frequency == 2

    def test_find_matching_patterns(self):
        learner = PatternLearner()
        learner.record("morning", "play music", {"time": "08:00", "day": "weekday"})
        matches = learner.find_matching_patterns({"time": "08:00", "day": "weekday"})
        assert len(matches) >= 1
        assert matches[0].action == "play music"

    def test_find_matching_patterns_no_match(self):
        learner = PatternLearner()
        learner.record("morning", "play music", {"time": "08:00"})
        matches = learner.find_matching_patterns({"time": "23:00"})
        assert len(matches) == 0

    def test_get_patterns(self):
        learner = PatternLearner()
        learner.record("morning", "a")
        learner.record("evening", "b")
        assert len(learner.get_patterns()) == 2

    def test_calculate_success_rate(self):
        learner = PatternLearner()
        p = learner.record("test", "action", success=True)
        learner.record("test", "action", success=True)
        learner.record("test", "action", success=False)
        rate = learner.calculate_success_rate(p.pattern_id)
        assert 0.66 < rate < 0.67

    def test_remove_pattern(self):
        learner = PatternLearner()
        p = learner.record("test", "action")
        assert learner.remove_pattern(p.pattern_id) is True
        assert learner.get_pattern_count() == 0

    def test_clear(self):
        learner = PatternLearner()
        learner.record("a", "b")
        learner.clear()
        assert learner.get_pattern_count() == 0


class TestActivitySummarizer:
    """Verify summary generation."""

    def test_generate_daily_summary_empty(self):
        summarizer = ActivitySummarizer()
        summary = summarizer.generate_summary("daily")
        assert summary.period == "daily"
        assert summary.total_interactions == 0

    def test_generate_summary_with_observations(self):
        summarizer = ActivitySummarizer()
        from datetime import datetime, timezone
        obs = LearningObservation(
            observation_type="preference",
            category="test",
            key="k",
            value="v",
            context={"intent": "greeting", "query": "hello"},
        )
        summarizer.add_observation(obs)
        summary = summarizer.generate_summary("daily")
        assert summary.total_interactions >= 1
        assert len(summary.top_intents) > 0

    def test_generate_weekly_summary(self):
        summarizer = ActivitySummarizer()
        summary = summarizer.generate_summary("weekly")
        assert summary.period == "weekly"

    def test_clear(self):
        summarizer = ActivitySummarizer()
        summarizer.add_observation(LearningObservation(
            observation_type="feedback", category="t", key="k", value="v"
        ))
        summarizer.clear()
        assert summarizer.get_observation_count() == 0


class TestLearningEngineService:
    """Verify service wrapper."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        svc = LearningEngineService()
        assert await svc.initialize() is True

    @pytest.mark.asyncio
    async def test_observe_and_get_preference(self):
        svc = LearningEngineService()
        await svc.initialize()
        pref = await svc.observe("theme", "color", "dark")
        assert pref.preferred_value == "dark"
        retrieved = await svc.get_preference("theme", "color")
        assert retrieved is not None

    @pytest.mark.asyncio
    async def test_get_all_preferences(self):
        svc = LearningEngineService()
        await svc.initialize()
        await svc.observe("a", "k1", "v1")
        await svc.observe("a", "k2", "v2")
        all_prefs = await svc.get_all_preferences()
        assert len(all_prefs) == 2

    @pytest.mark.asyncio
    async def test_forget_preference(self):
        svc = LearningEngineService()
        await svc.initialize()
        await svc.observe("a", "b", "c")
        assert await svc.forget_preference("a", "b") is True

    @pytest.mark.asyncio
    async def test_record_and_find_patterns(self):
        svc = LearningEngineService()
        await svc.initialize()
        p = await svc.record_pattern("morning", "coffee", {"time": "08:00"})
        assert p.trigger == "morning"
        matches = await svc.find_patterns({"time": "08:00"})
        assert len(matches) >= 1

    @pytest.mark.asyncio
    async def test_generate_summary(self):
        svc = LearningEngineService()
        await svc.initialize()
        summary = await svc.generate_summary("daily")
        assert summary.period == "daily"

    @pytest.mark.asyncio
    async def test_health(self):
        svc = LearningEngineService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"
        assert "preferences_count" in health

    @pytest.mark.asyncio
    async def test_stats(self):
        svc = LearningEngineService()
        await svc.initialize()
        stats = await svc.stats()
        assert stats["service"] == "jarvis_learning"
        assert "metrics" in stats

    @pytest.mark.asyncio
    async def test_shutdown(self):
        svc = LearningEngineService()
        await svc.initialize()
        await svc.shutdown()
        assert not svc.is_initialized()

    @pytest.mark.asyncio
    async def test_get_patterns(self):
        svc = LearningEngineService()
        await svc.initialize()
        await svc.record_pattern("test", "action")
        patterns = await svc.get_patterns()
        assert len(patterns) >= 1
