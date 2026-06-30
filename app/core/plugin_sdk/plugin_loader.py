"""
Plugin SDK — Plugin Loader.

Load, unload, reload plugins with version checking and dependency resolution.
"""

from __future__ import annotations

import os
import sys
import json
import uuid
import importlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Type

from .models import PluginManifest, PluginState
from .plugin_base import PluginBase

logger = logging.getLogger(__name__)

try:
    from packaging.version import Version, InvalidVersion
    HAS_PACKAGING = True
except ImportError:
    HAS_PACKAGING = False


class PluginLoader:
    """Load, unload, and manage plugins.

    Usage:
        loader = PluginLoader()
        loader.load_plugin(manifest)
        loader.unload_plugin("plugin_id")
        loader.get_loaded_plugins()
    """

    def __init__(self, plugin_dir: str = "./plugins",
                 max_plugins: int = 20,
                 enable_version_check: bool = True,
                 enable_dependency_resolution: bool = True):
        self.plugin_dir = plugin_dir
        self.max_plugins = max_plugins
        self.enable_version_check = enable_version_check
        self.enable_dependency_resolution = enable_dependency_resolution
        self._plugins: Dict[str, PluginManifest] = {}
        self._states: Dict[str, PluginState] = {}
        self._modules: Dict[str, Any] = {}
        self._instances: Dict[str, PluginBase] = {}

    def load_plugin(self, manifest_or_path: Any,
                    plugin_class: Optional[Type[PluginBase]] = None) -> bool:
        """Load a plugin from a manifest object or path.

        Args:
            manifest_or_path: PluginManifest object, path string, or
                              a PluginBase subclass instance.
            plugin_class: Optional PluginBase subclass.

        Returns:
            True if loaded successfully.
        """
        manifest = manifest_or_path
        plugin_instance = None

        if isinstance(manifest_or_path, PluginBase):
            plugin_instance = manifest_or_path
            manifest = plugin_instance.manifest

        if isinstance(manifest, str):
            manifest = self._load_manifest_from_path(manifest)
            if not manifest:
                return False

        if not isinstance(manifest, PluginManifest):
            logger.error("Invalid manifest type: %s", type(manifest).__name__)
            return False

        if len(self._plugins) >= self.max_plugins:
            logger.error("Max plugins (%d) reached", self.max_plugins)
            return False

        if manifest.id in self._plugins:
            logger.warning("Plugin already loaded: %s", manifest.id)
            return False

        if self.enable_version_check:
            compatible, reason = self.check_compatibility(
                manifest.version, manifest.min_api_version,
            )
            if not compatible:
                logger.error("Plugin '%s' version incompatible: %s", manifest.id, reason)
                return False

        if self.enable_dependency_resolution and manifest.dependencies:
            for dep_id in manifest.dependencies:
                if dep_id not in self._plugins:
                    logger.error("Unresolved dependency '%s' for plugin '%s'", dep_id, manifest.id)
                    return False

        if plugin_class is not None:
            if not PluginBase.validate(plugin_class):
                logger.error("Plugin class validation failed for '%s'", manifest.id)
                return False

        try:
            if manifest.entry_point:
                module = importlib.import_module(manifest.entry_point)
                self._modules[manifest.id] = module
                if plugin_class is None:
                    plugin_class = self._find_plugin_class(module)
        except (ImportError, ModuleNotFoundError) as e:
            logger.warning("Could not import entry point '%s': %s", manifest.entry_point, e)

        if plugin_class is not None and issubclass(plugin_class, PluginBase):
            try:
                plugin_instance = plugin_class(manifest)
                plugin_instance.initialize()
                self._instances[manifest.id] = plugin_instance
                logger.info("Instantiated plugin '%s' from class %s", manifest.id, plugin_class.__name__)
            except Exception as e:
                logger.error("Failed to instantiate plugin '%s': %s", manifest.id, e)
                return False

        self._plugins[manifest.id] = manifest
        self._states[manifest.id] = PluginState(status="loaded")
        logger.info("Loaded plugin: %s v%s", manifest.name, manifest.version)
        return True

    def unload_plugin(self, plugin_id: str) -> bool:
        """Unload a plugin by ID."""
        if plugin_id not in self._plugins:
            return False

        if plugin_id in self._instances:
            try:
                self._instances[plugin_id].shutdown()
            except Exception as e:
                logger.warning("Error shutting down plugin '%s': %s", plugin_id, e)

        del self._plugins[plugin_id]
        if plugin_id in self._states:
            self._states[plugin_id].status = "unloaded"
        if plugin_id in self._modules:
            del self._modules[plugin_id]
        if plugin_id in self._instances:
            del self._instances[plugin_id]
        logger.info("Unloaded plugin: %s", plugin_id)
        return True

    def reload_plugin(self, plugin_id: str) -> bool:
        """Reload a plugin by ID."""
        if plugin_id not in self._plugins:
            return False
        manifest = self._plugins[plugin_id]
        plugin_instance = self._instances.get(plugin_id)
        self.unload_plugin(plugin_id)
        if plugin_instance:
            return self.load_plugin(plugin_instance)
        return self.load_plugin(manifest)

    def get_loaded_plugins(self) -> List[Dict[str, Any]]:
        """Get list of loaded plugin summaries."""
        return [
            {
                "id": pid,
                "name": m.name,
                "version": m.version,
                "status": self._states.get(pid, PluginState()).status,
                "hooks": m.hooks,
            }
            for pid, m in self._plugins.items()
        ]

    def get_plugin_state(self, plugin_id: str) -> Optional[PluginState]:
        """Get the runtime state of a plugin."""
        return self._states.get(plugin_id)

    def get_plugin_instance(self, plugin_id: str) -> Optional[PluginBase]:
        """Get the PluginBase instance for a plugin."""
        return self._instances.get(plugin_id)

    def discover_plugins(self) -> List[PluginManifest]:
        """Discover plugins from the plugin directory.

        Returns list of discovered PluginManifests (not yet loaded).
        """
        discovered = []
        if not os.path.isdir(self.plugin_dir):
            logger.warning("Plugin directory not found: %s", self.plugin_dir)
            return discovered

        for item in os.listdir(self.plugin_dir):
            item_path = os.path.join(self.plugin_dir, item)
            manifest = self._load_manifest_from_path(item_path)
            if manifest:
                discovered.append(manifest)

        return discovered

    def check_compatibility(self, plugin_version: str,
                            api_version: str) -> Tuple[bool, str]:
        """Check if a plugin version is compatible with the required API version."""
        if HAS_PACKAGING:
            try:
                pv = Version(plugin_version)
                av = Version(api_version)
                compatible = pv >= av
                reason = (
                    f"plugin v{plugin_version} >= required v{api_version}"
                    if compatible
                    else f"plugin v{plugin_version} < required v{api_version}"
                )
                return compatible, reason
            except InvalidVersion:
                pass

        try:
            plugin_parts = [int(x) for x in plugin_version.split(".")]
            api_parts = [int(x) for x in api_version.split(".")]
            while len(plugin_parts) < 3:
                plugin_parts.append(0)
            while len(api_parts) < 3:
                api_parts.append(0)
            compatible = tuple(plugin_parts[:3]) >= tuple(api_parts[:3])
            reason = (
                f"plugin v{plugin_version} >= required v{api_version}"
                if compatible
                else f"plugin v{plugin_version} < required v{api_version}"
            )
            return compatible, reason
        except (ValueError, AttributeError) as e:
            return False, f"version parse error: {e}"

    def _load_manifest_from_path(self, path: str) -> Optional[PluginManifest]:
        """Try to load a PluginManifest from a file or directory."""
        manifest_file = None
        if os.path.isfile(path) and path.endswith(".json"):
            manifest_file = path
        elif os.path.isdir(path):
            for candidate in ["plugin.json", "manifest.json", f"{os.path.basename(path)}.json"]:
                fp = os.path.join(path, candidate)
                if os.path.isfile(fp):
                    manifest_file = fp
                    break

        if not manifest_file:
            return None

        try:
            with open(manifest_file, "r") as f:
                data = json.load(f)
            return PluginManifest(**data)
        except Exception as e:
            logger.error("Failed to load manifest from %s: %s", path, e)
            return None

    def _find_plugin_class(self, module) -> Optional[Type[PluginBase]]:
        """Find a PluginBase subclass in a module."""
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type)
                    and issubclass(attr, PluginBase)
                    and attr is not PluginBase):
                return attr
        return None
