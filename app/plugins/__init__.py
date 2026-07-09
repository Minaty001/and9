"""
app/plugins/__init__.py — Plugin registry for AND9

Plugins extend AND9 without modifying the kernel.
Each plugin declares which intents it handles.

Auto-discovery: all folders in app/plugins/ with a plugin.py
are auto-loaded on startup.
"""

import importlib
import logging
import os
from typing import Dict, Optional
from app.plugins.base_plugin import BasePlugin

logger = logging.getLogger(__name__)
_registry: Dict[str, BasePlugin] = {}
_intent_map: Dict[str, str] = {}   # intent -> plugin name


def load_all_plugins() -> None:
    """Auto-discover and load all plugins."""
    plugins_dir = os.path.dirname(__file__)
    for folder in os.listdir(plugins_dir):
        plugin_py = os.path.join(plugins_dir, folder, "plugin.py")
        if os.path.isfile(plugin_py):
            _load_plugin(folder)


def _load_plugin(name: str) -> None:
    try:
        mod = importlib.import_module(f"app.plugins.{name}.plugin")
        plugin: BasePlugin = mod.Plugin()
        plugin.initialize()
        _registry[plugin.name] = plugin
        for intent in plugin.intents:
            _intent_map[intent] = plugin.name
        logger.info(f"Plugin loaded: {plugin.name}")
    except Exception as e:
        logger.error(f"Failed to load plugin '{name}': {e}")


def get_plugin_for_intent(intent: str) -> Optional[BasePlugin]:
    name = _intent_map.get(intent)
    return _registry.get(name) if name else None