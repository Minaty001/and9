"""
Notification Manager Service.

Manages push notifications, in-app messages, toast alerts.
Priority queue, templates, channels.

Components:
    - NotificationQueue: Priority-based notification queue
    - TemplateEngine: Renders notification templates
    - NotificationManagerService: Lifecycle-managed service
"""

from .notification_queue import NotificationQueue
from .template_engine import TemplateEngine
from .service import NotificationManagerService
from .config import NotificationConfig
from .models import Notification, NotificationTemplate, NotificationChannel

__all__ = [
    "NotificationQueue",
    "TemplateEngine",
    "NotificationManagerService",
    "NotificationConfig",
    "Notification",
    "NotificationTemplate",
    "NotificationChannel",
]
