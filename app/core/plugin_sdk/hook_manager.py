"""
Plugin SDK — Hook Manager.

Register, unregister, and execute lifecycle hooks.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Callable, Dict, List, Optional
from collections import defaultdict

from .models import PluginHook

logger = logging.getLogger(__name__)


class HookManager:
    """Manage plugin lifecycle hooks.

    Usage:
        mgr = HookManager()
        mgr.register_hook(PluginHook(hook_type="on_initialize", ...))
        mgr.execute_hooks("on_initialize", {"service": ...})
    """

    def __init__(self):
        self._hooks: Dict[str, List[PluginHook]] = defaultdict(list)
        self._handlers: Dict[str, Dict[str, Callable]] = defaultdict(dict)

    def register_hook(self, hook: PluginHook) -> bool:
        """Register a hook.

        Returns True if registered.
        """
        hook_list = self._hooks[hook.hook_type]
        for existing in hook_list:
            if existing.plugin_id == hook.plugin_id and existing.hook_type == hook.hook_type:
                logger.warning("Hook already registered: %s/%s", hook.plugin_id, hook.hook_type)
                return False
        hook_list.append(hook)
        hook_list.sort(key=lambda h: h.priority)
        logger.debug("Registered hook: %s/%s (priority=%d)", hook.plugin_id, hook.hook_type, hook.priority)
        return True

    def unregister_hook(self, hook_type: str, plugin_id: str) -> bool:
        """Unregister a hook by type and plugin ID."""
        hook_list = self._hooks.get(hook_type, [])
        for i, hook in enumerate(hook_list):
            if hook.plugin_id == plugin_id:
                hook_list.pop(i)
                logger.debug("Unregistered hook: %s/%s", plugin_id, hook_type)
                return True
        return False

    def execute_hooks(self, hook_type: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute all hooks of a given type.

        Args:
            hook_type: Hook type to execute.
            context: Context dict passed to each hook.

        Returns:
            List of results from each hook execution.
        """
        hook_list = self._hooks.get(hook_type, [])
        if not hook_list:
            return []

        results = []
        for hook in hook_list:
            handler = self._handlers.get(hook.plugin_id, {}).get(hook.handler)
            t0 = time.perf_counter()
            try:
                if handler:
                    result = handler(context)
                else:
                    result = {"plugin_id": hook.plugin_id, "status": "no_handler"}
                elapsed = (time.perf_counter() - t0) * 1000
                results.append({
                    "plugin_id": hook.plugin_id,
                    "hook_type": hook_type,
                    "success": True,
                    "result": result,
                    "duration_ms": round(elapsed, 3),
                })
            except Exception as e:
                elapsed = (time.perf_counter() - t0) * 1000
                logger.error("Hook execution failed: %s/%s: %s", hook.plugin_id, hook.handler, e)
                results.append({
                    "plugin_id": hook.plugin_id,
                    "hook_type": hook_type,
                    "success": False,
                    "error": str(e),
                    "duration_ms": round(elapsed, 3),
                })

        return results

    def get_hooks(self, hook_type: str) -> List[PluginHook]:
        """Get all hooks of a given type."""
        return list(self._hooks.get(hook_type, []))

    def get_plugin_hooks(self, plugin_id: str) -> List[PluginHook]:
        """Get all hooks for a specific plugin."""
        result = []
        for hooks in self._hooks.values():
            for hook in hooks:
                if hook.plugin_id == plugin_id:
                    result.append(hook)
        return result

    def register_handler(self, plugin_id: str, handler_name: str, handler: Callable) -> None:
        """Register a callable handler for a plugin."""
        self._handlers[plugin_id][handler_name] = handler
