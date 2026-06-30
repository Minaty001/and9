"""
Phase 16 — App Launcher.

Handles launching Android applications by name, with support
checks against a known list of supported apps.
"""

import time
import logging
from typing import List, Optional

from .models import AndroidActionResult


class AppLauncher:
    """Launches Android applications by name.

    Checks if an app is in the supported list before simulating a launch.
    In a real deployment, this would dispatch to the Android ActivityManager.
    """

    def __init__(self, supported_apps: List[str]):
        self._supported_apps = [a.lower() for a in supported_apps]
        self._logger = logging.getLogger("app_launcher")

    def launch(self, app_name: str) -> AndroidActionResult:
        """Launch an Android app by name.

        Args:
            app_name: Name of the app to launch.

        Returns:
            AndroidActionResult with launch status.
        """
        start = time.perf_counter()
        app_lower = app_name.lower().strip()

        if app_lower not in self._supported_apps:
            duration_ms = (time.perf_counter() - start) * 1000
            return AndroidActionResult(
                success=False,
                action_type="launch_app",
                target=app_name,
                message=f"App '{app_name}' is not in the supported list",
                duration_ms=duration_ms,
                error=f"Unsupported app: {app_name}",
            )

        # Simulate app launch
        duration_ms = (time.perf_counter() - start) * 1000
        self._logger.info("Launched app: %s", app_name)
        return AndroidActionResult(
            success=True,
            action_type="launch_app",
            target=app_name,
            message=f"App '{app_name}' launched successfully",
            duration_ms=duration_ms,
        )

    def list_supported_apps(self) -> List[str]:
        """Return the list of supported app names.

        Returns:
            List of supported app name strings (original casing).
        """
        return list(self._supported_apps)

    def is_supported(self, app_name: str) -> bool:
        """Check if an app name is in the supported list.

        Args:
            app_name: Name to check.

        Returns:
            True if the app is supported.
        """
        return app_name.lower().strip() in self._supported_apps
