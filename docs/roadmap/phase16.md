# Phase 16: Android Controller

## Purpose
Abstracts Android device actions: app launch (30+ apps mapped to package names), media control (play/pause/next/previous), notification management (send/list/clear), clipboard (get/set), and hardware control (volume 0-100, brightness 0-100). Each component supports permission checking and configurable timeouts.

## Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `JARVIS_PHASE16_ENABLE_PERMISSION_CHECK` | true | Check permissions before actions |
| `JARVIS_PHASE16_DEFAULT_ACTION_TIMEOUT_MS` | 5000 | Default timeout |
| `JARVIS_PHASE16_ENABLE_HARDWARE_CONTROL` | true | Enable volume/brightness |
| `JARVIS_PHASE16_ENABLE_NOTIFICATION_ACCESS` | true | Enable notification access |

## Architecture
```
AndroidControllerService
  ├── AppLauncher          — launch_app(name) with support check
  ├── MediaController      — play/pause/next/previous/volume_up/volume_down
  ├── NotificationController — send/list/clear notifications
  ├── ClipboardController  — get/set clipboard text
  └── HardwareController   — set/get volume(0-100) and brightness(0-100)
```

## Code
```python
class AppLauncher:
    SUPPORTED_APPS = {"chrome": "com.android.chrome", "whatsapp": "com.whatsapp", ...}

    def launch_app(self, name: str) -> AndroidActionResult:
        package = self.SUPPORTED_APPS.get(name.lower())
        if not package: return AndroidActionResult(success=False, message="Unsupported app")
        return AndroidActionResult(success=True, message=f"Launching {name}")

class MediaController:
    def play(self) -> AndroidActionResult:
        return self._execute("media_control", "play")

class HardwareController:
    def set_volume(self, level: int):  # 0-100
        return self._execute("hardware", "set_volume", params={"level": level})
```

## Location
`app/skills/android/` — Android device control skill
