"""
Phase 38 — Configuration Service.

ServiceBase wrapper for the Configuration System service.
"""

from __future__ import annotations

import time
import json
import logging
from typing import Any, Dict, List, Optional

from services.base.service_base import ServiceBase
from .config import ConfigSystemConfig
from .models import ConfigEntry, ValidationError
from .config_store import ConfigStore
from .profile_manager import ProfileManager
from .validator import ConfigValidator
from .hot_reload import HotReloadManager

logger = logging.getLogger(__name__)


class ConfigService(ServiceBase):
    """Configuration system service.

    Usage:
        svc = ConfigService()
        await svc.initialize()
        svc.set("db.host", "localhost")
        val = svc.get("db.host")
    """

    def __init__(self, config: Optional[ConfigSystemConfig] = None):
        super().__init__(name="jarvis_config", version="1.0.0")
        self.config = config or ConfigSystemConfig()
        self.store: Optional[ConfigStore] = None
        self.profile_manager: Optional[ProfileManager] = None
        self.validator: Optional[ConfigValidator] = None
        self.hot_reload_manager: Optional[HotReloadManager] = None
        self._validation_results: Dict[str, Any] = {}
        self._start_time = 0.0

    async def initialize(self) -> bool:
        self._start_time = time.time()
        try:
            self.store = ConfigStore(self.config)
            self.validator = ConfigValidator()
            self.profile_manager = ProfileManager(
                self.config,
                store_entries=self.store._entries if self.store else None,
            )
            self._metrics.reset()

            # Startup validation: validate every stored config entry against its rules
            self._validation_results = self._validate_all()
            if self._validation_results.get("invalid_count", 0) > 0:
                logger.warning(
                    "Startup validation found %d invalid config entries",
                    self._validation_results["invalid_count"],
                )

            # Hot reload integration (when enabled)
            if self.config.enable_env_watch and self.config.hot_reload_interval_seconds > 0:
                self.hot_reload_manager = HotReloadManager(self.store, self.config)
                self.hot_reload_manager.start_watching(
                    interval_seconds=self.config.hot_reload_interval_seconds,
                    callback=self._on_hot_reload,
                )
                logger.info("Hot reload started (interval=%ds)", self.config.hot_reload_interval_seconds)

            self._initialized = True
            logger.info("ConfigService initialized")
            return True
        except Exception as e:
            logger.error("ConfigService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        logger.info("ConfigService shutting down...")
        if self.hot_reload_manager:
            self.hot_reload_manager.stop_watching()
        self._initialized = False

    # ── Startup Validation ──────────────────────────────────────────────

    def _validate_all(self) -> Dict[str, Any]:
        """Validate every stored config entry against its rules.

        This is best-effort: logs warnings for invalid entries but does not
        block startup. Returns a summary dict with results.
        """
        if not self.store or not self.validator:
            return {"valid": True, "invalid_count": 0, "errors": []}

        all_errors = []
        validated_count = 0
        invalid_count = 0

        for profile, entries in self.store._entries.items():
            for key, entry in entries.items():
                validated_count += 1
                if entry.validation_rules:
                    errors = self.validator.validate(key, entry.value, entry.validation_rules)
                    if errors:
                        invalid_count += 1
                        for err in errors:
                            logger.warning(
                                "Invalid config '%s' in profile '%s': %s",
                                key, profile, err.message,
                            )
                            all_errors.append({
                                "key": key,
                                "profile": profile,
                                "message": err.message,
                            })

        return {
            "valid": invalid_count == 0,
            "validated_count": validated_count,
            "invalid_count": invalid_count,
            "errors": all_errors,
        }

    def _on_hot_reload(self, key: str, old_value: Any, new_value: Any) -> None:
        """Callback invoked when hot reload detects a config change."""
        logger.info("Hot reload applied: %s = %r (was: %r)", key, new_value, old_value)
        self._metrics.counter("hot_reloads", 1)

    # ── Config Operations ──────────────────────────────────────────

    async def set_config(self, key: str, value: Any, profile: Optional[str] = None,
                         description: str = "", is_secret: bool = False,
                         is_immutable: bool = False) -> None:
        """Async alias for setting a config value."""
        if not self.store:
            raise RuntimeError("ConfigService not initialized")
        self.store.set(key, value, profile or "default", description, is_secret, is_immutable)
        self._metrics.counter("config_sets", 1)

    async def get_config(self, key: str, default: Any = None, profile: Optional[str] = None) -> Any:
        """Async alias for getting a config value."""
        if not self.store:
            raise RuntimeError("ConfigService not initialized")
        return self.store.get(key, default, profile or "default")

    async def has_config(self, key: str) -> bool:
        """Async alias for checking if a config key exists."""
        if not self.store:
            raise RuntimeError("ConfigService not initialized")
        return self.store.has(key)

    async def get_all_config(self, profile: Optional[str] = None) -> Dict[str, Any]:
        """Async alias for getting all config values."""
        if not self.store:
            raise RuntimeError("ConfigService not initialized")
        return self.store.get_all(profile or "default")

    async def delete_config(self, key: str, profile: Optional[str] = None) -> bool:
        """Async alias for deleting a config key."""
        if not self.store:
            raise RuntimeError("ConfigService not initialized")
        result = self.store.delete(key, profile or "default")
        if result:
            self._metrics.counter("config_deletes", 1)
        return result

    def get(self, key: str, default: Any = None, profile: Optional[str] = None) -> Any:
        if not self.store:
            raise RuntimeError("ConfigService not initialized")
        return self.store.get(key, default, profile)

    def set(self, key: str, value: Any, profile: Optional[str] = None,
            description: str = "", is_secret: bool = False,
            is_immutable: bool = False) -> None:
        if not self.store:
            raise RuntimeError("ConfigService not initialized")
        self.store.set(key, value, profile, description, is_secret, is_immutable)
        self._metrics.counter("config_sets", 1)

    def delete(self, key: str, profile: Optional[str] = None) -> bool:
        if not self.store:
            raise RuntimeError("ConfigService not initialized")
        result = self.store.delete(key, profile)
        if result:
            self._metrics.counter("config_deletes", 1)
        return result

    def has(self, key: str) -> bool:
        if not self.store:
            raise RuntimeError("ConfigService not initialized")
        return self.store.has(key)

    def get_all(self, profile: Optional[str] = None) -> Dict[str, Any]:
        if not self.store:
            raise RuntimeError("ConfigService not initialized")
        return self.store.get_all(profile)

    def get_by_prefix(self, prefix: str) -> Dict[str, Any]:
        if not self.store:
            raise RuntimeError("ConfigService not initialized")
        return self.store.get_by_prefix(prefix)

    # ── Profile Operations ─────────────────────────────────────────

    async def create_profile(self, name: str) -> bool:
        if not self.profile_manager:
            raise RuntimeError("ConfigService not initialized")
        return self.profile_manager.create_profile(name)

    async def activate_profile(self, name: str) -> bool:
        if not self.profile_manager:
            raise RuntimeError("ConfigService not initialized")
        return self.profile_manager.activate_profile(name)

    async def get_active_profile(self) -> str:
        if not self.profile_manager:
            raise RuntimeError("ConfigService not initialized")
        return self.profile_manager.get_active()

    async def list_profiles(self) -> List[str]:
        if not self.profile_manager:
            raise RuntimeError("ConfigService not initialized")
        return [p["name"] for p in self.profile_manager.list_profiles()]

    def delete_profile(self, name: str) -> bool:
        if not self.profile_manager:
            raise RuntimeError("ConfigService not initialized")
        return self.profile_manager.delete_profile(name)

    def clone_profile(self, source: str, target: str) -> bool:
        if not self.profile_manager:
            raise RuntimeError("ConfigService not initialized")
        return self.profile_manager.clone_profile(source, target)

    # ── Validation ─────────────────────────────────────────────────

    def validate(self, key: str, value: Any, rules: Any) -> List[ValidationError]:
        if not self.validator:
            raise RuntimeError("ConfigService not initialized")
        return self.validator.validate(key, value, rules)

    # ── Export / Import ─────────────────────────────────────────────

    def export_config(self, profile: Optional[str] = None) -> str:
        """Export config as JSON string."""
        if not self.store:
            raise RuntimeError("ConfigService not initialized")
        data = self.store.get_all(profile)
        return json.dumps(data, indent=2, default=str)

    def import_config(self, json_str: str, profile: Optional[str] = None) -> int:
        """Import config from JSON string.

        Returns number of keys imported.
        """
        if not self.store:
            raise RuntimeError("ConfigService not initialized")
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

    # ── Stats ──────────────────────────────────────────────────────

    async def health(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        active_profile = self.profile_manager.get_active() if self.profile_manager else "unknown"
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service_name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
            "active_profile": active_profile,
            "validation": self._validation_results,
            "hot_reload_active": self.hot_reload_manager is not None and self.hot_reload_manager._running if self.hot_reload_manager else False,
        }

    async def stats(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        all_data = self.store.get_all() if self.store else {}
        profiles = self.profile_manager.list_profiles() if self.profile_manager else []
        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            "config_count": len(all_data),
            "profiles": profiles,
            "metrics": self._metrics.snapshot(),
        }
