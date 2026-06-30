"""
Phase 39 — Plugin Base Class.

Abstract base class that all plugins must subclass.
Defines the contract every plugin must fulfill.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from .models import PluginManifest, PluginState

logger = logging.getLogger(__name__)


class PluginBase(ABC):
    """Abstract base class for all JARVIS plugins.

    Every plugin MUST subclass PluginBase and implement:
        - initialize()
        - shutdown()
        - get_metadata() -> dict

    Optional lifecycle hooks:
        - on_intent(context)
        - on_response(context)
        - on_turn(context)
        - on_error(context)

    Usage:
        class MyPlugin(PluginBase):
            def initialize(self):
                self._conn = connect()

            def shutdown(self):
                self._conn.close()

            def get_metadata(self):
                return {"description": "My custom plugin"}
    """

    def __init__(self, manifest: PluginManifest):
        self._manifest = manifest
        self._state = PluginState(status="installed")

    # ── Required abstract methods ────────────────────────────────

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the plugin.

        Called when the plugin is loaded. Perform any setup here.
        """
        ...

    @abstractmethod
    def shutdown(self) -> None:
        """Shut down the plugin.

        Called when the plugin is unloaded. Release all resources.
        """
        ...

    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """Return plugin metadata as a dictionary.

        Must contain at least:
            - "name": human-readable plugin name
            - "version": plugin version string
            - "description": brief description
        """
        ...

    # ── Properties ───────────────────────────────────────────────

    @property
    def manifest(self) -> PluginManifest:
        """Return the plugin manifest."""
        return self._manifest

    @property
    def state(self) -> PluginState:
        """Return the current plugin state."""
        return self._state

    # ── Optional lifecycle hooks ──────────────────────────────────

    def on_intent(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Called when an intent is being processed.

        Args:
            context: Intent context dictionary.

        Returns:
            Optional modifications to the context.
        """
        return None

    def on_response(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Called before a response is sent.

        Args:
            context: Response context dictionary.

        Returns:
            Optional modifications to the response.
        """
        return None

    def on_turn(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Called on each conversation turn.

        Args:
            context: Turn context dictionary.

        Returns:
            Optional modifications to the context.
        """
        return None

    def on_error(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Called when an error occurs.

        Args:
            context: Error context dictionary.

        Returns:
            Optional modifications or recovery hints.
        """
        return None

    # ── Validation ────────────────────────────────────────────────

    @classmethod
    def validate(cls, plugin_class: type) -> bool:
        """Validate that a plugin class implements all required methods.

        Args:
            plugin_class: The class to validate.

        Returns:
            True if the class implements required abstract methods.
        """
        if not issubclass(plugin_class, PluginBase):
            logger.error("Class %s does not inherit from PluginBase", plugin_class.__name__)
            return False

        # Check that abstract methods are implemented
        missing = []
        for method_name in ["initialize", "shutdown", "get_metadata"]:
            method = getattr(plugin_class, method_name, None)
            if method is None:
                missing.append(method_name)
                continue
            # Check if it's still abstract (wrapped by abstractmethod)
            if getattr(method, "__isabstractmethod__", False):
                missing.append(method_name)

        if missing:
            logger.error(
                "Plugin class %s is missing required methods: %s",
                plugin_class.__name__,
                ", ".join(missing),
            )
            return False

        return True

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self._manifest.id}, state={self._state.status})"
