"""
Phase 16 — Media Controller.

Controls media playback: play, pause, next, previous, volume up/down.
"""

import time
import logging
from typing import Optional

from .models import AndroidActionResult


class MediaController:
    """Controls media playback on the Android device.

    Simulates media control actions. In a real deployment, this would
    interact with Android's MediaSession framework.
    """

    VALID_ACTIONS = {"play", "pause", "next", "previous", "volume_up", "volume_down"}

    def __init__(self):
        self._logger = logging.getLogger("media_controller")

    def _execute(self, action: str) -> AndroidActionResult:
        """Execute a media control action.

        Args:
            action: One of play/pause/next/previous/volume_up/volume_down.

        Returns:
            AndroidActionResult with execution status.
        """
        start = time.perf_counter()

        if action not in self.VALID_ACTIONS:
            duration_ms = (time.perf_counter() - start) * 1000
            return AndroidActionResult(
                success=False,
                action_type="media_control",
                target=action,
                message=f"Invalid media action: {action}",
                duration_ms=duration_ms,
                error=f"Unknown media action '{action}'",
            )

        # Simulate media control
        duration_ms = (time.perf_counter() - start) * 1000
        action_label = action.replace("_", " ").title()
        self._logger.info("Media action: %s", action)
        return AndroidActionResult(
            success=True,
            action_type="media_control",
            target=action,
            message=f"Media '{action_label}' executed",
            duration_ms=duration_ms,
        )

    def play(self) -> AndroidActionResult:
        """Resume playback."""
        return self._execute("play")

    def pause(self) -> AndroidActionResult:
        """Pause playback."""
        return self._execute("pause")

    def next(self) -> AndroidActionResult:
        """Skip to next track."""
        return self._execute("next")

    def previous(self) -> AndroidActionResult:
        """Go to previous track."""
        return self._execute("previous")

    def volume_up(self) -> AndroidActionResult:
        """Increase media volume."""
        return self._execute("volume_up")

    def volume_down(self) -> AndroidActionResult:
        """Decrease media volume."""
        return self._execute("volume_down")
