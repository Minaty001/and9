# Phase 30: Notification Manager

## Purpose
Notification management service supporting push, in-app, and toast alerts with priority-based queuing, template rendering, and channel management. `NotificationManagerService` provides the unified API for sending, reading, dismissing, and querying notifications. `NotificationQueue` implements priority ordering (critical > high > normal > low) with expiration pruning. `TemplateEngine` handles template registration and variable substitution. `NotificationConfig` configures service name, rate limiting, sound/vibration, grouping, and retention.

## Architecture
```
NotificationManagerService
  ├── initialize() / shutdown()
  ├── send_notification(title, message, type, priority, channel) → notification_id
  ├── mark_read(id) / dismiss(id) / dismiss_all()
  ├── get_notifications(channel, priority, unread_only, limit)
  ├── register_channel(channel) / register_template(...)
  ├── render_template(name, variables) → (title, message)
  ├── health() / stats()
  │
  ├── NotificationQueue
  │     ├── enqueue(notification)
  │     ├── dequeue(priority) — critical > high > normal > low
  │     ├── peek() / size() / clear()
  │     └── _prune_expired()
  │
  ├── TemplateEngine
  │     ├── register_template(template) → template_id
  │     ├── render(name, variables) → (title, message)
  │     └── list_templates() / get_template() / delete_template()
  │
  └── Models: Notification, NotificationTemplate, NotificationChannel
```

## Code
```python
class NotificationManagerService:
    async def initialize(self):
        self.queue = NotificationQueue(self.config)
        self.template_engine = TemplateEngine(self.config)

    async def send_notification(self, title, message, notif_type="info", priority="normal", channel="general") -> str:
        notification = Notification(id=uuid.uuid4().hex[:12], type=notif_type, title=title,
                                     message=message, priority=priority, channel=channel)
        self._notifications[notification.id] = notification
        self.queue.enqueue(notification)
        return notification.id

class NotificationQueue:
    def enqueue(self, notification):
        priority = notification.priority if notification.priority in _PRIORITY_ORDER else "normal"
        self._queues[priority].append(notification.id)

    def dequeue(self, priority=None):
        for prio in ["critical", "high", "normal", "low"]:
            queue = self._queues.get(prio, [])
            while queue:
                nid = queue.pop(0)
                notif = self._all_notifications.get(nid)
                if notif and not notif.is_read: return notif
        return None

class TemplateEngine:
    def render(self, template_name, variables):
        template = self._templates.get(template_name)
        title, message = template.title_template, template.message_template
        for var_name, var_value in variables.items():
            title = title.replace("{" + var_name + "}", str(var_value))
            message = message.replace("{" + var_name + "}", str(var_value))
        return title, message
```

## Location
`app/services/notification/` — notification manager service, queue, template engine, models, config
