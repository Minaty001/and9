"""
Phase 38 — Profile Manager.

Create, delete, rename, activate configuration profiles.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from .config import ConfigSystemConfig

logger = logging.getLogger(__name__)


class ProfileManager:
    """Manage configuration profiles.

    Usage:
        mgr = ProfileManager()
        mgr.create_profile("production")
        mgr.activate_profile("production")
        mgr.list_profiles()
    """

    def __init__(self, config: Optional[ConfigSystemConfig] = None,
                 store_entries: Optional[Dict[str, Dict]] = None):
        self.config = config or ConfigSystemConfig()
        self._profiles: List[str] = ["default"]
        self._active: str = "default"
        self._store_entries = store_entries or {}

    def create_profile(self, name: str) -> bool:
        """Create a new profile.

        Returns True if created, False if already exists.
        """
        if name in self._profiles:
            return False
        self._profiles.append(name)
        if self._store_entries is not None and name not in self._store_entries:
            self._store_entries[name] = {}
        logger.debug("Created profile: %s", name)
        return True

    def delete_profile(self, name: str) -> bool:
        """Delete a profile.

        Returns True if deleted. Cannot delete the active profile.
        """
        if name == self._active:
            logger.warning("Cannot delete active profile: %s", name)
            return False
        if name not in self._profiles:
            return False
        self._profiles.remove(name)
        if self._store_entries is not None and name in self._store_entries:
            del self._store_entries[name]
        logger.debug("Deleted profile: %s", name)
        return True

    def rename_profile(self, old_name: str, new_name: str) -> bool:
        """Rename a profile.

        Returns True if renamed.
        """
        if old_name not in self._profiles:
            return False
        if new_name in self._profiles:
            logger.warning("Profile already exists: %s", new_name)
            return False

        idx = self._profiles.index(old_name)
        self._profiles[idx] = new_name

        if self._active == old_name:
            self._active = new_name

        if self._store_entries is not None and old_name in self._store_entries:
            self._store_entries[new_name] = self._store_entries.pop(old_name)

        logger.debug("Renamed profile '%s' -> '%s'", old_name, new_name)
        return True

    def activate_profile(self, name: str) -> bool:
        """Activate a profile by name.

        Returns True if activated.
        """
        if name not in self._profiles:
            return False
        self._active = name
        self.config.active_profile = name
        logger.debug("Activated profile: %s", name)
        return True

    def get_active(self) -> str:
        """Get the currently active profile name."""
        return self._active

    def list_profiles(self) -> List[Dict[str, str]]:
        """List all profiles with their status."""
        return [
            {"name": p, "active": p == self._active}
            for p in self._profiles
        ]

    def clone_profile(self, source: str, target: str) -> bool:
        """Clone a profile's entries into a new profile.

        Returns True if cloned.
        """
        if source not in self._profiles:
            return False
        if target in self._profiles:
            logger.warning("Target profile already exists: %s", target)
            return False

        self.create_profile(target)
        if self._store_entries is not None and source in self._store_entries:
            source_entries = self._store_entries[source]
            self._store_entries[target] = {
                k: v.copy() if hasattr(v, 'copy') else v
                for k, v in source_entries.items()
            }

        logger.debug("Cloned profile '%s' -> '%s'", source, target)
        return True
