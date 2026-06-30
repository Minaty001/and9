"""
Phase 30 — Notification Queue.

Priority-based notification queue with enqueue/dequeue operations.
Supports priority ordering: critical > high > normal > low.
"""

from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from collections import defaultdict

from .config import NotificationConfig
from .models import Notification

logger = logging.getLogger(__name__)

_PRIORITY_ORDER = {"critical": 0, "high": 1, "normal": 2, "low": 3}


class NotificationQueue:
    """Priority-based notification queue.

    Usage:
        queue = NotificationQueue()
        nid = queue.enqueue(Notification(...))
        next_notif = queue.dequeue()
    """

    def __init__(self, config: Optional[NotificationConfig] = None):
        self.config = config or NotificationConfig()
        self._queues: Dict[str, list] = defaultdict(list)
        self._all_notifications: Dict[str, Notification] = {}

    def enqueue(self, notification: Notification) -> str:
        """Enqueue a notification.

        Args:
            notification: Notification to enqueue.

        Returns:
            Notification ID.
        """
        self._all_notifications[notification.id] = notification

        priority = notification.priority if notification.priority in _PRIORITY_ORDER else "normal"
        self._queues[priority].append(notification.id)
        self._prune_expired()
        return notification.id

    def dequeue(self, priority: Optional[str] = None) -> Optional[Notification]:
        """Dequeue the highest-priority notification.

        Args:
            priority: Optional priority filter.

        Returns:
            The next Notification, or None if queue empty.
        """
        self._prune_expired()

        if priority and priority in _PRIORITY_ORDER:
            queue = self._queues.get(priority, [])
            while queue:
                nid = queue.pop(0)
                notif = self._all_notifications.get(nid)
                if notif and not notif.is_read:
                    return notif
            return None

        # Get from highest priority first
        for prio in ["critical", "high", "normal", "low"]:
            queue = self._queues.get(prio, [])
            while queue:
                nid = queue.pop(0)
                notif = self._all_notifications.get(nid)
                if notif and not notif.is_read:
                    return notif

        return None

    def peek(self, priority: Optional[str] = None) -> Optional[Notification]:
        """Peek at the next notification without removing it.

        Args:
            priority: Optional priority filter.

        Returns:
            Next Notification or None.
        """
        self._prune_expired()

        if priority and priority in _PRIORITY_ORDER:
            queue = self._queues.get(priority, [])
            for nid in queue:
                notif = self._all_notifications.get(nid)
                if notif and not notif.is_read:
                    return notif
            return None

        for prio in ["critical", "high", "normal", "low"]:
            queue = self._queues.get(prio, [])
            for nid in queue:
                notif = self._all_notifications.get(nid)
                if notif and not notif.is_read:
                    return notif

        return None

    def size(self) -> int:
        """Return total pending notification count."""
        self._prune_expired()
        return len([n for n in self._all_notifications.values() if not n.is_read])

    def get_pending_count(self) -> int:
        """Return count of unread notifications."""
        return self.size()

    def clear(self) -> int:
        """Clear all notifications.

        Returns:
            Number of notifications cleared.
        """
        count = len(self._all_notifications)
        self._queues.clear()
        self._all_notifications.clear()
        return count

    def _prune_expired(self) -> None:
        """Remove expired notifications."""
        now = datetime.now(timezone.utc)
        expired_ids = []
        for nid, notif in self._all_notifications.items():
            if notif.expires_at and notif.expires_at <= now:
                expired_ids.append(nid)

        for nid in expired_ids:
            del self._all_notifications[nid]
            for queue in self._queues.values():
                if nid in queue:
                    queue.remove(nid)
