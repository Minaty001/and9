"""
Phase 42 — Environment Manager.

Handles platform detection, environment profiles, and data directory resolution.
"""

from __future__ import annotations

import os
import platform
import logging
from typing import Any, Dict, List, Optional

from .config import DeploymentConfig
from .models import EnvironmentProfile

logger = logging.getLogger(__name__)

# Built-in profiles
BUILTIN_PROFILES: Dict[str, Dict[str, Any]] = {
    "development": {
        "name": "development",
        "platform": "desktop",
        "data_dir": "~/.jarvis",
        "config_overrides": {
            "log_level": "DEBUG",
            "debug_enabled": True,
            "mock_services": True,
        },
        "startup_services": ["core", "api", "cognition"],
        "enabled_features": ["debug", "verbose_logging", "mock_external_apis"],
        "resource_limits": {"cpu_percent": 50, "memory_mb": 512},
    },
    "staging": {
        "name": "staging",
        "platform": "cloud",
        "data_dir": "/var/lib/jarvis",
        "config_overrides": {
            "log_level": "INFO",
            "debug_enabled": False,
            "mock_services": False,
        },
        "startup_services": ["core", "api", "cognition", "database"],
        "enabled_features": ["external_apis_test_mode", "telemetry"],
        "resource_limits": {"cpu_percent": 75, "memory_mb": 1024},
    },
    "production": {
        "name": "production",
        "platform": "cloud",
        "data_dir": "/var/lib/jarvis",
        "config_overrides": {
            "log_level": "WARNING",
            "debug_enabled": False,
            "mock_services": False,
        },
        "startup_services": ["core", "api", "cognition", "database", "memory", "integrations"],
        "enabled_features": ["all_features", "telemetry", "error_reporting", "auto_scaling"],
        "resource_limits": {"cpu_percent": 90, "memory_mb": 2048, "disk_gb": 10},
    },
}


class EnvironmentManager:
    """Manages environment profiles, platform detection, and data directories.

    Usage:
        mgr = EnvironmentManager(config)
        profile = mgr.get_profile("development")
        platform = mgr.detect_platform()
        data_dir = mgr.get_data_dir()
    """

    def __init__(self, config: Optional[DeploymentConfig] = None):
        self.config = config or DeploymentConfig()
        self._profiles: Dict[str, EnvironmentProfile] = {}
        self._load_builtin_profiles()

    def _load_builtin_profiles(self) -> None:
        """Load built-in environment profiles."""
        for name, data in BUILTIN_PROFILES.items():
            self._profiles[name] = EnvironmentProfile(**data)

    def get_profile(self, name: str) -> Optional[EnvironmentProfile]:
        """Get an environment profile by name.

        Args:
            name: Profile name (development/staging/production or custom).

        Returns:
            The EnvironmentProfile or None if not found.
        """
        return self._profiles.get(name)

    def list_profiles(self) -> List[str]:
        """List all available profile names."""
        return list(self._profiles.keys())

    def add_profile(self, profile: EnvironmentProfile) -> None:
        """Register a custom profile."""
        self._profiles[profile.name] = profile

    def detect_platform(self) -> str:
        """Auto-detect the current platform.

        Returns:
            One of: "android", "desktop", "cloud"
        """
        # Android detection via Termux environment
        if os.environ.get("ANDROID_ROOT") or os.environ.get("TERMUX_VERSION"):
            return "android"

        # Cloud detection via environment variables
        cloud_vars = [
            "KUBERNETES_SERVICE_HOST",
            "CLOUD_RUN",
            "AWS_EXECUTION_ENV",
            "FLY_APP_NAME",
            "RENDER_INSTANCE_ID",
        ]
        if any(os.environ.get(v) for v in cloud_vars):
            return "cloud"

        # Desktop fallback
        return "desktop"

    def get_data_dir(self) -> str:
        """Return the appropriate data directory for the current platform.

        Returns:
            Expanded data directory path.
        """
        plat = self.detect_platform()
        if plat == "android":
            return self.config.termux_data_dir
        elif plat == "cloud":
            return "/var/lib/jarvis"
        else:
            # Desktop — expand ~
            return os.path.expanduser(self.config.desktop_data_dir)

    def resolve_data_dir(self, profile_name: Optional[str] = None) -> str:
        """Resolve data directory from a profile, falling back to platform default.

        Args:
            profile_name: Optional profile name to use.

        Returns:
            Resolved data directory path.
        """
        if profile_name:
            profile = self.get_profile(profile_name)
            if profile:
                return os.path.expanduser(profile.data_dir)
        return self.get_data_dir()
