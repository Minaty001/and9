"""
Phase 39 — Plugin Lifecycle Manager.

Manages state transitions for plugins and fires lifecycle hook events.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import PluginState

logger = logging.getLogger(__name__)

# Valid state transitions: current_state -> set(allowed_next_states)
_VALID_TRANSITIONS: Dict[str, set] = {
    "installed": {"enabled", "disabled", "error", "blocked"},
    "loaded": {"enabled", "disabled", "unloaded", "error", "blocked", "updating"},
    "enabled": {"disabled", "unloaded", "error", "blocked", "updating"},
    "disabled": {"enabled", "unloaded", "error", "blocked", "updating"},
    "updating": {"enabled", "disabled", "error", "blocked", "unloaded"},
    "blocked": {"disabled", "unloaded", "error"},
    "error": {"installed", "disabled", "enabled", "unloaded"},
    "unloaded": {"installed", "error"},
}


class LifecycleManager:
    """Manage plugin lifecycle state transitions.

    Usage:
        mgr = LifecycleManager()
        mgr.transition("plugin_1", "enabled")
        state = mgr.get_state("plugin_1")
        history = mgr.get_history("plugin_1")
    """

    def __init__(self):
        self._states: Dict[str, PluginState] = {}
        self._history: Dict[str, List[Dict[str, Any]]] = {}
        self._listeners: Dict[str, List[callable]] = {}

    def transition(self, plugin_id: str, new_state: str,
                   reason: str = "") -> bool:
        """Transition a plugin to a new state.

        Args:
            plugin_id: ID of the plugin.
            new_state: Target state.
            reason: Reason for the transition.

        Returns:
            True if the transition was valid and applied.
        """
        current_state = self._states.get(plugin_id)
        current_status = current_state.status if current_state else "unloaded"

        if new_state == current_status:
            logger.debug("Plugin '%s' already in state '%s'", plugin_id, new_state)
            return True

        # Validate transition
        allowed = _VALID_TRANSITIONS.get(current_status, set())
        if new_state not in allowed:
            logger.error(
                "Invalid state transition for plugin '%s': %s -> %s",
                plugin_id, current_status, new_state,
            )
            return False

        # Apply transition
        if current_state is None:
            self._states[plugin_id] = PluginState(status=new_state)

        self._states[plugin_id].status = new_state

        # Track transition event
        event = {
            "from_state": current_status,
            "to_state": new_state,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
        }

        if plugin_id not in self._history:
            self._history[plugin_id] = []
        self._history[plugin_id].append(event)

        if current_state is not None:
            if current_state.lifecycle_events is None:
                current_state.lifecycle_events = []
            current_state.lifecycle_events.append(event)

        logger.info(
            "Plugin '%s' transition: %s -> %s%s",
            plugin_id, current_status, new_state,
            f" ({reason})" if reason else "",
        )

        # Fire listeners
        self._fire_event(plugin_id, current_status, new_state, reason)

        return True

    def get_state(self, plugin_id: str) -> Optional[PluginState]:
        """Get the current state of a plugin.

        Returns None if the plugin is unknown.
        """
        return self._states.get(plugin_id)

    def get_history(self, plugin_id: str) -> List[Dict[str, Any]]:
        """Get the lifecycle event history for a plugin.

        Returns a list of event dicts, newest first.
        """
        events = self._history.get(plugin_id, [])
        return list(reversed(events))

    def on_transition(self, plugin_id: str, callback: callable) -> None:
        """Register a listener for state transitions of a specific plugin.

        Args:
            plugin_id: Plugin ID or "*" for all plugins.
            callback: Callable(plugin_id, from_state, to_state, reason).
        """
        if plugin_id not in self._listeners:
            self._listeners[plugin_id] = []
        self._listeners[plugin_id].append(callback)

    def _fire_event(self, plugin_id: str, from_state: str,
                    to_state: str, reason: str) -> None:
        """Fire transition event to registered listeners."""
        listeners = self._listeners.get(plugin_id, []) + self._listeners.get("*", [])
        for cb in listeners:
            try:
                cb(plugin_id, from_state, to_state, reason)
            except Exception as e:
                logger.warning("Lifecycle listener error for '%s': %s", plugin_id, e)

    @staticmethod
    def get_valid_transitions(state: str) -> List[str]:
        """Get list of valid target states from a given state."""
        return sorted(_VALID_TRANSITIONS.get(state, set()))

    @property
    def all_states(self) -> Dict[str, str]:
        """Return {plugin_id: status} for all tracked plugins."""
        return {pid: st.status for pid, st in self._states.items()}
