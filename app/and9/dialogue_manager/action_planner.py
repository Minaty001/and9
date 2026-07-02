"""
AND9 — Action Planner.

Validates filled slots, builds execution plans, and gates execution
until all required information is available.

Core rules:
  - NEVER execute until all required slots are filled
  - Validate slot values before planning execution
  - Build execution payloads compatible with the AND9 Android Executor
  - Provide clear error messages on validation failures
  - Support recovery by identifying which slots need correction

Execution flow:
  1. Check all required slots filled → if not, return (wait more)
  2. Validate slot values → if invalid, return error with guidance
  3. Build action payload → map slots to Android executor params
  4. Return ExecutionPlan with action type and payload
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from app.and9.dialogue_manager.intent_definitions import (
    get_intent_definition,
    IntentDefinition,
)
from app.and9.dialogue_manager.state_manager import TaskState, TaskStatus

logger = logging.getLogger(__name__)


@dataclass
class ExecutionPlan:
    """A validated execution plan ready for the AND9 Android Executor.

    Attributes:
        can_execute: Whether all conditions for execution are met.
        intent: The intent to execute.
        action_type: The AND9 action type string.
        params: Parameters dict for the action handler.
        payload: Android Intent payload.
        errors: List of validation errors (empty if can_execute=True).
        warnings: List of non-blocking warnings.
        success_message: Message to show on successful execution.
        failure_message: Message to show on execution failure.
        metadata: Additional execution metadata.
    """
    can_execute: bool = False
    intent: str = ""
    action_type: Optional[str] = None
    params: dict[str, Any] = field(default_factory=dict)
    payload: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    success_message: str = "Done! ✅"
    failure_message: str = "Kuch gadbad ho gayi! 😅"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "can_execute": self.can_execute,
            "intent": self.intent,
            "action_type": self.action_type,
            "params": self.params,
            "payload": self.payload,
            "errors": self.errors,
            "warnings": self.warnings,
            "success_message": self.success_message,
            "failure_message": self.failure_message,
        }


# ── Intent-to-Action Mapping ──────────────────────────────────────
# Maps intent names to AND9 action types and defines how to translate
# filled slots into action parameters.

_INTENT_ACTION_MAP = {
    "youtube": {
        "action": "youtube_search",
        "slot_map": {
            "search_query": "query",
        },
        "template": {
            "action": "search",
        },
    },
    "music": {
        "action": "youtube_play",
        "slot_map": {
            "song_name": "query",
        },
        "template": {},
    },
    "open_app": {
        "action": "open_app",
        "slot_map": {
            "app_name": "app_name",
        },
        "template": {},
    },
    "call": {
        "action": "call",
        "slot_map": {
            "contact_name": "contact_name",
            "number": "number",
        },
        "template": {},
    },
    "message": {
        "action": "send_sms",
        "slot_map": {
            "contact_name": "contact_name",
            "message_text": "message",
        },
        "template": {},
    },
    "alarm": {
        "action": "set_alarm",
        "slot_map": {
            "hour": "hour",
            "minute": "minute",
            "label": "label",
        },
        "template": {},
    },
    "timer": {
        "action": "set_timer",
        "slot_map": {
            "duration_seconds": "duration_seconds",
            "label": "label",
        },
        "template": {},
    },
    "reminder": {
        "action": "set_reminder",
        "slot_map": {
            "label": "label",
            "trigger_at": "trigger_at",
        },
        "template": {},
    },
    "search": {
        "action": "search",
        "slot_map": {
            "query": "query",
        },
        "template": {},
    },
    "flashlight": {
        "action": "flashlight",
        "slot_map": {
            "state": "state",
        },
        "template": {},
    },
    "volume": {
        "action": "volume_up",  # Default; will be refined
        "slot_map": {
            "action": "action",
        },
        "template": {},
    },
    "wifi": {
        "action": "wifi",
        "slot_map": {
            "state": "state",
        },
        "template": {},
    },
    "bluetooth": {
        "action": "bluetooth",
        "slot_map": {
            "state": "state",
        },
        "template": {},
    },
}

# Volume action mapping
_VOLUME_ACTION_MAP = {
    "up": "volume_up",
    "down": "volume_down",
    "mute": "volume_mute",
    "max": "volume_max",
}


class ActionPlanner:
    """Validates and plans action execution from dialogue task state.

    Acts as a gating layer — no execution happens unless all
    requirements are met.
    """

    def __init__(self):
        pass

    def can_execute(self, task_state: TaskState) -> tuple[bool, list[str]]:
        """Check if a task is ready for execution.

        Args:
            task_state: The task to check.

        Returns:
            Tuple of (can_execute, list_of_errors).
            If can_execute is True, errors is empty.
        """
        errors = []

        # Rule 1: All required slots must be filled
        if task_state.missing_slots:
            errors.append(f"Missing required slots: {', '.join(task_state.missing_slots)}")

        # Rule 2: Status must be appropriate
        if task_state.status == TaskStatus.PAUSED:
            errors.append("Task is paused — resume it first")
        if task_state.status == TaskStatus.CANCELLED:
            errors.append("Task was cancelled")
        if task_state.status == TaskStatus.COMPLETED:
            errors.append("Task is already completed")

        # Rule 3: Must have a known intent
        if not task_state.intent:
            errors.append("No intent detected")

        return (len(errors) == 0, errors)

    def validate_slots(self, task_state: TaskState) -> tuple[bool, list[str]]:
        """Validate the values of all filled slots.

        Uses the validation functions defined in the intent definitions.

        Args:
            task_state: The task to validate.

        Returns:
            Tuple of (all_valid, list_of_error_messages).
        """
        intent_def = get_intent_definition(task_state.intent)
        if not intent_def:
            return True, []  # No definition → skip validation

        errors = []
        for slot_def in intent_def.required_slots + intent_def.optional_slots:
            if slot_def.name in task_state.filled_slots and slot_def.validation_fn:
                value = task_state.filled_slots[slot_def.name]
                try:
                    is_valid, error_msg = slot_def.validation_fn(str(value))
                    if not is_valid:
                        errors.append(f"{slot_def.name}: {error_msg}")
                except Exception as e:
                    errors.append(f"{slot_def.name}: validation error: {e}")

        return (len(errors) == 0, errors)

    def plan(self, task_state: TaskState) -> ExecutionPlan:
        """Create an execution plan from a task state.

        Validates everything and builds the action payload.

        Args:
            task_state: The task to plan execution for.

        Returns:
            An ExecutionPlan with all validation results.
        """
        # Check basic execution readiness
        can_exec, exec_errors = self.can_execute(task_state)
        if not can_exec:
            return ExecutionPlan(
                can_execute=False,
                intent=task_state.intent,
                errors=exec_errors,
            )

        # Validate slot values
        slots_valid, slot_errors = self.validate_slots(task_state)
        if not slots_valid:
            return ExecutionPlan(
                can_execute=False,
                intent=task_state.intent,
                errors=slot_errors,
            )

        # Build action payload
        action_info = _INTENT_ACTION_MAP.get(task_state.intent)
        if not action_info:
            return ExecutionPlan(
                can_execute=False,
                intent=task_state.intent,
                errors=[f"No action mapping for intent '{task_state.intent}'"],
            )

        # Map filled slots to action parameters
        params = {}
        action_type = action_info["action"]
        for slot_name, param_name in action_info["slot_map"].items():
            if slot_name in task_state.filled_slots:
                params[param_name] = task_state.filled_slots[slot_name]

        # Add template defaults
        for key, value in action_info["template"].items():
            if key not in params:
                params[key] = value

        # Special handling for volume intent
        if task_state.intent == "volume":
            vol_action = task_state.filled_slots.get("action", "up")
            action_type = _VOLUME_ACTION_MAP.get(vol_action.lower(), "volume_up")

        # Build success and failure messages
        intent_def = get_intent_definition(task_state.intent)
        success_msg = intent_def.success_message if intent_def else "Done! ✅"
        failure_msg = intent_def.failure_message if intent_def else "Failed! 😅"

        # Try to format messages with slot values
        try:
            success_msg = success_msg.format(**task_state.filled_slots)
        except (KeyError, ValueError):
            pass
        try:
            failure_msg = failure_msg.format(**task_state.filled_slots)
        except (KeyError, ValueError):
            pass

        # Build Android-compatible payload
        payload = self._build_payload(action_type, params)

        return ExecutionPlan(
            can_execute=True,
            intent=task_state.intent,
            action_type=action_type,
            params=params,
            payload=payload,
            errors=[],
            success_message=success_msg,
            failure_message=failure_msg,
            metadata={
                "task_id": task_state.task_id,
                "filled_slots": dict(task_state.filled_slots),
            },
        )

    def _build_payload(self, action_type: str,
                       params: dict[str, Any]) -> dict[str, Any]:
        """Build an Android-compatible payload dict.

        Args:
            action_type: The AND9 action type.
            params: The action parameters.

        Returns:
            A payload dict compatible with the Android Executor.
        """
        # Basic payload structure matches what android_executor.py expects
        payload = {
            "action": action_type,
            "params": params,
        }

        # Add specific intent extras for Android
        if action_type == "open_app" and "app_name" in params:
            payload["intent"] = {
                "action": "android.intent.action.MAIN",
                "extras": {"app_name": params["app_name"]},
            }
        elif action_type == "call" and "number" in params:
            payload["intent"] = {
                "action": "android.intent.action.CALL",
                "data": f"tel:{params['number']}",
            }
        elif action_type == "youtube_search" and "query" in params:
            payload["intent"] = {
                "action": "android.intent.action.VIEW",
                "package": "com.google.android.youtube",
                "data": f"https://www.youtube.com/results?search_query={params['query']}",
            }
        elif action_type == "youtube_play" and "query" in params:
            payload["intent"] = {
                "action": "android.intent.action.VIEW",
                "package": "com.google.android.youtube",
                "data": f"https://www.youtube.com/results?search_query={params['query']}",
            }

        return payload
