"""
Phase 16 — Android Controller Service.

Wraps all Android sub-controllers in a ServiceBase lifecycle.
"""

import time
import logging
from typing import Any, Dict, List, Optional

from services.base.service_base import ServiceBase
from .config import AndroidConfig
from .models import AndroidAction, AndroidActionResult
from .app_launcher import AppLauncher
from .media_controller import MediaController
from .notification_controller import NotificationController
from .clipboard_controller import ClipboardController
from .hardware_controller import HardwareController


class AndroidControllerService(ServiceBase):
    """Service wrapper for the Android Controller.

    Manages sub-controllers (AppLauncher, MediaController,
    NotificationController, ClipboardController, HardwareController)
    and provides a unified execute() API.
    """

    def __init__(self, config: Optional[AndroidConfig] = None):
        super().__init__(name="jarvis_android", version="1.0.0")
        self.config = config or AndroidConfig()
        self._start_time = 0.0
        self._logger = None

        # Sub-controllers
        self._app_launcher: Optional[AppLauncher] = None
        self._media_controller: Optional[MediaController] = None
        self._notification_controller: Optional[NotificationController] = None
        self._clipboard_controller: Optional[ClipboardController] = None
        self._hardware_controller: Optional[HardwareController] = None

    async def initialize(self) -> bool:
        """Initialize the Android controller service.

        Returns:
            True if initialization succeeded.
        """
        self._start_time = time.time()
        try:
            self._logger = logging.getLogger("android_controller_service")
            self._metrics.reset()

            self._app_launcher = AppLauncher(
                supported_apps=self.config.supported_apps,
            )
            self._media_controller = MediaController()
            self._notification_controller = NotificationController()
            self._clipboard_controller = ClipboardController()
            self._hardware_controller = HardwareController()

            self._initialized = True
            self._metrics.counter("initializations")
            self._logger.info("AndroidControllerService initialized")
            return True

        except Exception as e:
            self._logger.error("AndroidControllerService initialization failed: %s", e)
            self._initialized = False
            return False

    async def shutdown(self) -> None:
        """Shut down the Android controller service."""
        if self._logger:
            self._logger.info("AndroidControllerService shutting down...")
        self._app_launcher = None
        self._media_controller = None
        self._notification_controller = None
        self._clipboard_controller = None
        self._hardware_controller = None
        self._initialized = False

    async def health(self) -> Dict[str, Any]:
        """Return service health status."""
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        status = "healthy" if self._initialized else "unhealthy"
        return {
            "status": status,
            "service_name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
        }

    async def stats(self) -> Dict[str, Any]:
        """Return service statistics and metrics."""
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            "initialized": self._initialized,
            "controllers": {
                "app_launcher": self._app_launcher is not None,
                "media_controller": self._media_controller is not None,
                "notification_controller": self._notification_controller is not None,
                "clipboard_controller": self._clipboard_controller is not None,
                "hardware_controller": self._hardware_controller is not None,
            },
            "metrics": self._metrics.snapshot(),
        }

    def execute(self, action: AndroidAction) -> AndroidActionResult:
        """Execute an Android action.

        Routes to the appropriate sub-controller based on action_type.

        Args:
            action: The AndroidAction to execute.

        Returns:
            AndroidActionResult with execution status.
        """
        if not self._initialized:
            return AndroidActionResult(
                success=False,
                action_type=action.action_type,
                target=action.target,
                message="Service not initialized",
                duration_ms=0.0,
                error="AndroidControllerService not initialized",
            )

        self._metrics.counter("actions_executed")

        action_type = action.action_type
        target = action.target

        if action_type == "launch_app":
            return self._app_launcher.launch(target)

        elif action_type == "media_control":
            return self._media_controller._execute(target)

        elif action_type == "notification":
            title = action.params.get("title", "")
            text = action.params.get("text", "")
            return self._notification_controller.send(title, text)

        elif action_type == "clipboard":
            if target == "set":
                text = action.params.get("text", "")
                success = self._clipboard_controller.set(text)
                return AndroidActionResult(
                    success=success,
                    action_type="clipboard",
                    target="set",
                    message="Clipboard set" if success else "Clipboard set failed",
                    duration_ms=0.0,
                )
            elif target == "get":
                content = self._clipboard_controller.get()
                return AndroidActionResult(
                    success=True,
                    action_type="clipboard",
                    target="get",
                    result_data=content,
                    message="Clipboard retrieved",
                    duration_ms=0.0,
                )

        elif action_type == "volume":
            level = action.params.get("level", -1)
            success = self._hardware_controller.set_volume(level)
            return AndroidActionResult(
                success=success,
                action_type="volume",
                target=str(level),
                message=f"Volume set to {level}" if success else f"Invalid volume: {level}",
                duration_ms=0.0,
                error=None if success else f"Volume {level} out of range (0-100)",
            )

        elif action_type == "brightness":
            level = action.params.get("level", -1)
            success = self._hardware_controller.set_brightness(level)
            return AndroidActionResult(
                success=success,
                action_type="brightness",
                target=str(level),
                message=f"Brightness set to {level}" if success else f"Invalid brightness: {level}",
                duration_ms=0.0,
                error=None if success else f"Brightness {level} out of range (0-100)",
            )

        elif action_type == "accessibility":
            return AndroidActionResult(
                success=False,
                action_type="accessibility",
                target=target,
                message="Accessibility actions not yet implemented",
                duration_ms=0.0,
                error="Accessibility not implemented",
            )

        else:
            return AndroidActionResult(
                success=False,
                action_type=action_type,
                target=target,
                message=f"Unknown action type: {action_type}",
                duration_ms=0.0,
                error=f"Unknown action type: {action_type}",
            )

    # ── Convenience Methods ──────────────────────────────────────

    def launch_app(self, app_name: str) -> AndroidActionResult:
        """Launch an app by name."""
        return self._app_launcher.launch(app_name)

    def media_play(self) -> AndroidActionResult:
        """Play media."""
        return self._media_controller.play()

    def media_pause(self) -> AndroidActionResult:
        """Pause media."""
        return self._media_controller.pause()

    def media_next(self) -> AndroidActionResult:
        """Next track."""
        return self._media_controller.next()

    def media_previous(self) -> AndroidActionResult:
        """Previous track."""
        return self._media_controller.previous()

    def media_volume_up(self) -> AndroidActionResult:
        """Volume up."""
        return self._media_controller.volume_up()

    def media_volume_down(self) -> AndroidActionResult:
        """Volume down."""
        return self._media_controller.volume_down()

    def send_notification(self, title: str, text: str) -> AndroidActionResult:
        """Send a notification."""
        return self._notification_controller.send(title, text)

    def list_notifications(self) -> List[Dict]:
        """List recent notifications."""
        return self._notification_controller.list_recent()

    def clear_notification(self, notification_id: int) -> bool:
        """Clear a notification."""
        return self._notification_controller.clear(notification_id)

    def clipboard_set(self, text: str) -> bool:
        """Set clipboard content."""
        return self._clipboard_controller.set(text)

    def clipboard_get(self) -> str:
        """Get clipboard content."""
        return self._clipboard_controller.get()

    def set_volume(self, level: int) -> bool:
        """Set volume level (0-100)."""
        return self._hardware_controller.set_volume(level)

    def set_brightness(self, level: int) -> bool:
        """Set brightness level (0-100)."""
        return self._hardware_controller.set_brightness(level)

    def get_volume(self) -> int:
        """Get current volume."""
        return self._hardware_controller.get_volume()

    def get_brightness(self) -> int:
        """Get current brightness."""
        return self._hardware_controller.get_brightness()

    def list_supported_apps(self) -> List[str]:
        """List supported app names."""
        return self._app_launcher.list_supported_apps()
