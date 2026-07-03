"""
AND9 — Task Manager.

Orchestrates multiple active dialogue tasks. Supports:

  - Creating and switching between tasks
  - Task prioritization
  - Pausing/resuming all tasks (interruption scenarios)
  - Garbage collection of old completed tasks
  - Finding the next actionable task

The TaskManager wraps DialogueStateTracker and adds higher-level
coordination logic.
"""

import logging
from typing import Optional

from app.dialogue_manager.state_manager import (
    DialogueStateTracker,
    TaskState,
    TaskStatus,
)

logger = logging.getLogger(__name__)

# Priority ranking for intents (lower number = higher priority)
_INTENT_PRIORITY = {
    "emergency": 1,
    "call": 2,
    "message": 3,
    "alarm": 4,
    "timer": 5,
    "reminder": 6,
    "open_app": 7,
    "youtube": 8,
    "music": 9,
    "flashlight": 10,
    "volume": 11,
    "wifi": 12,
    "bluetooth": 13,
    "search": 14,
    "chat": 15,
}


class TaskManager:
    """High-level task orchestration.

    Manages the lifecycle and coordination of all active dialogue tasks.
    """

    def __init__(self, state_tracker: DialogueStateTracker):
        self.tracker = state_tracker

    def create_and_activate(self, intent: str,
                            required_slots: list[str],
                            optional_slots: list[str] | None = None,
                            parent_task_id: str | None = None) -> TaskState:
        """Create a new task and make it active.

        Args:
            intent: Intent name.
            required_slots: Required slot names.
            optional_slots: Optional slot names.
            parent_task_id: Optional parent task for interruption linking.

        Returns:
            The newly created TaskState.
        """
        return self.tracker.create_task(
            intent=intent,
            required_slots=required_slots,
            optional_slots=optional_slots or [],
            parent_task_id=parent_task_id,
        )

    def switch_to_task(self, task_id: str) -> bool:
        """Switch the active task to a different one.

        Args:
            task_id: Task to make active.

        Returns:
            True if the switch succeeded.
        """
        task = self.tracker.get_task(task_id)
        if not task:
            return False

        # Pause the current active task if it's still in progress
        current_active = self.tracker.get_active_task()
        if current_active and current_active.task_id != task_id:
            if current_active.is_active and current_active.status not in (
                TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.FAILED
            ):
                self.tracker.pause_task(current_active.task_id)
                logger.info("Paused task %s while switching to %s",
                            current_active.task_id, task_id)

        return self.tracker.set_active_task(task_id)

    def get_next_actionable_task(self) -> Optional[TaskState]:
        """Get the highest-priority task that is ready to execute.

        Scans all active tasks for one that is READY_TO_EXECUTE.
        Returns the one with highest priority (lowest priority number).

        Returns:
            TaskState that is ready, or None.
        """
        active = self.tracker.get_active_tasks()
        ready = [t for t in active if t.status == TaskStatus.READY_TO_EXECUTE]
        if not ready:
            return None

        # Sort by intent priority, then by creation time (oldest first)
        ready.sort(key=lambda t: (_INTENT_PRIORITY.get(t.intent, 99), t.created_at))
        return ready[0]

    def handle_interruption(self, current_message: str,
                            new_intent: str) -> tuple[Optional[TaskState], Optional[TaskState]]:
        """Handle an interruption where the user switches to a new task.

        Args:
            current_message: The user's message.
            new_intent: The newly detected intent.

        Returns:
            Tuple of (paused_task, new_task).
            paused_task is the task that was interrupted (or None).
            new_task is the newly created task for the interruption (or None).
        """
        active_task = self.tracker.get_active_task()

        # If there's an active task that's in-progress, pause it
        paused_task = None
        if active_task and active_task.is_active and active_task.status not in (
            TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.FAILED
        ):
            self.tracker.pause_task(active_task.task_id)
            paused_task = active_task
            logger.info("Interruption: paused task %s for new intent '%s'",
                        active_task.task_id, new_intent)

        return paused_task, None

    def handle_resume(self, message: str) -> Optional[TaskState]:
        """Handle a resume request from the user.

        Args:
            message: The user's message (checked for resume keywords).

        Returns:
            The resumed TaskState, or None if no resume occurred.
        """
        task = self.tracker.find_task_for_resume(message)
        if task:
            self.tracker.resume_task(task.task_id)
            logger.info("Resumed task %s (intent=%s)", task.task_id, task.intent)
            return task
        return None

    def cancel_current_task(self) -> Optional[TaskState]:
        """Cancel the currently active task.

        Returns:
            The cancelled task, or None if no active task.
        """
        active = self.tracker.get_active_task()
        if active and active.is_active:
            self.tracker.mark_cancelled(active.task_id)
            # Switch to the next paused task if any
            paused = self.tracker.get_paused_tasks()
            if paused:
                self.tracker.resume_task(paused[-1].task_id)
            return active
        return None

    def complete_and_continue(self, task_id: str,
                              completion_status: str = "success") -> Optional[TaskState]:
        """Complete a task and resume the next paused task if any.

        Args:
            task_id: Task to mark as completed.
            completion_status: Status string (default "success").

        Returns:
            The next task that was resumed, or None.
        """
        self.tracker.mark_completed(task_id, completion_status)

        # Check if this task has linked interrupted tasks or parent
        task = self.tracker.get_task(task_id)
        next_task = None
        if task:
            # Try to resume the parent task (the one that was interrupted)
            if task.parent_task_id:
                parent = self.tracker.get_task(task.parent_task_id)
                if parent and parent.status == TaskStatus.PAUSED:
                    self.tracker.resume_task(parent.task_id)
                    next_task = parent

        if not next_task:
            # Resume any other paused task
            paused = self.tracker.get_paused_tasks()
            if paused:
                self.tracker.resume_task(paused[-1].task_id)
                next_task = paused[-1]

        return next_task

    def pause_all_active(self) -> int:
        """Pause all active (non-terminal) tasks.

        Returns:
            Number of tasks paused.
        """
        count = 0
        active = self.tracker.get_active_tasks()
        for task in active:
            if task.status not in (TaskStatus.PAUSED, TaskStatus.COMPLETED,
                                    TaskStatus.CANCELLED, TaskStatus.FAILED):
                self.tracker.pause_task(task.task_id)
                count += 1
        return count

    def resume_most_recent_paused(self) -> Optional[TaskState]:
        """Resume the most recently paused task.

        Returns:
            The resumed task, or None.
        """
        paused = self.tracker.get_paused_tasks()
        if paused:
            task = paused[-1]
            self.tracker.resume_task(task.task_id)
            return task
        return None

    def get_active_count(self) -> int:
        """Get the number of currently active tasks."""
        return len(self.tracker.get_active_tasks())

    def get_summary(self) -> dict:
        """Get a human-readable summary of all tasks."""
        stats = self.tracker.get_stats()
        active_task = self.tracker.get_active_task()
        return {
            "stats": stats,
            "current_task": active_task.to_dict() if active_task else None,
            "paused_tasks": [
                {
                    "task_id": t.task_id,
                    "intent": t.intent,
                    "missing_slots": t.missing_slots,
                    "waiting_for": t.waiting_for,
                }
                for t in self.tracker.get_paused_tasks()
            ],
        }
