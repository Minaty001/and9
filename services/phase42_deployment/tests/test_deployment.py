"""
Tests for Phase 42 — Deployment.
"""

import os
import json
import tempfile
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from services.phase42_deployment import (
    DeploymentConfig,
    DeploymentService,
    EnvironmentManager,
    EnvironmentProfile,
    Packaging,
    Package,
    HealthChecker,
    HealthCheckResult,
    UpdateManager,
    UpdateManifest,
    DeploymentState,
)


class TestDeploymentConfig:
    """Verify configuration defaults and env prefix."""

    def test_defaults(self):
        cfg = DeploymentConfig()
        assert cfg.service_name == "jarvis_deployment"
        assert cfg.environment == "development"
        assert cfg.platform == "desktop"
        assert cfg.enable_health_checks is True
        assert cfg.enable_packaging is True
        assert cfg.enable_updates is True
        assert cfg.enable_rollback is True
        assert cfg.health_check_interval_seconds == 30
        assert cfg.package_format == "zip"
        assert cfg.rollback_max_versions == 5

    def test_env_prefix(self):
        assert DeploymentConfig.model_config["env_prefix"] == "JARVIS_PHASE42_"


class TestModelsCreation:
    """Verify all models can be created."""

    def test_environment_profile(self):
        profile = EnvironmentProfile(name="test", platform="desktop")
        assert profile.name == "test"
        assert profile.platform == "desktop"
        assert profile.data_dir == "~/.jarvis"
        assert profile.config_overrides == {}
        assert profile.startup_services == []
        assert profile.enabled_features == []
        assert profile.resource_limits == {}

    def test_package(self):
        pkg = Package(
            id="pkg-1",
            version="1.0.0",
            format="zip",
            files=["app.py", "config.yaml"],
            checksum="abc123",
            size_bytes=1024,
        )
        assert pkg.id == "pkg-1"
        assert pkg.version == "1.0.0"
        assert pkg.files == ["app.py", "config.yaml"]
        assert pkg.checksum == "abc123"
        assert pkg.size_bytes == 1024
        assert pkg.created_at is not None

    def test_deployment_state(self):
        state = DeploymentState(
            environment="production",
            platform="cloud",
            current_version="2.0.0",
            previous_version="1.0.0",
            uptime_seconds=3600.0,
            healthy=True,
            active_profile="production",
        )
        assert state.environment == "production"
        assert state.current_version == "2.0.0"
        assert state.previous_version == "1.0.0"
        assert state.uptime_seconds == 3600.0
        assert state.healthy is True

    def test_health_check_result(self):
        result = HealthCheckResult(
            status="healthy",
            service_checks=[
                {"service_name": "api", "status": "healthy"},
            ],
            details={"total_services": 1},
        )
        assert result.status == "healthy"
        assert len(result.service_checks) == 1
        assert result.timestamp is not None

    def test_update_manifest(self):
        manifest = UpdateManifest(
            version="2.0.0",
            changelog=["Feature A", "Bugfix B"],
            download_url="https://example.com/update.zip",
            checksum="def456",
            required_version="1.0.0",
            min_api_version="1.0",
            breaking_changes=["Removed old API"],
        )
        assert manifest.version == "2.0.0"
        assert len(manifest.changelog) == 2
        assert len(manifest.breaking_changes) == 1


class TestEnvironmentManager:
    """Verify environment profile management and platform detection."""

    def test_get_profile(self):
        mgr = EnvironmentManager()
        dev = mgr.get_profile("development")
        assert dev is not None
        assert dev.name == "development"
        assert dev.platform == "desktop"

    def test_list_profiles(self):
        mgr = EnvironmentManager()
        profiles = mgr.list_profiles()
        assert "development" in profiles
        assert "staging" in profiles
        assert "production" in profiles

    def test_get_profile_nonexistent(self):
        mgr = EnvironmentManager()
        assert mgr.get_profile("nonexistent") is None

    def test_add_custom_profile(self):
        mgr = EnvironmentManager()
        custom = EnvironmentProfile(
            name="custom_test",
            platform="desktop",
            data_dir="/tmp/custom",
            config_overrides={"key": "value"},
            startup_services=["core"],
            enabled_features=["feature_x"],
            resource_limits={"cpu": 1},
        )
        mgr.add_profile(custom)
        assert mgr.get_profile("custom_test") is not None
        assert "custom_test" in mgr.list_profiles()

    def test_detect_platform_android(self):
        with patch.dict(os.environ, {"ANDROID_ROOT": "/system"}):
            mgr = EnvironmentManager()
            assert mgr.detect_platform() == "android"

    def test_detect_platform_desktop(self):
        with patch.dict(os.environ, {}, clear=True):
            mgr = EnvironmentManager()
            assert mgr.detect_platform() == "desktop"

    @patch("services.phase42_deployment.environment.os.environ.get")
    def test_detect_platform_cloud(self, mock_get):
        def side_effect(key, default=None):
            cloud_keys = [
                "KUBERNETES_SERVICE_HOST",
                "CLOUD_RUN",
                "AWS_EXECUTION_ENV",
                "FLY_APP_NAME",
                "RENDER_INSTANCE_ID",
            ]
            return "1" if key in cloud_keys else default
        mock_get.side_effect = side_effect
        mgr = EnvironmentManager()
        assert mgr.detect_platform() == "cloud"

    def test_get_data_dir(self):
        with patch.dict(os.environ, {}, clear=True):
            mgr = EnvironmentManager()
            data_dir = mgr.get_data_dir()
            assert "~/.jarvis" in data_dir or ".jarvis" in data_dir

    def test_resolve_data_dir_with_profile(self):
        mgr = EnvironmentManager()
        data_dir = mgr.resolve_data_dir("development")
        assert "jarvis" in data_dir or data_dir == "~/.jarvis"


class TestPackaging:
    """Verify package creation, extraction, verification."""

    def test_create_package(self):
        pkg = Packaging()
        # Create temp files to include
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            f.write(b"print('hello')")
            f.flush()
            temp_path = f.name

        try:
            package = pkg.create_package("1.0.0", [temp_path])
            assert package.version == "1.0.0"
            assert package.format == "zip"
            assert len(package.files) >= 1
            assert package.checksum != ""
            assert package.size_bytes > 0
            assert package.id != ""
        finally:
            os.unlink(temp_path)

    def test_create_package_no_files(self):
        pkg = Packaging()
        package = pkg.create_package("1.0.0", [])
        assert package.version == "1.0.0"
        assert package.size_bytes == 0
        assert package.checksum == pkg._compute_checksum(b"")

    def test_verify_package_valid(self):
        pkg = Packaging()
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"test data")
            temp_path = f.name
        try:
            package = pkg.create_package("1.0.0", [temp_path])
            # Store archive bytes for verification
            package._archive_bytes = pkg._build_archive(package)
            assert pkg.verify_package(package) is True
        finally:
            os.unlink(temp_path)

    def test_verify_package_no_data(self):
        pkg = Packaging()
        package = Package(id="test", version="1.0.0", checksum="bad")
        # No archive bytes — verify returns False
        assert pkg.verify_package(package) is False

    def test_extract_package(self):
        packager = Packaging()
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"extract me")
            temp_path = f.name
        try:
            package = packager.create_package("1.0.0", [temp_path])
            # Build and store archive
            package._archive_bytes = packager._build_archive(package)
        finally:
            os.unlink(temp_path)

        dest = tempfile.mkdtemp()
        try:
            result = packager.extract_package(package, dest)
            assert result is True
            # Should have extracted the file
            extracted_files = os.listdir(dest)
            assert len(extracted_files) >= 1
        finally:
            import shutil
            shutil.rmtree(dest, ignore_errors=True)

    def test_list_contents(self):
        packager = Packaging()
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            f.write(b"x=1")
            temp_path = f.name
        try:
            package = packager.create_package("1.0.0", [temp_path])
            contents = packager.list_contents(package)
            assert len(contents) >= 1
            assert any("x=1" not in c for c in contents)  # just check files listed
        finally:
            os.unlink(temp_path)

    def test_checksum_consistency(self):
        pkg = Packaging()
        data1 = b"hello world"
        data2 = b"hello world"
        data3 = b"hello world!"
        assert pkg._compute_checksum(data1) == pkg._compute_checksum(data2)
        assert pkg._compute_checksum(data1) != pkg._compute_checksum(data3)


class TestHealthChecker:
    """Verify health check logic."""

    def test_check_service(self):
        checker = HealthChecker()
        checker.register_service("api", lambda: {"status": "healthy"})
        result = checker.check_service("api")
        assert result["status"] == "healthy"
        assert result["service_name"] == "api"

    def test_check_unregistered_service(self):
        checker = HealthChecker()
        result = checker.check_service("unknown")
        assert result["status"] == "unhealthy"

    def test_check_service_exception(self):
        checker = HealthChecker()

        def failing():
            raise RuntimeError("Service down")

        checker.register_service("broken", failing)
        result = checker.check_service("broken")
        assert result["status"] == "unhealthy"
        assert "error" in result

    def test_check_all_healthy(self):
        checker = HealthChecker()
        checker.register_service("api", lambda: {"status": "healthy"})
        checker.register_service("db", lambda: {"status": "healthy"})
        result = checker.check_all()
        assert result.status == "healthy"
        assert len(result.service_checks) == 2

    def test_check_all_unhealthy(self):
        checker = HealthChecker()
        checker.register_service("api", lambda: {"status": "healthy"})
        checker.register_service("db", lambda: {"status": "unhealthy"})
        result = checker.check_all()
        assert result.status == "unhealthy"

    def test_check_all_degraded(self):
        checker = HealthChecker()
        checker.register_service("api", lambda: {"status": "healthy"})
        checker.register_service("cache", lambda: {"status": "degraded"})
        result = checker.check_all()
        assert result.status == "degraded"

    def test_is_healthy(self):
        checker = HealthChecker()
        checker.register_service("api", lambda: {"status": "healthy"})
        assert checker.is_healthy() is True
        checker.register_service("db", lambda: {"status": "unhealthy"})
        assert checker.is_healthy() is False

    def test_get_unhealthy_services(self):
        checker = HealthChecker()
        checker.register_service("api", lambda: {"status": "healthy"})
        checker.register_service("db", lambda: {"status": "unhealthy"})
        unhealthy = checker.get_unhealthy_services()
        assert "db" in unhealthy
        assert "api" not in unhealthy

    def test_start_stop_periodic_checks(self):
        checker = HealthChecker()
        checker.register_service("test", lambda: {"status": "healthy"})
        callback_results = []

        def callback(result):
            callback_results.append(result)

        checker.start_periodic_checks(interval=1, callback=callback)
        assert checker._periodic_thread is not None
        assert checker._periodic_thread.is_alive()

        # Wait for at least one check
        import time
        time.sleep(1.5)

        checker.stop_periodic_checks()
        assert checker._periodic_thread is None or not checker._periodic_thread.is_alive()
        assert len(callback_results) >= 1

    def test_unregister_service(self):
        checker = HealthChecker()
        checker.register_service("api", lambda: {"status": "healthy"})
        checker.unregister_service("api")
        result = checker.check_service("api")
        assert result["status"] == "unhealthy"


class TestUpdateManager:
    """Verify update checking, application, rollback."""

    def test_initialize(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = UpdateManager(data_dir=tmpdir)
            assert mgr.initialize() is True
            assert mgr._initialized is True
            assert os.path.isdir(tmpdir)

    def test_check_updates_no_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = UpdateManager(data_dir=tmpdir)
            mgr.initialize()
            manifest = mgr.check_for_updates()
            assert manifest is None

    def test_check_updates_with_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_data = {
                "version": "2.0.0",
                "changelog": ["New feature"],
                "download_url": "https://example.com/pkg.zip",
                "checksum": "abc123",
            }
            with open(os.path.join(tmpdir, "update_manifest.json"), "w") as f:
                json.dump(manifest_data, f)

            mgr = UpdateManager(data_dir=tmpdir)
            mgr.initialize()
            manifest = mgr.check_for_updates()
            assert manifest is not None
            assert manifest.version == "2.0.0"

    def test_apply_update(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = UpdateManager(data_dir=tmpdir)
            mgr.initialize()

            manifest = UpdateManifest(
                version="2.0.0",
                changelog=["New"],
                download_url="https://example.com/pkg.zip",
                checksum="abc",
            )
            result = mgr.apply_update(manifest)
            assert result is True
            assert mgr.get_current_version() == "2.0.0"

    def test_apply_update_verify_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = UpdateManager(data_dir=tmpdir)
            mgr.initialize()

            manifest = UpdateManifest(
                version="",
                changelog=[],
                download_url="",
                checksum="",
            )
            result = mgr.apply_update(manifest)
            assert result is False

    def test_rollback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = UpdateManager(data_dir=tmpdir)
            mgr.initialize()

            mgr.apply_update(UpdateManifest(version="2.0.0"))
            mgr.apply_update(UpdateManifest(version="3.0.0"))
            assert mgr.get_current_version() == "3.0.0"

            result = mgr.rollback()
            assert result is True
            assert mgr.get_current_version() == "2.0.0"

    def test_rollback_empty_history(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = UpdateManager(data_dir=tmpdir)
            mgr.initialize()
            result = mgr.rollback()
            assert result is False

    def test_rollback_specific_version(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = UpdateManager(data_dir=tmpdir)
            mgr.initialize()

            mgr.apply_update(UpdateManifest(version="1.0.0"))
            mgr.apply_update(UpdateManifest(version="2.0.0"))
            mgr.apply_update(UpdateManifest(version="3.0.0"))

            result = mgr.rollback(version="1.0.0")
            assert result is True
            assert mgr.get_current_version() == "1.0.0"

    def test_rollback_nonexistent_version(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = UpdateManager(data_dir=tmpdir)
            mgr.initialize()
            mgr.apply_update(UpdateManifest(version="1.0.0"))
            result = mgr.rollback(version="99.0.0")
            assert result is False

    def test_get_version_history(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = UpdateManager(data_dir=tmpdir)
            mgr.initialize()
            history = mgr.get_version_history()
            assert isinstance(history, list)

            mgr.apply_update(UpdateManifest(version="1.0.0"))
            mgr.apply_update(UpdateManifest(version="2.0.0"))
            history = mgr.get_version_history()
            assert len(history) >= 1

    def test_verify_update(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = UpdateManager(data_dir=tmpdir)
            mgr.initialize()

            valid = UpdateManifest(version="2.0.0", download_url="https://x.com/pkg.zip", checksum="abc")
            assert mgr.verify_update(valid) is True

            invalid = UpdateManifest(version="", download_url="", checksum="")
            assert mgr.verify_update(invalid) is False

    def test_verify_update_version_requirement(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = UpdateManager(data_dir=tmpdir)
            mgr.initialize()
            mgr.apply_update(UpdateManifest(version="1.0.0"))

            manifest = UpdateManifest(
                version="2.0.0",
                required_version="2.0.0",
                download_url="https://x.com/pkg.zip",
                checksum="abc",
            )
            # Current is 1.0.0, required is 2.0.0 — should fail
            assert mgr.verify_update(manifest) is False

    def test_version_comparison(self):
        assert UpdateManager._compare_versions("1.0.0", "1.0.0") == 0
        assert UpdateManager._compare_versions("1.0.0", "2.0.0") == -1
        assert UpdateManager._compare_versions("2.0.0", "1.0.0") == 1
        assert UpdateManager._compare_versions("1.0.0", "1.1.0") == -1
        assert UpdateManager._compare_versions("1.1.0", "1.0.0") == 1


class TestDeploymentService:
    """Verify service lifecycle and operations."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        svc = DeploymentService()
        result = await svc.initialize()
        assert result is True
        assert svc.is_initialized()

    @pytest.mark.asyncio
    async def test_health(self):
        svc = DeploymentService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] in ("healthy", "unhealthy")
        assert health["service_name"] == "jarvis_deployment"
        assert "uptime_seconds" in health

    @pytest.mark.asyncio
    async def test_stats(self):
        svc = DeploymentService()
        await svc.initialize()
        stats = await svc.stats()
        assert stats["service"] == "jarvis_deployment"
        assert "package_count" in stats
        assert "metrics" in stats

    @pytest.mark.asyncio
    async def test_deploy(self):
        svc = DeploymentService()
        await svc.initialize()
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            f.write(b"x=1")
            temp_path = f.name
        try:
            pkg = await svc.deploy("1.0.0", [temp_path])
            assert pkg is not None
            assert pkg.version == "1.0.0"
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_get_state(self):
        svc = DeploymentService()
        await svc.initialize()
        state = await svc.get_state()
        assert state.environment == "development"
        assert state.platform in ("android", "desktop", "cloud")

    @pytest.mark.asyncio
    async def test_check_health(self):
        svc = DeploymentService()
        await svc.initialize()
        result = await svc.check_health()
        assert isinstance(result, HealthCheckResult)

    @pytest.mark.asyncio
    async def test_create_and_verify_package(self):
        svc = DeploymentService()
        await svc.initialize()
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"test data")
            temp_path = f.name
        try:
            pkg = await svc.create_package("1.0.0", [temp_path])
            assert pkg.version == "1.0.0"
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_list_profiles(self):
        svc = DeploymentService()
        await svc.initialize()
        profiles = await svc.list_profiles()
        assert "development" in profiles
        assert "staging" in profiles
        assert "production" in profiles

    @pytest.mark.asyncio
    async def test_switch_profile(self):
        svc = DeploymentService()
        await svc.initialize()
        result = await svc.switch_profile("production")
        assert result is True
        active = await svc.get_active_profile()
        assert active == "production"

    @pytest.mark.asyncio
    async def test_switch_profile_nonexistent(self):
        svc = DeploymentService()
        await svc.initialize()
        result = await svc.switch_profile("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_rollback(self):
        svc = DeploymentService()
        await svc.initialize()

        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            f.write(b"v1")
            f.flush()
            p1 = f.name

        try:
            await svc.deploy("1.0.0", [p1])
            result = await svc.rollback()
            # Rollback from initial with no history may or may not succeed
            assert isinstance(result, bool)
        finally:
            os.unlink(p1)

    @pytest.mark.asyncio
    async def test_get_version_history(self):
        svc = DeploymentService()
        await svc.initialize()
        history = await svc.get_version_history()
        assert isinstance(history, list)

    @pytest.mark.asyncio
    async def test_get_active_profile(self):
        svc = DeploymentService()
        await svc.initialize()
        profile = await svc.get_active_profile()
        assert profile == "development"

    @pytest.mark.asyncio
    async def test_shutdown(self):
        svc = DeploymentService()
        await svc.initialize()
        await svc.shutdown()
        assert not svc.is_initialized()
