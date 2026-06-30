"""
Phase 42 — Deployment Service.

ServiceBase wrapper for deployment, packaging, health checks, and updates.
"""

from __future__ import annotations

import os
import time
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from services.base.service_base import ServiceBase
from .config import DeploymentConfig
from .models import (
    EnvironmentProfile,
    Package,
    DeploymentState,
    HealthCheckResult,
    UpdateManifest,
)
from .environment import EnvironmentManager
from .packaging import Packaging
from .health_checker import HealthChecker
from .update_manager import UpdateManager

logger = logging.getLogger(__name__)


class DeploymentService(ServiceBase):
    """Deployment service managing environment, packaging, health, and updates.

    Usage:
        svc = DeploymentService()
        await svc.initialize()
        state = await svc.get_state()
        pkg = await svc.deploy("1.0.0", ["/path/to/file"])
        await svc.check_health()
    """

    def __init__(self, config: Optional[DeploymentConfig] = None):
        super().__init__(name="jarvis_deployment", version="1.0.0")
        self.config = config or DeploymentConfig()
        self.env_manager: Optional[EnvironmentManager] = None
        self.packaging: Optional[Packaging] = None
        self.health_checker: Optional[HealthChecker] = None
        self.update_manager: Optional[UpdateManager] = None
        self._start_time = 0.0
        self._state: Optional[DeploymentState] = None
        self._packages: List[Package] = []

    async def initialize(self) -> bool:
        """Initialize the deployment service.

        Detects platform, loads environment profile, creates managers.
        """
        self._start_time = time.time()
        try:
            self.env_manager = EnvironmentManager(self.config)
            self.packaging = Packaging(self.config.package_format)
            self.health_checker = HealthChecker()
            self.update_manager = UpdateManager(
                data_dir=self.env_manager.get_data_dir(),
                max_versions=self.config.rollback_max_versions,
                update_check_url=self.config.update_check_url,
            )

            # Detect platform
            detected_platform = self.env_manager.detect_platform()

            # Create initial state
            self._state = DeploymentState(
                environment=self.config.environment,
                platform=detected_platform,
                current_version=self.version,
                uptime_seconds=0.0,
                last_deployed=datetime.now(timezone.utc),
                healthy=True,
                active_profile=self.config.environment,
            )

            # Register self as a health-checkable service
            self.health_checker.register_service(
                "deployment",
                self._self_health_check,
            )

            # Start periodic checks if enabled
            if self.config.enable_health_checks:
                self.health_checker.start_periodic_checks(
                    interval=self.config.health_check_interval_seconds,
                )

            self._metrics.reset()
            self._initialized = True
            logger.info(
                "DeploymentService initialized (platform=%s, env=%s)",
                detected_platform,
                self.config.environment,
            )
            return True
        except Exception as e:
            logger.error("DeploymentService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        """Shut down the deployment service gracefully."""
        logger.info("DeploymentService shutting down...")
        if self.health_checker:
            self.health_checker.stop_periodic_checks()
        self._initialized = False

    def _self_health_check(self) -> Dict[str, Any]:
        """Internal health check for the deployment service itself."""
        return {
            "service_name": self.name,
            "status": "healthy" if self._initialized else "unhealthy",
            "version": self.version,
            "environment": self.config.environment,
            "platform": self._state.platform if self._state else "unknown",
        }

    # ── Health & Stats ────────────────────────────────────────────

    async def health(self) -> Dict[str, Any]:
        """Return comprehensive health status including all service checks."""
        uptime = time.time() - self._start_time if self._start_time > 0 else 0

        if not self.health_checker:
            return {
                "status": "unhealthy",
                "service_name": self.name,
                "version": self.version,
                "error": "Health checker not initialized",
                "uptime_seconds": round(uptime, 1),
            }

        result = self.health_checker.check_all()
        if self._state:
            self._state.healthy = result.status == "healthy"
            self._state.last_health_check = datetime.now(timezone.utc)
            self._state.uptime_seconds = uptime

        return {
            "status": result.status,
            "service_name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
            "environment": self.config.environment,
            "platform": self._state.platform if self._state else "unknown",
            "service_checks": result.service_checks,
            "details": result.details,
        }

    async def stats(self) -> Dict[str, Any]:
        """Return deployment service statistics."""
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        version_history = []
        if self.update_manager:
            version_history = self.update_manager.get_version_history()

        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            "environment": self.config.environment,
            "platform": self._state.platform if self._state else "unknown",
            "package_count": len(self._packages),
            "version_history_count": len(version_history),
            "active_profile": self._state.active_profile if self._state else None,
            "healthy": self._state.healthy if self._state else False,
            "metrics": self._metrics.snapshot(),
        }

    # ── Deployment Operations ─────────────────────────────────────

    async def deploy(self, version: str, files: List[str]) -> Optional[Package]:
        """Create a package and deploy it.

        Args:
            version: Version string for the deployment.
            files: List of file paths to include.

        Returns:
            The created Package, or None on failure.
        """
        if not self._initialized:
            raise RuntimeError("DeploymentService not initialized")

        if not self.packaging:
            raise RuntimeError("Packaging not initialized")

        pkg = self.packaging.create_package(version, files)
        self._packages.append(pkg)

        # Update state
        if self._state:
            self._state.previous_version = self._state.current_version
            self._state.current_version = version
            self._state.last_deployed = datetime.now(timezone.utc)

        self._metrics.counter("deployments", 1)
        logger.info("Deployed version %s (package=%s, files=%d)", version, pkg.id, len(files))
        return pkg

    async def rollback(self, version: Optional[str] = None) -> bool:
        """Rollback to a previous version.

        Args:
            version: Specific version to rollback to, or None for previous.

        Returns:
            True if rollback succeeded.
        """
        if not self._initialized:
            raise RuntimeError("DeploymentService not initialized")

        if not self.config.enable_rollback:
            logger.warning("Rollback is disabled")
            return False

        if not self.update_manager:
            raise RuntimeError("UpdateManager not initialized")

        success = self.update_manager.rollback(version)
        if success and self._state:
            current = self.update_manager.get_current_version()
            if current:
                self._state.current_version = current
            self._state.last_deployed = datetime.now(timezone.utc)

        if success:
            self._metrics.counter("rollbacks", 1)
        return success

    async def get_state(self) -> DeploymentState:
        """Get the current deployment state."""
        if not self._initialized:
            raise RuntimeError("DeploymentService not initialized")

        if self._state and self._start_time > 0:
            self._state.uptime_seconds = time.time() - self._start_time

        return self._state

    async def check_health(self) -> HealthCheckResult:
        """Run a health check on all registered services.

        Returns:
            A HealthCheckResult with aggregated status.
        """
        if not self.health_checker:
            raise RuntimeError("Health checker not initialized")

        result = self.health_checker.check_all()

        if self._state:
            self._state.healthy = result.status == "healthy"
            self._state.last_health_check = datetime.now(timezone.utc)

        self._metrics.counter("health_checks", 1)
        return result

    # ── Packaging Operations ──────────────────────────────────────

    async def create_package(self, version: str, files: List[str]) -> Package:
        """Create a deployment package."""
        if not self.packaging:
            raise RuntimeError("Packaging not initialized")
        pkg = self.packaging.create_package(version, files)
        self._packages.append(pkg)
        self._metrics.counter("packages_created", 1)
        return pkg

    async def verify_package(self, package: Package) -> bool:
        """Verify a package's integrity."""
        if not self.packaging:
            raise RuntimeError("Packaging not initialized")
        return self.packaging.verify_package(package)

    async def extract_package(self, package: Package, dest_dir: str) -> bool:
        """Extract a package to a destination."""
        if not self.packaging:
            raise RuntimeError("Packaging not initialized")
        return self.packaging.extract_package(package, dest_dir)

    # ── Update Operations ─────────────────────────────────────────

    async def get_available_updates(self) -> Optional[UpdateManifest]:
        """Check for available updates."""
        if not self.update_manager:
            raise RuntimeError("UpdateManager not initialized")
        return self.update_manager.check_for_updates()

    async def apply_update(self, manifest: UpdateManifest) -> bool:
        """Apply an update from a manifest."""
        if not self._initialized:
            raise RuntimeError("DeploymentService not initialized")
        if not self.update_manager:
            raise RuntimeError("UpdateManager not initialized")

        success = self.update_manager.apply_update(manifest)
        if success:
            current = self.update_manager.get_current_version()
            if self._state and current:
                self._state.current_version = current
            self._metrics.counter("updates_applied", 1)
        return success

    async def get_version_history(self) -> List[Dict[str, Any]]:
        """Get deployment version history."""
        if not self.update_manager:
            raise RuntimeError("UpdateManager not initialized")
        return self.update_manager.get_version_history()

    # ── Profile Operations ────────────────────────────────────────

    async def list_profiles(self) -> List[str]:
        """List all available environment profiles."""
        if not self.env_manager:
            raise RuntimeError("EnvironmentManager not initialized")
        return self.env_manager.list_profiles()

    async def get_active_profile(self) -> Optional[str]:
        """Get the active profile name."""
        if self._state:
            return self._state.active_profile
        return None

    async def switch_profile(self, profile_name: str) -> bool:
        """Switch to a different environment profile.

        Args:
            profile_name: Name of the profile to switch to.

        Returns:
            True if the switch succeeded.
        """
        if not self.env_manager:
            raise RuntimeError("EnvironmentManager not initialized")

        profile = self.env_manager.get_profile(profile_name)
        if not profile:
            logger.warning("Profile not found: %s", profile_name)
            return False

        if self._state:
            self._state.active_profile = profile_name
            self._state.environment = profile_name

        self.config.environment = profile_name
        self._metrics.counter("profile_switches", 1)
        logger.info("Switched to profile: %s", profile_name)
        return True
