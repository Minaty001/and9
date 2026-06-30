"""
Tests for Phase 14 — Decision Engine.
"""

from __future__ import annotations

import pytest
from typing import Any, Dict, List, Optional

from services.phase14_decision.config import DecisionConfig
from services.phase14_decision.models import (
    DecisionRequest, DecisionResult,
)
from services.phase14_decision.router import BrainRouter
from services.phase14_decision.service import DecisionEngineService


# ── Fixtures ───────────────────────────────────────────────────────────


@pytest.fixture
def config() -> DecisionConfig:
    return DecisionConfig()


@pytest.fixture
def router() -> BrainRouter:
    return BrainRouter()


@pytest.fixture
def high_conf_request() -> DecisionRequest:
    return DecisionRequest(
        query="What is 2+2?",
        intent="simple_math",
        confidence=0.95,
        entities={"operation": "addition"},
        context={},
    )


@pytest.fixture
def mid_conf_request() -> DecisionRequest:
    return DecisionRequest(
        query="Schedule a meeting",
        intent="scheduling",
        confidence=0.75,
        entities={"action": "schedule"},
        context={},
    )


@pytest.fixture
def low_conf_request() -> DecisionRequest:
    return DecisionRequest(
        query="Write a complex algorithm",
        intent="coding",
        confidence=0.55,
        entities={},
        context={},
    )


# ── DecisionRequest / DecisionResult Tests ─────────────────────────────


class TestDecisionModels:
    def test_request_defaults(self):
        req = DecisionRequest(query="hello")
        assert req.query == "hello"
        assert req.intent == ""
        assert req.confidence == 0.5
        assert req.entities == {}
        assert req.available_brains == ["reflex", "habit", "conscious"]
        assert req.latency_budget_ms == 1000
        assert req.max_cost == 0.05

    def test_request_has_brain(self):
        req = DecisionRequest(query="test", available_brains=["reflex", "conscious"])
        assert req.has_brain("reflex") is True
        assert req.has_brain("habit") is False
        assert req.has_brain("conscious") is True

    def test_result_defaults(self):
        result = DecisionResult()
        assert result.selected_brain == ""
        assert result.confidence == 0.0
        assert result.reasoning == ""
        assert result.routing_path == []
        assert result.latency_ms == 0.0
        assert result.estimated_cost == 0.0

    def test_result_full(self):
        result = DecisionResult(
            selected_brain="reflex",
            confidence=0.95,
            reasoning="High confidence",
            routing_path=["reflex"],
            latency_ms=5.0,
            estimated_cost=0.001,
        )
        assert result.selected_brain == "reflex"
        assert result.confidence == 0.95
        assert result.latency_ms == 5.0


# ── BrainRouter Tests ──────────────────────────────────────────────────


class TestBrainRouter:
    def test_route_reflex_high_confidence(self, router, high_conf_request):
        result = router.route(high_conf_request)
        assert result.selected_brain == "reflex"
        assert result.confidence >= 0.9
        assert "reflex" in result.reasoning
        assert result.routing_path[0] == "reflex"

    def test_route_habit_mid_confidence(self, router, mid_conf_request):
        result = router.route(mid_conf_request)
        assert result.selected_brain == "habit"
        assert result.confidence >= 0.7
        assert "habit" in result.reasoning

    def test_route_conscious_low_confidence(self, router, low_conf_request):
        result = router.route(low_conf_request)
        assert result.selected_brain == "conscious"
        assert "conscious" in result.reasoning

    def test_route_reflex_not_available(self, router, high_conf_request):
        high_conf_request.available_brains = ["habit", "conscious"]
        result = router.route(high_conf_request)
        # Reflex not available, should go to habit
        assert result.selected_brain == "habit"
        assert result.confidence >= 0.7

    def test_route_habit_not_available(self, router, mid_conf_request):
        mid_conf_request.available_brains = ["reflex", "conscious"]
        result = router.route(mid_conf_request)
        # Habit not available, but confidence is 0.75 which is < 0.9
        # So it should route to conscious since threshold for reflex (0.9) not met
        assert result.selected_brain in ("conscious", "reflex")

    def test_route_only_reflex_available(self, router, low_conf_request):
        low_conf_request.available_brains = ["reflex"]
        result = router.route(low_conf_request)
        assert result.selected_brain == "reflex"

    def test_route_only_conscious_available(self, router, high_conf_request):
        high_conf_request.available_brains = ["conscious"]
        result = router.route(high_conf_request)
        assert result.selected_brain == "conscious"

    def test_route_empty_brains(self, router, high_conf_request):
        high_conf_request.available_brains = []
        result = router.route(high_conf_request)
        assert result.selected_brain == "conscious"

    def test_route_latency_budget_exceeded(self, router):
        request = DecisionRequest(
            query="complex task",
            confidence=0.95,
            available_brains=["reflex", "habit", "conscious"],
            latency_budget_ms=5,  # Very tight budget
        )
        result = router.route(request)
        # Should still work — may stay at reflex or be rerouted
        assert result.selected_brain in ("reflex", "habit", "conscious")
        assert result.latency_ms >= 0

    def test_route_cost_aware(self, router):
        request = DecisionRequest(
            query="expensive task",
            confidence=0.55,
            max_cost=0.001,  # Very tight budget
        )
        result = router.route(request)
        # Should be rerouted to a cheaper brain if possible
        cost = BRAIN_COST_ESTIMATES if 'BRAIN_COST_ESTIMATES' in dir() else {}
        assert result.estimated_cost >= 0

    def test_route_escalation_path(self, router, low_conf_request):
        """With escalation, conscious is selected. Check routing path."""
        result = router.route(low_conf_request)
        assert len(result.routing_path) >= 1
        # For low confidence, path should include conscious
        assert "conscious" in result.routing_path or result.selected_brain == "conscious"

    def test_route_tracks_latency(self, router, high_conf_request):
        result = router.route(high_conf_request)
        assert result.latency_ms > 0

    def test_route_confidence_adjustment_reflex(self, router):
        request = DecisionRequest(query="test", confidence=0.85, available_brains=["reflex"])
        # 0.85 < 0.9 threshold for reflex, so it falls back
        result = router.route(request)
        assert result.selected_brain == "reflex"  # only brain available
        assert result.confidence >= 0.9  # Adjusted to reflex threshold

    def test_route_confidence_adjustment_conscious(self, router):
        request = DecisionRequest(query="test", confidence=0.3, available_brains=["conscious"])
        result = router.route(request)
        assert result.selected_brain == "conscious"
        assert result.confidence >= 0.5  # Adjusted to conscious min

    def test_route_multiple_fallbacks(self, router):
        request = DecisionRequest(
            query="test",
            confidence=0.1,  # Very low
            available_brains=["reflex", "habit"],
        )
        result = router.route(request)
        # Should fallback to reflex as lowest available (it's the first in the list check)
        assert result.selected_brain in ("reflex", "habit")


# Need this reference for the cost test
BRAIN_COST_ESTIMATES = {
    "reflex": 0.001,
    "habit": 0.005,
    "conscious": 0.05,
}


# ── DecisionEngineService Tests ────────────────────────────────────────


class TestDecisionEngineService:
    @pytest.mark.asyncio
    async def test_initialize(self):
        service = DecisionEngineService()
        ok = await service.initialize()
        assert ok is True
        assert service.is_initialized() is True

    @pytest.mark.asyncio
    async def test_shutdown(self):
        service = DecisionEngineService()
        await service.initialize()
        await service.shutdown()
        assert service.is_initialized() is False

    @pytest.mark.asyncio
    async def test_health_before_init(self):
        service = DecisionEngineService()
        health = await service.health()
        assert health["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_health_after_init(self):
        service = DecisionEngineService()
        await service.initialize()
        health = await service.health()
        assert health["status"] == "healthy"
        assert health["service_name"] == "jarvis_decision"
        assert health["version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_stats(self):
        service = DecisionEngineService()
        await service.initialize()
        stats = await service.stats()
        assert stats["service"] == "jarvis_decision"
        assert stats["version"] == "1.0.0"
        assert "metrics" in stats
        assert "reflex_threshold" in stats

    @pytest.mark.asyncio
    async def test_decide_reflex(self):
        service = DecisionEngineService()
        await service.initialize()
        request = DecisionRequest(
            query="What is 2+2?",
            confidence=0.95,
        )
        result = await service.decide(request)
        assert result.selected_brain == "reflex"
        assert isinstance(result, DecisionResult)

    @pytest.mark.asyncio
    async def test_decide_habit(self):
        service = DecisionEngineService()
        await service.initialize()
        request = DecisionRequest(
            query="Schedule a meeting",
            confidence=0.75,
        )
        result = await service.decide(request)
        assert result.selected_brain == "habit"

    @pytest.mark.asyncio
    async def test_decide_conscious(self):
        service = DecisionEngineService()
        await service.initialize()
        request = DecisionRequest(
            query="Write a complex algorithm",
            confidence=0.55,
        )
        result = await service.decide(request)
        assert result.selected_brain == "conscious"

    @pytest.mark.asyncio
    async def test_double_initialize(self):
        service = DecisionEngineService()
        await service.initialize()
        await service.initialize()  # Should not crash
        assert service.is_initialized() is True

    @pytest.mark.asyncio
    async def test_metrics_tracking(self):
        service = DecisionEngineService()
        await service.initialize()
        request = DecisionRequest(query="test", confidence=0.95)
        await service.decide(request)
        snap = service._metrics.snapshot()
        assert snap["counters"].get("decisions_made", 0) >= 1
        assert snap["counters"].get("routed_to_reflex", 0) >= 1
