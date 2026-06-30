"""
Tests for Phase 29 — Automation Engine.
"""

import pytest
from services.phase29_automation import (
    RuleEngine,
    AutomationService,
    AutomationConfig,
    AutomationRule,
    RuleExecution,
)


class TestRuleEngine:
    """Verify rule management and evaluation."""

    def test_add_rule(self):
        engine = RuleEngine()
        rule = AutomationRule(
            id="1", name="Test Rule",
            trigger={"type": "time", "params": {"hour": 9}},
            actions=[{"type": "notify", "params": {"message": "Time!"}}],
        )
        rid = engine.add_rule(rule)
        assert rid == "1"
        assert len(engine.list_rules()) == 1

    def test_get_rule(self):
        engine = RuleEngine()
        rule = AutomationRule(id="1", name="Test", trigger={"type": "time"}, actions=[])
        engine.add_rule(rule)
        assert engine.get_rule("1") is not None
        assert engine.get_rule("x") is None

    def test_update_rule(self):
        engine = RuleEngine()
        rule = AutomationRule(id="1", name="Test", trigger={"type": "time"}, actions=[])
        engine.add_rule(rule)
        updated = engine.update_rule("1", name="Updated")
        assert updated.name == "Updated"

    def test_remove_rule(self):
        engine = RuleEngine()
        rule = AutomationRule(id="1", name="Test", trigger={"type": "time"}, actions=[])
        engine.add_rule(rule)
        assert engine.remove_rule("1") is True
        assert engine.remove_rule("x") is False

    def test_enable_disable_rule(self):
        engine = RuleEngine()
        rule = AutomationRule(id="1", name="Test", trigger={"type": "time"}, actions=[])
        engine.add_rule(rule)
        assert engine.disable_rule("1") is True
        assert not engine.get_rule("1").is_active
        assert engine.enable_rule("1") is True
        assert engine.get_rule("1").is_active

    def test_evaluate_time_trigger_match(self):
        engine = RuleEngine()
        rule = AutomationRule(
            id="1", name="Time Test",
            trigger={"type": "time", "params": {"hour": 9}},
            actions=[{"type": "notify", "params": {"message": "Good morning!"}}],
        )
        success, execution = engine.evaluate_and_execute(rule, {"hour": 9})
        assert success is True
        assert execution.success is True

    def test_evaluate_time_trigger_no_match(self):
        engine = RuleEngine()
        rule = AutomationRule(
            id="1", name="Time Test",
            trigger={"type": "time", "params": {"hour": 9}},
            actions=[{"type": "notify", "params": {"message": "Good morning!"}}],
        )
        success, execution = engine.evaluate_and_execute(rule, {"hour": 14})
        assert success is False

    def test_evaluate_event_trigger(self):
        engine = RuleEngine()
        rule = AutomationRule(
            id="1", name="Event Test",
            trigger={"type": "event", "params": {"event": "user_login"}},
            actions=[{"type": "notify", "params": {"message": "User logged in"}}],
        )
        success, execution = engine.evaluate_and_execute(rule, {"event": "user_login"})
        assert success is True

    def test_evaluate_context_trigger(self):
        engine = RuleEngine()
        rule = AutomationRule(
            id="1", name="Context Test",
            trigger={"type": "context", "params": {"key": "location", "value": "home"}},
            actions=[{"type": "system", "params": {"action": "lights_on"}}],
        )
        success, execution = engine.evaluate_and_execute(rule, {"location": "home"})
        assert success is True

    def test_cooldown_respects(self):
        engine = RuleEngine()
        rule = AutomationRule(
            id="1", name="Cooldown Test",
            trigger={"type": "time", "params": {"hour": 9}},
            actions=[{"type": "notify", "params": {"message": "Hi"}}],
            cooldown_seconds=3600,
        )
        engine.add_rule(rule)
        # First execution should succeed
        s1, _ = engine.evaluate_and_execute(rule, {"hour": 9})
        assert s1 is True
        # Second immediate execution should fail due to cooldown
        s2, _ = engine.evaluate_and_execute(rule, {"hour": 9})
        assert s2 is False

    def test_rule_inactive_does_not_fire(self):
        engine = RuleEngine()
        rule = AutomationRule(
            id="1", name="Inactive",
            trigger={"type": "time", "params": {"hour": 9}},
            actions=[],
            is_active=False,
        )
        engine.add_rule(rule)
        success, _ = engine.evaluate_and_execute(rule, {"hour": 9})
        assert success is False

    def test_get_execution_history(self):
        engine = RuleEngine()
        rule = AutomationRule(
            id="1", name="History Test",
            trigger={"type": "time", "params": {"hour": 9}},
            actions=[{"type": "notify", "params": {"message": "Hi"}}],
        )
        engine.add_rule(rule)
        engine.evaluate_and_execute(rule, {"hour": 9})
        history = engine.get_execution_history()
        assert len(history) >= 1

    def test_get_stats(self):
        engine = RuleEngine()
        stats = engine.get_stats()
        assert "total_rules" in stats
        assert "active_rules" in stats

    def test_clear(self):
        engine = RuleEngine()
        rule = AutomationRule(id="1", name="Test", trigger={"type": "time"}, actions=[])
        engine.add_rule(rule)
        engine.clear()
        assert len(engine.list_rules()) == 0


class TestAutomationService:
    """Verify service wrapper."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        svc = AutomationService()
        assert await svc.initialize() is True

    @pytest.mark.asyncio
    async def test_create_and_get_rule(self):
        svc = AutomationService()
        await svc.initialize()
        rule = AutomationRule(
            id="1", name="Test",
            trigger={"type": "time", "params": {"hour": 9}},
            actions=[{"type": "notify", "params": {"message": "Hi"}}],
        )
        rid = await svc.create_rule(rule)
        assert rid == "1"
        retrieved = await svc.get_rule("1")
        assert retrieved is not None

    @pytest.mark.asyncio
    async def test_update_rule(self):
        svc = AutomationService()
        await svc.initialize()
        rule = AutomationRule(id="1", name="Test", trigger={"type": "time"}, actions=[])
        await svc.create_rule(rule)
        updated = await svc.update_rule("1", name="Updated")
        assert updated.name == "Updated"

    @pytest.mark.asyncio
    async def test_delete_rule(self):
        svc = AutomationService()
        await svc.initialize()
        rule = AutomationRule(id="1", name="Test", trigger={"type": "time"}, actions=[])
        await svc.create_rule(rule)
        assert await svc.delete_rule("1") is True

    @pytest.mark.asyncio
    async def test_enable_disable_rule(self):
        svc = AutomationService()
        await svc.initialize()
        rule = AutomationRule(id="1", name="Test", trigger={"type": "time"}, actions=[])
        await svc.create_rule(rule)
        assert await svc.disable_rule("1") is True
        assert await svc.enable_rule("1") is True

    @pytest.mark.asyncio
    async def test_evaluate_and_execute(self):
        svc = AutomationService()
        await svc.initialize()
        rule = AutomationRule(
            id="1", name="Test",
            trigger={"type": "time", "params": {"hour": 9}},
            actions=[{"type": "notify", "params": {"message": "Hi"}}],
        )
        await svc.create_rule(rule)
        success, execution = await svc.evaluate_and_execute(rule, {"hour": 9})
        assert success is True

    @pytest.mark.asyncio
    async def test_list_rules(self):
        svc = AutomationService()
        await svc.initialize()
        rule = AutomationRule(id="1", name="Test", trigger={"type": "time"}, actions=[])
        await svc.create_rule(rule)
        rules = await svc.list_rules()
        assert len(rules) >= 1

    @pytest.mark.asyncio
    async def test_get_execution_history(self):
        svc = AutomationService()
        await svc.initialize()
        rule = AutomationRule(
            id="1", name="Test",
            trigger={"type": "time", "params": {"hour": 9}},
            actions=[{"type": "notify", "params": {"message": "Hi"}}],
        )
        await svc.create_rule(rule)
        await svc.evaluate_and_execute(rule, {"hour": 9})
        history = await svc.get_execution_history()
        assert len(history) >= 1

    @pytest.mark.asyncio
    async def test_health(self):
        svc = AutomationService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_stats(self):
        svc = AutomationService()
        await svc.initialize()
        stats = await svc.stats()
        assert stats["service"] == "jarvis_automation"

    @pytest.mark.asyncio
    async def test_shutdown(self):
        svc = AutomationService()
        await svc.initialize()
        await svc.shutdown()
        assert not svc.is_initialized()
