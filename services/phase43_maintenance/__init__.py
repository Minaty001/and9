"""
Phase 43 — Maintenance
=======================

Manages versioning, backups, deprecation notices, and system diagnostics
to keep JARVIS reliable and maintainable over time.

Components:
    - VersionManager: Tracks version, changelog, compatibility
    - BackupManager: Create/restore/list/delete/prune backups
    - DeprecationManager: Register, query, clean up deprecation notices
    - DiagnosticsEngine: Run system diagnostics, health checks, export reports
    - MaintenanceService: ServiceBase wrapper
"""

from .versioning import VersionManager
from .backups import BackupManager
from .deprecation import DeprecationManager
from .diagnostics import DiagnosticsEngine
from .service import MaintenanceService
from .config import MaintenanceConfig
from .models import Version, Backup, MigrationScript, DeprecationNotice, DiagnosticReport

__all__ = [
    "VersionManager",
    "BackupManager",
    "DeprecationManager",
    "DiagnosticsEngine",
    "MaintenanceService",
    "MaintenanceConfig",
    "Version",
    "Backup",
    "MigrationScript",
    "DeprecationNotice",
    "DiagnosticReport",
]
