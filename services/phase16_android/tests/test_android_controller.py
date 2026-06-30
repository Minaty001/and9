"""
Tests for Phase 16 — Android Controller.

Covers:
    - AndroidActionResult creation, success/failure
    - AppLauncher: launch supported/unsupported, list
    - MediaController: all control actions
    - NotificationController: send, list, clear
    - ClipboardController: set/get roundtrip
    - HardwareController: volume/brightness validation
    - AndroidControllerService: init/shutdown/health/stats, full execute flow
"""

import pytest

from services.phase16_android import (
    AndroidConfig,
    AndroidAction,
    AndroidActionResult,
    AppLauncher,
    MediaController,
    NotificationController,
    ClipboardController,
    HardwareController,
    AndroidControllerService,
)
from services.base import ServiceBase


# ═════════════════════════════════════════════════════════════════
# AndroidActionResult Tests
# ═════════════════════════════════════════════════════════════════


class TestAndroidActionResult:
    """Verify AndroidActionResult model."""

    def test_success_result(self):
        r = AndroidActionResult(
            success=True,
            action_type="launch_app",
            target="chrome",
            message="App launched",
            duration_ms=10.0,
        )
        assert r.success is True
        assert r.action_type == "launch_app"
        assert r.target == "chrome"
        assert r.error is None

    def test_failure_result(self):
        r = AndroidActionResult(
            success=False,
            action_type="launch_app",
            target="unknown",
            message="App not found",
            duration_ms=5.0,
            error="Unsupported app",
        )
        assert r.success is False
        assert r.error == "Unsupported app"


# ═════════════════════════════════════════════════════════════════
# AppLauncher Tests
# ═════════════════════════════════════════════════════════════════


class TestAppLauncher:
    """Verify AppLauncher operations."""

    def test_launch_supported(self):
        launcher = AppLauncher(supported_apps=["chrome", "youtube"])
        result = launcher.launch("chrome")
        assert result.success is True
        assert result.action_type == "launch_app"
        assert result.target == "chrome"

    def test_launch_unsupported(self):
        launcher = AppLauncher(supported_apps=["chrome"])
        result = launcher.launch("nonexistent")
        assert result.success is False
        assert "not in the supported list" in result.message.lower()

    def test_launch_case_insensitive(self):
        launcher = AppLauncher(supported_apps=["Chrome"])
        result = launcher.launch("CHROME")
        assert result.success is True

    def test_list_supported_apps(self):
        apps = ["chrome", "youtube", "gmail"]
        launcher = AppLauncher(supported_apps=apps)
        listed = launcher.list_supported_apps()
        assert len(listed) == 3
        assert "chrome" in listed

    def test_is_supported(self):
        launcher = AppLauncher(supported_apps=["chrome", "maps"])
        assert launcher.is_supported("chrome") is True
        assert launcher.is_supported("maps") is True
        assert launcher.is_supported("unknown") is False


# ═════════════════════════════════════════════════════════════════
# MediaController Tests
# ═════════════════════════════════════════════════════════════════


class TestMediaController:
    """Verify MediaController actions."""

    @pytest.fixture
    def controller(self):
        return MediaController()

    def test_play(self, controller):
        result = controller.play()
        assert result.success is True
        assert result.action_type == "media_control"
        assert result.target == "play"

    def test_pause(self, controller):
        result = controller.pause()
        assert result.success is True
        assert result.target == "pause"

    def test_next(self, controller):
        result = controller.next()
        assert result.success is True
        assert result.target == "next"

    def test_previous(self, controller):
        result = controller.previous()
        assert result.success is True
        assert result.target == "previous"

    def test_volume_up(self, controller):
        result = controller.volume_up()
        assert result.success is True
        assert result.target == "volume_up"

    def test_volume_down(self, controller):
        result = controller.volume_down()
        assert result.success is True
        assert result.target == "volume_down"

    def test_invalid_action(self):
        # Accessing _execute directly with invalid action
        controller = MediaController()
        result = controller._execute("invalid_action")
        assert result.success is False
        assert "invalid" in result.message.lower()


# ═════════════════════════════════════════════════════════════════
# NotificationController Tests
# ═════════════════════════════════════════════════════════════════


class TestNotificationController:
    """Verify NotificationController operations."""

    @pytest.fixture
    def controller(self):
        return NotificationController()

    def test_send_notification(self, controller):
        result = controller.send("Test Title", "Test body text")
        assert result.success is True
        assert result.action_type == "notification"
        assert result.result_data is not None
        assert result.result_data["title"] == "Test Title"

    def test_send_empty_notification(self, controller):
        result = controller.send("", "")
        assert result.success is False
        assert "required" in result.message.lower()

    def test_list_recent(self, controller):
        controller.send("Title 1", "Body 1")
        controller.send("Title 2", "Body 2")
        notifications = controller.list_recent()
        assert len(notifications) == 2
        # Most recent first
        assert notifications[0]["title"] == "Title 2"

    def test_clear_notification(self, controller):
        controller.send("Test", "Body")
        notifications = controller.list_recent()
        nid = notifications[0]["id"]
        assert controller.clear(nid) is True
        assert len(controller.list_recent()) == 0

    def test_clear_nonexistent(self, controller):
        assert controller.clear(9999) is False


# ═════════════════════════════════════════════════════════════════
# ClipboardController Tests
# ═════════════════════════════════════════════════════════════════


class TestClipboardController:
    """Verify ClipboardController operations."""

    def test_set_and_get(self):
        cb = ClipboardController()
        assert cb.set("Hello World") is True
        assert cb.get() == "Hello World"

    def test_get_empty(self):
        cb = ClipboardController()
        assert cb.get() == ""

    def test_overwrite(self):
        cb = ClipboardController()
        cb.set("First")
        cb.set("Second")
        assert cb.get() == "Second"


# ═════════════════════════════════════════════════════════════════
# HardwareController Tests
# ═════════════════════════════════════════════════════════════════


class TestHardwareController:
    """Verify HardwareController operations."""

    @pytest.fixture
    def hw(self):
        return HardwareController()

    def test_set_volume_valid(self, hw):
        assert hw.set_volume(75) is True
        assert hw.get_volume() == 75

    def test_set_volume_out_of_range_low(self, hw):
        assert hw.set_volume(-1) is False
        assert hw.get_volume() == 50  # default

    def test_set_volume_out_of_range_high(self, hw):
        assert hw.set_volume(101) is False

    def test_set_volume_non_int(self, hw):
        assert hw.set_volume("50") is False  # type: ignore

    def test_set_brightness_valid(self, hw):
        assert hw.set_brightness(50) is True
        assert hw.get_brightness() == 50

    def test_set_brightness_out_of_range(self, hw):
        assert hw.set_brightness(150) is False
        assert hw.get_brightness() == 70  # default

    def test_set_brightness_zero(self, hw):
        assert hw.set_brightness(0) is True
        assert hw.get_brightness() == 0

    def test_set_volume_zero(self, hw):
        assert hw.set_volume(0) is True
        assert hw.get_volume() == 0


# ═════════════════════════════════════════════════════════════════
# AndroidControllerService Tests
# ═════════════════════════════════════════════════════════════════


class TestAndroidControllerService:
    """Verify AndroidControllerService lifecycle and execution."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        svc = AndroidControllerService()
        result = await svc.initialize()
        assert result is True
        assert svc.is_initialized() is True

    @pytest.mark.asyncio
    async def test_health_after_init(self):
        svc = AndroidControllerService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"
        assert health["initialized"] is True
        assert health["service_name"] == "jarvis_android"

    @pytest.mark.asyncio
    async def test_stats(self):
        svc = AndroidControllerService()
        await svc.initialize()
        stats = await svc.stats()
        assert stats["service"] == "jarvis_android"
        assert stats["initialized"] is True
        assert "controllers" in stats

    @pytest.mark.asyncio
    async def test_shutdown(self):
        svc = AndroidControllerService()
        await svc.initialize()
        await svc.shutdown()
        assert svc.is_initialized() is False

    @pytest.mark.asyncio
    async def test_execute_launch_app(self):
        svc = AndroidControllerService()
        await svc.initialize()
        action = AndroidAction(action_type="launch_app", target="chrome")
        result = svc.execute(action)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_launch_unsupported(self):
        svc = AndroidControllerService()
        await svc.initialize()
        action = AndroidAction(action_type="launch_app", target="unknown_app")
        result = svc.execute(action)
        assert result.success is False

    @pytest.mark.asyncio
    async def test_execute_media_play(self):
        svc = AndroidControllerService()
        await svc.initialize()
        action = AndroidAction(action_type="media_control", target="play")
        result = svc.execute(action)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_notification(self):
        svc = AndroidControllerService()
        await svc.initialize()
        action = AndroidAction(
            action_type="notification",
            target="send",
            params={"title": "Test", "text": "Body"},
        )
        result = svc.execute(action)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_clipboard_set(self):
        svc = AndroidControllerService()
        await svc.initialize()
        action = AndroidAction(
            action_type="clipboard",
            target="set",
            params={"text": "Hello"},
        )
        result = svc.execute(action)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_clipboard_get(self):
        svc = AndroidControllerService()
        await svc.initialize()
        svc.clipboard_set("World")
        action = AndroidAction(action_type="clipboard", target="get")
        result = svc.execute(action)
        assert result.success is True
        assert result.result_data == "World"

    @pytest.mark.asyncio
    async def test_execute_volume(self):
        svc = AndroidControllerService()
        await svc.initialize()
        action = AndroidAction(
            action_type="volume",
            target="75",
            params={"level": 75},
        )
        result = svc.execute(action)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_volume_invalid(self):
        svc = AndroidControllerService()
        await svc.initialize()
        action = AndroidAction(
            action_type="volume",
            target="150",
            params={"level": 150},
        )
        result = svc.execute(action)
        assert result.success is False

    @pytest.mark.asyncio
    async def test_execute_brightness(self):
        svc = AndroidControllerService()
        await svc.initialize()
        action = AndroidAction(
            action_type="brightness",
            target="50",
            params={"level": 50},
        )
        result = svc.execute(action)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_unknown_action(self):
        svc = AndroidControllerService()
        await svc.initialize()
        action = AndroidAction(action_type="unknown_type", target="x")
        result = svc.execute(action)
        assert result.success is False
        assert "unknown" in result.message.lower()

    @pytest.mark.asyncio
    async def test_execute_before_init(self):
        svc = AndroidControllerService()
        # Don't initialize
        action = AndroidAction(action_type="launch_app", target="chrome")
        result = svc.execute(action)
        assert result.success is False

    @pytest.mark.asyncio
    async def test_convenience_methods(self):
        svc = AndroidControllerService()
        await svc.initialize()

        # App launch
        assert svc.launch_app("chrome").success is True
        assert svc.launch_app("unknown").success is False

        # Media
        assert svc.media_play().success is True
        assert svc.media_pause().success is True
        assert svc.media_next().success is True
        assert svc.media_previous().success is True
        assert svc.media_volume_up().success is True
        assert svc.media_volume_down().success is True

        # Notifications
        assert svc.send_notification("Title", "Body").success is True
        assert len(svc.list_notifications()) > 0
        nid = svc.list_notifications()[0]["id"]
        assert svc.clear_notification(nid) is True

        # Clipboard
        assert svc.clipboard_set("Test") is True
        assert svc.clipboard_get() == "Test"

        # Hardware
        assert svc.set_volume(80) is True
        assert svc.get_volume() == 80
        assert svc.set_brightness(40) is True
        assert svc.get_brightness() == 40

        # List
        apps = svc.list_supported_apps()
        assert len(apps) > 0
        assert "chrome" in apps


# ═════════════════════════════════════════════════════════════════
# AndroidConfig Tests
# ═════════════════════════════════════════════════════════════════


class TestAndroidConfig:
    """Verify AndroidConfig defaults."""

    def test_default_config(self):
        cfg = AndroidConfig()
        assert cfg.service_name == "jarvis_android"
        assert cfg.enable_permission_check is True
        assert cfg.default_action_timeout_ms == 5000
        assert len(cfg.supported_apps) > 0
        assert "chrome" in cfg.supported_apps
        assert cfg.enable_hardware_control is True
        assert cfg.enable_notification_access is True

    def test_config_override(self):
        cfg = AndroidConfig(
            service_name="custom_android",
            enable_permission_check=False,
            supported_apps=["custom_app"],
        )
        assert cfg.service_name == "custom_android"
        assert cfg.enable_permission_check is False
        assert cfg.supported_apps == ["custom_app"]
