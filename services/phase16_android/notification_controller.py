"""
Phase 16 — Notification Controller.

Manages Android notifications: send, list recent, clear.
"""

import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .models import AndroidActionResult


class NotificationController:
    """Controls Android notifications.

    Simulates sending, listing, and clearing notifications.
    In a real deployment, this would use Android's NotificationManager.
    """

    def __init__(self):
        self._notifications: List[Dict] = []
        self._counter = 0
        self._logger = logging.getLogger("notification_controller")

    def send(self, title: str, text: str) -> AndroidActionResult:
        """Send a notification.

        Args:
            title: Notification title.
            text: Notification body text.

        Returns:
            AndroidActionResult with send status.
        """
        start = time.perf_counter()

        if not title or not text:
            duration_ms = (time.perf_counter() - start) * 1000
            return AndroidActionResult(
                success=False,
                action_type="notification",
                target="send",
                message="Notification title and text are required",
                duration_ms=duration_ms,
                error="Empty title or text",
            )

        self._counter += 1
        notification = {
            "id": self._counter,
            "title": title,
            "text": text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._notifications.append(notification)

        duration_ms = (time.perf_counter() - start) * 1000
        self._logger.info("Notification sent: %s", title)
        return AndroidActionResult(
            success=True,
            action_type="notification",
            target="send",
            result_data=notification,
            message=f"Notification '{title}' sent",
            duration_ms=duration_ms,
        )

    def list_recent(self) -> List[Dict]:
        """List recent notifications.

        Returns:
            List of notification dicts, most recent first.
        """
        return list(reversed(self._notifications))

    def clear(self, notification_id: int) -> bool:
        """Clear a notification by ID.

        Args:
            notification_id: The ID of the notification to clear.

        Returns:
            True if the notification was found and cleared.
        """
        for i, n in enumerate(self._notifications):
            if n["id"] == notification_id:
                self._notifications.pop(i)
                self._logger.info("Cleared notification %d", notification_id)
                return True
        self._logger.warning("Notification %d not found", notification_id)
        return False
