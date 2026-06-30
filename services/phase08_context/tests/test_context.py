"""
Tests for Phase 8 — Context Builder.
"""

import pytest
from services.phase08_context import (
    ContextManager,
    ContextBuilderService,
    ContextConfig,
    TurnContext,
    ContextSnapshot,
)


class TestTurnContext:
    """Verify TurnContext model."""

    def test_create_turn(self):
        turn = TurnContext(turn_id=0, query="hello")
        assert turn.turn_id == 0
        assert turn.query == "hello"
        assert turn.intent == ""
        assert turn.entities == {}

    def test_age_seconds(self):
        from datetime import datetime, timezone, timedelta
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        turn = TurnContext(turn_id=0, query="test", timestamp=future)
        # the timestamps are in the future, so age will be negative
        age = turn.age_seconds(datetime.now(timezone.utc))
        assert age < 0  # timestamp is in the future

    def test_decay_factor(self):
        turn = TurnContext(turn_id=0, query="test")
        factor = turn.decay_factor(0.85)
        assert 0.0 < factor <= 1.0


class TestContextManager:
    """Verify sliding window, decay, search, and pruning."""

    def test_add_turn(self):
        mgr = ContextManager()
        turn = mgr.add_turn(query="hello world", intent="greeting")
        assert turn.turn_id == 0
        assert turn.query == "hello world"
        assert mgr.get_turn_count() == 1

    def test_sliding_window(self):
        mgr = ContextManager(ContextConfig(max_turns=3))
        for i in range(5):
            mgr.add_turn(query=f"turn {i}", intent=f"intent_{i}")
        assert mgr.get_turn_count() == 5
        snapshot = mgr.get_snapshot()
        assert len(snapshot.recent_turns) == 3  # only 3 kept

    def test_entity_tracking(self):
        mgr = ContextManager()
        mgr.add_turn(query="weather in delhi", entities={"location": ["Delhi"]})
        mgr.add_turn(query="weather in mumbai", entities={"location": ["Mumbai"]})
        snapshot = mgr.get_snapshot()
        assert "location" in snapshot.active_entities
        assert "Delhi" in snapshot.active_entities["location"]
        assert "Mumbai" in snapshot.active_entities["location"]

    def test_relevance_search(self):
        mgr = ContextManager()
        mgr.add_turn(query="what's the weather", intent="weather_query", entities={"location": ["Delhi"]})
        mgr.add_turn(query="play despacito", intent="play_music", entities={"media": ["despacito"]})
        results = mgr.search_relevant("weather in delhi", top_k=3)
        assert len(results) >= 1
        # The weather turn should score highest
        top = results[0]
        assert top.turn.intent == "weather_query"

    def test_search_empty(self):
        mgr = ContextManager()
        results = mgr.search_relevant("hello", top_k=3)
        assert results == []

    def test_clear(self):
        mgr = ContextManager()
        mgr.add_turn(query="hello")
        mgr.clear()
        assert mgr.get_turn_count() == 0
        snapshot = mgr.get_snapshot()
        assert len(snapshot.recent_turns) == 0

    def test_prune_low_relevance(self):
        mgr = ContextManager(ContextConfig(relevance_threshold=0.9))
        for i in range(10):
            mgr.add_turn(query=f"turn {i}", intent=f"intent_{i}" if i < 3 else "")
        snapshot = mgr.get_snapshot()
        # Should keep at least 3 (min_keep)
        assert len(snapshot.recent_turns) >= 3


class TestContextBuilderService:
    """Verify service wrapper."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        svc = ContextBuilderService()
        result = await svc.initialize()
        assert result is True
        assert svc.is_initialized()

    @pytest.mark.asyncio
    async def test_process(self):
        svc = ContextBuilderService()
        await svc.initialize()
        snapshot = await svc.process("hello", intent="greeting")
        assert isinstance(snapshot, ContextSnapshot)
        assert snapshot.turn_count == 1
        assert snapshot.current_turn is not None
        assert snapshot.current_turn.query == "hello"

    @pytest.mark.asyncio
    async def test_process_with_entities(self):
        svc = ContextBuilderService()
        await svc.initialize()
        snapshot = await svc.process(
            "weather in delhi",
            intent="weather_query",
            entities={"location": ["Delhi"]},
        )
        assert snapshot.turn_count == 1
        assert "location" in snapshot.active_entities

    @pytest.mark.asyncio
    async def test_multi_turn_context(self):
        svc = ContextBuilderService(ContextConfig(max_turns=2))
        await svc.initialize()
        await svc.process("first turn", intent="intent_a")
        s2 = await svc.process("second turn", intent="intent_b")
        assert s2.recent_intents == ["intent_a", "intent_b"]
        # Add a third
        s3 = await svc.process("third turn", intent="intent_c")
        assert len(s3.recent_turns) == 2  # max_turns=2
        assert "intent_b" in s3.recent_intents
        assert "intent_c" in s3.recent_intents

    @pytest.mark.asyncio
    async def test_search(self):
        svc = ContextBuilderService()
        await svc.initialize()
        await svc.process("weather in delhi", intent="weather_query")
        await svc.process("play despacito", intent="play_music")
        results = await svc.search("delhi weather", top_k=3)
        assert len(results) >= 1
        assert results[0].turn.intent == "weather_query"

    @pytest.mark.asyncio
    async def test_get_context(self):
        svc = ContextBuilderService()
        await svc.initialize()
        ctx = await svc.get_context()
        assert ctx.turn_count == 0
        await svc.process("hello")
        ctx = await svc.get_context()
        assert ctx.turn_count == 1

    @pytest.mark.asyncio
    async def test_clear(self):
        svc = ContextBuilderService()
        await svc.initialize()
        await svc.process("hello")
        await svc.clear()
        ctx = await svc.get_context()
        assert ctx.turn_count == 0

    @pytest.mark.asyncio
    async def test_health(self):
        svc = ContextBuilderService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"
        assert "turns_processed" in health

    @pytest.mark.asyncio
    async def test_shutdown(self):
        svc = ContextBuilderService()
        await svc.initialize()
        await svc.shutdown()
        assert not svc.is_initialized()
