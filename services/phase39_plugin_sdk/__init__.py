"""
Phase 39 — Plugin SDK
======================

Plugin system: register, load, unload, version management, sandbox,
hooks on service lifecycle.

Components:
    - PluginBase: Abstract base class for all plugins
    - PluginLoader: Load, unload, reload plugins
    - HookManager: Register, unregister, execute hooks
    - Sandbox: Execute plugin code with restrictions
    - LifecycleManager: Manage plugin state transitions
    - PluginSdkService: ServiceBase wrapper
"""

from .config import PluginSdkConfig
from .models import PluginManifest, PluginHook, PluginState
from .plugin_base import PluginBase
from .plugin_loader import PluginLoader
from .lifecycle import LifecycleManager
from .hook_manager import HookManager
from .sandbox import Sandbox, ResourceLimiter
from .service import PluginSdkService

__all__ = [
    "PluginSdkConfig",
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
]
