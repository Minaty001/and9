"""
AND9 — Task Queue: Priority-Ordered Task Management for the Orchestrator.

The TaskQueue provides a thread-safe, priority-ordered queue for
managing orchestration tasks. It supports:

  - Enqueue with priority (HIGH, MEDIUM, LOW)
  - Dequeue (FIFO within priority level)
  - Cancel individual or all tasks
  - Status tracking (pending, active, completed, failed, cancelled)
  - Listing all tasks with their state

Architecture:
    TaskPriority (enum)
    OrchestratorTask (dataclass)
    TaskQueue (container)
"""

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class TaskPriority(Enum):
    """Priority levels for orchestration tasks."""
    HIGH = 0
    MEDIUM = 1
    LOW = 2


class TaskStatus(Enum):
    """Lifecycle status of a task."""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


@dataclass
class OrchestratorTask:
    """A single task in the orchestration queue.

    Attributes:
        id: Unique task identifier.
        agent_name: Name of the target agent (or "orchestrator" for compound).
        subtask: The subtask description / input.
        priority: TaskPriority level.
        status: Current lifecycle status.
        context: Optional execution context dict.
        created_at: Timestamp of creation.
        started_at: Timestamp when execution began.
        completed_at: Timestamp when execution finished.
        timeout_s: Maximum execution time in seconds (0 = no timeout).
        retry_count: Current retry attempt number.
        max_retries: Maximum retry attempts before giving up.
        result: The result data once completed.
        error: Error message if failed.
        depends_on: List of task IDs that must complete before this one.
        metadata: Arbitrary metadata dict.
    """
    subtask: str
    agent_name: str = "orchestrator"
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    context: Optional[dict] = None
    timeout_s: float = 0.0
    max_retries: int = 2
    retry_count: int = 0
    depends_on: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    id: str = field(default_factory=lambda: f"task_{uuid.uuid4().hex[:12]}")
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Any = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "agent_name": self.agent_name,
            "subtask": self.subtask[:100],
            "priority": self.priority.name,
            "status": self.status.value,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "depends_on": list(self.depends_on),
            "timeout_s": self.timeout_s,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "has_result": self.result is not None,
            "error": self.error,
        }

    def __repr__(self) -> str:
        return (f"OrchestratorTask(id={self.id[:16]}, "
                f"agent='{self.agent_name}', "
                f"status={self.status.value}, "
                f"prio={self.priority.name})")


class TaskQueue:
    """Thread-safe priority-ordered task queue.

    Internal ordering: HIGH tasks dequeued before MEDIUM before LOW.
    Within the same priority, tasks are dequeued FIFO.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._tasks: dict[str, OrchestratorTask] = {}
        self._pending: list[str] = []   # ordered list of pending task IDs
        self._logger = __import__("logging").getLogger(__name__)

    # ── Mutation ────────────────────────────────────────────────────

    def enqueue(self, task: OrchestratorTask) -> str:
        """Add a task to the queue.

        Args:
            task: The task to enqueue.

        Returns:
            The task ID.
        """
        with self._lock:
            self._tasks[task.id] = task
            self._pending.append(task.id)
            self._logger.debug("Enqueued task '%s' (prio=%s, agent='%s')",
                               task.id[:16], task.priority.name, task.agent_name)
        return task.id

    def enqueue_many(self, tasks: list[OrchestratorTask]) -> list[str]:
        """Add multiple tasks atomically.

        Args:
            tasks: List of tasks to enqueue.

        Returns:
            List of task IDs in insertion order.
        """
        with self._lock:
            ids = []
            for t in tasks:
                self._tasks[t.id] = t
                self._pending.append(t.id)
                ids.append(t.id)
        return ids

    def dequeue(self) -> Optional[OrchestratorTask]:
        """Remove and return the highest-priority pending task.

        Tasks whose dependencies are not yet met are skipped until
        their dependencies resolve.

        Returns:
            The next task, or None if no tasks are available.
        """
        with self._lock:
            # Sort pending by priority (HIGH=0 first), then by creation time
            available = [
                tid for tid in self._pending
                if self._tasks[tid].status == TaskStatus.PENDING
            ]
            if not available:
                return None

            # Check dependencies and priority order
            best = None
            for i, tid in enumerate(available):
                task = self._tasks[tid]
                # Check dependencies
                if not self._dependencies_met(task):
                    continue
                # Pick the highest priority; break ties by order (FIFO)
                if best is None or task.priority.value < best.priority.value:
                    best = task

            if best is None:
                return None

            # Remove from pending list
            actual_id = self._pending.index(best.id)
            self._pending.pop(actual_id)
            best.status = TaskStatus.ACTIVE
            best.started_at = datetime.now().isoformat()
            return best

    def _dependencies_met(self, task: OrchestratorTask) -> bool:
        """Check whether all dependencies of a task are satisfied."""
        for dep_id in task.depends_on:
            dep = self._tasks.get(dep_id)
            if dep is None:
                return False
            if dep.status not in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
                return False
        return True

    def cancel(self, task_id: str) -> bool:
        """Cancel a pending or active task.

        Args:
            task_id: ID of the task to cancel.

        Returns:
            True if cancelled, False if not found or already terminal.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False
            if task.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
                return False
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now().isoformat()
            # Remove from pending if present
            if task_id in self._pending:
                self._pending.remove(task_id)
            self._logger.info("Cancelled task '%s'", task_id[:16])
            return True

    def cancel_all(self) -> int:
        """Cancel all pending and active tasks.

        Returns:
            Number of tasks cancelled.
        """
        with self._lock:
            count = 0
            for tid in list(self._pending):
                self.cancel(tid)
                count += 1
            for tid, task in self._tasks.items():
                if task.status == TaskStatus.ACTIVE:
                    task.status = TaskStatus.CANCELLED
                    task.completed_at = datetime.now().isoformat()
                    count += 1
        return count

    def mark_completed(self, task_id: str, result: Any = None) -> bool:
        """Mark a task as completed.

        Args:
            task_id: ID of the task.
            result: Optional result data.

        Returns:
            True if updated, False if not found.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now().isoformat()
            task.result = result
            return True

    def mark_failed(self, task_id: str, error: str,
                    retry: bool = True) -> bool:
        """Mark a task as failed, optionally scheduling a retry.

        Args:
            task_id: ID of the task.
            error: Error description.
            retry: If True and retry_count < max_retries, re-enqueue.

        Returns:
            True if updated, False if not found.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False

            task.retry_count += 1
            task.error = error

            if retry and task.retry_count <= task.max_retries:
                task.status = TaskStatus.RETRYING
                task.started_at = None
                # Re-enqueue
                self._pending.append(task.id)
                self._logger.info(
                    "Task '%s' retry %d/%d",
                    task_id[:16], task.retry_count, task.max_retries,
                )
            else:
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.now().isoformat()
                self._logger.warning(
                    "Task '%s' failed after %d retries: %s",
                    task_id[:16], task.retry_count, error,
                )
            return True

    # ── Queries ─────────────────────────────────────────────────────

    def get(self, task_id: str) -> Optional[OrchestratorTask]:
        """Get a task by ID."""
        with self._lock:
            return self._tasks.get(task_id)

    def list_tasks(self, status_filter: Optional[TaskStatus] = None) -> list[dict]:
        """List all tasks, optionally filtered by status.

        Returns:
            List of task dicts sorted by creation time (newest first).
        """
        with self._lock:
            result = []
            for task in sorted(
                self._tasks.values(),
                key=lambda t: t.created_at,
                reverse=True,
            ):
                if status_filter is None or task.status == status_filter:
                    result.append(task.to_dict())
            return result

    @property
    def pending_count(self) -> int:
        """Number of tasks waiting to execute."""
        with self._lock:
            return sum(
                1 for t in self._tasks.values()
                if t.status == TaskStatus.PENDING
            )

    @property
    def active_count(self) -> int:
        """Number of tasks currently executing."""
        with self._lock:
            return sum(
                1 for t in self._tasks.values()
                if t.status == TaskStatus.ACTIVE
            )

    @property
    def total_count(self) -> int:
        """Total number of tasks ever enqueued."""
        with self._lock:
            return len(self._tasks)

    def clear_completed(self) -> int:
        """Remove all completed and cancelled tasks from the store.

        Returns:
            Number of tasks removed.
        """
        with self._lock:
            terminal = {
                tid for tid, t in self._tasks.items()
                if t.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.FAILED)
            }
            for tid in terminal:
                del self._tasks[tid]
            return len(terminal)

    def to_dict(self) -> dict:
        """Serialize queue state for monitoring."""
        with self._lock:
            return {
                "total": len(self._tasks),
                "pending": self.pending_count,
                "active": self.active_count,
                "completed": sum(
                    1 for t in self._tasks.values()
                    if t.status == TaskStatus.COMPLETED
                ),
                "failed": sum(
                    1 for t in self._tasks.values()
                    if t.status == TaskStatus.FAILED
                ),
                "cancelled": sum(
                    1 for t in self._tasks.values()
                    if t.status == TaskStatus.CANCELLED
                ),
            }
