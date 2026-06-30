"""
Phase 43 — Version Manager.

Tracks software version, changelog, and compatibility information.
Supports bumping major/minor/patch and comparing versions.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from .models import Version
from .config import MaintenanceConfig

logger = logging.getLogger(__name__)


class VersionManager:
    """Manages application versioning and changelog.

    Usage:
        vm = VersionManager()
        vm.set_version(Version(major=1, minor=2, patch=3))
        vm.bump_minor()
        vm.get_version().major == 1
        vm.get_version().minor == 3
    """

    def __init__(self, config: Optional[MaintenanceConfig] = None):
        self.config = config or MaintenanceConfig()
        self._version = Version(
            major=1,
            minor=0,
            patch=0,
            changelog=["Initial version"],
        )
        self._changelog: List[str] = list(self._version.changelog)

    def set_version(self, version: Version) -> None:
        """Set the current version."""
        self._version = version
        self._changelog = list(version.changelog)
        logger.info("Version set to %s", self.generate_version_string())

    def get_version(self) -> Version:
        """Get the current version."""
        return self._version

    def bump_major(self, changelog_entry: Optional[str] = None) -> Version:
        """Bump major version (e.g., 1.2.3 -> 2.0.0)."""
        self._version.major += 1
        self._version.minor = 0
        self._version.patch = 0
        entry = changelog_entry or f"Major version bump to v{self.generate_version_string()}"
        self._add_changelog(entry)
        logger.info("Bumped major to %s", self.generate_version_string())
        return self._version

    def bump_minor(self, changelog_entry: Optional[str] = None) -> Version:
        """Bump minor version (e.g., 1.2.3 -> 1.3.0)."""
        self._version.minor += 1
        self._version.patch = 0
        entry = changelog_entry or f"Minor version bump to v{self.generate_version_string()}"
        self._add_changelog(entry)
        logger.info("Bumped minor to %s", self.generate_version_string())
        return self._version

    def bump_patch(self, changelog_entry: Optional[str] = None) -> Version:
        """Bump patch version (e.g., 1.2.3 -> 1.2.4)."""
        self._version.patch += 1
        entry = changelog_entry or f"Patch version bump to v{self.generate_version_string()}"
        self._add_changelog(entry)
        logger.info("Bumped patch to %s", self.generate_version_string())
        return self._version

    def compare(self, v1: Version, v2: Version) -> int:
        """Compare two versions. Returns -1 if v1 < v2, 0 if equal, 1 if v1 > v2."""
        for attr in ("major", "minor", "patch"):
            diff = getattr(v1, attr) - getattr(v2, attr)
            if diff < 0:
                return -1
            if diff > 0:
                return 1
        return 0

    def is_compatible(self, version: Version, api_version: str) -> bool:
        """Check if a version is compatible with a given API version.

        Compatibility is determined by matching the major version against
        the compatibility map stored in the version object.
        """
        if version.api_version:
            return version.api_version == api_version
        # Fallback: check compatibility dict
        for comp_key, comp_val in version.compatibility.items():
            if comp_key == "api" or comp_key.endswith("_api"):
                if comp_val == api_version:
                    return True
        # Default: major version match
        return api_version.startswith(str(version.major))

    def get_changelog(self) -> List[str]:
        """Get all changelog entries."""
        return list(self._changelog)

    def generate_version_string(self) -> str:
        """Format as MAJOR.MINOR.PATCH.

        Returns:
            Version string like "1.2.3".
        """
        return f"{self._version.major}.{self._version.minor}.{self._version.patch}"

    # ── Internal ──────────────────────────────────────────────────

    def _add_changelog(self, entry: str) -> None:
        self._changelog.append(entry)
        self._version.changelog = list(self._changelog)
