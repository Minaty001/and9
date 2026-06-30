"""
Phase 45 — Plugin Marketplace.

Manages plugin listings, installation, ratings, and search.
Comes with built-in mock plugins.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from .models import PluginListing
from .config import RoadmapConfig

logger = logging.getLogger(__name__)


_BUILTIN_PLUGINS = [
    PluginListing(
        id="voice-enhancer",
        name="Voice Enhancer",
        version="2.1.0",
        author="JARVIS Labs",
        description="Enhance voice input quality with noise reduction and echo cancellation",
        rating=4.5,
        downloads=15200,
        categories=["audio", "voice", "enhancement"],
    ),
    PluginListing(
        id="smart-home",
        name="Smart Home Hub",
        version="1.3.0",
        author="HomeAutomation Inc",
        description="Control smart home devices: lights, thermostat, locks, and sensors",
        rating=4.2,
        downloads=28300,
        categories=["home", "automation", "iot"],
    ),
    PluginListing(
        id="email-assistant",
        name="Email Assistant",
        version="3.0.0",
        author="MailTech",
        description="Draft, summarize, and manage emails with AI-powered assistance",
        rating=4.8,
        downloads=42100,
        categories=["productivity", "communication", "email"],
    ),
    PluginListing(
        id="calendar-pro",
        name="Calendar Pro",
        version="1.1.0",
        author="Scheduler AI",
        description="Advanced calendar management with smart scheduling and reminders",
        rating=4.0,
        downloads=9800,
        categories=["productivity", "calendar", "scheduling"],
    ),
    PluginListing(
        id="weather-plus",
        name="Weather Plus",
        version="2.0.0",
        author="WeatherStack",
        description="Real-time weather forecasts, alerts, and historical data analysis",
        rating=4.6,
        downloads=31500,
        categories=["utilities", "weather", "data"],
    ),
]


class PluginMarketplace:
    """Manages the plugin marketplace.

    Usage:
        pm = PluginMarketplace()
        plugins = pm.list_plugins()
        plugin = pm.get_plugin('voice-enhancer')
        pm.install_plugin('voice-enhancer')
    """

    def __init__(self, config: Optional[RoadmapConfig] = None):
        self.config = config or RoadmapConfig()
        # Load built-in plugins
        self._plugins: Dict[str, PluginListing] = {p.id: p for p in _BUILTIN_PLUGINS}

    def list_plugins(self, category: Optional[str] = None) -> List[PluginListing]:
        """List available plugins, optionally filtered by category.

        Args:
            category: Optional category filter.

        Returns:
            List of PluginListing.
        """
        if category:
            return [p for p in self._plugins.values() if category in p.categories]
        return list(self._plugins.values())

    def get_plugin(self, plugin_id: str) -> Optional[PluginListing]:
        """Get a specific plugin by ID.

        Args:
            plugin_id: Plugin identifier.

        Returns:
            PluginListing or None.
        """
        return self._plugins.get(plugin_id)

    def install_plugin(self, plugin_id: str) -> bool:
        """Install a plugin.

        Args:
            plugin_id: Plugin identifier.

        Returns:
            True if installed, False if not found or already installed.
        """
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            logger.warning("Plugin not found: %s", plugin_id)
            return False
        if plugin.installed:
            logger.info("Plugin '%s' already installed", plugin_id)
            return False
        plugin.installed = True
        logger.info("Installed plugin '%s'", plugin_id)
        return True

    def uninstall_plugin(self, plugin_id: str) -> bool:
        """Uninstall a plugin.

        Args:
            plugin_id: Plugin identifier.

        Returns:
            True if uninstalled, False if not found or not installed.
        """
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return False
        if not plugin.installed:
            return False
        plugin.installed = False
        logger.info("Uninstalled plugin '%s'", plugin_id)
        return True

    def rate_plugin(self, plugin_id: str, rating: float) -> bool:
        """Rate a plugin.

        Args:
            plugin_id: Plugin identifier.
            rating: Rating value (0.0-5.0).

        Returns:
            True if rated, False if plugin not found.
        """
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return False
        rating = max(0.0, min(5.0, rating))
        # Simulate weighted average
        plugin.rating = round((plugin.rating * plugin.downloads + rating) / (plugin.downloads + 1), 1)
        plugin.downloads += 1
        logger.info("Rated plugin '%s' (%.1f)", plugin_id, rating)
        return True

    def search_plugins(self, query: str) -> List[PluginListing]:
        """Search plugins by name, description, or category.

        Args:
            query: Search query.

        Returns:
            List of matching PluginListing.
        """
        q = query.lower()
        results = []
        for plugin in self._plugins.values():
            if (q in plugin.name.lower()
                    or q in plugin.description.lower()
                    or q in plugin.author.lower()
                    or any(q in cat.lower() for cat in plugin.categories)):
                results.append(plugin)
        return results
