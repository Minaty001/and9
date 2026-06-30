"""
Tests for Phase 15 — Skill Router.

Covers:
    - SkillDefinition creation and version comparison
    - SkillRegistry: register/get/unregister/find_by_intent (priority sorting, entity matching)
    - SkillRouter: route with matching skills, fallback on failure, no-match case
    - SkillRouterService: init/shutdown/health/stats full flow
"""

import pytest
from datetime import datetime

from services.phase15_skill import (
    SkillConfig,
    SkillDefinition,
    SkillResult,
    SkillRegistry,
    SkillRouter,
    SkillRouterService,
)
from services.base import ServiceBase


# ═════════════════════════════════════════════════════════════════
# SkillDefinition Tests
# ═════════════════════════════════════════════════════════════════


class TestSkillDefinition:
    """Verify SkillDefinition model creation and defaults."""

    def test_minimal_definition(self):
        sd = SkillDefinition(id="test", name="Test")
        assert sd.id == "test"
        assert sd.name == "Test"
        assert sd.version == "1.0.0"
        assert sd.description == ""
        assert sd.intents == []
        assert sd.required_entities == []
        assert sd.optional_entities == []
        assert sd.priority == 0
        assert sd.enabled is True
        assert sd.config == {}

    def test_full_definition(self):
        sd = SkillDefinition(
            id="weather",
            name="Weather Skill",
            version="2.1.0",
            description="Fetches weather data",
            intents=["get_weather", "forecast"],
            required_entities=["location"],
            optional_entities=["date"],
            priority=10,
            enabled=True,
            config={"api_key": "test"},
        )
        assert sd.id == "weather"
        assert sd.version == "2.1.0"
        assert "get_weather" in sd.intents
        assert "location" in sd.required_entities
        assert sd.priority == 10

    def test_version_string(self):
        sd1 = SkillDefinition(id="a", name="A", version="1.0.0")
        sd2 = SkillDefinition(id="b", name="B", version="2.0.0")
        # Version is stored as string; comparison is string-based
        assert sd1.version == "1.0.0"
        assert sd2.version == "2.0.0"


# ═════════════════════════════════════════════════════════════════
# SkillResult Tests
# ═════════════════════════════════════════════════════════════════


class TestSkillResult:
    """Verify SkillResult model."""

    def test_success_result(self):
        sr = SkillResult(
            skill_id="test",
            success=True,
            output="OK",
            confidence=0.95,
            duration_ms=10.0,
        )
        assert sr.skill_id == "test"
        assert sr.success is True
        assert sr.error is None

    def test_failure_result(self):
        sr = SkillResult(
            skill_id="test",
            success=False,
            output="",
            confidence=0.0,
            duration_ms=5.0,
            error="Something went wrong",
        )
        assert sr.success is False
        assert sr.error == "Something went wrong"


# ═════════════════════════════════════════════════════════════════
# SkillRegistry Tests
# ═════════════════════════════════════════════════════════════════


class TestSkillRegistry:
    """Verify SkillRegistry operations."""

    def test_register_and_get(self):
        reg = SkillRegistry()
        sd = SkillDefinition(id="test", name="Test")
        assert reg.register(sd) is True
        retrieved = reg.get("test")
        assert retrieved is not None
        assert retrieved.id == "test"
        assert retrieved.name == "Test"

    def test_get_nonexistent(self):
        reg = SkillRegistry()
        assert reg.get("nonexistent") is None

    def test_unregister(self):
        reg = SkillRegistry()
        sd = SkillDefinition(id="test", name="Test")
        reg.register(sd)
        assert reg.unregister("test") is True
        assert reg.get("test") is None

    def test_unregister_nonexistent(self):
        reg = SkillRegistry()
        assert reg.unregister("nonexistent") is False

    def test_duplicate_registration(self):
        reg = SkillRegistry()
        sd1 = SkillDefinition(id="test", name="Test")
        sd2 = SkillDefinition(id="test", name="Test V2", version="2.0.0")
        assert reg.register(sd1) is True
        # Overwrite should succeed
        assert reg.register(sd2) is True
        retrieved = reg.get("test")
        assert retrieved.version == "2.0.0"

    def test_find_by_intent_no_entities(self):
        reg = SkillRegistry()
        sd = SkillDefinition(id="test", name="Test", intents=["greeting"])
        reg.register(sd)
        matches = reg.find_by_intent("greeting")
        assert len(matches) == 1
        assert matches[0].id == "test"

    def test_find_by_intent_no_match(self):
        reg = SkillRegistry()
        sd = SkillDefinition(id="test", name="Test", intents=["greeting"])
        reg.register(sd)
        matches = reg.find_by_intent("weather")
        assert len(matches) == 0

    def test_find_by_intent_priority_sorting(self):
        reg = SkillRegistry()
        low = SkillDefinition(id="low", name="Low", intents=["test"], priority=0)
        high = SkillDefinition(id="high", name="High", intents=["test"], priority=10)
        reg.register(low)
        reg.register(high)
        matches = reg.find_by_intent("test")
        assert len(matches) == 2
        assert matches[0].id == "high"  # higher priority first
        assert matches[1].id == "low"

    def test_find_by_intent_entity_matching(self):
        reg = SkillRegistry()
        sd1 = SkillDefinition(
            id="weather_full",
            name="Weather Full",
            intents=["weather"],
            required_entities=["location", "date"],
            priority=5,
        )
        sd2 = SkillDefinition(
            id="weather_basic",
            name="Weather Basic",
            intents=["weather"],
            required_entities=["location"],
            priority=5,
        )
        reg.register(sd1)
        reg.register(sd2)

        # Only location entity provided - basic should match, full should not
        matches = reg.find_by_intent("weather", {"location": "London"})
        assert len(matches) == 1
        assert matches[0].id == "weather_basic"

    def test_find_by_intent_disabled_skill(self):
        reg = SkillRegistry()
        sd = SkillDefinition(id="disabled", name="Disabled", intents=["test"], enabled=False)
        reg.register(sd)
        matches = reg.find_by_intent("test")
        assert len(matches) == 0

    def test_list(self):
        reg = SkillRegistry()
        reg.register(SkillDefinition(id="a", name="A", intents=["x"]))
        reg.register(SkillDefinition(id="b", name="B", intents=["y"]))
        assert len(reg.list()) == 2

    def test_max_skills_limit(self):
        reg = SkillRegistry(max_skills=2)
        assert reg.register(SkillDefinition(id="a", name="A")) is True
        assert reg.register(SkillDefinition(id="b", name="B")) is True
        assert reg.register(SkillDefinition(id="c", name="C")) is False

    def test_version_history(self):
        reg = SkillRegistry(enable_versioning=True)
        reg.register(SkillDefinition(id="test", name="Test", version="1.0.0"))
        reg.register(SkillDefinition(id="test", name="Test", version="2.0.0"))
        history = reg.get_version_history("test")
        assert len(history) == 2
        assert history[0].version == "2.0.0"  # newest first


# ═════════════════════════════════════════════════════════════════
# SkillRouter Tests
# ═════════════════════════════════════════════════════════════════


class TestSkillRouter:
    """Verify SkillRouter routing logic."""

    def test_route_matching_skills(self):
        reg = SkillRegistry()
        reg.register(SkillDefinition(
            id="greeter", name="Greeter", intents=["greeting"], priority=5,
        ))
        router = SkillRouter(reg)
        results = router.route("greeting")
        assert len(results) == 1
        assert results[0].skill_id == "greeter"
        assert results[0].success is True

    def test_route_no_match(self):
        reg = SkillRegistry()
        reg.register(SkillDefinition(id="greeter", name="Greeter", intents=["greeting"]))
        router = SkillRouter(reg)
        results = router.route("weather")
        assert len(results) == 0

    def test_route_fallback_on_failure(self):
        reg = SkillRegistry()
        # First skill will fail, second should be tried
        reg.register(SkillDefinition(
            id="failing", name="Failing", intents=["test"],
            config={"simulate_failure": True}, priority=5,
        ))
        reg.register(SkillDefinition(
            id="backup", name="Backup", intents=["test"], priority=0,
        ))
        router = SkillRouter(reg, enable_fallback=True)
        results = router.route("test")
        assert len(results) == 2
        assert results[0].success is False
        assert results[0].skill_id == "failing"
        assert results[1].success is True
        assert results[1].skill_id == "backup"

    def test_route_no_fallback(self):
        reg = SkillRegistry()
        reg.register(SkillDefinition(
            id="failing", name="Failing", intents=["test"],
            config={"simulate_failure": True}, priority=5,
        ))
        reg.register(SkillDefinition(
            id="backup", name="Backup", intents=["test"], priority=0,
        ))
        router = SkillRouter(reg, enable_fallback=False)
        results = router.route("test")
        assert len(results) == 1
        assert results[0].success is False

    def test_route_collect_all(self):
        reg = SkillRegistry()
        reg.register(SkillDefinition(
            id="skill1", name="Skill 1", intents=["test"], priority=5,
        ))
        reg.register(SkillDefinition(
            id="skill2", name="Skill 2", intents=["test"], priority=0,
        ))
        router = SkillRouter(reg)
        results = router.route("test", context={"collect_all": True})
        assert len(results) == 2
        assert results[0].skill_id == "skill1"
        assert results[1].skill_id == "skill2"


# ═════════════════════════════════════════════════════════════════
# SkillRouterService Tests
# ═════════════════════════════════════════════════════════════════


class TestSkillRouterService:
    """Verify SkillRouterService lifecycle."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        svc = SkillRouterService()
        result = await svc.initialize()
        assert result is True
        assert svc.is_initialized() is True

    @pytest.mark.asyncio
    async def test_health_after_init(self):
        svc = SkillRouterService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"
        assert health["initialized"] is True
        assert health["service_name"] == "jarvis_skill_router"

    @pytest.mark.asyncio
    async def test_stats(self):
        svc = SkillRouterService()
        await svc.initialize()
        stats = await svc.stats()
        assert stats["service"] == "jarvis_skill_router"
        assert stats["initialized"] is True
        assert "registry" in stats

    @pytest.mark.asyncio
    async def test_shutdown(self):
        svc = SkillRouterService()
        await svc.initialize()
        await svc.shutdown()
        assert svc.is_initialized() is False

    @pytest.mark.asyncio
    async def test_register_and_route(self):
        svc = SkillRouterService()
        await svc.initialize()
        skill = SkillDefinition(id="test", name="Test", intents=["greeting"])
        assert svc.register_skill(skill) is True
        results = svc.route("greeting")
        assert len(results) == 1
        assert results[0].success is True
        assert len(svc.list_skills()) == 1

    @pytest.mark.asyncio
    async def test_unregister_skill(self):
        svc = SkillRouterService()
        await svc.initialize()
        skill = SkillDefinition(id="test", name="Test", intents=["greeting"])
        svc.register_skill(skill)
        assert svc.unregister_skill("test") is True
        assert len(svc.list_skills()) == 0

    @pytest.mark.asyncio
    async def test_service_stats_with_skills(self):
        svc = SkillRouterService()
        await svc.initialize()
        svc.register_skill(SkillDefinition(id="a", name="A", intents=["x"]))
        svc.register_skill(SkillDefinition(id="b", name="B", intents=["y"]))
        stats = await svc.stats()
        assert stats["registry"]["skills_count"] == 2


# ═════════════════════════════════════════════════════════════════
# SkillConfig Tests
# ═════════════════════════════════════════════════════════════════


class TestSkillConfig:
    """Verify SkillConfig defaults."""

    def test_default_config(self):
        cfg = SkillConfig()
        assert cfg.service_name == "jarvis_skill_router"
        assert cfg.max_skills == 100
        assert cfg.enable_versioning is True
        assert cfg.enable_fallback is True
        assert cfg.fallback_timeout_ms == 5000
        assert cfg.enable_plugin_discovery is True

    def test_config_override(self):
        cfg = SkillConfig(max_skills=50, enable_fallback=False)
        assert cfg.max_skills == 50
        assert cfg.enable_fallback is False
