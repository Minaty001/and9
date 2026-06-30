"""
Phase 39 — Plugin Loader.

Load, unload, reload plugins with version checking and dependency resolution.
Integrates with PluginBase for validation and enhanced version checking.
"""

from __future__ import annotations

import os
import sys
import uuid
import importlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Type

from .config import PluginSdkConfig
from .models import PluginManifest, PluginState
from .plugin_base import PluginBase

logger = logging.getLogger(__name__)

try:
    from packaging.version import Version, InvalidVersion
    HAS_PACKAGING = True
except ImportError:
    HAS_PACKAGING = False
    logger.debug("packaging.version not available, using tuple comparison")


class PluginLoader:
    """Load, unload, and manage plugins.

    Usage:
        loader = PluginLoader()
        loader.load_plugin(manifest)
        loader.unload_plugin("plugin_id")
        loader.get_loaded_plugins()
    """

    def __init__(self, config: Optional[PluginSdkConfig] = None):
        self.config = config or PluginSdkConfig()
        self._plugins: Dict[str, PluginManifest] = {}
        self._states: Dict[str, PluginState] = {}
        self._modules: Dict[str, Any] = {}
        self._instances: Dict[str, PluginBase] = {}  # plugin_id -> PluginBase instance

    def load_plugin(self, manifest_or_path: Any,
                    plugin_class: Optional[Type[PluginBase]] = None) -> bool:
        """Load a plugin from a manifest object or path.

        Args:
            manifest_or_path: PluginManifest object, path string, or
                              a PluginBase subclass instance.
            plugin_class: Optional PluginBase subclass. If provided, the
                          plugin is validated and instantiated.

        Returns:
            True if loaded successfully.
        """
        manifest = manifest_or_path
        plugin_instance = None

        # If a PluginBase instance is passed directly
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

        # Check limits
        if len(self._plugins) >= self.config.max_plugins:
            logger.error("Max plugins (%d) reached", self.config.max_plugins)
            return False

        # Check if already loaded
        if manifest.id in self._plugins:
            logger.warning("Plugin already loaded: %s", manifest.id)
            return False

        # Version check
        if self.config.enable_version_check:
            compatible, reason = self.check_compatibility(
                manifest.version, manifest.min_api_version
            )
            if not compatible:
                logger.error(
                    "Plugin '%s' version incompatible: %s", manifest.id, reason
                )
                return False

        # Dependency resolution
        if self.config.enable_dependency_resolution and manifest.dependencies:
            for dep_id in manifest.dependencies:
                if dep_id not in self._plugins:
                    logger.error(
                        "Unresolved dependency '%s' for plugin '%s'", dep_id, manifest.id
                    )
                    return False

        # Validate PluginBase if class provided
        if plugin_class is not None:
            if not PluginBase.validate(plugin_class):
                logger.error(
                    "Plugin class validation failed for '%s'", manifest.id
                )
                return False

        # Try to load entry point module
        try:
            if manifest.entry_point:
                module = importlib.import_module(manifest.entry_point)
                self._modules[manifest.id] = module
                # If plugin_class not provided, try to find a PluginBase subclass in module
                if plugin_class is None:
                    plugin_class = self._find_plugin_class(module)
        except (ImportError, ModuleNotFoundError) as e:
            logger.warning(
                "Could not import entry point '%s': %s", manifest.entry_point, e
            )

        # Instantiate PluginBase if class was found
        if plugin_class is not None and issubclass(plugin_class, PluginBase):
            try:
                plugin_instance = plugin_class(manifest)
                plugin_instance.initialize()
                self._instances[manifest.id] = plugin_instance
                logger.info(
                    "Instantiated plugin '%s' from class %s",
                    manifest.id, plugin_class.__name__
                )
            except Exception as e:
                logger.error(
                    "Failed to instantiate plugin '%s': %s", manifest.id, e
                )
                return False

        self._plugins[manifest.id] = manifest
        self._states[manifest.id] = PluginState(
            status="loaded",
            loaded_at=datetime.now(timezone.utc),
        )
        logger.info("Loaded plugin: %s v%s", manifest.name, manifest.version)
        return True

    def unload_plugin(self, id: str) -> bool:
        """Unload a plugin by ID.

        Returns True if unloaded.
        """
        if id not in self._plugins:
            return False

        # Shutdown plugin instance if it exists
        if id in self._instances:
            try:
                self._instances[id].shutdown()
            except Exception as e:
                logger.warning("Error shutting down plugin '%s': %s", id, e)

        del self._plugins[id]
        if id in self._states:
            self._states[id].status = "unloaded"
        if id in self._modules:
            del self._modules[id]
        if id in self._instances:
            del self._instances[id]
        logger.info("Unloaded plugin: %s", id)
        return True

    def reload_plugin(self, id: str) -> bool:
        """Reload a plugin by ID.

        Returns True if reloaded.
        """
        if id not in self._plugins:
            return False
        manifest = self._plugins[id]
        plugin_instance = self._instances.get(id)
        self.unload_plugin(id)
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

    def get_plugin_state(self, id: str) -> Optional[PluginState]:
        """Get the runtime state of a plugin."""
        return self._states.get(id)

    def get_plugin_instance(self, id: str) -> Optional[PluginBase]:
        """Get the PluginBase instance for a plugin."""
        return self._instances.get(id)

    def discover_plugins(self) -> List[PluginManifest]:
        """Discover plugins from the plugin directory.

        Returns list of discovered PluginManifests (not yet loaded).
        """
        discovered = []
        plugin_dir = self.config.plugin_dir
        if not os.path.isdir(plugin_dir):
            logger.warning("Plugin directory not found: %s", plugin_dir)
            return discovered

        for item in os.listdir(plugin_dir):
            item_path = os.path.join(plugin_dir, item)
            manifest = self._load_manifest_from_path(item_path)
            if manifest:
                discovered.append(manifest)

        return discovered

    def check_compatibility(self, plugin_version: str,
                            api_version: str) -> Tuple[bool, str]:
        """Check if a plugin version is compatible with the required API version.

        Uses packaging.version if available, otherwise falls back to
        simple tuple comparison of version components.

        Args:
            plugin_version: The version string of the plugin.
            api_version: The minimum API version required.

        Returns:
            Tuple of (compatible: bool, reason: str).
        """
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
            except InvalidVersion as e:
                logger.warning("Invalid version string: %s", e)
                # Fallback to tuple comparison below

        # Fallback: tuple comparison
        try:
            plugin_parts = [int(x) for x in plugin_version.split(".")]
            api_parts = [int(x) for x in api_version.split(".")]
            # Pad shorter lists
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
            import json
            with open(manifest_file, "r") as f:
                data = json.load(f)
            return PluginManifest(**data)
        except Exception as e:
            logger.error("Failed to load manifest from %s: %s", path, e)
            return None

    def _check_api_version(self, min_api_version: str) -> bool:
        """Check if the current API version meets the minimum (legacy compatibility)."""
        compatible, _ = self.check_compatibility("1.0.0", min_api_version)
        return compatible

    def _find_plugin_class(self, module) -> Optional[Type[PluginBase]]:
        """Find a PluginBase subclass in a module."""
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type)
                    and issubclass(attr, PluginBase)
                    and attr is not PluginBase):
                return attr
        return None
