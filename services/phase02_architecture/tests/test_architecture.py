"""
Tests for Phase 2 — Architecture (Event Bus, Module Registry, Service).
"""

import pytest
from services.phase02_architecture import (
    EventBus,
    Event,
    EventPriority,
    ModuleRegistry,
    ArchitectureService,
    ArchitectureConfig,
)
from services.phase02_architecture.errors import (
    ModuleNotFoundError,
    ModuleRegistrationError,
    CircularDependencyError,
    EventBusError,
)
from services.phase02_architecture.models import ModuleStatus, ModuleRegistration
from services.base import ServiceBase


# ═════════════════════════════════════════════════════════════════
# Event Bus Tests
# ═════════════════════════════════════════════════════════════════


class TestEventBus:
    """Verify EventBus pub/sub behavior."""

    @pytest.mark.asyncio
    async def test_emit_no_handlers(self):
        bus = EventBus()
        count = await bus.emit(Event("test.event", {"key": "val"}))
        assert count == 0

    @pytest.mark.asyncio
    async def test_subscribe_and_emit(self):
        bus = EventBus()
        received = []

        async def handler(event: Event):
            received.append(event.payload)

        bus.subscribe("test.event", handler)
        count = await bus.emit(Event("test.event", {"msg": "hello"}))

        assert count == 1
        assert len(received) == 1
        assert received[0] == {"msg": "hello"}

    @pytest.mark.asyncio
    async def test_wildcard_handler(self):
        bus = EventBus()
        received = []

        async def wildcard(event: Event):
            received.append(event.type)

        bus.subscribe("*", wildcard)
        await bus.emit(Event("type.a"))
        await bus.emit(Event("type.b"))

        assert received == ["type.a", "type.b"]

    @pytest.mark.asyncio
    async def test_on_decorator(self):
        bus = EventBus()
        received = []

        @bus.on("decorator.test")
        async def handler(event: Event):
            received.append(event.type)

        await bus.emit(Event("decorator.test"))
        assert received == ["decorator.test"]

    @pytest.mark.asyncio
    async def test_handler_error_isolation(self):
        """One failing handler should not prevent others from running."""
        bus = EventBus()
        results = []

        async def fail_handler(event: Event):
            raise ValueError("I fail")

        async def good_handler(event: Event):
            results.append("success")

        bus.subscribe("test", fail_handler)
        bus.subscribe("test", good_handler)

        count = await bus.emit(Event("test"))
        assert count == 1  # only the good one "succeeded"
        assert results == ["success"]

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        bus = EventBus()
        results = []

        async def handler(event: Event):
            results.append("called")

        bus.subscribe("test", handler)
        bus.unsubscribe("test", handler)

        count = await bus.emit(Event("test"))
        assert count == 0
        assert results == []

    def test_event_creation(self):
        event = Event("my.event", {"data": 123}, source="test", priority=EventPriority.HIGH)
        assert event.type == "my.event"
        assert event.payload == {"data": 123}
        assert event.source == "test"
        assert event.priority == EventPriority.HIGH
        assert event.id is not None
        assert event.timestamp > 0

    def test_get_stats_empty(self):
        bus = EventBus()
        stats = bus.get_stats()
        assert stats["total_events"] == 0
        assert stats["failed_events"] == 0
        assert stats["handlers_registered"] == 0

    def test_get_stats_after_emit(self):
        bus = EventBus()
        # Emit without handlers — still counts
        import asyncio
        asyncio.run(bus.emit(Event("no.op")))
        stats = bus.get_stats()
        assert stats["total_events"] == 1

    def test_reset(self):
        bus = EventBus()

        async def h(event): pass
        bus.subscribe("x", h)
        bus.reset()
        assert bus.get_stats()["handlers_registered"] == 0
        assert bus.get_stats()["total_events"] == 0


# ═════════════════════════════════════════════════════════════════
# Module Registry Tests
# ═════════════════════════════════════════════════════════════════


class MockService(ServiceBase):
    async def initialize(self): return True
    async def shutdown(self): pass
    async def health(self): return {"status": "healthy"}
    async def stats(self): return {}


class TestModuleRegistry:
    """Verify ModuleRegistry registration and resolution."""

    def setup_method(self):
        self.registry = ModuleRegistry()
        self.svc_a = MockService(name="mod_a")
        self.svc_b = MockService(name="mod_b")
        self.svc_c = MockService(name="mod_c")

    def test_register(self):
        reg = self.registry.register("mod_a", self.svc_a)
        assert reg.name == "mod_a"
        assert reg.status == ModuleStatus.REGISTERED
        assert self.registry.count == 1

    def test_register_duplicate(self):
        self.registry.register("mod_a", self.svc_a)
        with pytest.raises(ModuleRegistrationError):
            self.registry.register("mod_a", self.svc_a)

    def test_get_module(self):
        self.registry.register("mod_a", self.svc_a)
        retrieved = self.registry.get("mod_a")
        assert retrieved is self.svc_a

    def test_get_module_not_found(self):
        with pytest.raises(ModuleNotFoundError):
            self.registry.get("nonexistent")

    def test_dependency_resolution(self):
        self.registry.register("mod_a", self.svc_a)
        self.registry.register("mod_b", self.svc_b, dependencies=["mod_a"])
        self.registry.register("mod_c", self.svc_c, dependencies=["mod_b"])

        deps = self.registry.resolve_dependencies("mod_c")
        # mod_a should come before mod_b before mod_c
        assert deps == ["mod_a", "mod_b", "mod_c"]

    def test_circular_dependency(self):
        self.registry.register("mod_a", self.svc_a, dependencies=["mod_b"])
        self.registry.register("mod_b", self.svc_b, dependencies=["mod_a"])

        with pytest.raises(CircularDependencyError):
            self.registry.resolve_dependencies("mod_a")

    def test_missing_dependency(self):
        self.registry.register("mod_a", self.svc_a, dependencies=["missing_mod"])
        with pytest.raises(ModuleNotFoundError):
            self.registry.resolve_dependencies("mod_a")

    def test_status_management(self):
        self.registry.register("mod_a", self.svc_a)
        self.registry.set_status("mod_a", ModuleStatus.INITIALIZED)
        assert self.registry.get_status("mod_a") == ModuleStatus.INITIALIZED

    def test_list_modules(self):
        self.registry.register("mod_a", self.svc_a)
        self.registry.register("mod_b", self.svc_b)
        modules = self.registry.list_modules()
        assert len(modules) == 2
        names = [m["name"] for m in modules]
        assert "mod_a" in names
        assert "mod_b" in names

    def test_list_modules_with_filter(self):
        self.registry.register("mod_a", self.svc_a)
        self.registry.set_status("mod_a", ModuleStatus.INITIALIZED)
        self.registry.register("mod_b", self.svc_b)

        active = self.registry.list_modules(status_filter=ModuleStatus.REGISTERED)
        assert len(active) == 1
        assert active[0]["name"] == "mod_b"

    def test_unregister(self):
        self.registry.register("mod_a", self.svc_a)
        assert self.registry.unregister("mod_a") is True
        assert self.registry.unregister("mod_a") is False

    def test_check_dependencies(self):
        self.registry.register("mod_a", self.svc_a)
        self.registry.register("mod_b", self.svc_b, dependencies=["mod_a"])
        self.registry.set_status("mod_a", ModuleStatus.INITIALIZED)

        assert self.registry.check_dependencies("mod_b") is True
        assert self.registry.check_dependencies("mod_a") is True  # no deps


# ═════════════════════════════════════════════════════════════════
# ArchitectureService Tests
# ═════════════════════════════════════════════════════════════════


class TestArchitectureService:
    """Verify ArchitectureService lifecycle and coordination."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        svc = ArchitectureService()
        result = await svc.initialize()
        assert result is True
        assert svc.is_initialized() is True

    @pytest.mark.asyncio
    async def test_health(self):
        svc = ArchitectureService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"
        assert health["modules_count"] == 0

    @pytest.mark.asyncio
    async def test_stats(self):
        svc = ArchitectureService()
        await svc.initialize()
        stats = await svc.stats()
        assert "modules" in stats
        assert "event_bus" in stats

    @pytest.mark.asyncio
    async def test_register_and_get_module(self):
        svc = ArchitectureService()
        await svc.initialize()
        mock = MockService(name="test_mod")
        await svc.register_module("test_mod", mock)
        retrieved = await svc.get_module("test_mod")
        assert retrieved is mock

    @pytest.mark.asyncio
    async def test_emit_event(self):
        svc = ArchitectureService()
        await svc.initialize()
        results = []

        async def handler(event):
            results.append(event.payload)

        await svc.subscribe("test.event", handler)
        count = await svc.emit_event("test.event", {"msg": "hello"})
        assert count == 1
        assert results == [{"msg": "hello"}]

    @pytest.mark.asyncio
    async def test_shutdown(self):
        svc = ArchitectureService()
        await svc.initialize()
        await svc.shutdown()
        assert svc.is_initialized() is False

    @pytest.mark.asyncio
    async def test_list_modules(self):
        svc = ArchitectureService()
        await svc.initialize()
        mock = MockService(name="m")
        await svc.register_module("m", mock)
        modules = await svc.list_modules()
        assert len(modules) == 1
        assert modules[0]["name"] == "m"
