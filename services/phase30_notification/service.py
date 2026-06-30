"""
Phase 30 — Notification Manager Service.

ServiceBase wrapper for the Notification Manager.
"""

from __future__ import annotations

import time
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from services.base.service_base import ServiceBase
from .config import NotificationConfig
from .models import Notification, NotificationTemplate, NotificationChannel
from .notification_queue import NotificationQueue
from .template_engine import TemplateEngine

logger = logging.getLogger(__name__)


class NotificationManagerService(ServiceBase):
    """Notification manager service for push, in-app, and toast alerts.

    Usage:
        svc = NotificationManagerService()
        await svc.initialize()
        nid = await svc.send_notification("info", "Hello", "World")
    """

    def __init__(self, config: Optional[NotificationConfig] = None):
        super().__init__(name="jarvis_notification", version="1.0.0")
        self.config = config or NotificationConfig()
        self.queue: Optional[NotificationQueue] = None
        self.template_engine: Optional[TemplateEngine] = None
        self._channels: Dict[str, NotificationChannel] = {}
        self._notifications: Dict[str, Notification] = {}
        self._start_time = 0.0

    async def initialize(self) -> bool:
        self._start_time = time.time()
        try:
            self.queue = NotificationQueue(self.config)
            self.template_engine = TemplateEngine(self.config)

            # Register default channel
            default_channel = NotificationChannel(
                id="general",
                name="General",
                type="in-app",
                enabled=True,
            )
            self._channels["general"] = default_channel

            self._metrics.reset()
            self._initialized = True
            logger.info("NotificationManagerService initialized")
            return True
        except Exception as e:
            logger.error("NotificationManagerService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        logger.info("NotificationManagerService shutting down...")
        self._initialized = False

    async def send_notification(
        self,
        title: str,
        message: str,
        notif_type: str = "info",
        priority: str = "normal",
        channel: str = "general",
        source: str = "system",
        data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Send a notification."""
        if not self.queue:
            raise RuntimeError("NotificationManagerService not initialized")

        notification = Notification(
            id=uuid.uuid4().hex[:12],
            type=notif_type,
            title=title,
            message=message,
            priority=priority,
            channel=channel,
            source=source,
            data=data or {},
            expires_at=datetime.now(timezone.utc) + timedelta(hours=self.config.retention_hours),
        )

        self._notifications[notification.id] = notification
        t0 = time.perf_counter()
        self.queue.enqueue(notification)
        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.counter("notifications_sent", 1)
        self._metrics.histogram("send_time_ms", elapsed)
        return notification.id

    async def create_notification(
        self,
        title: str,
        message: str,
        notif_type: str = "info",
        priority: str = "normal",
        channel: str = "general",
    ) -> str:
        """Create (alias for send) a notification."""
        return await self.send_notification(title, message, notif_type, priority, channel)

    async def mark_read(self, notification_id: str) -> bool:
        """Mark a notification as read."""
        notif = self._notifications.get(notification_id)
        if not notif:
            return False
        notif.is_read = True
        self._metrics.counter("notifications_read", 1)
        return True

    async def dismiss(self, notification_id: str) -> bool:
        """Dismiss (remove) a notification."""
        if notification_id in self._notifications:
            del self._notifications[notification_id]
            return True
        return False

    async def dismiss_all(self) -> int:
        """Dismiss all notifications.

        Returns:
            Number dismissed.
        """
        count = 0
        for notif in self._notifications.values():
            if not notif.is_read:
                notif.is_read = True
                count += 1
        return count

    async def register_channel(self, channel: NotificationChannel) -> str:
        """Register a notification channel."""
        self._channels[channel.id] = channel
        return channel.id

    async def get_notifications(
        self,
        channel: Optional[str] = None,
        priority: Optional[str] = None,
        unread_only: bool = False,
        limit: int = 50,
    ) -> List[Notification]:
        """Get notifications with filters.

        Args:
            channel: Optional channel filter.
            priority: Optional priority filter.
            unread_only: Only return unread.
            limit: Max results.

        Returns:
            List of Notification.
        """
        results = list(self._notifications.values())

        if channel:
            results = [n for n in results if n.channel == channel]
        if priority:
            results = [n for n in results if n.priority == priority]
        if unread_only:
            results = [n for n in results if not n.is_read]

        results.sort(key=lambda n: n.timestamp, reverse=True)
        return results[:limit]

    async def render_template(self, template_name: str, variables: Dict[str, Any]) -> Tuple[str, str]:
        """Render a notification template."""
        if not self.template_engine:
            raise RuntimeError("NotificationManagerService not initialized")
        return self.template_engine.render(template_name, variables)

    async def register_template(
        self,
        template_or_name: NotificationTemplate | str,
        title_template: Optional[str] = None,
        message_template: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Register a notification template.

        Accepts either a NotificationTemplate object or individual args
        (name, title_template, message_template).
        """
        if not self.template_engine:
            raise RuntimeError("NotificationManagerService not initialized")
        if isinstance(template_or_name, NotificationTemplate):
            return self.template_engine.register_template(template_or_name)
        import uuid
        template = NotificationTemplate(
            id=uuid.uuid4().hex[:12],
            name=template_or_name,
            title_template=title_template or "",
            message_template=message_template or "",
            **kwargs,
        )
        return self.template_engine.register_template(template)

    async def health(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        pending = self.queue.get_pending_count() if self.queue else 0
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service_name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
            "pending_notifications": pending,
        }

    async def stats(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        total = len(self._notifications)
        unread = sum(1 for n in self._notifications.values() if not n.is_read)
        templates = self.template_engine.get_template_count() if self.template_engine else 0
        channels = len(self._channels)
        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            "total_notifications": total,
            "unread_notifications": unread,
            "registered_templates": templates,
            "channels": channels,
            "metrics": self._metrics.snapshot(),
        }
