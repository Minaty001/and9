"""
app/core/plugin_sdk/ — Plugin SDK

Plugin system: register, load, unload, version management, sandbox,
hooks on service lifecycle.
"""

from .models import PluginManifest, PluginHook, PluginState
from .plugin_base import PluginBase
from .plugin_loader import PluginLoader
from .lifecycle import LifecycleManager
from .hook_manager import HookManager
from .sandbox import Sandbox, ResourceLimiter
from .service import PluginSdkService, PluginSdkConfig

__all__ = [
    "PluginManifest",
    "PluginHook",
    "PluginState",
    "PluginBase",
    "PluginLoader",
    "LifecycleManager",
    "HookManager",
    "Sandbox",
    "ResourceLimiter",
    "PluginSdkService",
    "PluginSdkConfig",
]
