"""
Tests for Phase 10 — Reflex Brain.
"""

import pytest
from services.phase10_reflex import (
    ReflexBrain,
    ReflexAction,
    ReflexResult,
    ReflexService,
    ReflexConfig,
)


class TestReflexAction:
    """Verify ReflexAction model."""

    def test_create_action(self):
        action = ReflexAction(
            action_id="test_pattern",
            pattern=r"hello",
            intent="greeting",
            response="Hi there!",
        )
        assert action.action_id == "test_pattern"
        assert action.intent == "greeting"
        assert action.response == "Hi there!"
        assert action.priority == 100
        assert action.is_enabled is True

    def test_match(self):
        action = ReflexAction(action_id="test", pattern=r"hello", intent="greeting")
        match = action.match("hello world")
        assert match is not None
        match = action.match("goodbye")
        assert match is None

    def test_match_case_insensitive(self):
        action = ReflexAction(action_id="test", pattern=r"hello")
        assert action.match("HELLO") is not None
        assert action.match("Hello") is not None

    def test_to_dict(self):
        action = ReflexAction(
            action_id="test", pattern=r"hello", intent="greeting",
            response="Hi", priority=10,
        )
        d = action.to_dict()
        assert d["action_id"] == "test"
        assert d["intent"] == "greeting"
        assert d["priority"] == 10
        assert d["is_enabled"] is True


class TestReflexResult:
    """Verify ReflexResult model."""

    def test_default_no_match(self):
        r = ReflexResult()
        assert r.matched is False
        assert r.action is None
        assert r.response is None

    def test_matched_result(self):
        action = ReflexAction(action_id="test", pattern=r"hi", response="Hello!")
        r = ReflexResult(matched=True, action=action, response="Hello!", intent="greeting", confidence=0.95)
        assert r.matched is True
        assert r.intent == "greeting"
        assert r.confidence == 0.95

    def test_to_dict(self):
        action = ReflexAction(action_id="test", pattern=r"hi")
        r = ReflexResult(matched=True, action=action, response="Hello!")
        d = r.to_dict()
        assert d["matched"] is True
        assert d["action_id"] == "test"
        assert d["response"] == "Hello!"


class TestReflexBrain:
    """Verify core pattern matching engine."""

    def test_basic_match(self):
        brain = ReflexBrain()
        brain.initialize()
        result = brain.process("hello")
        assert result.matched is True
        assert result.intent == "greeting"

    def test_no_match(self):
        brain = ReflexBrain()
        brain.initialize()
        result = brain.process("supercalifragilisticexpialidocious")
        assert result.matched is False

    def test_empty_input(self):
        brain = ReflexBrain()
        brain.initialize()
        result = brain.process("")
        assert result.matched is False

    def test_none_input(self):
        brain = ReflexBrain()
        brain.initialize()
        result = brain.process("")
        assert result.matched is False

    def test_priority_ordering(self):
        brain = ReflexBrain(ReflexConfig(enable_default_actions=False))
        brain.add_action(ReflexAction("low", r".*", "catchall", priority=200))
        brain.add_action(ReflexAction("high", r"hello", "greeting", priority=10))
        result = brain.process("hello")
        assert result.matched is True
        assert result.action.action_id == "high"  # higher priority matched first

    def test_disabled_action_not_matched(self):
        brain = ReflexBrain(ReflexConfig(enable_default_actions=False))
        brain.add_action(ReflexAction("disabled", r".*", "catchall", is_enabled=False))
        result = brain.process("anything")
        assert result.matched is False

    def test_remove_action(self):
        brain = ReflexBrain(ReflexConfig(enable_default_actions=False))
        brain.add_action(ReflexAction("test", r"hello"))
        assert brain.get_action_count() == 1
        brain.remove_action("test")
        assert brain.get_action_count() == 0

    def test_remove_nonexistent(self):
        brain = ReflexBrain(ReflexConfig(enable_default_actions=False))
        assert brain.remove_action("nonexistent") is False

    def test_get_action(self):
        brain = ReflexBrain(ReflexConfig(enable_default_actions=False))
        brain.add_action(ReflexAction("test", r"hello", response="Hi"))
        action = brain.get_action("test")
        assert action is not None
        assert action.response == "Hi"

    def test_get_action_nonexistent(self):
        brain = ReflexBrain(ReflexConfig(enable_default_actions=False))
        assert brain.get_action("nonexistent") is None

    def test_list_actions_sorted_by_priority(self):
        brain = ReflexBrain(ReflexConfig(enable_default_actions=False))
        brain.add_action(ReflexAction("a2", r"two", priority=50))
        brain.add_action(ReflexAction("a1", r"one", priority=10))
        actions = brain.list_actions()
        assert actions[0].action_id == "a1"
        assert actions[1].action_id == "a2"

    def test_default_actions_are_loaded(self):
        brain = ReflexBrain()
        brain.initialize()
        assert brain.get_action_count() >= 10  # at least 10 defaults

    def test_handler_execution(self):
        brain = ReflexBrain(ReflexConfig(enable_default_actions=False))
        brain.add_action(ReflexAction(
            "handler_test",
            r"what.*name",
            response=None,
            handler=lambda text: "My name is JARVIS!",
        ))
        result = brain.process("what is your name")
        assert result.matched is True
        assert result.response == "My name is JARVIS!"

    def test_handler_error_does_not_crash(self):
        brain = ReflexBrain(ReflexConfig(enable_default_actions=False))
        brain.add_action(ReflexAction(
            "crashy",
            r"crash",
            response="Fallback response",
            handler=lambda text: (_ for _ in ()).throw(RuntimeError("Boom")),
        ))
        result = brain.process("crash")
        assert result.matched is True
        assert result.response == "Fallback response"

    def test_many_actions_max_limit(self):
        cfg = ReflexConfig(max_actions=5)
        brain = ReflexBrain(cfg)
        for i in range(10):
            brain.add_action(ReflexAction(f"a{i}", rf"pat{i}", priority=100))
        assert brain.get_action_count() == 5  # max_actions cap


class TestReflexService:
    """Verify service wrapper."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        svc = ReflexService()
        result = await svc.initialize()
        assert result is True
        assert svc.is_initialized()

    @pytest.mark.asyncio
    async def test_process_match(self):
        svc = ReflexService()
        await svc.initialize()
        result = await svc.process("hello")
        assert result.matched is True
        assert result.intent == "greeting"

    @pytest.mark.asyncio
    async def test_process_no_match(self):
        svc = ReflexService()
        await svc.initialize()
        result = await svc.process("xyznonexistent")
        assert result.matched is False

    @pytest.mark.asyncio
    async def test_add_and_remove_action(self):
        svc = ReflexService()
        await svc.initialize()
        action = await svc.add_action("custom", r"custom pattern", intent="custom_intent")
        assert action.intent == "custom_intent"

        result = await svc.process("custom pattern test")
        assert result.matched is True
        assert result.intent == "custom_intent"

        removed = await svc.remove_action("custom")
        assert removed is True

        result = await svc.process("custom pattern test")
        assert result.matched is False

    @pytest.mark.asyncio
    async def test_list_actions(self):
        svc = ReflexService()
        await svc.initialize()
        actions = await svc.list_actions()
        assert len(actions) >= 10  # defaults

    @pytest.mark.asyncio
    async def test_get_action(self):
        svc = ReflexService(ReflexConfig(enable_default_actions=False))
        await svc.initialize()
        await svc.add_action("test", r"hello", response="Hello world")
        action = await svc.get_action("test")
        assert action is not None
        assert action["response"] == "Hello world"

    @pytest.mark.asyncio
    async def test_get_action_nonexistent(self):
        svc = ReflexService(ReflexConfig(enable_default_actions=False))
        await svc.initialize()
        action = await svc.get_action("nonexistent")
        assert action is None

    @pytest.mark.asyncio
    async def test_health(self):
        svc = ReflexService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"
        assert "registered_actions" in health

    @pytest.mark.asyncio
    async def test_shutdown(self):
        svc = ReflexService()
        await svc.initialize()
        await svc.shutdown()
        assert not svc.is_initialized()
