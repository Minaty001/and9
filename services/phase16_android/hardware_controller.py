"""
Phase 16 — Hardware Controller.

Controls Android hardware: volume level and screen brightness.
"""

import logging
from typing import Optional


class HardwareController:
    """Controls Android hardware parameters.

    Manages volume (0-100) and brightness (0-100) levels.
    In a real deployment, this would use Android's AudioManager
    and PowerManager.
    """

    def __init__(self):
        self._volume: int = 50
        self._brightness: int = 70
        self._logger = logging.getLogger("hardware_controller")

    def set_volume(self, level: int) -> bool:
        """Set volume level (0-100).

        Args:
            level: Volume level from 0 to 100.

        Returns:
            True if volume was set, False if out of range.
        """
        if not isinstance(level, int) or level < 0 or level > 100:
            self._logger.warning("Invalid volume level: %s", level)
            return False
        self._volume = level
        self._logger.info("Volume set to %d", level)
        return True

    def get_volume(self) -> int:
        """Get current volume level.

        Returns:
            Current volume level (0-100).
        """
        return self._volume

    def set_brightness(self, level: int) -> bool:
        """Set screen brightness level (0-100).

        Args:
            level: Brightness level from 0 to 100.

        Returns:
            True if brightness was set, False if out of range.
        """
        if not isinstance(level, int) or level < 0 or level > 100:
            self._logger.warning("Invalid brightness level: %s", level)
            return False
        self._brightness = level
        self._logger.info("Brightness set to %d", level)
        return True

    def get_brightness(self) -> int:
        """Get current brightness level.

        Returns:
            Current brightness level (0-100).
        """
        return self._brightness
