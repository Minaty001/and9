"""AND9 — Intent Action Handlers.

Each module implements a specific device action (call, alarm, timer, etc.)
as pure functions that return Android intent payloads.
"""

from .action_verifier import verify_action
from .alarm_actions import execute_set_alarm
from .app_actions import execute_open_app, execute_close_app
from .call_actions import execute_call, execute_message
from .device_actions import (
    handle_flashlight,
    handle_volume,
    handle_wifi,
    handle_bluetooth,
    handle_airplane_mode,
    handle_home,
    handle_camera,
    handle_search,
    handle_clipboard,
    handle_media_control,
    handle_screen_state,
    handle_notification_read,
)
from .reminder_actions import (
    execute_set_reminder,
    execute_list_reminders,
    execute_delete_reminder,
    execute_pause_reminder,
    execute_resume_reminder,
    execute_snooze_reminder,
    execute_clear_all_reminders,
    execute_show_completed,
)
from .timer_actions import execute_set_timer
from .time_actions import handle_get_time
from .youtube_actions import execute_youtube_search, execute_youtube_play

__all__ = [
    "verify_action",
    "execute_set_alarm",
    "execute_open_app",
    "execute_close_app",
    "execute_call",
    "execute_message",
    "handle_flashlight",
    "handle_volume",
    "handle_wifi",
    "handle_bluetooth",
    "handle_airplane_mode",
    "handle_home",
    "handle_camera",
    "handle_search",
    "handle_clipboard",
    "handle_media_control",
    "handle_screen_state",
    "handle_notification_read",
    "execute_set_reminder",
    "execute_list_reminders",
    "execute_delete_reminder",
    "execute_pause_reminder",
    "execute_resume_reminder",
    "execute_snooze_reminder",
    "execute_clear_all_reminders",
    "execute_show_completed",
    "execute_set_timer",
    "handle_get_time",
    "execute_youtube_search",
    "execute_youtube_play",
]
