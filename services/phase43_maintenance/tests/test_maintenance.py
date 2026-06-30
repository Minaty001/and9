"""
Tests for Phase 43 — Maintenance.
"""

import pytest
from services.phase43_maintenance import (
    VersionManager,
    BackupManager,
    DeprecationManager,
    DiagnosticsEngine,
    MaintenanceService,
    MaintenanceConfig,
    Version,
    Backup,
    DeprecationNotice,
    DiagnosticReport,
)


class TestVersionManager:
    """Verify version management, bumps, comparison, and changelog."""

    def test_initial_version(self):
        vm = VersionManager()
        v = vm.get_version()
        assert v.major == 1
        assert v.minor == 0
        assert v.patch == 0

    def test_set_version(self):
        vm = VersionManager()
        v = Version(major=2, minor=3, patch=4, changelog=["Release v2.3.4"])
        vm.set_version(v)
        assert vm.generate_version_string() == "2.3.4"

    def test_bump_major(self):
        vm = VersionManager()
        vm.bump_major("Breaking change")
        v = vm.get_version()
        assert v.major == 2
        assert v.minor == 0
        assert v.patch == 0

    def test_bump_minor(self):
        vm = VersionManager()
        vm.set_version(Version(major=1, minor=0, patch=0))
        vm.bump_minor("New feature")
        v = vm.get_version()
        assert v.major == 1
        assert v.minor == 1
        assert v.patch == 0

    def test_bump_patch(self):
        vm = VersionManager()
        vm.bump_patch("Bug fix")
        v = vm.get_version()
        assert v.major == 1
        assert v.minor == 0
        assert v.patch == 1

    def test_compare_equal(self):
        vm = VersionManager()
        v1 = Version(major=1, minor=2, patch=3)
        v2 = Version(major=1, minor=2, patch=3)
        assert vm.compare(v1, v2) == 0

    def test_compare_less(self):
        vm = VersionManager()
        v1 = Version(major=1, minor=2, patch=3)
        v2 = Version(major=1, minor=2, patch=4)
        assert vm.compare(v1, v2) == -1

    def test_compare_greater(self):
        vm = VersionManager()
        v1 = Version(major=2, minor=0, patch=0)
        v2 = Version(major=1, minor=9, patch=9)
        assert vm.compare(v1, v2) == 1

    def test_is_compatible(self):
        vm = VersionManager()
        v = Version(major=1, minor=0, patch=0, api_version="v1")
        assert vm.is_compatible(v, "v1") is True
        assert vm.is_compatible(v, "v2") is False

    def test_changelog(self):
        vm = VersionManager()
        vm.bump_patch("Fix critical bug")
        vm.bump_minor("Add user preferences")
        log = vm.get_changelog()
        assert len(log) >= 2

    def test_generate_version_string(self):
        vm = VersionManager()
        vm.set_version(Version(major=3, minor=2, patch=1))
        assert vm.generate_version_string() == "3.2.1"


class TestBackupManager:
    """Verify backup creation, restore, delete, prune, and verification."""

    def test_create_backup(self):
        bm = BackupManager(MaintenanceConfig(enable_backup=True))
        b = bm.create_backup("test-backup", {"key": "value"}, backup_type="full")
        assert b.name == "test-backup"
        assert b.type == "full"
        assert b.size_bytes > 0
        assert b.checksum != ""

    def test_list_backups(self):
        bm = BackupManager(MaintenanceConfig(enable_backup=True))
        bm.create_backup("b1", {"a": 1})
        bm.create_backup("b2", {"b": 2})
        backups = bm.list_backups()
        assert len(backups) == 2

    def test_restore_backup(self):
        bm = BackupManager(MaintenanceConfig(enable_backup=True))
        data = {"key": "value", "nested": {"a": 1}}
        b = bm.create_backup("restore-test", data)
        restored = bm.restore_backup(b.id)
        assert restored == data

    def test_restore_nonexistent(self):
        bm = BackupManager(MaintenanceConfig(enable_backup=True))
        with pytest.raises(ValueError, match="Backup not found"):
            bm.restore_backup("nonexistent")

    def test_delete_backup(self):
        bm = BackupManager(MaintenanceConfig(enable_backup=True))
        b = bm.create_backup("delete-me", {"x": 1})
        assert bm.delete_backup(b.id) is True
        assert bm.list_backups() == []

    def test_delete_nonexistent(self):
        bm = BackupManager(MaintenanceConfig(enable_backup=True))
        assert bm.delete_backup("nonexistent") is False

    def test_verify_backup_valid(self):
        bm = BackupManager(MaintenanceConfig(enable_backup=True))
        b = bm.create_backup("verify-test", {"data": "test"})
        assert bm.verify_backup(b.id) is True

    def test_verify_backup_invalid(self):
        bm = BackupManager(MaintenanceConfig(enable_backup=True))
        assert bm.verify_backup("nonexistent") is False

    def test_prune_old_backups(self):
        cfg = MaintenanceConfig(enable_backup=True, max_backups=3)
        bm = BackupManager(cfg)
        for i in range(5):
            bm.create_backup(f"backup-{i}", {"i": i})
        pruned = bm.prune_old_backups()
        assert len(bm.list_backups()) <= 3
        assert pruned >= 2

    def test_backup_disabled(self):
        cfg = MaintenanceConfig(enable_backup=False)
        bm = BackupManager(cfg)
        with pytest.raises(RuntimeError, match="disabled"):
            bm.create_backup("fail", {})


class TestDeprecationManager:
    """Verify deprecation registration, checking, expiration, and cleanup."""

    def test_deprecate(self):
        dm = DeprecationManager()
        d = dm.deprecate("old_api", "api", "new_api", "3.0.0")
        assert d.item_name == "old_api"
        assert d.item_type == "api"
        assert d.alternative == "new_api"

    def test_check_deprecated_found(self):
        dm = DeprecationManager()
        dm.deprecate("legacy_endpoint", "endpoint", "v2/endpoint", "4.0.0")
        assert dm.check_deprecated("legacy_endpoint", "endpoint") is True

    def test_check_deprecated_not_found(self):
        dm = DeprecationManager()
        assert dm.check_deprecated("nonexistent", "api") is False

    def test_get_deprecations(self):
        dm = DeprecationManager()
        dm.deprecate("item1", "api", "item2", "3.0.0")
        dm.deprecate("old_config", "config", "new_config", "3.0.0")
        notices = dm.get_deprecations()
        assert len(notices) == 2

    def test_get_expired(self):
        dm = DeprecationManager()
        dm.set_current_version("3.0.0")
        dm.deprecate("old_item", "api", "new_item", "2.0.0")  # expired
        dm.deprecate("current_item", "api", "better_item", "4.0.0")  # not expired
        expired = dm.get_expired()
        assert len(expired) == 1
        assert expired[0].item_name == "old_item"

    def test_cleanup_expired(self):
        dm = DeprecationManager()
        dm.set_current_version("3.0.0")
        dm.deprecate("removed", "api", "new", "2.0.0")
        dm.deprecate("kept", "api", "better", "5.0.0")
        removed = dm.cleanup_expired()
        assert removed == 1
        assert len(dm.get_deprecations()) == 1

    def test_cleanup_no_expired(self):
        dm = DeprecationManager()
        dm.set_current_version("1.0.0")
        dm.deprecate("future", "api", "later", "3.0.0")
        assert dm.cleanup_expired() == 0


class TestDiagnosticsEngine:
    """Verify diagnostics, health checks, resource usage, and recommendations."""

    def test_run_diagnostics(self):
        de = DiagnosticsEngine()
        report = de.run_diagnostics()
        assert isinstance(report, DiagnosticReport)
        assert report.id != ""
        assert "cpu_percent" in report.resource_usage
        assert "memory_percent" in report.resource_usage

    def test_check_service_health(self):
        de = DiagnosticsEngine()
        de.register_service("test_svc", lambda: {"status": "healthy"})
        health = de.check_service_health(["test_svc"])
        assert health["test_svc"]["status"] == "healthy"

    def test_check_service_health_unregistered(self):
        de = DiagnosticsEngine()
        health = de.check_service_health(["unknown_svc"])
        assert health["unknown_svc"]["status"] == "unknown"

    def test_analyze_error_logs(self):
        de = DiagnosticsEngine()
        logs = [
            {"level": "ERROR", "message": "fail"},
            {"level": "ERROR", "message": "fail2"},
            {"level": "WARNING", "message": "warn"},
        ]
        counts = de.analyze_error_logs(logs)
        assert counts.get("ERROR") == 2
        assert counts.get("WARNING") == 1

    def test_analyze_error_logs_empty_fallback(self):
        de = DiagnosticsEngine()
        counts = de.analyze_error_logs([])
        # Should return mock values
        assert "ERROR" in counts

    def test_generate_recommendations_no_issues(self):
        de = DiagnosticsEngine()
        recs = de.generate_recommendations([])
        assert len(recs) >= 1
        assert "normal" in recs[0].lower()

    def test_generate_recommendations_with_issues(self):
        de = DiagnosticsEngine()
        issues = [
            {"type": "high_cpu", "detail": "92"},
            {"type": "high_memory", "detail": "88"},
        ]
        recs = de.generate_recommendations(issues)
        assert len(recs) >= 2
        assert any("CPU" in r for r in recs)
        assert any("memory" in r.lower() for r in recs)

    def test_export_report_json(self):
        de = DiagnosticsEngine()
        report = de.run_diagnostics()
        output = de.export_report(report, "json")
        assert '"id"' in output
        assert '"recommendations"' in output

    def test_export_report_text(self):
        de = DiagnosticsEngine()
        report = de.run_diagnostics()
        output = de.export_report(report, "text")
        assert "Diagnostic Report" in output
        assert "Service Health" in output

    def test_export_report_invalid_format(self):
        de = DiagnosticsEngine()
        report = de.run_diagnostics()
        with pytest.raises(ValueError, match="Unsupported"):
            de.export_report(report, "xml")


class TestMaintenanceService:
    """Verify service wrapper."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        svc = MaintenanceService()
        assert await svc.initialize() is True

    @pytest.mark.asyncio
    async def test_version_management(self):
        svc = MaintenanceService()
        await svc.initialize()
        v = await svc.get_version()
        assert v.major == 1
        v = await svc.bump_minor("Test bump")
        assert v.minor == 1

    @pytest.mark.asyncio
    async def test_backup_lifecycle(self):
        svc = MaintenanceService()
        await svc.initialize()
        backup = await svc.create_backup("lifecycle-test", {"a": 1})
        assert backup.id != ""
        backups = await svc.list_backups()
        assert len(backups) == 1
        data = await svc.restore_backup(backup.id)
        assert data == {"a": 1}
        assert await svc.delete_backup(backup.id) is True

    @pytest.mark.asyncio
    async def test_deprecation_management(self):
        svc = MaintenanceService()
        await svc.initialize()
        d = await svc.deprecate("old_api", "api", "new_api", "3.0.0", "Use new_api instead")
        assert d.item_name == "old_api"
        assert await svc.check_deprecated("old_api", "api") is True

    @pytest.mark.asyncio
    async def test_diagnostics(self):
        svc = MaintenanceService()
        await svc.initialize()
        report = await svc.run_diagnostics()
        assert isinstance(report, DiagnosticReport)
        output = await svc.export_report(report, "json")
        assert "recommendations" in output

    @pytest.mark.asyncio
    async def test_health(self):
        svc = MaintenanceService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"
        assert "backup_count" in health
        assert "deprecation_count" in health

    @pytest.mark.asyncio
    async def test_shutdown(self):
        svc = MaintenanceService()
        await svc.initialize()
        await svc.shutdown()
        assert not svc.is_initialized()
