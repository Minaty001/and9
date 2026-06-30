"""
Phase 42 — Deployment
======================

Manages environment profiles, packaging, health checks, and update/rollback
for the JARVIS assistant across Android, desktop, and cloud platforms.

Components:
    - EnvironmentManager: Platform detection, profile management
    - Packaging: Package creation, extraction, verification
    - HealthChecker: Service health monitoring with periodic checks
    - UpdateManager: Update checking, application, rollback
    - DeploymentService: ServiceBase wrapper
"""

from .environment import EnvironmentManager, EnvironmentProfile
from .packaging import Packaging, Package
from .health_checker import HealthChecker, HealthCheckResult
from .update_manager import UpdateManager, UpdateManifest
from .service import DeploymentService
from .config import DeploymentConfig
from .models import DeploymentState

__all__ = [
    "EnvironmentManager",
    "EnvironmentProfile",
    "Packaging",
    "Package",
    "HealthChecker",
    "HealthCheckResult",
    "UpdateManager",
    "UpdateManifest",
    "DeploymentService",
    "DeploymentConfig",
    "DeploymentState",
]
