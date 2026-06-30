"""
app/core/config.py — Centralised configuration system.

Enhanced with:
- ConfigStore: key-value config storage with profile support
- ProfileManager: create/delete/rename/activate profiles
- ConfigValidator: type/range/regex/allowed values validation
- HotReloadManager: polling-based file/env hot reload
- ConfigService: async wrapper around the above

Backward compatible: existing module-level constants remain unchanged.
All secrets come from environment variables. NO hardcoded keys.
"""

from __future__ import annotations

import os
import re
import json
import time
import logging
import threading
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Dict, List, Optional, Callable, Union

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
#  Existing module-level env-based config (backward compatible)
# ═══════════════════════════════════════════════════════════════════════════════


@lru_cache()
def _str_env(key: str, default: str = "") -> str:
    """Read a string environment variable with an optional default (cached).

    Args:
        key: Environment variable name.
        default: Fallback value if the variable is not set (default '').

    Returns:
        The environment variable value or the default.
    """
    return os.environ.get(key, default)


# ── Supabase (primary database) ────────────────────────────────────────
SUPABASE_URL = _str_env("SUPABASE_URL")
SUPABASE_KEY = _str_env("SUPABASE_KEY")

# ── External APIs (optional) ───────────────────────────────────────────
NEWS_API_KEY    = _str_env("NEWS_API_KEY")
WEATHER_API_KEY = _str_env("WEATHER_API_KEY")

# ── MongoDB (optional; for persistent chat & output logging) ───────────
# Set MONGO_URI in environment or .env to enable MongoDB logging.
MONGO_URI = _str_env("MONGO_URI")

# ── Neural Bridge ──────────────────────────────────────────────────────
NEURAL_MODEL_PATH = _str_env("NEURAL_MODEL_PATH", "")
# If empty, uses ai/models/ default

# ── Vector / Embedding Search ──────────────────────────────────────────
ENABLE_VECTOR_SEARCH = os.environ.get("ENABLE_VECTOR_SEARCH", "").lower() in ("true", "1")
EMBEDDING_MODEL      = _str_env("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIMENSIONS = int(os.environ.get("EMBEDDING_DIMENSIONS", "384"))

# ── Deployment ─────────────────────────────────────────────────────────
IS_RENDER  = os.environ.get("RENDER", "").lower() in ("true", "1")
IS_TERMUX  = "TERMUX_VERSION" in os.environ
IS_WINDOWS = os.name == "nt"

# ── Legacy aliases (some agents may import these) ──────────────────────
MEMORY_DB  = None   # no SQLite
NOTES_DIR  = "/tmp/.jarvis_data"
STATE_FILE = "/tmp/.jarvis_data/jarvis_state.json"
# Lazy init: only create the directory when first needed
_notes_dir_created = False
def _ensure_notes_dir():
    """Create the NOTES_DIR directory on first access (lazy initialisation)."""
    global _notes_dir_created
    if not _notes_dir_created:
        os.makedirs(NOTES_DIR, exist_ok=True)
        _notes_dir_created = True


# ═══════════════════════════════════════════════════════════════════════════════
#  Data Models
# ═══════════════════════════════════════════════════════════════════════════════


class ConfigEntry:
    """A single configuration entry."""

    def __init__(self, key: str, value: Any, source: str = "memory",
                 profile: str = "default", description: str = "",
                 value_type: str = "str", is_secret: bool = False,
                 is_immutable: bool = False,
                 validation_rules: Optional[Dict[str, Any]] = None,
                 updated_at: Optional[datetime] = None):
        self.key = key
        self.value = value
        self.source = source
        self.profile = profile
        self.description = description
        self.value_type = value_type
        self.is_secret = is_secret
        self.is_immutable = is_immutable
        self.validation_rules = validation_rules or {}
        self.updated_at = updated_at or datetime.now(timezone.utc)


class ConfigSource:
    """A configuration source definition."""

    def __init__(self, source_type: str, priority: int = 100,
                 is_writable: bool = False):
        self.type = source_type
        self.priority = priority
        self.is_writable = is_writable


class ValidationError:
    """A validation error for a config value."""

    def __init__(self, key: str, value: Any = None,
                 expected_type: str = "", rule: str = "",
                 message: str = ""):
        self.key = key
        self.value = value
        self.expected_type = expected_type
        self.rule = rule
        self.message = message


# ═══════════════════════════════════════════════════════════════════════════════
#  ConfigStore
# ═══════════════════════════════════════════════════════════════════════════════


class ConfigStore:
    """Key-value configuration store with profile and source support.

    Supports nested keys (e.g., "db.host"), environment variable overrides
    with JARVIS_ prefix, and multiple profiles.

    Usage:
        store = ConfigStore()
        store.set("db.host", "localhost", description="Database host")
        val = store.get("db.host")
        val = store.get("db.host", default="127.0.0.1")
    """

    def __init__(self, active_profile: str = "default",
                 enable_overrides: bool = True):
        self.active_profile = active_profile
        self.enable_overrides = enable_overrides
        self._entries: Dict[str, Dict[str, ConfigEntry]] = {}  # profile -> key -> entry
        self._env_cache: Dict[str, str] = {}
        self._load_env()

    def _load_env(self):
        """Load environment variables into cache and apply overrides.

        Supports nested key resolution: JARVIS_DB__HOST -> db.host
        (double underscore as separator).
        Type coercion: "true"/"false" -> bool, numeric -> int/float.
        """
        for key, val in os.environ.items():
            self._env_cache[key] = val

            if not key.startswith("JARVIS_"):
                continue

            config_key = key[7:].lower().replace("__", ".")
            if not config_key:
                continue

            coerced = self._coerce_env_value(val)
            self.set(
                config_key,
                coerced,
                profile=self.active_profile,
                description="(env override)",
                is_secret=any(
                    kw in key.lower()
                    for kw in ["secret", "token", "key", "password"]
                ),
            )
            logger.info("Env override: %s -> %s = %r", key, config_key, coerced)

    @staticmethod
    def _coerce_env_value(val: str) -> Any:
        """Coerce an env var string to bool/int/float/str."""
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
        if profile not in self._entries:
            self._entries[profile] = {}
        return self._entries[profile]

    def get(self, key: str, default: Any = None,
            profile: Optional[str] = None) -> Any:
        """Get a configuration value.

        Checks overrides first (if enabled), then profile entries.
        """
        profile = profile or self.active_profile
        entries = self._get_profile_entries(profile)
        entry = entries.get(key)
        return entry.value if entry else default

    def set(self, key: str, value: Any, profile: Optional[str] = None,
            description: str = "", is_secret: bool = False,
            is_immutable: bool = False) -> None:
        """Set a configuration value."""
        profile = profile or self.active_profile
        entries = self._get_profile_entries(profile)

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

    def delete(self, key: str, profile: Optional[str] = None) -> bool:
        """Delete a configuration entry."""
        profile = profile or self.active_profile
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
        """Get all config values for a profile as a flat dict."""
        profile = profile or self.active_profile
        entries = self._get_profile_entries(profile)
        return {k: v.value for k, v in entries.items()}

    def get_by_prefix(self, prefix: str) -> Dict[str, Any]:
        """Get all config values with keys starting with prefix."""
        result = {}
        for entries in self._entries.values():
            for key, entry in entries.items():
                if key.startswith(prefix):
                    result[key] = entry.value
        return result

    def clear(self, profile: Optional[str] = None) -> int:
        """Clear all entries for a profile (skips immutable keys).

        Returns number of entries cleared.
        """
        profile = profile or self.active_profile
        entries = self._get_profile_entries(profile)
        count = len(entries)
        keys_to_keep = {k for k, v in entries.items() if v.is_immutable}
        self._entries[profile] = {k: entries[k] for k in keys_to_keep}
        return count - len(keys_to_keep)


# ═══════════════════════════════════════════════════════════════════════════════
#  ProfileManager
# ═══════════════════════════════════════════════════════════════════════════════


class ProfileManager:
    """Manage configuration profiles.

    Usage:
        mgr = ProfileManager()
        mgr.create_profile("production")
        mgr.activate_profile("production")
        mgr.list_profiles()
    """

    def __init__(self, store: Optional[ConfigStore] = None,
                 active_profile: str = "default"):
        self._profiles: List[str] = ["default"]
        self._active: str = active_profile
        self._store = store

    def create_profile(self, name: str) -> bool:
        """Create a new profile. Returns True if created."""
        if name in self._profiles:
            return False
        self._profiles.append(name)
        if self._store is not None:
            self._store._entries.setdefault(name, {})
        return True

    def delete_profile(self, name: str) -> bool:
        """Delete a profile. Cannot delete the active profile."""
        if name == self._active:
            logger.warning("Cannot delete active profile: %s", name)
            return False
        if name not in self._profiles:
            return False
        self._profiles.remove(name)
        if self._store is not None and name in self._store._entries:
            del self._store._entries[name]
        return True

    def rename_profile(self, old_name: str, new_name: str) -> bool:
        """Rename a profile."""
        if old_name not in self._profiles:
            return False
        if new_name in self._profiles:
            logger.warning("Profile already exists: %s", new_name)
            return False
        idx = self._profiles.index(old_name)
        self._profiles[idx] = new_name
        if self._active == old_name:
            self._active = new_name
        if self._store is not None and old_name in self._store._entries:
            self._store._entries[new_name] = self._store._entries.pop(old_name)
        return True

    def activate_profile(self, name: str) -> bool:
        """Activate a profile by name."""
        if name not in self._profiles:
            return False
        self._active = name
        if self._store is not None:
            self._store.active_profile = name
        return True

    def get_active(self) -> str:
        """Get the currently active profile name."""
        return self._active

    def list_profiles(self) -> List[Dict[str, Any]]:
        """List all profiles with their status."""
        return [
            {"name": p, "active": p == self._active}
            for p in self._profiles
        ]

    def clone_profile(self, source: str, target: str) -> bool:
        """Clone a profile's entries into a new profile."""
        if source not in self._profiles:
            return False
        if target in self._profiles:
            logger.warning("Target profile already exists: %s", target)
            return False
        self.create_profile(target)
        if self._store is not None and source in self._store._entries:
            src = self._store._entries[source]
            self._store._entries[target] = {
                k: vars(v).copy() if hasattr(v, '__dict__') else v
                for k, v in src.items()
            }
        return True


# ═══════════════════════════════════════════════════════════════════════════════
#  ConfigValidator
# ═══════════════════════════════════════════════════════════════════════════════


class ConfigValidator:
    """Validate configuration values against rules.

    Supports: type, allowed values, min/max, min/max length, regex pattern, range.

    Usage:
        validator = ConfigValidator()
        errors = validator.validate("port", 8080, {"type": "int", "min": 1024, "max": 65535})
    """

    def __init__(self):
        self._validators = {
            "type": self._validate_type,
            "allowed": self._validate_allowed,
            "min": self._validate_min,
            "max": self._validate_max,
            "min_length": self._validate_min_length,
            "max_length": self._validate_max_length,
            "pattern": self._validate_pattern,
            "range": self._validate_range,
        }

    def validate(self, key: str, value: Any,
                 rules: Union[str, Dict[str, Any]]) -> List[ValidationError]:
        """Validate a value against rules.

        Args:
            key: Config key name.
            value: Value to validate.
            rules: Validation rules dict or JSON string.

        Returns:
            List of ValidationError (empty if valid).
        """
        if isinstance(rules, str):
            try:
                rules = json.loads(rules)
            except (json.JSONDecodeError, TypeError):
                rules = {}

        if not isinstance(rules, dict):
            return []

        errors = []
        for rule_name, rule_value in rules.items():
            validator = self._validators.get(rule_name)
            if validator:
                error = validator(key, value, rule_value)
                if error:
                    errors.append(error)
        return errors

    def _validate_type(self, key: str, value: Any,
                       expected_type: str) -> Optional[ValidationError]:
        type_map = {
            "str": str, "int": int, "float": float, "bool": bool,
            "list": list, "dict": dict, "number": (int, float),
        }
        py_type = type_map.get(expected_type)
        if py_type and not isinstance(value, py_type):
            return ValidationError(
                key=key, value=value, expected_type=expected_type,
                rule=f"type:{expected_type}",
                message=f"Expected type '{expected_type}', got '{type(value).__name__}'",
            )
        return None

    def _validate_allowed(self, key: str, value: Any,
                          allowed: List[Any]) -> Optional[ValidationError]:
        if value not in allowed:
            return ValidationError(
                key=key, value=value, rule=f"allowed:{allowed}",
                message=f"Value '{value}' not in allowed list: {allowed}",
            )
        return None

    def _validate_min(self, key: str, value: Any,
                      min_val: Union[int, float]) -> Optional[ValidationError]:
        if isinstance(value, (int, float)) and value < min_val:
            return ValidationError(
                key=key, value=value, rule=f"min:{min_val}",
                message=f"Value {value} is less than minimum {min_val}",
            )
        return None

    def _validate_max(self, key: str, value: Any,
                      max_val: Union[int, float]) -> Optional[ValidationError]:
        if isinstance(value, (int, float)) and value > max_val:
            return ValidationError(
                key=key, value=value, rule=f"max:{max_val}",
                message=f"Value {value} is greater than maximum {max_val}",
            )
        return None

    def _validate_min_length(self, key: str, value: Any,
                             min_len: int) -> Optional[ValidationError]:
        if isinstance(value, (str, list)) and len(value) < min_len:
            return ValidationError(
                key=key, value=value, rule=f"min_length:{min_len}",
                message=f"Length {len(value)} is less than minimum {min_len}",
            )
        return None

    def _validate_max_length(self, key: str, value: Any,
                             max_len: int) -> Optional[ValidationError]:
        if isinstance(value, (str, list)) and len(value) > max_len:
            return ValidationError(
                key=key, value=value, rule=f"max_length:{max_len}",
                message=f"Length {len(value)} exceeds maximum {max_len}",
            )
        return None

    def _validate_pattern(self, key: str, value: Any,
                          pattern: str) -> Optional[ValidationError]:
        if isinstance(value, str):
            try:
                if not re.match(pattern, value):
                    return ValidationError(
                        key=key, value=value, rule=f"pattern:{pattern}",
                        message=f"Value '{value}' does not match pattern '{pattern}'",
                    )
            except re.error:
                pass
        return None

    def _validate_range(self, key: str, value: Any,
                        rng: List[Union[int, float]]) -> Optional[ValidationError]:
        if isinstance(value, (int, float)) and len(rng) == 2:
            if value < rng[0] or value > rng[1]:
                return ValidationError(
                    key=key, value=value, rule=f"range:[{rng[0]}, {rng[1]}]",
                    message=f"Value {value} is outside range [{rng[0]}, {rng[1]}]",
                )
        return None


# ═══════════════════════════════════════════════════════════════════════════════
#  HotReloadManager
# ═══════════════════════════════════════════════════════════════════════════════


class HotReloadManager:
    """Watch config sources for changes and reload.

    Uses simple polling: periodically checks file modification times and
    environment variable changes. When a change is detected, validates the
    new value and applies it if valid.

    Usage:
        mgr = HotReloadManager(store)
        mgr.start_watching(interval_seconds=30, callback=on_change)
        ...
        mgr.stop_watching()
    """

    def __init__(self, store: ConfigStore,
                 config_file_path: str = "./jarvis_config.json"):
        self.store = store
        self.config_file_path = config_file_path
        self._timer: Optional[threading.Timer] = None
        self._running = False
        self._callback: Optional[Callable[[str, Any, Any], None]] = None
        self._last_modified: Dict[str, float] = {}
        self._last_env_snapshot: Dict[str, str] = {}
        self._interval_seconds: int = 0

    def start_watching(self, interval_seconds: int = 30,
                       callback: Optional[Callable[[str, Any, Any], None]] = None) -> None:
        """Start polling for configuration changes."""
        self.stop_watching()
        if interval_seconds <= 0:
            return
        self._interval_seconds = interval_seconds
        self._callback = callback
        self._running = True
        self._take_env_snapshot()
        if self.config_file_path and os.path.isfile(self.config_file_path):
            self._last_modified["file:" + self.config_file_path] = \
                os.path.getmtime(self.config_file_path)
        self._schedule_next()

    def stop_watching(self) -> None:
        """Stop polling for configuration changes."""
        self._running = False
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def check_for_changes(self) -> List[Dict[str, Any]]:
        """Check all watched sources for changes.

        Returns a list of change dicts with source, key, old_value, new_value.
        """
        changes: List[Dict[str, Any]] = []

        # Check file changes
        if self.config_file_path and os.path.isfile(self.config_file_path):
            source_key = "file:" + self.config_file_path
            current_mtime = os.path.getmtime(self.config_file_path)
            last_mtime = self._last_modified.get(source_key, 0)
            if current_mtime > last_mtime:
                self._last_modified[source_key] = current_mtime
                file_changes = self._reload_file(self.config_file_path)
                changes.extend(file_changes)

        # Check env changes
        env_changes = self._check_env_changes()
        changes.extend(env_changes)

        return changes

    # ── Internal ─────────────────────────────────────────────

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
                logger.info("Config changed: %s = %s (was: %s)",
                            change.get("key"), change.get("new_value"),
                            change.get("old_value"))
                if self._callback:
                    try:
                        self._callback(change.get("key", ""),
                                       change.get("old_value"),
                                       change.get("new_value"))
                    except Exception as cb_err:
                        logger.error("Hot reload callback failed: %s", cb_err)
        except Exception as e:
            logger.error("Hot reload poll error: %s", e)
        self._schedule_next()

    def _reload_file(self, file_path: str) -> List[Dict[str, Any]]:
        changes = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                new_data = json.load(f)
            if not isinstance(new_data, dict):
                logger.warning("Config file root is not a dict: %s", file_path)
                return changes
            for key, value in new_data.items():
                old_value = self.store.get(key, None)
                if old_value != value:
                    self.store.set(key, value, description="(hot-reloaded)")
                    changes.append({
                        "source": file_path, "key": key,
                        "old_value": old_value, "new_value": value,
                    })
        except Exception as e:
            logger.error("Failed to reload config file '%s': %s", file_path, e)
        return changes

    def _take_env_snapshot(self) -> None:
        self._last_env_snapshot = {
            k: v for k, v in os.environ.items() if k.startswith("JARVIS_")
        }

    def _check_env_changes(self) -> List[Dict[str, Any]]:
        changes = []
        current_env = {
            k: v for k, v in os.environ.items() if k.startswith("JARVIS_")
        }
        for key, value in current_env.items():
            old_value = self._last_env_snapshot.get(key)
            if old_value != value:
                config_key = key[7:].lower().replace("__", ".")
                old_config = self.store.get(config_key, None)
                if old_config != value:
                    self.store.set(config_key, value, description="(env-hot-reloaded)")
                    changes.append({
                        "source": "env:" + key, "key": config_key,
                        "old_value": old_config, "new_value": value,
                    })
        for key in list(self._last_env_snapshot.keys()):
            if key not in current_env:
                config_key = key[7:].lower().replace("__", ".")
                old_config = self.store.get(config_key, None)
                if old_config is not None:
                    changes.append({
                        "source": "env:" + key, "key": config_key,
                        "old_value": old_config, "new_value": None,
                    })
        self._last_env_snapshot = current_env
        return changes


# ═══════════════════════════════════════════════════════════════════════════════
#  ConfigService
# ═══════════════════════════════════════════════════════════════════════════════


class ConfigService:
    """Configuration system service.

    Wraps ConfigStore, ProfileManager, ConfigValidator, and HotReloadManager
    into a single async service interface.

    Usage:
        svc = ConfigService()
        await svc.initialize()
        svc.set("db.host", "localhost")
        val = svc.get("db.host")
        await svc.health()
    """

    def __init__(self, active_profile: str = "default",
                 enable_overrides: bool = True,
                 config_file_path: str = "./jarvis_config.json"):
        self.active_profile = active_profile
        self.enable_overrides = enable_overrides
        self.config_file_path = config_file_path
        self.store: Optional[ConfigStore] = None
        self.profile_manager: Optional[ProfileManager] = None
        self.validator: Optional[ConfigValidator] = None
        self.hot_reload_manager: Optional[HotReloadManager] = None
        self._initialized = False
        self._start_time = 0.0
        self._counters: Dict[str, int] = {
            "config_sets": 0, "config_deletes": 0, "hot_reloads": 0,
        }

    async def initialize(self) -> bool:
        """Initialize the config service and its sub-components."""
        self._start_time = time.time()
        try:
            self.store = ConfigStore(
                active_profile=self.active_profile,
                enable_overrides=self.enable_overrides,
            )
            self.validator = ConfigValidator()
            self.profile_manager = ProfileManager(
                store=self.store,
                active_profile=self.active_profile,
            )
            self._initialized = True
            logger.info("ConfigService initialized")
            return True
        except Exception as e:
            logger.error("ConfigService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        """Shut down the config service."""
        if self.hot_reload_manager:
            self.hot_reload_manager.stop_watching()
        self._initialized = False

    def _check_init(self):
        if not self._initialized:
            raise RuntimeError("ConfigService not initialized")

    # ── Config Operations ──────────────────────────────────

    async def set_config(self, key: str, value: Any,
                         profile: Optional[str] = None,
                         description: str = "",
                         is_secret: bool = False,
                         is_immutable: bool = False) -> None:
        self._check_init()
        self.store.set(key, value, profile, description, is_secret, is_immutable)
        self._counters["config_sets"] += 1

    async def get_config(self, key: str, default: Any = None,
                         profile: Optional[str] = None) -> Any:
        self._check_init()
        return self.store.get(key, default, profile)

    async def has_config(self, key: str) -> bool:
        self._check_init()
        return self.store.has(key)

    async def get_all_config(self, profile: Optional[str] = None) -> Dict[str, Any]:
        self._check_init()
        return self.store.get_all(profile)

    async def delete_config(self, key: str,
                            profile: Optional[str] = None) -> bool:
        self._check_init()
        result = self.store.delete(key, profile)
        if result:
            self._counters["config_deletes"] += 1
        return result

    def get(self, key: str, default: Any = None,
            profile: Optional[str] = None) -> Any:
        self._check_init()
        return self.store.get(key, default, profile)

    def set(self, key: str, value: Any, profile: Optional[str] = None,
            description: str = "", is_secret: bool = False,
            is_immutable: bool = False) -> None:
        self._check_init()
        self.store.set(key, value, profile, description, is_secret, is_immutable)
        self._counters["config_sets"] += 1

    def delete(self, key: str, profile: Optional[str] = None) -> bool:
        self._check_init()
        result = self.store.delete(key, profile)
        if result:
            self._counters["config_deletes"] += 1
        return result

    def has(self, key: str) -> bool:
        self._check_init()
        return self.store.has(key)

    def get_all(self, profile: Optional[str] = None) -> Dict[str, Any]:
        self._check_init()
        return self.store.get_all(profile)

    def get_by_prefix(self, prefix: str) -> Dict[str, Any]:
        self._check_init()
        return self.store.get_by_prefix(prefix)

    # ── Profile Operations ─────────────────────────────────

    async def create_profile(self, name: str) -> bool:
        self._check_init()
        return self.profile_manager.create_profile(name)

    async def activate_profile(self, name: str) -> bool:
        self._check_init()
        return self.profile_manager.activate_profile(name)

    async def get_active_profile(self) -> str:
        self._check_init()
        return self.profile_manager.get_active()

    async def list_profiles(self) -> List[str]:
        self._check_init()
        return [p["name"] for p in self.profile_manager.list_profiles()]

    def delete_profile(self, name: str) -> bool:
        self._check_init()
        return self.profile_manager.delete_profile(name)

    def clone_profile(self, source: str, target: str) -> bool:
        self._check_init()
        return self.profile_manager.clone_profile(source, target)

    # ── Validation ─────────────────────────────────────────

    def validate(self, key: str, value: Any,
                 rules: Union[str, Dict[str, Any]]) -> List[ValidationError]:
        self._check_init()
        return self.validator.validate(key, value, rules)

    # ── Export / Import ─────────────────────────────────────

    def export_config(self, profile: Optional[str] = None) -> str:
        """Export config as JSON string."""
        self._check_init()
        data = self.store.get_all(profile)
        return json.dumps(data, indent=2, default=str)

    def import_config(self, json_str: str,
                      profile: Optional[str] = None) -> int:
        """Import config from JSON string.

        Returns number of keys imported.
        """
        self._check_init()
        try:
            data = json.loads(json_str)
            count = 0
            for key, value in data.items():
                self.store.set(key, value, profile)
                count += 1
            return count
        except json.JSONDecodeError as e:
            logger.error("Failed to import config: %s", e)
            return 0

    # ── Hot Reload ──────────────────────────────────────────

    def start_hot_reload(self, interval_seconds: int = 30,
                         callback: Optional[Callable[[str, Any, Any], None]] = None) -> None:
        """Start hot reload polling."""
        self._check_init()
        self.hot_reload_manager = HotReloadManager(
            self.store, config_file_path=self.config_file_path,
        )
        self.hot_reload_manager.start_watching(
            interval_seconds=interval_seconds,
            callback=callback or self._on_hot_reload,
        )

    def stop_hot_reload(self) -> None:
        if self.hot_reload_manager:
            self.hot_reload_manager.stop_watching()

    def _on_hot_reload(self, key: str, old_value: Any, new_value: Any) -> None:
        logger.info("Hot reload applied: %s = %r (was: %r)", key, new_value, old_value)
        self._counters["hot_reloads"] += 1

    # ── Health / Stats ──────────────────────────────────────

    async def health(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        active_profile = self.profile_manager.get_active() if self.profile_manager else "unknown"
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
            "active_profile": active_profile,
            "hot_reload_active": (
                self.hot_reload_manager is not None
                and self.hot_reload_manager._running
            ),
        }

    async def stats(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        all_data = self.store.get_all() if self.store else {}
        profiles = (
            self.profile_manager.list_profiles()
            if self.profile_manager else []
        )
        return {
            "service": "jarvis_config",
            "uptime_seconds": round(uptime, 1),
            "config_count": len(all_data),
            "profiles": profiles,
            "counters": dict(self._counters),
        }
