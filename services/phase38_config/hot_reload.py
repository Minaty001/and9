"""
Phase 38 — Hot Reload Manager.

Polling-based configuration hot reload. Watches config sources (files, env)
for changes and triggers a reload callback when changes are detected.
"""

from __future__ import annotations

import os
import time
import logging
import threading
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from .config import ConfigSystemConfig
from .config_store import ConfigStore

logger = logging.getLogger(__name__)


class HotReloadManager:
    """Watch config sources for changes and reload.

    Uses simple polling: periodically checks file modification times and
    environment variable timestamps. When a change is detected, re-reads
    the source, validates new values, and applies them if valid.

    Usage:
        mgr = HotReloadManager(store)
        mgr.start_watching(interval_seconds=30, callback=on_change)
        ...
        mgr.stop_watching()
    """

    def __init__(self, store: ConfigStore, config: Optional[ConfigSystemConfig] = None):
        self.store = store
        self.config = config or ConfigSystemConfig()
        self._timer: Optional[threading.Timer] = None
        self._running = False
        self._callback: Optional[Callable[[str, Any, Any], None]] = None
        # Track last modification times per source
        self._last_modified: Dict[str, float] = {}
        self._last_env_snapshot: Dict[str, str] = {}
        self._interval_seconds: int = 0

    # ── Lifecycle ───────────────────────────────────────────────────────

    def start_watching(self, interval_seconds: int = 30,
                       callback: Optional[Callable[[str, Any, Any], None]] = None) -> None:
        """Start polling for configuration changes.

        Args:
            interval_seconds: Polling interval in seconds.
            callback: Optional callback invoked on each reload with
                      (source_key, old_value, new_value).
        """
        self.stop_watching()

        if interval_seconds <= 0:
            logger.info("Hot reload disabled (interval <= 0)")
            return

        self._interval_seconds = interval_seconds
        self._callback = callback
        self._running = True
        self._take_env_snapshot()

        # Record initial file modification times
        if self.config.config_file_path and os.path.isfile(self.config.config_file_path):
            self._last_modified["file:" + self.config.config_file_path] = \
                os.path.getmtime(self.config.config_file_path)

        self._schedule_next()
        logger.info("Hot reload started (interval=%ds)", interval_seconds)

    def stop_watching(self) -> None:
        """Stop polling for configuration changes."""
        self._running = False
        if self._timer:
            self._timer.cancel()
            self._timer = None

    # ── Polling ─────────────────────────────────────────────────────────

    def check_for_changes(self) -> List[Dict[str, Any]]:
        """Check all watched sources for changes.

        Returns:
            A list of change dicts: [{"source": ..., "key": ..., "old_value": ..., "new_value": ...}]
        """
        changes: List[Dict[str, Any]] = []

        # 1. Check file changes
        if self.config.config_file_path and os.path.isfile(self.config.config_file_path):
            source_key = "file:" + self.config.config_file_path
            current_mtime = os.path.getmtime(self.config.config_file_path)
            last_mtime = self._last_modified.get(source_key, 0)
            if current_mtime > last_mtime:
                self._last_modified[source_key] = current_mtime
                file_changes = self._reload_file(self.config.config_file_path)
                changes.extend(file_changes)

        # 2. Check env changes
        env_changes = self._check_env_changes()
        changes.extend(env_changes)

        return changes

    # ── Internal ────────────────────────────────────────────────────────

    def _schedule_next(self) -> None:
        if not self._running:
            return

        self._timer = threading.Timer(self._interval_seconds, self._poll)
        self._timer.daemon = True
        self._timer.start()

    def _poll(self) -> None:
        if not self._running:
            return
        try:
            changes = self.check_for_changes()
            for change in changes:
                logger.info(
                    "Config changed: %s = %s (was: %s)",
                    change.get("key"),
                    change.get("new_value"),
                    change.get("old_value"),
                )
                if self._callback:
                    try:
                        self._callback(
                            change.get("key", ""),
                            change.get("old_value"),
                            change.get("new_value"),
                        )
                    except Exception as cb_err:
                        logger.error("Hot reload callback failed: %s", cb_err)
        except Exception as e:
            logger.error("Hot reload poll error: %s", e)

        self._schedule_next()

    def _reload_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Re-read a config file and apply changes.

        Returns a list of change dicts.
        """
        changes: List[Dict[str, Any]] = []
        try:
            import json
            with open(file_path, "r", encoding="utf-8") as f:
                new_data = json.load(f)

            if not isinstance(new_data, dict):
                logger.warning("Config file root is not a dict: %s", file_path)
                return changes

            for key, value in new_data.items():
                old_value = self.store.get(key, None)
                if old_value != value:
                    # Validate the new value before applying
                    from .validator import ConfigValidator
                    validator = ConfigValidator()
                    rules = {"type": type(value).__name__}
                    errors = validator.validate(key, value, rules)
                    if errors:
                        logger.warning(
                            "Hot reload validation failed for '%s': %s",
                            key, errors[0].message,
                        )
                        continue
                    self.store.set(key, value, description="(hot-reloaded)")
                    changes.append({
                        "source": file_path,
                        "key": key,
                        "old_value": old_value,
                        "new_value": value,
                    })
        except Exception as e:
            logger.error("Failed to reload config file '%s': %s", file_path, e)

        return changes

    def _take_env_snapshot(self) -> None:
        """Take a snapshot of current environment variables matching JARVIS_ prefix."""
        self._last_env_snapshot = {
            k: v for k, v in os.environ.items() if k.startswith("JARVIS_")
        }

    def _check_env_changes(self) -> List[Dict[str, Any]]:
        """Check if env vars have changed since last snapshot.

        Returns a list of change dicts.
        """
        changes: List[Dict[str, Any]] = []
        current_env = {k: v for k, v in os.environ.items() if k.startswith("JARVIS_")}

        # Check for new or changed keys
        for key, value in current_env.items():
            old_value = self._last_env_snapshot.get(key)
            if old_value != value:
                config_key = self._env_to_config_key(key)
                old_config = self.store.get(config_key, None)
                if old_config != value:
                    self.store.set(config_key, value, description="(env-hot-reloaded)")
                    changes.append({
                        "source": "env:" + key,
                        "key": config_key,
                        "old_value": old_config,
                        "new_value": value,
                    })

        # Check for removed keys
        for key in list(self._last_env_snapshot.keys()):
            if key not in current_env:
                config_key = self._env_to_config_key(key)
                old_config = self.store.get(config_key, None)
                if old_config is not None:
                    changes.append({
                        "source": "env:" + key,
                        "key": config_key,
                        "old_value": old_config,
                        "new_value": None,
                    })

        self._last_env_snapshot = current_env
        return changes

    @staticmethod
    def _env_to_config_key(env_key: str) -> str:
        """Convert an env var name to a config key.

        E.g., JARVIS_DB_HOST -> db.host
        """
        # Strip JARVIS_ prefix
        key = env_key
        if key.startswith("JARVIS_"):
            key = key[7:]
        # Double underscore becomes dot separator for nested keys
        key = key.replace("__", ".")
        # Single underscore remains as-is
        return key.lower()
