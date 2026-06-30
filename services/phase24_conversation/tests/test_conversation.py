"""
Tests for Phase 24 — Conversation Manager.
"""

import time
import pytest
from services.phase24_conversation import (
    ConversationConfig,
    DialogueState,
    Session,
    SessionManager,
    DialogueTracker,
    ReferenceResolver,
    ConversationManagerService,
)


class TestConversationConfig:
    """Verify ConversationConfig creation."""

    def test_default_config(self):
        config = ConversationConfig()
        assert config.service_name == "jarvis_conversation"
        assert config.max_session_duration_minutes == 30
        assert config.session_timeout_seconds == 1800

    def test_custom_config(self):
        config = ConversationConfig(
            max_turns_per_session=50,
            enable_reference_resolution=False,
        )
        assert config.max_turns_per_session == 50
        assert config.enable_reference_resolution is False

    def test_env_prefix(self):
        assert ConversationConfig.model_config["env_prefix"] == "JARVIS_PHASE24_"


class TestDialogueState:
    """Verify DialogueState creation."""

    def test_create_state(self):
        state = DialogueState(session_id="sess_001")
        assert state.session_id == "sess_001"
        assert state.turn_count == 0
        assert state.active_topic == "general"

    def test_state_with_values(self):
        state = DialogueState(
            session_id="sess_002",
            turn_count=5,
            active_topic="weather",
            user_goal="check_weather",
        )
        assert state.turn_count == 5
        assert state.active_topic == "weather"
        assert state.user_goal == "check_weather"


class TestSession:
    """Verify Session creation."""

    def test_create_session(self):
        session = Session(id="sess_001")
        assert session.id == "sess_001"
        assert session.active is True
        assert session.dialogue_states == []

    def test_session_with_metadata(self):
        session = Session(id="sess_002", metadata={"user": "test"})
        assert session.metadata["user"] == "test"
        assert session.active is True


class TestSessionManager:
    """Verify SessionManager behavior."""

    def test_create_session(self):
        mgr = SessionManager()
        session = mgr.create_session()
        assert session.id is not None
        assert session.active is True

    def test_create_session_with_metadata(self):
        mgr = SessionManager()
        session = mgr.create_session(metadata={"source": "web"})
        assert session.metadata["source"] == "web"

    def test_get_session(self):
        mgr = SessionManager()
        session = mgr.create_session()
        retrieved = mgr.get_session(session.id)
        assert retrieved is not None
        assert retrieved.id == session.id

    def test_get_nonexistent_session(self):
        mgr = SessionManager()
        assert mgr.get_session("nonexistent") is None

    def test_end_session(self):
        mgr = SessionManager()
        session = mgr.create_session()
        assert mgr.end_session(session.id) is True
        assert mgr.get_session(session.id) is None

    def test_end_nonexistent_session(self):
        mgr = SessionManager()
        assert mgr.end_session("nonexistent") is False

    def test_list_active_sessions(self):
        mgr = SessionManager()
        s1 = mgr.create_session()
        s2 = mgr.create_session()
        mgr.end_session(s1.id)

        active = mgr.list_active_sessions()
        assert len(active) == 1
        assert active[0].id == s2.id

    def test_timeout_check(self):
        mgr = SessionManager(session_timeout_seconds=0)
        session = mgr.create_session()
        time.sleep(0.01)
        expired = mgr.timeout_check()
        assert expired >= 1
        assert mgr.get_session(session.id) is None

    def test_add_dialogue_state(self):
        mgr = SessionManager()
        session = mgr.create_session()
        state = DialogueState(session_id=session.id)
        assert mgr.add_dialogue_state(session.id, state) is True
        assert len(session.dialogue_states) == 1

    def test_add_dialogue_state_inactive(self):
        mgr = SessionManager()
        session = mgr.create_session()
        mgr.end_session(session.id)
        state = DialogueState(session_id=session.id)
        assert mgr.add_dialogue_state(session.id, state) is False

    def test_get_dialogue_state(self):
        mgr = SessionManager()
        session = mgr.create_session()
        state = DialogueState(session_id=session.id, active_topic="weather")
        mgr.add_dialogue_state(session.id, state)
        retrieved = mgr.get_dialogue_state(session.id)
        assert retrieved is not None
        assert retrieved.active_topic == "weather"


class TestDialogueTracker:
    """Verify DialogueTracker behavior."""

    def test_update_state(self):
        tracker = DialogueTracker()
        state = tracker.update_state("sess_001", "What's the weather like?")
        assert state.session_id == "sess_001"
        assert state.active_topic == "weather"

    def test_detect_topic_weather(self):
        tracker = DialogueTracker()
        assert tracker.detect_topic("What is the temperature?") == "weather"

    def test_detect_topic_news(self):
        tracker = DialogueTracker()
        assert tracker.detect_topic("Latest headlines") == "news"

    def test_detect_topic_greeting(self):
        tracker = DialogueTracker()
        assert tracker.detect_topic("Hello there") == "greeting"

    def test_detect_topic_general(self):
        tracker = DialogueTracker()
        assert tracker.detect_topic("Some random text") == "general"

    def test_update_state_with_entities(self):
        tracker = DialogueTracker()
        state = tracker.update_state(
            "sess_001",
            "What's the weather in Mumbai?",
            entities={"location": "Mumbai"},
        )
        assert state.recent_entities.get("location") == "Mumbai"

    def test_track_goal(self):
        tracker = DialogueTracker()
        assert tracker.track_goal("sess_001", "find_weather") is True

    def test_add_pending_question(self):
        tracker = DialogueTracker()
        assert tracker.add_pending_question("sess_001", "What is your name?") is True

    def test_extract_entities_location(self):
        tracker = DialogueTracker()
        entities = tracker.extract_entities("Weather in Mumbai")
        assert entities.get("location") == "Mumbai"

    def test_extract_entities_language(self):
        tracker = DialogueTracker()
        entities = tracker.extract_entities("Python programming")
        assert entities.get("language") == "Python"


class TestReferenceResolver:
    """Verify ReferenceResolver behavior."""

    def test_resolve_pronoun(self):
        resolver = ReferenceResolver()
        state = DialogueState(
            session_id="sess_001",
            references={"location": "Mumbai"},
        )
        resolved = resolver.resolve("it", "sess_001", [state])
        assert resolved == "Mumbai"

    def test_resolve_unresolved(self):
        resolver = ReferenceResolver()
        resolved = resolver.resolve("it", "sess_001", [])
        assert resolved == "it"  # Returns original if unresolved

    def test_resolve_non_reference(self):
        resolver = ReferenceResolver()
        resolved = resolver.resolve("python", "sess_001", [])
        assert resolved == "python"

    def test_resolve_from_entities(self):
        resolver = ReferenceResolver()
        state = DialogueState(
            session_id="sess_001",
            recent_entities={"location": "Delhi"},
        )
        resolved = resolver.resolve("there", "sess_001", [state])
        assert resolved == "Delhi"

    def test_resolve_from_topic(self):
        resolver = ReferenceResolver()
        state = DialogueState(
            session_id="sess_001",
            active_topic="weather",
        )
        resolved = resolver.resolve("it", "sess_001", [state])
        assert resolved == "weather"

    def test_extract_references(self):
        resolver = ReferenceResolver()
        refs = resolver.extract_references("What is it and how does that work?")
        assert "it" in refs
        assert "that" in refs

    def test_extract_references_no_refs(self):
        resolver = ReferenceResolver()
        refs = resolver.extract_references("Hello world")
        assert len(refs) == 0


class TestConversationManagerService:
    """Verify service wrapper."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        svc = ConversationManagerService()
        assert await svc.initialize() is True

    @pytest.mark.asyncio
    async def test_shutdown(self):
        svc = ConversationManagerService()
        await svc.initialize()
        await svc.shutdown()
        assert not svc.is_initialized()

    @pytest.mark.asyncio
    async def test_health(self):
        svc = ConversationManagerService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"
        assert health["service_name"] == "jarvis_conversation"

    @pytest.mark.asyncio
    async def test_stats(self):
        svc = ConversationManagerService()
        await svc.initialize()
        stats = await svc.stats()
        assert stats["service"] == "jarvis_conversation"
        assert "metrics" in stats

    @pytest.mark.asyncio
    async def test_create_session(self):
        svc = ConversationManagerService()
        await svc.initialize()
        session = await svc.create_session()
        assert session.id is not None
        assert session.active is True

    @pytest.mark.asyncio
    async def test_get_session(self):
        svc = ConversationManagerService()
        await svc.initialize()
        session = await svc.create_session()
        retrieved = await svc.get_session(session.id)
        assert retrieved is not None
        assert retrieved.id == session.id

    @pytest.mark.asyncio
    async def test_end_session(self):
        svc = ConversationManagerService()
        await svc.initialize()
        session = await svc.create_session()
        assert await svc.end_session(session.id) is True
        assert await svc.get_session(session.id) is None

    @pytest.mark.asyncio
    async def test_process_turn(self):
        svc = ConversationManagerService()
        await svc.initialize()
        session = await svc.create_session()
        state = await svc.process_turn(session.id, "What's the weather?")
        assert state.active_topic == "weather"
        assert state.turn_count == 1

    @pytest.mark.asyncio
    async def test_process_turn_with_intent(self):
        svc = ConversationManagerService()
        await svc.initialize()
        session = await svc.create_session()
        state = await svc.process_turn(
            session.id,
            "What's the weather?",
            intent="weather_query",
            entities={"location": "Mumbai"},
        )
        assert state.active_topic == "weather"
        assert state.recent_entities.get("location") == "Mumbai"

    @pytest.mark.asyncio
    async def test_get_state(self):
        svc = ConversationManagerService()
        await svc.initialize()
        session = await svc.create_session()
        await svc.process_turn(session.id, "Hello")
        state = await svc.get_state(session.id)
        assert state is not None
        assert state.session_id == session.id

    @pytest.mark.asyncio
    async def test_resolve_reference(self):
        svc = ConversationManagerService()
        await svc.initialize()
        session = await svc.create_session()
        await svc.process_turn(
            session.id,
            "What's the weather in Mumbai?",
            entities={"location": "Mumbai"},
        )
        resolved = await svc.resolve_reference("it", session.id)
        assert resolved == "Mumbai"

    @pytest.mark.asyncio
    async def test_get_active_sessions(self):
        svc = ConversationManagerService()
        await svc.initialize()
        await svc.create_session()
        await svc.create_session()
        active = await svc.get_active_sessions()
        assert len(active) == 2

    @pytest.mark.asyncio
    async def test_timeout_check(self):
        svc = ConversationManagerService()
        await svc.initialize()
        # Override timeout to 0 for testing
        svc.session_manager._session_timeout = 0
        session = await svc.create_session()
        import asyncio
        await asyncio.sleep(0.01)
        expired = await svc.timeout_check()
        assert expired >= 1

    @pytest.mark.asyncio
    async def test_process_turn_not_initialized(self):
        svc = ConversationManagerService()
        with pytest.raises(RuntimeError, match="not initialized"):
            await svc.process_turn("sess", "Hello")

    @pytest.mark.asyncio
    async def test_process_turn_invalid_session(self):
        svc = ConversationManagerService()
        await svc.initialize()
        with pytest.raises(ValueError, match="Session not found"):
            await svc.process_turn("nonexistent", "Hello")
