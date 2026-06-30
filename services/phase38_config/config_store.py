"""
Phase 38 — Config Store.

Key-value config storage with profile support for multiple sources.
"""

from __future__ import annotations

import os
import json
import time
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from .config import ConfigSystemConfig
from .models import ConfigEntry, ConfigSource

logger = logging.getLogger(__name__)


class ConfigStore:
    """Key-value configuration store with profile and source support.

    Usage:
        store = ConfigStore()
        store.set("db.host", "localhost")
        val = store.get("db.host")
    """

    def __init__(self, config: Optional[ConfigSystemConfig] = None):
        self.config = config or ConfigSystemConfig()
        self._entries: Dict[str, Dict[str, ConfigEntry]] = {}  # profile -> {key -> ConfigEntry}
        self._sources: Dict[str, ConfigSource] = {
            "memory": ConfigSource(type="memory", priority=10, is_writable=True),
            "file": ConfigSource(type="file", priority=50, is_writable=True),
            "env": ConfigSource(type="env", priority=100, is_writable=False),
        }
        self._env_cache: Dict[str, str] = {}
        self._load_env()

    def _load_env(self):
        """Load environment variables into cache and apply overrides.

        Supports nested key resolution: DB__HOST -> db.host (double underscore as separator).
        Type coercion from string values: "true"/"false" -> bool, numeric strings -> int/float.
        Each override is logged at startup.
        """
        prefix = "JARVIS_"
        for key, val in os.environ.items():
            self._env_cache[key] = val

            if not key.startswith(prefix):
                continue

            # Convert env key to config key
            config_key = key[len(prefix):].lower()
            # Double underscore -> dot (nested key)
            config_key = config_key.replace("__", ".")

            if not config_key:
                continue

            # Attempt type coercion
            coerced_value = self._coerce_env_value(val)

            # Store in the active profile as env override
            profile = self.config.active_profile
            # Store with source = "env"
            self.set(
                config_key,
                coerced_value,
                profile=profile,
                description="(env override)",
                is_secret=any(secret in key.lower() for secret in ["secret", "token", "key", "password"]),
            )
            logger.info("Env override: %s -> %s = %r (coerced from '%s')", key, config_key, coerced_value, val)

    @staticmethod
    def _coerce_env_value(val: str) -> Any:
        """Coerce an environment variable string to the appropriate Python type.

        Supports bool ("true"/"false"/"1"/"0"), int, float, and fallback to str.
        """
        if val.lower() in ("true", "1", "yes"):
            return True
        if val.lower() in ("false", "0", "no"):
            return False
        try:
            if "." in val and val.count(".") == 1:
                return float(val)
            return int(val)
        except (ValueError, TypeError):
            return val

    def _get_profile_entries(self, profile: str) -> Dict[str, ConfigEntry]:
        """Get or create the entry dict for a profile."""
        if profile not in self._entries:
            self._entries[profile] = {}
        return self._entries[profile]

    def _resolve_sources(self, key: str, profile: str) -> Optional[Any]:
        """Resolve a key by checking sources in priority order."""
        # 1. Check memory profile entries
        entries = self._get_profile_entries(profile)
        if key in entries:
            return entries[key].value

        # 2. Check env (for this profile)
        env_key = f"JARVIS_{profile.upper()}_{key.upper().replace('.', '_')}"
        if env_key in self._env_cache:
            return self._env_cache[env_key]

        # 3. Check env without profile
        env_key = f"JARVIS_{key.upper().replace('.', '_')}"
        if env_key in self._env_cache:
            return self._env_cache[env_key]

        return None

    def get(self, key: str, default: Any = None, profile: Optional[str] = None) -> Any:
        """Get a configuration value.

        Args:
            key: Configuration key.
            default: Default value if not found.
            profile: Profile name (defaults to active profile).

        Returns:
            The configuration value or default.
        """
        profile = profile or self.config.active_profile

        # Check overrides
        if self.config.enable_overrides:
            val = self._resolve_sources(key, profile)
            if val is not None:
                return val

        # Check active profile entries
        entries = self._get_profile_entries(profile)
        entry = entries.get(key)
        if entry:
            return entry.value

        return default

    def set(self, key: str, value: Any, profile: Optional[str] = None, description: str = "",
            is_secret: bool = False, is_immutable: bool = False) -> None:
        """Set a configuration value.

        Args:
            key: Configuration key.
            value: Value to set.
            profile: Profile name (defaults to active profile).
            description: Human-readable description.
            is_secret: Whether this value is secret.
            is_immutable: Whether this value can be changed.
        """
        profile = profile or self.config.active_profile
        entries = self._get_profile_entries(profile)

        # Check immutability
        if key in entries and entries[key].is_immutable:
            logger.warning("Cannot modify immutable key: %s", key)
            return

        value_type = type(value).__name__
        entry = ConfigEntry(
            key=key,
            value=value,
            source="memory",
            profile=profile,
            description=description,
            value_type=value_type,
            is_secret=is_secret,
            is_immutable=is_immutable,
            updated_at=datetime.now(timezone.utc),
        )
        entries[key] = entry
        logger.debug("Set config: %s = %s (profile=%s)", key, value, profile)

    def delete(self, key: str, profile: Optional[str] = None) -> bool:
        """Delete a configuration entry.

        Returns True if deleted.
        """
        profile = profile or self.config.active_profile
        entries = self._get_profile_entries(profile)
        if key in entries:
            if entries[key].is_immutable:
                logger.warning("Cannot delete immutable key: %s", key)
                return False
            del entries[key]
            return True
        return False

    def has(self, key: str) -> bool:
        """Check if a key exists in any profile."""
        for entries in self._entries.values():
            if key in entries:
                return True
        return False

    def get_all(self, profile: Optional[str] = None) -> Dict[str, Any]:
        """Get all config entries for a profile as a flat dict."""
        profile = profile or self.config.active_profile
        entries = self._get_profile_entries(profile)
        return {k: v.value for k, v in entries.items()}

    def get_by_prefix(self, prefix: str) -> Dict[str, Any]:
        """Get all config entries with keys starting with prefix."""
        result = {}
        for entries in self._entries.values():
            for key, entry in entries.items():
                if key.startswith(prefix):
                    result[key] = entry.value
        return result

    def clear(self, profile: Optional[str] = None) -> int:
        """Clear all entries for a profile.

        Returns number of entries cleared.
        """
        profile = profile or self.config.active_profile
        entries = self._get_profile_entries(profile)
        count = len(entries)
        # Only clear non-immutable entries
        keys_to_keep = {k for k, v in entries.items() if v.is_immutable}
        self._entries[profile] = {k: entries[k] for k in keys_to_keep}
        return count - len(keys_to_keep)
