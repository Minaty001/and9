"""
Phase 39 — Plugin SDK Service.

ServiceBase wrapper for the Plugin SDK service.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Callable, Dict, List, Optional

from services.base.service_base import ServiceBase
from .config import PluginSdkConfig
from .models import PluginManifest, PluginHook, PluginState
from .plugin_loader import PluginLoader
from .hook_manager import HookManager
from .sandbox import Sandbox

logger = logging.getLogger(__name__)


class PluginSdkService(ServiceBase):
    """Plugin SDK service for managing plugins and hooks.

    Usage:
        svc = PluginSdkService()
        await svc.initialize()
        svc.load_plugin(manifest)
        svc.execute_hooks("on_initialize", {})
    """

    def __init__(self, config: Optional[PluginSdkConfig] = None):
        super().__init__(name="jarvis_plugin_sdk", version="1.0.0")
        self.config = config or PluginSdkConfig()
        self.plugin_loader: Optional[PluginLoader] = None
        self.hook_manager: Optional[HookManager] = None
        self.sandbox: Optional[Sandbox] = None
        self._start_time = 0.0

    async def initialize(self) -> bool:
        self._start_time = time.time()
        try:
            self.plugin_loader = PluginLoader(self.config)
            self.hook_manager = HookManager()
            self.sandbox = Sandbox(self.config)
            self._metrics.reset()
            self._initialized = True

            # Auto-load plugins
            if self.config.plugin_auto_load:
                discovered = self.plugin_loader.discover_plugins()
                for manifest in discovered[:self.config.max_plugins]:
                    self.plugin_loader.load_plugin(manifest)
                    logger.info("Auto-loaded plugin: %s", manifest.name)

            logger.info("PluginSdkService initialized")
            return True
        except Exception as e:
            logger.error("PluginSdkService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        logger.info("PluginSdkService shutting down...")
        # Unload all plugins
        if self.plugin_loader:
            for info in self.plugin_loader.get_loaded_plugins():
                self.plugin_loader.unload_plugin(info["id"])
        self._initialized = False

    # ── Plugin Operations ───────────────────────────────────────────

    async def load_plugin(self, manifest_or_path: Any) -> bool:
        if not self.plugin_loader:
            raise RuntimeError("PluginSdkService not initialized")
        result = self.plugin_loader.load_plugin(manifest_or_path)
        if result:
            self._metrics.counter("plugins_loaded", 1)
        return result

    async def unload_plugin(self, id: str) -> bool:
        if not self.plugin_loader:
            raise RuntimeError("PluginSdkService not initialized")
        result = self.plugin_loader.unload_plugin(id)
        if result:
            self._metrics.counter("plugins_unloaded", 1)
        return result

    async def reload_plugin(self, id: str) -> bool:
        if not self.plugin_loader:
            raise RuntimeError("PluginSdkService not initialized")
        return self.plugin_loader.reload_plugin(id)

    async def discover_plugins(self) -> List[PluginManifest]:
        if not self.plugin_loader:
            raise RuntimeError("PluginSdkService not initialized")
        return self.plugin_loader.discover_plugins()

    async def get_loaded_plugins(self) -> List[Dict[str, Any]]:
        if not self.plugin_loader:
            raise RuntimeError("PluginSdkService not initialized")
        return self.plugin_loader.get_loaded_plugins()

    async def get_plugin_info(self, id: str) -> Optional[Dict[str, Any]]:
        """Get detailed info about a plugin."""
        if not self.plugin_loader:
            raise RuntimeError("PluginSdkService not initialized")
        for info in self.plugin_loader.get_loaded_plugins():
            if info["id"] == id:
                return info
        return None

    async def get_plugin_state(self, id: str) -> Optional[PluginState]:
        if not self.plugin_loader:
            raise RuntimeError("PluginSdkService not initialized")
        return self.plugin_loader.get_plugin_state(id)

    # ── Hook Operations ─────────────────────────────────────────────

    async def register_hook(self, hook_type: str, plugin_id: str,
                             handler: Callable[[Dict[str, Any]], Any],
                             priority: int = 100) -> bool:
        if not self.hook_manager:
            raise RuntimeError("PluginSdkService not initialized")
        # Create PluginHook object
        hook = PluginHook(hook_type=hook_type, priority=priority,
                          handler=handler.__name__, plugin_id=plugin_id)
        result = self.hook_manager.register_hook(hook)
        if result:
            self.hook_manager.register_handler(plugin_id, handler.__name__, handler)
            self._metrics.counter("hooks_registered", 1)
        return result

    async def unregister_hook(self, hook_type: str, plugin_id: str) -> bool:
        if not self.hook_manager:
            raise RuntimeError("PluginSdkService not initialized")
        return self.hook_manager.unregister_hook(hook_type, plugin_id)

    async def execute_hooks(self, hook_type: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not self.hook_manager:
            raise RuntimeError("PluginSdkService not initialized")
        results = self.hook_manager.execute_hooks(hook_type, context)
        self._metrics.counter("hooks_executed", len(results))
        return results

    async def get_hooks(self, hook_type: str) -> List[PluginHook]:
        if not self.hook_manager:
            raise RuntimeError("PluginSdkService not initialized")
        return self.hook_manager.get_hooks(hook_type)

    async def get_plugin_hooks(self, plugin_id: str) -> List[PluginHook]:
        if not self.hook_manager:
            raise RuntimeError("PluginSdkService not initialized")
        return self.hook_manager.get_plugin_hooks(plugin_id)

    # ── Health / Stats ─────────────────────────────────────────────

    async def health(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        plugins = self.plugin_loader.get_loaded_plugins() if self.plugin_loader else []
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service_name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
            "loaded_plugins": len(plugins),
        }

    async def stats(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        plugins = self.plugin_loader.get_loaded_plugins() if self.plugin_loader else []
        hook_count = len(self.hook_manager._hooks) if self.hook_manager else 0
        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            "loaded_plugins": plugins,
            "hook_types_count": hook_count,
            "metrics": self._metrics.snapshot(),
        }
