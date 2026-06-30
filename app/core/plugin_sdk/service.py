"""
Plugin SDK — Service.

Wrapper around PluginLoader, HookManager, and Sandbox.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Callable, Dict, List, Optional

from .models import PluginManifest, PluginHook, PluginState
from .plugin_loader import PluginLoader
from .hook_manager import HookManager
from .sandbox import Sandbox

logger = logging.getLogger(__name__)


class PluginSdkConfig:
    """Configuration for PluginSdkService."""

    def __init__(self,
                 service_name: str = "jarvis_plugin_sdk",
                 plugin_dir: str = "./plugins",
                 max_plugins: int = 20,
                 enable_version_check: bool = True,
                 enable_dependency_resolution: bool = True,
                 sandbox_timeout_ms: int = 5000,
                 sandbox_allowed_imports: Optional[List[str]] = None,
                 plugin_auto_load: bool = True):
        self.service_name = service_name
        self.plugin_dir = plugin_dir
        self.max_plugins = max_plugins
        self.enable_version_check = enable_version_check
        self.enable_dependency_resolution = enable_dependency_resolution
        self.sandbox_timeout_ms = sandbox_timeout_ms
        self.sandbox_allowed_imports = sandbox_allowed_imports or []
        self.plugin_auto_load = plugin_auto_load


class PluginSdkService:
    """Plugin SDK service for managing plugins and hooks.

    Usage:
        svc = PluginSdkService()
        await svc.initialize()
        svc.load_plugin(manifest)
        svc.execute_hooks("on_initialize", {})
    """

    def __init__(self, config: Optional[PluginSdkConfig] = None):
        self.config = config or PluginSdkConfig()
        self.plugin_loader: Optional[PluginLoader] = None
        self.hook_manager: Optional[HookManager] = None
        self.sandbox: Optional[Sandbox] = None
        self._initialized = False
        self._start_time = 0.0
        self._counters: Dict[str, int] = {
            "plugins_loaded": 0, "plugins_unloaded": 0,
            "hooks_registered": 0, "hooks_executed": 0,
        }

    async def initialize(self) -> bool:
        """Initialize the plugin SDK service."""
        self._start_time = time.time()
        try:
            self.plugin_loader = PluginLoader(
                plugin_dir=self.config.plugin_dir,
                max_plugins=self.config.max_plugins,
                enable_version_check=self.config.enable_version_check,
                enable_dependency_resolution=self.config.enable_dependency_resolution,
            )
            self.hook_manager = HookManager()
            self.sandbox = Sandbox(
                sandbox_timeout_ms=self.config.sandbox_timeout_ms,
                allowed_imports=self.config.sandbox_allowed_imports,
            )
            self._initialized = True

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
        """Shut down the plugin SDK service."""
        logger.info("PluginSdkService shutting down...")
        if self.plugin_loader:
            for info in self.plugin_loader.get_loaded_plugins():
                self.plugin_loader.unload_plugin(info["id"])
        self._initialized = False

    def _check_init(self):
        if not self._initialized:
            raise RuntimeError("PluginSdkService not initialized")

    # ── Plugin Operations ───────────────────────────────────────────

    async def load_plugin(self, manifest_or_path: Any) -> bool:
        self._check_init()
        result = self.plugin_loader.load_plugin(manifest_or_path)
        if result:
            self._counters["plugins_loaded"] += 1
        return result

    async def unload_plugin(self, plugin_id: str) -> bool:
        self._check_init()
        result = self.plugin_loader.unload_plugin(plugin_id)
        if result:
            self._counters["plugins_unloaded"] += 1
        return result

    async def reload_plugin(self, plugin_id: str) -> bool:
        self._check_init()
        return self.plugin_loader.reload_plugin(plugin_id)

    async def discover_plugins(self) -> List[PluginManifest]:
        self._check_init()
        return self.plugin_loader.discover_plugins()

    async def get_loaded_plugins(self) -> List[Dict[str, Any]]:
        self._check_init()
        return self.plugin_loader.get_loaded_plugins()

    async def get_plugin_info(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        self._check_init()
        for info in self.plugin_loader.get_loaded_plugins():
            if info["id"] == plugin_id:
                return info
        return None

    async def get_plugin_state(self, plugin_id: str) -> Optional[PluginState]:
        self._check_init()
        return self.plugin_loader.get_plugin_state(plugin_id)

    # ── Hook Operations ─────────────────────────────────────────────

    async def register_hook(self, hook_type: str, plugin_id: str,
                            handler: Callable[[Dict[str, Any]], Any],
                            priority: int = 100) -> bool:
        self._check_init()
        hook = PluginHook(hook_type=hook_type, priority=priority,
                          handler=handler.__name__, plugin_id=plugin_id)
        result = self.hook_manager.register_hook(hook)
        if result:
            self.hook_manager.register_handler(plugin_id, handler.__name__, handler)
            self._counters["hooks_registered"] += 1
        return result

    async def unregister_hook(self, hook_type: str, plugin_id: str) -> bool:
        self._check_init()
        return self.hook_manager.unregister_hook(hook_type, plugin_id)

    async def execute_hooks(self, hook_type: str,
                            context: Dict[str, Any]) -> List[Dict[str, Any]]:
        self._check_init()
        results = self.hook_manager.execute_hooks(hook_type, context)
        self._counters["hooks_executed"] += len(results)
        return results

    async def get_hooks(self, hook_type: str) -> List[PluginHook]:
        self._check_init()
        return self.hook_manager.get_hooks(hook_type)

    async def get_plugin_hooks(self, plugin_id: str) -> List[PluginHook]:
        self._check_init()
        return self.hook_manager.get_plugin_hooks(plugin_id)

    # ── Health / Stats ─────────────────────────────────────────────

    async def health(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        plugins = self.plugin_loader.get_loaded_plugins() if self.plugin_loader else []
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
            "loaded_plugins": len(plugins),
        }

    async def stats(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        plugins = self.plugin_loader.get_loaded_plugins() if self.plugin_loader else []
        hook_count = len(self.hook_manager._hooks) if self.hook_manager else 0
        return {
            "service": getattr(self.config, "service_name", "jarvis_plugin_sdk"),
            "uptime_seconds": round(uptime, 1),
            "loaded_plugins": plugins,
            "hook_types_count": hook_count,
            "counters": dict(self._counters),
        }
