"""
Tests for Phase 38 — Configuration System.
"""

import pytest
from services.phase38_config import (
    ConfigSystemConfig,
    ConfigEntry,
    ConfigSource,
    ValidationError,
    ConfigStore,
    ProfileManager,
    ConfigValidator,
    ConfigService,
)


class TestConfigStore:
    """Verify config key-value storage with profile support."""

    def test_set_and_get(self):
        store = ConfigStore()
        store.set("db.host", "localhost")
        assert store.get("db.host") == "localhost"

    def test_get_default(self):
        store = ConfigStore()
        assert store.get("nonexistent", "default_val") == "default_val"

    def test_delete(self):
        store = ConfigStore()
        store.set("key", "value")
        assert store.delete("key") is True
        assert store.get("key") is None

    def test_delete_nonexistent(self):
        store = ConfigStore()
        assert store.delete("nonexistent") is False

    def test_has(self):
        store = ConfigStore()
        store.set("key", "val")
        assert store.has("key") is True
        assert store.has("other") is False

    def test_get_all(self):
        store = ConfigStore()
        store.set("a", 1)
        store.set("b", 2)
        all_config = store.get_all()
        assert all_config == {"a": 1, "b": 2}

    def test_get_by_prefix(self):
        store = ConfigStore()
        store.set("db.host", "localhost")
        store.set("db.port", 5432)
        store.set("app.name", "test")
        prefixed = store.get_by_prefix("db.")
        assert len(prefixed) == 2

    def test_clear(self):
        store = ConfigStore()
        store.set("key", "val")
        assert store.clear() >= 1
        assert store.get("key") is None

    def test_profile_isolation(self):
        store = ConfigStore()
        store.set("key", "default_val", profile="default")
        store.set("key", "override_val", profile="production")
        assert store.get("key", profile="default") == "default_val"
        assert store.get("key", profile="production") == "override_val"

    def test_immutable_protection(self):
        store = ConfigStore()
        store.set("immutable_key", "original", is_immutable=True)
        store.set("immutable_key", "modified")
        assert store.get("immutable_key") == "original"


class TestProfileManager:
    """Verify profile management."""

    def test_create_profile(self):
        mgr = ProfileManager()
        assert mgr.create_profile("test") is True
        assert mgr.create_profile("test") is False  # duplicate

    def test_activate_profile(self):
        mgr = ProfileManager()
        mgr.create_profile("prod")
        assert mgr.activate_profile("prod") is True
        assert mgr.get_active() == "prod"

    def test_activate_nonexistent(self):
        mgr = ProfileManager()
        assert mgr.activate_profile("nonexistent") is False

    def test_delete_profile(self):
        mgr = ProfileManager()
        mgr.create_profile("staging")
        # Cannot delete active
        assert mgr.delete_profile("default") is False
        assert mgr.delete_profile("staging") is True

    def test_rename_profile(self):
        mgr = ProfileManager()
        mgr.create_profile("old")
        assert mgr.rename_profile("old", "new") is True
        assert "old" not in [p["name"] for p in mgr.list_profiles()]
        assert "new" in [p["name"] for p in mgr.list_profiles()]

    def test_list_profiles(self):
        mgr = ProfileManager()
        profiles = mgr.list_profiles()
        assert len(profiles) >= 1
        assert any(p["active"] for p in profiles)

    def test_clone_profile(self):
        mgr = ProfileManager(store_entries={})
        mgr.create_profile("source")
        assert mgr.clone_profile("source", "clone") is True


class TestConfigValidator:
    """Verify config validation."""

    def test_validate_type(self):
        validator = ConfigValidator()
        errors = validator.validate("port", "not_int", {"type": "int"})
        assert len(errors) == 1
        assert "Expected type" in errors[0].message

    def test_validate_allowed(self):
        validator = ConfigValidator()
        errors = validator.validate("mode", "invalid", {"allowed": ["a", "b", "c"]})
        assert len(errors) == 1

    def test_validate_min(self):
        validator = ConfigValidator()
        errors = validator.validate("count", 5, {"min": 10})
        assert len(errors) == 1

    def test_validate_max(self):
        validator = ConfigValidator()
        errors = validator.validate("count", 100, {"max": 50})
        assert len(errors) == 1

    def test_validate_min_length(self):
        validator = ConfigValidator()
        errors = validator.validate("name", "ab", {"min_length": 3})
        assert len(errors) == 1

    def test_validate_max_length(self):
        validator = ConfigValidator()
        errors = validator.validate("name", "toolong", {"max_length": 3})
        assert len(errors) == 1

    def test_validate_pattern(self):
        validator = ConfigValidator()
        errors = validator.validate("email", "not-an-email", {"pattern": r".+@.+\..+"})
        assert len(errors) == 1

    def test_validate_range(self):
        validator = ConfigValidator()
        errors = validator.validate("value", 200, {"range": [0, 100]})
        assert len(errors) == 1

    def test_validate_valid(self):
        validator = ConfigValidator()
        errors = validator.validate("port", 8080, {"type": "int", "min": 1024, "max": 65535})
        assert len(errors) == 0


class TestConfigService:
    """Verify service wrapper."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        svc = ConfigService()
        assert await svc.initialize() is True

    @pytest.mark.asyncio
    async def test_get_set_delete(self):
        svc = ConfigService()
        await svc.initialize()
        svc.set("test.key", "test_value")
        assert svc.get("test.key") == "test_value"
        assert svc.has("test.key") is True
        assert svc.delete("test.key") is True

    @pytest.mark.asyncio
    async def test_profile_operations(self):
        svc = ConfigService()
        await svc.initialize()
        assert svc.create_profile("staging") is True
        assert svc.activate_profile("staging") is True
        assert svc.get_active_profile() == "staging"

    @pytest.mark.asyncio
    async def test_validate(self):
        svc = ConfigService()
        await svc.initialize()
        errors = svc.validate("port", "bad", {"type": "int"})
        assert len(errors) == 1

    @pytest.mark.asyncio
    async def test_export_import(self):
        svc = ConfigService()
        await svc.initialize()
        svc.set("exp.key", "exp_val")
        exported = svc.export_config()
        assert "exp_val" in exported
        count = svc.import_config('{"new.key": "new_val"}')
        assert count == 1
        assert svc.get("new.key") == "new_val"

    @pytest.mark.asyncio
    async def test_health(self):
        svc = ConfigService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_stats(self):
        svc = ConfigService()
        await svc.initialize()
        stats = await svc.stats()
        assert stats["service"] == "jarvis_config"

    @pytest.mark.asyncio
    async def test_shutdown(self):
        svc = ConfigService()
        await svc.initialize()
        await svc.shutdown()
        assert not svc.is_initialized()
