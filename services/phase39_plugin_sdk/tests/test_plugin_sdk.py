"""
Tests for Phase 39 — Plugin SDK.
"""

import pytest
from services.phase39_plugin_sdk import (
    PluginSdkConfig,
    PluginManifest,
    PluginHook,
    PluginState,
    PluginLoader,
    HookManager,
    Sandbox,
    PluginSdkService,
)


class TestPluginLoader:
    """Verify plugin loading/unloading."""

    def test_load_plugin(self):
        loader = PluginLoader()
        manifest = PluginManifest(
            id="test_plugin",
            name="Test Plugin",
            version="1.0.0",
            entry_point="",
        )
        assert loader.load_plugin(manifest) is True

    def test_load_duplicate(self):
        loader = PluginLoader()
        manifest = PluginManifest(id="dup", name="Dup", version="1.0.0")
        assert loader.load_plugin(manifest) is True
        assert loader.load_plugin(manifest) is False  # duplicate

    def test_unload_plugin(self):
        loader = PluginLoader()
        manifest = PluginManifest(id="to_unload", name="Unload", version="1.0.0")
        loader.load_plugin(manifest)
        assert loader.unload_plugin("to_unload") is True

    def test_unload_nonexistent(self):
        loader = PluginLoader()
        assert loader.unload_plugin("nonexistent") is False

    def test_reload_plugin(self):
        loader = PluginLoader()
        manifest = PluginManifest(id="reload", name="Reload", version="1.0.0")
        loader.load_plugin(manifest)
        assert loader.reload_plugin("reload") is True

    def test_get_loaded_plugins(self):
        loader = PluginLoader()
        manifest = PluginManifest(id="p1", name="P1", version="1.0.0")
        loader.load_plugin(manifest)
        plugins = loader.get_loaded_plugins()
        assert len(plugins) == 1
        assert plugins[0]["id"] == "p1"

    def test_get_plugin_state(self):
        loader = PluginLoader()
        manifest = PluginManifest(id="p1", name="P1", version="1.0.0")
        loader.load_plugin(manifest)
        state = loader.get_plugin_state("p1")
        assert state is not None
        assert state.status == "loaded"

    def test_max_plugins(self):
        cfg = PluginSdkConfig(max_plugins=2)
        loader = PluginLoader(cfg)
        m1 = PluginManifest(id="a", name="A", version="1.0.0")
        m2 = PluginManifest(id="b", name="B", version="1.0.0")
        m3 = PluginManifest(id="c", name="C", version="1.0.0")
        assert loader.load_plugin(m1) is True
        assert loader.load_plugin(m2) is True
        assert loader.load_plugin(m3) is False  # max reached

    def test_version_check(self):
        cfg = PluginSdkConfig(enable_version_check=True)
        loader = PluginLoader(cfg)
        manifest = PluginManifest(id="v", name="V", version="1.0.0",
                                  min_api_version="99.0.0")
        # API version is 1.0.0, so this should fail
        assert loader.load_plugin(manifest) is False


class TestHookManager:
    """Verify hook registration and execution."""

    def test_register_hook(self):
        mgr = HookManager()
        hook = PluginHook(hook_type="on_initialize", priority=100,
                          handler="handler_func", plugin_id="plugin_a")
        assert mgr.register_hook(hook) is True

    def test_register_duplicate(self):
        mgr = HookManager()
        hook = PluginHook(hook_type="on_initialize", priority=100,
                          handler="h", plugin_id="p")
        mgr.register_hook(hook)
        assert mgr.register_hook(hook) is False

    def test_unregister_hook(self):
        mgr = HookManager()
        hook = PluginHook(hook_type="on_intent", priority=50,
                          handler="h", plugin_id="p")
        mgr.register_hook(hook)
        assert mgr.unregister_hook("on_intent", "p") is True
        assert mgr.unregister_hook("on_intent", "p") is False

    def test_execute_hooks(self):
        mgr = HookManager()
        hook = PluginHook(hook_type="on_initialize", priority=100,
                          handler="handler", plugin_id="p")
        mgr.register_hook(hook)
        results = mgr.execute_hooks("on_initialize", {"data": 1})
        assert len(results) == 1
        assert results[0]["plugin_id"] == "p"

    def test_execute_hooks_empty(self):
        mgr = HookManager()
        results = mgr.execute_hooks("nonexistent", {})
        assert results == []

    def test_get_hooks(self):
        mgr = HookManager()
        hook = PluginHook(hook_type="on_intent", priority=100,
                          handler="h", plugin_id="p")
        mgr.register_hook(hook)
        hooks = mgr.get_hooks("on_intent")
        assert len(hooks) == 1

    def test_get_plugin_hooks(self):
        mgr = HookManager()
        h1 = PluginHook(hook_type="on_initialize", priority=100,
                        handler="h1", plugin_id="p1")
        h2 = PluginHook(hook_type="on_shutdown", priority=200,
                        handler="h2", plugin_id="p1")
        mgr.register_hook(h1)
        mgr.register_hook(h2)
        hooks = mgr.get_plugin_hooks("p1")
        assert len(hooks) == 2


class TestSandbox:
    """Verify sandbox execution."""

    def test_execute_success(self):
        sandbox = Sandbox()
        result, error = sandbox.execute(lambda: 42)
        assert result == 42
        assert error is None

    def test_execute_error(self):
        sandbox = Sandbox()

        def failing():
            raise ValueError("test error")

        result, error = sandbox.execute(failing)
        assert result is None
        assert error == "test error"

    def test_execute_timeout(self):
        sandbox = Sandbox()

        def slow():
            import time
            time.sleep(10)
            return "done"

        result, error = sandbox.execute(slow, timeout_ms=100)
        assert result is None
        assert error is not None
        assert "timed out" in error.lower()


class TestPluginSdkService:
    """Verify service wrapper."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        svc = PluginSdkService()
        assert await svc.initialize() is True

    @pytest.mark.asyncio
    async def test_load_and_unload_plugin(self):
        svc = PluginSdkService()
        await svc.initialize()
        manifest = PluginManifest(id="test_svc", name="Test", version="1.0.0",
                                  entry_point="")
        assert svc.load_plugin(manifest) is True
        assert svc.unload_plugin("test_svc") is True

    @pytest.mark.asyncio
    async def test_hook_operations(self):
        svc = PluginSdkService()
        await svc.initialize()
        hook = PluginHook(hook_type="on_intent", priority=100,
                          handler="handler", plugin_id="test")
        assert svc.register_hook(hook) is True
        results = svc.execute_hooks("on_intent", {"query": "hello"})
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_get_loaded_plugins(self):
        svc = PluginSdkService()
        await svc.initialize()
        manifest = PluginManifest(id="gp", name="GP", version="1.0.0",
                                  entry_point="")
        svc.load_plugin(manifest)
        plugins = svc.get_loaded_plugins()
        assert len(plugins) >= 1

    @pytest.mark.asyncio
    async def test_health(self):
        svc = PluginSdkService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_stats(self):
        svc = PluginSdkService()
        await svc.initialize()
        stats = await svc.stats()
        assert stats["service"] == "jarvis_plugin_sdk"

    @pytest.mark.asyncio
    async def test_shutdown(self):
        svc = PluginSdkService()
        await svc.initialize()
        await svc.shutdown()
        assert not svc.is_initialized()
