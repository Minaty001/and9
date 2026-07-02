"""
AND9 — Dialogue State Tracker (DST).

Tracks the state of every active conversation task. Each task maintains:

  - Task ID         — Unique identifier
  - Intent          — What the user wants to do
  - Status          — Current lifecycle state
  - Required Slots  — Slots that must be filled
  - Filled Slots    — Values collected so far
  - Missing Slots   — What's still needed
  - Waiting For     — Which slot is being asked about
  - Last Messages   — Most recent user/assistant exchange
  - Timestamps      — Creation and last-updated times
  - Completion      — Whether and how it was completed

Thread-safe: Uses a threading.Lock for all state mutations.
"""

import json
import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Lifecycle states for a dialogue task."""
    PENDING = "pending"                 # Just created, no info collected yet
    WAITING_FOR_INFO = "waiting_for_info"  # Awaiting user input for a slot
    READY_TO_EXECUTE = "ready_to_execute"  # All slots filled, ready to act
    EXECUTING = "executing"             # Action being executed
    COMPLETED = "completed"             # Successfully executed
    PAUSED = "paused"                   # Interrupted by user
    CANCELLED = "cancelled"             # User cancelled the task
    FAILED = "failed"                   # Execution failed

    def __str__(self) -> str:
        return self.value


@dataclass
class TaskState:
    """Complete state of a single dialogue task.

    This is the core data structure that the Dialogue State Tracker
    maintains for every active task.
    """
    task_id: str = ""
    intent: str = ""
    status: TaskStatus = TaskStatus.PENDING
    required_slots: list[str] = field(default_factory=list)
    optional_slots: list[str] = field(default_factory=list)
    filled_slots: dict[str, Any] = field(default_factory=dict)
    waiting_for: Optional[str] = None
    last_user_message: str = ""
    last_assistant_message: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    completion_status: Optional[str] = None
    parent_task_id: Optional[str] = None  # For interruption linking
    linked_tasks: list[str] = field(default_factory=list)  # Tasks created during interruption
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def missing_slots(self) -> list[str]:
        """Dynamically compute missing required slots."""
        filled = set(self.filled_slots.keys())
        return [s for s in self.required_slots if s not in filled]

    @property
    def age_seconds(self) -> float:
        """Age of the task in seconds."""
        return time.time() - self.created_at

    @property
    def is_active(self) -> bool:
        """Whether this task is still active (not completed/cancelled/failed)."""
        return self.status in (
            TaskStatus.PENDING,
            TaskStatus.WAITING_FOR_INFO,
            TaskStatus.READY_TO_EXECUTE,
            TaskStatus.EXECUTING,
            TaskStatus.PAUSED,
        )

    def to_dict(self) -> dict:
        """Serialize to a JSON-safe dict."""
        d = asdict(self)
        d["status"] = self.status.value
        d["missing_slots"] = self.missing_slots
        d["age_seconds"] = self.age_seconds
        d["is_active"] = self.is_active
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "TaskState":
        """Deserialize from a dict."""
        if "status" in data and isinstance(data["status"], str):
            try:
                data["status"] = TaskStatus(data["status"])
            except ValueError:
                data["status"] = TaskStatus.PENDING
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class DialogueStateTracker:
    """Central Dialogue State Tracker.

    Manages all active, paused, and completed tasks. Thread-safe.
    Supports optional file-based persistence for Termux compatibility.
    """

    def __init__(self, persist_path: Optional[str] = None):
        self._lock = threading.RLock()
        self._tasks: dict[str, TaskState] = {}
        self._active_task_id: Optional[str] = None
        self._task_counter: int = 0
        self._persist_path = persist_path

        # Load persisted state if available
        if persist_path and os.path.exists(persist_path):
            self._load()

    # ── Task CRUD ──────────────────────────────────────────────────

    def create_task(self, intent: str,
                    required_slots: Optional[list[str]] = None,
                    optional_slots: Optional[list[str]] = None,
                    parent_task_id: Optional[str] = None) -> TaskState:
        """Create a new task and set it as the active task.

        Args:
            intent: The intent name (e.g., "youtube", "call").
            required_slots: List of required slot names.
            optional_slots: List of optional slot names.
            parent_task_id: Optional parent task ID for interruption linking.

        Returns:
            The newly created TaskState.
        """
        with self._lock:
            self._task_counter += 1
            task_id = f"{intent}_{self._task_counter:04d}_{uuid.uuid4().hex[:6]}"

            task = TaskState(
                task_id=task_id,
                intent=intent,
                status=TaskStatus.PENDING,
                required_slots=required_slots or [],
                optional_slots=optional_slots or [],
                filled_slots={},
                parent_task_id=parent_task_id,
            )
            self._tasks[task_id] = task
            self._active_task_id = task_id
            logger.info("Created task %s: intent=%s slots=%s",
                        task_id, intent, required_slots)
            self._save()
            return task

    def get_task(self, task_id: str) -> Optional[TaskState]:
        """Get a task by ID."""
        with self._lock:
            return self._tasks.get(task_id)

    def get_active_task(self) -> Optional[TaskState]:
        """Get the currently active task."""
        with self._lock:
            if self._active_task_id:
                return self._tasks.get(self._active_task_id)
            return None

    def set_active_task(self, task_id: str) -> bool:
        """Set a specific task as active.

        Args:
            task_id: The task to make active.

        Returns:
            True if the task exists and was set as active.
        """
        with self._lock:
            if task_id in self._tasks:
                self._active_task_id = task_id
                logger.info("Switched active task to %s", task_id)
                return True
            return False

    def get_active_task_id(self) -> Optional[str]:
        """Get the ID of the currently active task."""
        with self._lock:
            return self._active_task_id

    def update_task(self, task_id: str, **fields) -> bool:
        """Update fields on a task.

        Automatically updates 'updated_at' timestamp.

        Args:
            task_id: Task to update.
            **fields: Fields to update (e.g., status=TaskStatus.WAITING_FOR_INFO).

        Returns:
            True if the task was found and updated.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                logger.warning("Task %s not found for update", task_id)
                return False

            for key, value in fields.items():
                if hasattr(task, key):
                    setattr(task, key, value)

            task.updated_at = time.time()
            self._save()
            return True

    def delete_task(self, task_id: str) -> bool:
        """Delete a task completely.

        Args:
            task_id: Task to delete.

        Returns:
            True if the task existed and was deleted.
        """
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                if self._active_task_id == task_id:
                    self._active_task_id = None
                self._save()
                return True
            return False

    # ── Status Transitions ─────────────────────────────────────────

    def mark_waiting(self, task_id: str, waiting_for: str) -> bool:
        """Mark a task as waiting for user input on a specific slot."""
        return self.update_task(
            task_id,
            status=TaskStatus.WAITING_FOR_INFO,
            waiting_for=waiting_for,
        )

    def mark_ready(self, task_id: str) -> bool:
        """Mark a task as ready to execute (all slots filled)."""
        return self.update_task(
            task_id,
            status=TaskStatus.READY_TO_EXECUTE,
            waiting_for=None,
        )

    def mark_executing(self, task_id: str) -> bool:
        """Mark a task as currently being executed."""
        return self.update_task(
            task_id,
            status=TaskStatus.EXECUTING,
        )

    def mark_completed(self, task_id: str,
                       completion_status: Optional[str] = "success") -> bool:
        """Mark a task as completed successfully."""
        return self.update_task(
            task_id,
            status=TaskStatus.COMPLETED,
            completed_at=time.time(),
            completion_status=completion_status,
            waiting_for=None,
        )

    def mark_failed(self, task_id: str,
                    completion_status: Optional[str] = "error") -> bool:
        """Mark a task as failed."""
        return self.update_task(
            task_id,
            status=TaskStatus.FAILED,
            completed_at=time.time(),
            completion_status=completion_status,
        )

    def mark_cancelled(self, task_id: str) -> bool:
        """Mark a task as cancelled by the user."""
        return self.update_task(
            task_id,
            status=TaskStatus.CANCELLED,
            completed_at=time.time(),
            completion_status="cancelled",
            waiting_for=None,
        )

    def pause_task(self, task_id: str) -> bool:
        """Pause a task (user interrupted)."""
        return self.update_task(
            task_id,
            status=TaskStatus.PAUSED,
        )

    def resume_task(self, task_id: str) -> bool:
        """Resume a paused task."""
        task = self.get_task(task_id)
        if not task:
            return False

        # Determine status on resume
        filled_all = len(task.missing_slots) == 0
        new_status = TaskStatus.READY_TO_EXECUTE if filled_all else TaskStatus.WAITING_FOR_INFO

        self.update_task(
            task_id,
            status=new_status,
        )
        self.set_active_task(task_id)
        return True

    # ── Query ──────────────────────────────────────────────────────

    def get_paused_tasks(self) -> list[TaskState]:
        """Get all paused tasks, oldest first."""
        with self._lock:
            return sorted(
                [t for t in self._tasks.values() if t.status == TaskStatus.PAUSED],
                key=lambda t: t.updated_at,
            )

    def get_active_tasks(self) -> list[TaskState]:
        """Get all non-terminal tasks (active, waiting, paused)."""
        with self._lock:
            return [
                t for t in self._tasks.values()
                if t.is_active
            ]

    def get_tasks_by_intent(self, intent: str) -> list[TaskState]:
        """Get all tasks for a given intent, newest first."""
        with self._lock:
            return sorted(
                [t for t in self._tasks.values() if t.intent == intent],
                key=lambda t: t.created_at,
                reverse=True,
            )

    def find_task_for_resume(self, message: str) -> Optional[TaskState]:
        """Find the most recently paused task for resumption.

        Checks keywords in the message to find matching intent.
        """
        message_lower = message.lower()
        paused = self.get_paused_tasks()
        if not paused:
            return None

        # If message contains "continue"/"resume", return most recent paused task
        if any(kw in message_lower for kw in ["continue", "resume", "go on",
                                                "jari rakho", "jaari rakho",
                                                "phir se", "again", "same"]):
            return paused[-1] if paused else None

        # Try to match intent keywords
        intent_keywords = {
            "youtube": ["youtube", "video", "song", "gaana", "music"],
            "call": ["call", "phone", "dial"],
            "message": ["message", "sms", "text", "msg"],
            "alarm": ["alarm"],
            "timer": ["timer"],
            "reminder": ["reminder", "remind"],
        }

        for intent, keywords in intent_keywords.items():
            if any(kw in message_lower for kw in keywords):
                for task in reversed(paused):
                    if task.intent == intent:
                        return task

        return None

    def get_stats(self) -> dict:
        """Get summary statistics."""
        with self._lock:
            all_tasks = list(self._tasks.values())
            active = [t for t in all_tasks if t.is_active]
            completed = [t for t in all_tasks if t.status == TaskStatus.COMPLETED]
            failed = [t for t in all_tasks if t.status == TaskStatus.FAILED]
            cancelled = [t for t in all_tasks if t.status == TaskStatus.CANCELLED]

            return {
                "total_tasks": len(all_tasks),
                "active_tasks": len(active),
                "paused_tasks": len(self.get_paused_tasks()),
                "completed_tasks": len(completed),
                "failed_tasks": len(failed),
                "cancelled_tasks": len(cancelled),
                "current_active_task": self._active_task_id,
                "avg_completion_time_ms": self._avg_completion_time(completed),
            }

    def cleanup_old_tasks(self, max_age_seconds: int = 3600) -> int:
        """Remove completed/failed/cancelled tasks older than max_age.

        Args:
            max_age_seconds: Maximum age in seconds before cleanup.

        Returns:
            Number of tasks removed.
        """
        with self._lock:
            now = time.time()
            to_remove = []
            for task_id, task in self._tasks.items():
                if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                    if task.completed_at and (now - task.completed_at) > max_age_seconds:
                        to_remove.append(task_id)

            for task_id in to_remove:
                del self._tasks[task_id]

            if to_remove:
                logger.info("Cleaned up %d old tasks", len(to_remove))
                self._save()

            return len(to_remove)

    def get_all_tasks(self) -> dict[str, TaskState]:
        """Get all tasks (for API listing)."""
        with self._lock:
            return dict(self._tasks)

    # ── Persistence ────────────────────────────────────────────────

    def _save(self):
        """Persist task states to disk (debounced via the caller)."""
        if not self._persist_path:
            return
        try:
            os.makedirs(os.path.dirname(self._persist_path), exist_ok=True)
            with self._lock:
                data = {
                    "task_counter": self._task_counter,
                    "active_task_id": self._active_task_id,
                    "tasks": {tid: t.to_dict() for tid, t in self._tasks.items()},
                }
            with open(self._persist_path, "w") as f:
                json.dump(data, f, indent=2, default=str, ensure_ascii=False)
        except Exception as e:
            logger.warning("Failed to persist dialogue state: %s", e)

    def _load(self):
        """Load task states from disk."""
        if not self._persist_path or not os.path.exists(self._persist_path):
            return
        try:
            with open(self._persist_path) as f:
                data = json.load(f)
            self._task_counter = data.get("task_counter", 0)
            self._active_task_id = data.get("active_task_id")
            for tid, tdata in data.get("tasks", {}).items():
                self._tasks[tid] = TaskState.from_dict(tdata)
            logger.info("Loaded %d tasks from %s", len(self._tasks), self._persist_path)
        except Exception as e:
            logger.warning("Failed to load dialogue state: %s", e)

    def _avg_completion_time(self, completed_tasks: list[TaskState]) -> float:
        """Calculate average completion time in ms for completed tasks."""
        if not completed_tasks:
            return 0.0
        times = []
        for t in completed_tasks:
            if t.completed_at and t.created_at:
                times.append((t.completed_at - t.created_at) * 1000)
        return sum(times) / len(times) if times else 0.0
