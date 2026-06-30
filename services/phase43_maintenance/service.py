"""
Phase 43 — Maintenance Service.

ServiceBase wrapper for the Maintenance subsystem.
Provides versioning, backup, deprecation, and diagnostics management.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Dict, List, Optional

from services.base.service_base import ServiceBase
from .config import MaintenanceConfig
from .models import Version, Backup, DeprecationNotice, DiagnosticReport
from .versioning import VersionManager
from .backups import BackupManager
from .deprecation import DeprecationManager
from .diagnostics import DiagnosticsEngine

logger = logging.getLogger(__name__)


class MaintenanceService(ServiceBase):
    """Maintenance service for versioning, backups, deprecations, and diagnostics.

    Usage:
        svc = MaintenanceService()
        await svc.initialize()
        await svc.create_backup("pre-upgrade", {"key": "value"})
        report = await svc.run_diagnostics()
    """

    def __init__(self, config: Optional[MaintenanceConfig] = None):
        super().__init__(name="jarvis_maintenance", version="1.0.0")
        self.config = config or MaintenanceConfig()
        self.version_manager: Optional[VersionManager] = None
        self.backup_manager: Optional[BackupManager] = None
        self.deprecation_manager: Optional[DeprecationManager] = None
        self.diagnostics_engine: Optional[DiagnosticsEngine] = None
        self._start_time = 0.0

    async def initialize(self) -> bool:
        self._start_time = time.time()
        try:
            self.version_manager = VersionManager(self.config)
            self.backup_manager = BackupManager(self.config)
            self.deprecation_manager = DeprecationManager(self.config)
            self.diagnostics_engine = DiagnosticsEngine(self.config)

            self.deprecation_manager.set_current_version(
                self.version_manager.generate_version_string()
            )

            self._metrics.reset()
            self._initialized = True
            logger.info("MaintenanceService initialized")
            return True
        except Exception as e:
            logger.error("MaintenanceService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        logger.info("MaintenanceService shutting down...")
        self._initialized = False

    # ── Version Management ────────────────────────────────────────

    async def set_version(self, version: Version) -> None:
        if not self.version_manager:
            raise RuntimeError("MaintenanceService not initialized")
        if isinstance(version, str):
            parts = version.split(".")
            major = int(parts[0]) if len(parts) > 0 else 0
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0
            version = Version(major=major, minor=minor, patch=patch)
        self.version_manager.set_version(version)
        self.deprecation_manager.set_current_version(
            self.version_manager.generate_version_string()
        )
        self._metrics.counter("version_set", 1)

    async def get_version(self) -> Version:
        if not self.version_manager:
            raise RuntimeError("MaintenanceService not initialized")
        return self.version_manager.get_version()

    async def bump_major(self, changelog_entry: Optional[str] = None) -> Version:
        if not self.version_manager:
            raise RuntimeError("MaintenanceService not initialized")
        v = self.version_manager.bump_major(changelog_entry)
        self._metrics.counter("version_bump_major", 1)
        return v

    async def bump_minor(self, changelog_entry: Optional[str] = None) -> Version:
        if not self.version_manager:
            raise RuntimeError("MaintenanceService not initialized")
        v = self.version_manager.bump_minor(changelog_entry)
        self._metrics.counter("version_bump_minor", 1)
        return v

    async def bump_patch(self, changelog_entry: Optional[str] = None) -> Version:
        if not self.version_manager:
            raise RuntimeError("MaintenanceService not initialized")
        v = self.version_manager.bump_patch(changelog_entry)
        self._metrics.counter("version_bump_patch", 1)
        return v

    async def compare_versions(self, v1: Version, v2: Version) -> int:
        if not self.version_manager:
            raise RuntimeError("MaintenanceService not initialized")
        return self.version_manager.compare(v1, v2)

    async def get_changelog(self) -> List[str]:
        if not self.version_manager:
            raise RuntimeError("MaintenanceService not initialized")
        return self.version_manager.get_changelog()

    # ── Backup Management ─────────────────────────────────────────

    async def create_backup(
        self,
        name: str,
        data: Any,
        backup_type: str = "full",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Backup:
        if not self.backup_manager:
            raise RuntimeError("MaintenanceService not initialized")
        t0 = time.perf_counter()
        backup = self.backup_manager.create_backup(name, data, backup_type, metadata)
        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.counter("backups_created", 1)
        self._metrics.histogram("backup_create_time_ms", elapsed)
        return backup

    async def restore_backup(self, backup_id: str) -> Any:
        if not self.backup_manager:
            raise RuntimeError("MaintenanceService not initialized")
        t0 = time.perf_counter()
        data = self.backup_manager.restore_backup(backup_id)
        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.counter("backups_restored", 1)
        self._metrics.histogram("backup_restore_time_ms", elapsed)
        return data

    async def list_backups(self) -> List[Backup]:
        if not self.backup_manager:
            raise RuntimeError("MaintenanceService not initialized")
        return self.backup_manager.list_backups()

    async def delete_backup(self, backup_id: str) -> bool:
        if not self.backup_manager:
            raise RuntimeError("MaintenanceService not initialized")
        result = self.backup_manager.delete_backup(backup_id)
        if result:
            self._metrics.counter("backups_deleted", 1)
        return result

    async def prune_backups(self) -> int:
        if not self.backup_manager:
            raise RuntimeError("MaintenanceService not initialized")
        count = self.backup_manager.prune_old_backups()
        self._metrics.counter("backups_pruned", count)
        return count

    async def verify_backup(self, backup_id: str) -> bool:
        if not self.backup_manager:
            raise RuntimeError("MaintenanceService not initialized")
        return self.backup_manager.verify_backup(backup_id)

    # ── Deprecation Management ────────────────────────────────────

    async def deprecate(
        self,
        item_name: str,
        item_type: str = "api",
        alternative: Optional[str] = None,
        removal_version: Optional[str] = None,
        notice: str = "",
    ) -> DeprecationNotice:
        if not self.deprecation_manager:
            raise RuntimeError("MaintenanceService not initialized")
        d = self.deprecation_manager.deprecate(item_name, item_type, alternative, removal_version, notice)
        self._metrics.counter("deprecations_added", 1)
        return d

    async def get_deprecations(self) -> List[DeprecationNotice]:
        if not self.deprecation_manager:
            raise RuntimeError("MaintenanceService not initialized")
        return self.deprecation_manager.get_deprecations()

    async def check_deprecated(self, item_name: str, item_type: str = "api") -> bool:
        if not self.deprecation_manager:
            raise RuntimeError("MaintenanceService not initialized")
        return self.deprecation_manager.check_deprecated(item_name, item_type)

    async def cleanup_deprecations(self) -> int:
        if not self.deprecation_manager:
            raise RuntimeError("MaintenanceService not initialized")
        count = self.deprecation_manager.cleanup_expired()
        self._metrics.counter("deprecations_cleaned", count)
        return count

    # ── Diagnostics ───────────────────────────────────────────────

    async def run_diagnostics(self) -> DiagnosticReport:
        if not self.diagnostics_engine:
            raise RuntimeError("MaintenanceService not initialized")
        t0 = time.perf_counter()
        report = self.diagnostics_engine.run_diagnostics()
        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.counter("diagnostics_run", 1)
        self._metrics.histogram("diagnostics_time_ms", elapsed)
        return report

    async def export_report(self, report: DiagnosticReport, fmt: str = "json") -> str:
        if not self.diagnostics_engine:
            raise RuntimeError("MaintenanceService not initialized")
        return self.diagnostics_engine.export_report(report, fmt)

    # ── Health / Stats ────────────────────────────────────────────

    async def health(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        ver_str = self.version_manager.generate_version_string() if self.version_manager else "unknown"
        backup_count = len(self.backup_manager.list_backups()) if self.backup_manager else 0
        deprecation_count = len(self.deprecation_manager.get_deprecations()) if self.deprecation_manager else 0
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service_name": self.name,
            "version": self.version,
            "app_version": ver_str,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
            "backup_count": backup_count,
            "deprecation_count": deprecation_count,
        }

    async def stats(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        ver_str = self.version_manager.generate_version_string() if self.version_manager else "unknown"
        return {
            "service": self.name,
            "version": self.version,
            "app_version": ver_str,
            "uptime_seconds": round(uptime, 1),
            "metrics": self._metrics.snapshot(),
        }
