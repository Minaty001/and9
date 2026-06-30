# Phase 30: Notification Manager

## Overview

Manages push notifications, in-app messages, and toast alerts. Provides a priority queue, notification templates, and channel-based routing.

## Architecture

```
Services / System Events
          │
          ▼
┌─────────────────────┐
│ NotificationManager  │  ◄── Create, send, dismiss notifications
│                      │
│  ┌───────────────┐   │
│  │  Priority Queue│   │  Ordered: critical > high > normal > low
│  └───────────────┘   │
│  ┌───────────────┐   │
│  │Template Engine │   │  Variable substitution for notifications
│  └───────────────┘   │
│  ┌───────────────┐   │
│  │   Channels     │   │  in-app, push, toast, log
│  └───────────────┘   │
└─────────┬───────────┘
          │
          ▼
    User / Device Notifications
```

## Components

- **NotificationQueue**: Priority-based queue with critical > high > normal > low ordering
- **TemplateEngine**: Registers templates with variable placeholders for rendering
- **NotificationManagerService**: ServiceBase wrapper

## Usage

```python
from services.phase30_notification import (
    NotificationManagerService,
    NotificationTemplate,
)
svc = NotificationManagerService()
await svc.initialize()

# Send notification
await svc.send_notification("info", "Hello", "This is a message")

# Register template and render
template = NotificationTemplate(
    id="1", name="welcome",
    title_template="Welcome {name}",
    message_template="Hello {name}!",
    variables=["name"],
)
await svc.register_template(template)
title, msg = await svc.render_template("welcome", {"name": "User"})
```
