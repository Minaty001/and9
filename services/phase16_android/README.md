# Phase 16 — Android Controller

Abstract Android actions: app launch, media, notifications, clipboard, volume, brightness, accessibility.

## Components

- **AndroidConfig**: Configuration with permission check, default timeout, supported apps, hardware/notification access flags.
- **AndroidAction**: Pydantic model for an action with type, target, params, timeout, confirmation flag.
- **AndroidActionResult**: Pydantic model for action results with success, message, duration, error.
- **AppLauncher**: Launch apps by name with support checking against a known list (30+ apps).
- **MediaController**: Play, pause, next, previous, volume_up, volume_down.
- **NotificationController**: Send, list recent, clear notifications.
- **ClipboardController**: Get and set clipboard text.
- **HardwareController**: Set/get volume (0-100) and brightness (0-100).
- **AndroidControllerService(ServiceBase)**: Full lifecycle service with unified `execute()` API.

## Usage

```python
from services.phase16_android import AndroidControllerService, AndroidAction

svc = AndroidControllerService()
await svc.initialize()

# Launch an app
result = svc.launch_app("chrome")

# Execute via action object
action = AndroidAction(
    action_type="media_control",
    target="play",
)
result = svc.execute(action)

# Set volume
svc.set_volume(75)
await svc.shutdown()
```

## Configuration

Environment variables with prefix `JARVIS_PHASE16_`:

| Variable | Default | Description |
|---|---|---|
| ENABLE_PERMISSION_CHECK | True | Check permissions before actions |
| DEFAULT_ACTION_TIMEOUT_MS | 5000 | Default action timeout |
| SUPPORTED_APPS | [30+ apps] | List of supported app names |
| ENABLE_HARDWARE_CONTROL | True | Enable volume/brightness control |
| ENABLE_NOTIFICATION_ACCESS | True | Enable notification access |
