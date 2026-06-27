"""
AND9 — Reminder Actions (Phase 9 of Refactor + Phase G/H/I).

Stores reminders with optional persistence via EventSystem.
Supports both relative (after 10 minutes) and absolute
(7 pm meeting) time formats.

Also handles reminder management commands (list, delete, pause,
resume, snooze, clear_all, show_completed) with session memory
for context tracking and input validation.

The reminder is persisted to the EventSystem for cross-session
retention. Label cleanup strips time-related noise words.
"""
import logging
import re
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional, Any

logger = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")


# ── Reminder Management Helpers ──────────────────────────────────


def _title_from_reminder(r: dict) -> str:
    """Format a reminder for display."""
    rid = r.get("id", "?")
    title = r.get("title", "(no title)")
    trigger = r.get("trigger_time", "")[:16] if r.get("trigger_time") else ""
    status = r.get("status", "unknown")
    return f"  #{rid} {title} ({trigger}) [{status}]"


def _format_reminder_list(reminders: list[dict], heading: str) -> str:
    """Format a list of reminders into a response string."""
    if not reminders:
        return f"{heading} — Koi reminder nahi hai. 😴"
    lines = [heading]
    for r in reminders:
        lines.append(_title_from_reminder(r))
    lines.append(f"\nTotal: {len(reminders)}")
    return "\n".join(lines)


# ── Session Memory (Phase H) ─────────────────────────────────────

# In-memory context: user_id -> {"last_reminder_id": int, "last_intent": str}
_active_reminder_context: dict[str, dict] = {}


def _get_context(user_id: str = "default") -> dict:
    """Get or create session context for a user."""
    if user_id not in _active_reminder_context:
        _active_reminder_context[user_id] = {}
    return _active_reminder_context[user_id]


def _set_context(user_id: str, key: str, value: Any) -> None:
    """Set a session context value."""
    ctx = _get_context(user_id)
    ctx[key] = value


def _clear_context(user_id: str) -> None:
    """Clear session context for a user."""
    _active_reminder_context.pop(user_id, None)


# ── Input Validation (Phase I) ──────────────────────────────────


def _validate_reminder_id(reminder_id: Any) -> Optional[int]:
    """Validate and parse a reminder ID."""
    if reminder_id is None:
        return None
    try:
        return int(reminder_id)
    except (ValueError, TypeError):
        return None


def _resolve_reminder_id(reminder_id: Any, user_id: str = "default") -> Optional[int]:
    """Resolve a reminder ID, falling back to session context if not provided."""
    rid = _validate_reminder_id(reminder_id)
    if rid is not None:
        # Save to context
        _set_context(user_id, "last_reminder_id", rid)
        return rid
    # Try from context
    ctx = _get_context(user_id)
    return ctx.get("last_reminder_id")


# ── Core: Set Reminder ──────────────────────────────────────────


def execute_set_reminder(trigger_at: dict,
                         label: str = "AND9 Reminder",
                         repeat_rule: str = "",
                         repeat_days: Optional[list[int]] = None,
                         repeat_end: Optional[str] = None,
                         events_sys: Optional[Any] = None) -> dict:
    """Set a reminder with optional EventSystem persistence.

    Args:
        trigger_at: Dict with time info:
            - type "absolute": {"type": "absolute", "hour": N, "minute": N}
            - type "relative": {"type": "relative", "seconds": N}
        label: Reminder title/label.
        events_sys: Optional EventSystem for persistent storage.

    Returns:
        Dict with response, action, payload.
    """
    if not trigger_at or "type" not in trigger_at:
        if label and label != "AND9 Reminder":
            return {
                "response": f"'{label}' — Kab yaad dilana hai? Time batao! ⏰",
                "action": "SET_REMINDER",
                "payload": {"label": label},
            }
        return {
            "response": "Kya aur kab yaad dilana hai? Jaise 'remind me after 10 minutes meeting' ⏰",
            "action": "SET_REMINDER",
            "payload": {},
        }

    now = datetime.now(IST)
    reminder_time = None

    if trigger_at["type"] == "absolute":
        hour = trigger_at.get("hour") or 0
        minute = trigger_at.get("minute") or 0
        reminder_time = now.replace(
            hour=hour,
            minute=minute,
            second=0, microsecond=0,
        )
        if reminder_time < now:
            reminder_time += timedelta(days=1)

    elif trigger_at["type"] == "relative":
        seconds = trigger_at.get("seconds")
        if not seconds:
            return {
                "response": "Reminder ka time samajh nahi aaya. Seconds missing. ⏰",
                "action": "SET_REMINDER",
                "payload": {},
            }
        reminder_time = now + timedelta(seconds=seconds)

    # Phase I: Validate trigger time
    if reminder_time and reminder_time <= now:
        reminder_time += timedelta(seconds=10)  # ensure at least 10s in future

    # Persist via EventSystem if available
    persisted = False
    if events_sys and reminder_time:
        try:
            events_sys.add_event(
                title=label,
                event_time=reminder_time.isoformat(),
                notes=f"Reminder: {label}",
            )
            persisted = True
            _set_context("default", "last_reminder_id", None)  # context for new reminder
        except Exception as e:
            logger.error("Failed to persist reminder: %s", e)

    # Also persist to the worker-polled SQLite DB for guaranteed firing
    if reminder_time:
        try:
            from backend.services.reminder import storage as reminder_storage
            repeat_days_payload = json.dumps(repeat_days) if repeat_days else None
            rid = reminder_storage.add(
                title=label,
                trigger_time=reminder_time,
                repeat_rule=repeat_rule or "",
                repeat_days=repeat_days_payload,
                repeat_end=repeat_end,
            )
            _set_context("default", "last_reminder_id", rid)
        except Exception as e:
            logger.error("Failed to persist reminder to worker storage: %s", e)

    if label and label != "AND9 Reminder":
        return {
            "response": f"Reminder set kar diya! '{label}' ke liye ⏰",
            "action": "SET_REMINDER",
                "payload": {
                    "trigger_at": trigger_at,
                    "label": label,
                    "repeat_rule": repeat_rule,
                    "repeat_days": repeat_days,
                    "persisted": persisted,
                },
            }

    return {
        "response": "Reminder set kar diya! Par kya yaad dilana hai? ⏰",
        "action": "SET_REMINDER",
        "payload": {
            "trigger_at": trigger_at,
            "label": "",
            "repeat_rule": repeat_rule,
            "repeat_days": repeat_days,
        },
    }


# ── Phase G: Reminder Management Handlers ────────────────────────


def execute_list_reminders(**kwargs) -> dict:
    """List all active (pending/paused) reminders."""
    try:
        from backend.services.reminder import storage as s
        active = s.get_active(user_id=kwargs.get("user_id", "default"))
        response = _format_reminder_list(active, "📋 Active Reminders:")
        return {
            "response": response,
            "action": "LIST_REMINDERS",
            "payload": {"reminders": active, "count": len(active)},
        }
    except Exception as e:
        logger.error("List reminders failed: %s", e)
        return {
            "response": "Reminders load nahi ho paaye. 🚫",
            "action": "LIST_REMINDERS",
            "payload": {"error": str(e)},
        }


def execute_show_completed(**kwargs) -> dict:
    """Show recently fired/completed reminders."""
    try:
        from backend.services.reminder import storage as s
        completed = s.get_completed(user_id=kwargs.get("user_id", "default"), limit=10)
        response = _format_reminder_list(completed, "✅ Completed Reminders:")
        return {
            "response": response,
            "action": "SHOW_COMPLETED_REMINDERS",
            "payload": {"reminders": completed, "count": len(completed)},
        }
    except Exception as e:
        logger.error("Show completed reminders failed: %s", e)
        return {
            "response": "Completed reminders load nahi ho paaye. 🚫",
            "action": "SHOW_COMPLETED_REMINDERS",
            "payload": {"error": str(e)},
        }


def execute_delete_reminder(reminder_id: Any = None, **kwargs) -> dict:
    """Delete/cancel a reminder by ID."""
    rid = _resolve_reminder_id(reminder_id)
    if rid is None:
        return {
            "response": "Kaun sa reminder delete karna hai? Reminder ID batao. 🗑️\nReminders dekhne ke liye 'reminder list' bolo.",
            "action": "DELETE_REMINDER",
            "payload": {},
        }
    try:
        from backend.services.reminder import storage as s
        ok = s.cancel(rid)
        if ok:
            _set_context("default", "last_reminder_id", rid)
            return {
                "response": f"Reminder #{rid} delete kar diya! 🗑️",
                "action": "DELETE_REMINDER",
                "payload": {"reminder_id": rid, "cancelled": True},
            }
        return {
            "response": f"Reminder #{rid} nahi mila. Ho sakta hai pehle hi delete/fire ho chuka ho. 🚫",
            "action": "DELETE_REMINDER",
            "payload": {"reminder_id": rid, "cancelled": False},
        }
    except Exception as e:
        logger.error("Delete reminder failed: %s", e)
        return {
            "response": f"Reminder #{rid} delete karne mein error: {e} 🚫",
            "action": "DELETE_REMINDER",
            "payload": {"error": str(e)},
        }


def execute_pause_reminder(reminder_id: Any = None, **kwargs) -> dict:
    """Pause a reminder by ID."""
    rid = _resolve_reminder_id(reminder_id)
    if rid is None:
        return {
            "response": "Kaun sa reminder pause karna hai? Reminder ID batao. ⏸️",
            "action": "PAUSE_REMINDER",
            "payload": {},
        }
    try:
        from backend.services.reminder import storage as s
        ok = s.pause(rid)
        if ok:
            return {
                "response": f"Reminder #{rid} pause kar diya! ⏸️",
                "action": "PAUSE_REMINDER",
                "payload": {"reminder_id": rid, "paused": True},
            }
        return {
            "response": f"Reminder #{rid} pause nahi ho paaya. Sirf pending reminders pause ho sakte hain. 🚫",
            "action": "PAUSE_REMINDER",
            "payload": {"reminder_id": rid, "paused": False},
        }
    except Exception as e:
        logger.error("Pause reminder failed: %s", e)
        return {
            "response": f"Reminder #{rid} pause karne mein error: {e} 🚫",
            "action": "PAUSE_REMINDER",
            "payload": {"error": str(e)},
        }


def execute_resume_reminder(reminder_id: Any = None, **kwargs) -> dict:
    """Resume a paused reminder by ID."""
    rid = _resolve_reminder_id(reminder_id)
    if rid is None:
        return {
            "response": "Kaun sa reminder resume karna hai? Reminder ID batao. ▶️",
            "action": "RESUME_REMINDER",
            "payload": {},
        }
    try:
        from backend.services.reminder import storage as s
        ok = s.resume(rid)
        if ok:
            return {
                "response": f"Reminder #{rid} resume kar diya! ▶️",
                "action": "RESUME_REMINDER",
                "payload": {"reminder_id": rid, "resumed": True},
            }
        return {
            "response": f"Reminder #{rid} resume nahi ho paaya. Sirf paused reminders resume ho sakte hain. 🚫",
            "action": "RESUME_REMINDER",
            "payload": {"reminder_id": rid, "resumed": False},
        }
    except Exception as e:
        logger.error("Resume reminder failed: %s", e)
        return {
            "response": f"Reminder #{rid} resume karne mein error: {e} 🚫",
            "action": "RESUME_REMINDER",
            "payload": {"error": str(e)},
        }


def execute_snooze_reminder(reminder_id: Any = None, minutes: int = 5, **kwargs) -> dict:
    """Snooze a reminder by ID for N minutes."""
    rid = _resolve_reminder_id(reminder_id)
    if rid is None:
        # If no ID, try to snooze the last active reminder
        try:
            from backend.services.reminder import storage as s
            due = s.get_due()
            if due:
                # Snooze the first due reminder
                rid = due[0]["id"]
                minutes = max(1, int(minutes))
                ok = s.snooze(rid, minutes)
                if ok:
                    return {
                        "response": f"Reminder #{rid} ko {minutes} minute ke liye snooze kar diya! 😴⏰",
                        "action": "SNOOZE_REMINDER",
                        "payload": {"reminder_id": rid, "minutes": minutes},
                    }
        except Exception as e:
            logger.error("Snooze fallback failed: %s", e)
        return {
            "response": "Kaun sa reminder snooze karna hai? Reminder ID batao. 😴",
            "action": "SNOOZE_REMINDER",
            "payload": {},
        }
    try:
        from backend.services.reminder import storage as s
        minutes = max(1, int(minutes) if minutes else 5)
        ok = s.snooze(rid, minutes)
        if ok:
            return {
                "response": f"Reminder #{rid} ko {minutes} minute ke liye snooze kar diya! 😴⏰",
                "action": "SNOOZE_REMINDER",
                "payload": {"reminder_id": rid, "minutes": minutes},
            }
        return {
            "response": f"Reminder #{rid} snooze nahi ho paaya. 🚫",
            "action": "SNOOZE_REMINDER",
            "payload": {"reminder_id": rid, "snoozed": False},
        }
    except Exception as e:
        logger.error("Snooze reminder failed: %s", e)
        return {
            "response": f"Reminder #{rid} snooze karne mein error: {e} 🚫",
            "action": "SNOOZE_REMINDER",
            "payload": {"error": str(e)},
        }


def execute_clear_all_reminders(**kwargs) -> dict:
    """Cancel all pending/snoozed reminders."""
    try:
        from backend.services.reminder import storage as s
        count = s.clear_all(user_id=kwargs.get("user_id", "default"))
        if count > 0:
            return {
                "response": f"Saare {count} reminders clear kar diye! 🧹✨",
                "action": "CLEAR_ALL_REMINDERS",
                "payload": {"cleared_count": count},
            }
        return {
            "response": "Clear karne ke liye koi reminder nahi hai. 😴",
            "action": "CLEAR_ALL_REMINDERS",
            "payload": {"cleared_count": 0},
        }
    except Exception as e:
        logger.error("Clear all reminders failed: %s", e)
        return {
            "response": "Reminders clear karne mein error. 🚫",
            "action": "CLEAR_ALL_REMINDERS",
            "payload": {"error": str(e)},
        }
