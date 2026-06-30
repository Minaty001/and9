"""
Phase 42 — Update Manager.

Manages application updates: checking for updates, applying updates,
rolling back to previous versions, and maintaining version history.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .models import UpdateManifest, Package

logger = logging.getLogger(__name__)


class VersionRecord:
    """Internal record tracking a deployment version."""

    def __init__(
        self,
        version: str,
        timestamp: Optional[datetime] = None,
        manifest: Optional[UpdateManifest] = None,
        package: Optional[Package] = None,
    ):
        self.version = version
        self.timestamp = timestamp or datetime.now(timezone.utc)
        self.manifest = manifest
        self.package = package


class UpdateManager:
    """Checks for updates, applies them, and manages rollback.

    Usage:
        mgr = UpdateManager(data_dir="/tmp/jarvis_updates")
        manifest = mgr.check_for_updates()
        if manifest:
            mgr.apply_update(manifest)
        mgr.rollback()
    """

    def __init__(
        self,
        data_dir: str = "/tmp/jarvis_updates",
        max_versions: int = 5,
        update_check_url: str = "",
    ):
        self.data_dir = data_dir
        self.max_versions = max_versions
        self.update_check_url = update_check_url
        self._version_history: List[VersionRecord] = []
        self._current_version: Optional[str] = None
        self._initialized = False

    # ── Initialization ────────────────────────────────────────────

    def initialize(self) -> bool:
        """Initialize the update manager, loading persisted state."""
        os.makedirs(self.data_dir, exist_ok=True)
        self._load_history()
        self._initialized = True
        logger.info("UpdateManager initialized in %s", self.data_dir)
        return True

    def _load_history(self) -> None:
        """Load version history from disk."""
        history_file = os.path.join(self.data_dir, "version_history.json")
        if os.path.isfile(history_file):
            try:
                with open(history_file) as f:
                    data = json.load(f)
                for entry in data:
                    record = VersionRecord(
                        version=entry["version"],
                        timestamp=datetime.fromisoformat(entry["timestamp"]),
                    )
                    self._version_history.append(record)
                self._current_version = data[-1]["version"] if data else None
                logger.info("Loaded %d version history entries", len(self._version_history))
            except Exception as e:
                logger.warning("Failed to load version history: %s", e)

    def _save_history(self) -> None:
        """Persist version history to disk."""
        history_file = os.path.join(self.data_dir, "version_history.json")
        try:
            data = [
                {
                    "version": r.version,
                    "timestamp": r.timestamp.isoformat(),
                }
                for r in self._version_history
            ]
            with open(history_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error("Failed to save version history: %s", e)

    # ── Update Checking ───────────────────────────────────────────

    def check_for_updates(self) -> Optional[UpdateManifest]:
        """Check remote for available updates.

        In a real implementation this would query the update server.
        For now, returns None unless a local manifest file exists.

        Returns:
            An UpdateManifest if an update is available, None otherwise.
        """
        manifest_file = os.path.join(self.data_dir, "update_manifest.json")
        if not os.path.isfile(manifest_file):
            return None

        try:
            with open(manifest_file) as f:
                data = json.load(f)
            return UpdateManifest(**data)
        except Exception as e:
            logger.error("Failed to read update manifest: %s", e)
            return None

    def apply_update(self, manifest: UpdateManifest) -> bool:
        """Apply an update from its manifest.

        Args:
            manifest: The UpdateManifest describing the update.

        Returns:
            True if the update was applied successfully.
        """
        if not self._initialized:
            self.initialize()

        # Verify the update before applying
        if not self.verify_update(manifest):
            logger.error("Update verification failed for version %s", manifest.version)
            return False

        # Record current version for rollback
        if self._current_version:
            self._version_history.append(
                VersionRecord(version=self._current_version)
            )

        # Trim history to max_versions
        while len(self._version_history) > self.max_versions:
            self._version_history.pop(0)

        # Apply the update
        self._current_version = manifest.version

        # Persist state
        self._save_history()

        logger.info("Update applied: version %s", manifest.version)
        return True

    def rollback(self, version: Optional[str] = None) -> bool:
        """Rollback to a previous version.

        Args:
            version: Specific version to rollback to, or None for previous.

        Returns:
            True if rollback succeeded.
        """
        if not self._version_history:
            logger.warning("No version history available for rollback")
            return False

        if version:
            # Find specific version in history
            for i, record in enumerate(self._version_history):
                if record.version == version:
                    self._current_version = record.version
                    # Remove this and all later entries
                    self._version_history = self._version_history[:i]
                    self._save_history()
                    logger.info("Rolled back to version %s", version)
                    return True
            logger.warning("Version %s not found in history", version)
            return False
        else:
            # Rollback to previous (last entry)
            last = self._version_history.pop()
            self._current_version = last.version
            self._save_history()
            logger.info("Rolled back to version %s", last.version)
            return True

    def get_version_history(self) -> List[Dict[str, Any]]:
        """Get the version history as a list of dicts.

        Returns:
            List of version history entries with version and timestamp.
        """
        return [
            {
                "version": r.version,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in self._version_history
        ]

    def verify_update(self, manifest: UpdateManifest) -> bool:
        """Verify update integrity before applying.

        Args:
            manifest: The UpdateManifest to verify.

        Returns:
            True if the update passes verification.
        """
        if not manifest.version:
            logger.error("Update manifest missing version")
            return False

        if not manifest.download_url and not manifest.checksum:
            # Local-only update without remote download is acceptable
            pass

        if manifest.required_version and self._current_version:
            # Check required version
            if self._compare_versions(self._current_version, manifest.required_version) < 0:
                logger.error(
                    "Current version %s below required %s",
                    self._current_version,
                    manifest.required_version,
                )
                return False

        return True

    def get_current_version(self) -> Optional[str]:
        """Get the currently deployed version."""
        return self._current_version

    @staticmethod
    def _compare_versions(v1: str, v2: str) -> int:
        """Compare two version strings (semver-like).

        Returns:
            -1 if v1 < v2, 0 if equal, 1 if v1 > v2.
        """
        parts1 = [int(p) for p in v1.split(".") if p.isdigit()]
        parts2 = [int(p) for p in v2.split(".") if p.isdigit()]
        for a, b in zip(parts1, parts2):
            if a < b:
                return -1
            if a > b:
                return 1
        if len(parts1) < len(parts2):
            return -1
        if len(parts1) > len(parts2):
            return 1
        return 0
