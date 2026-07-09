"""
app/core/task_queue.py — Priority task queue for AND9

No task executes directly. Every action is enqueued here.

Priority levels:
  0 = CRITICAL  (emergency stop, auth failures)
  1 = HIGH      (voice commands, app launch, timers)
  2 = MEDIUM    (file operations, web search)
  3 = LOW       (cache cleanup, memory compression)
"""

import logging
import threading
import queue
import uuid
from dataclasses import dataclass, field
from typing import Callable, Dict, Any, Optional
from enum import IntEnum
from app.core.event_bus import EventBus

logger = logging.getLogger(__name__)


class Priority(IntEnum):
    CRITICAL = 0
    HIGH     = 1
    MEDIUM   = 2
    LOW      = 3


@dataclass(order=True)
class Task:
    priority: int
    task_id: str = field(compare=False, default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = field(compare=False, default="")
    fn: Callable = field(compare=False, default=None)
    args: tuple = field(compare=False, default_factory=tuple)
    kwargs: dict = field(compare=False, default_factory=dict)
    retries: int = field(compare=False, default=2)
    timeout_sec: int = field(compare=False, default=30)

    # Internal state
    attempts: int = field(compare=False, default=0)
    status: str = field(compare=False, default="queued")


class TaskQueue:
    def __init__(self, event_bus: EventBus):
        self._bus = event_bus
        self._queue: queue.PriorityQueue = queue.PriorityQueue()
        self._results: Dict[str, Any] = {}
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._running = True
        self._worker_thread = threading.Thread(
            target=self._worker_loop, daemon=True, name="TaskQueue-Worker"
        )
        self._worker_thread.start()
        logger.info("TaskQueue: worker started.")

    def enqueue(self, fn: Callable, name: str = "",
                priority: int = Priority.MEDIUM,
                args: tuple = (), kwargs: dict = None,
                retries: int = 2, timeout_sec: int = 30) -> str:
        """Add a task to the queue. Returns task_id."""
        task = Task(
            priority=priority, name=name, fn=fn,
            args=args, kwargs=kwargs or {},
            retries=retries, timeout_sec=timeout_sec
        )
        self._queue.put(task)
        self._bus.publish("task.queued", {
            "task_id": task.task_id, "name": name, "priority": priority
        }, source="task_queue")
        return task.task_id

    def get_result(self, task_id: str) -> Optional[Any]:
        return self._results.get(task_id)

    def depth(self) -> int:
        return self._queue.qsize()

    def drain(self) -> None:
        """Shutdown: wait for queue to empty, then stop worker.
        Clears any remaining tasks to prevent deadlock if
        the worker thread has already stopped.
        """
        # Clear any unprocessed tasks to prevent deadlock on join
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except queue.Empty:
                break
        self._queue.join()
        self._running = False

    def _worker_loop(self) -> None:
        while self._running:
            try:
                task: Task = self._queue.get(timeout=1)
            except queue.Empty:
                continue

            task.status = "running"
            task.attempts += 1
            self._bus.publish("task.started", {
                "task_id": task.task_id, "name": task.name,
                "attempt": task.attempts
            }, source="task_queue")

            try:
                result = task.fn(*task.args, **task.kwargs)
                task.status = "completed"
                self._results[task.task_id] = result
                self._bus.publish("task.completed", {
                    "task_id": task.task_id, "name": task.name
                }, source="task_queue")
            except Exception as e:
                logger.warning(f"TaskQueue: task '{task.name}' failed: {e} "
                               f"(attempt {task.attempts}/{task.retries+1})")
                if task.attempts <= task.retries:
                    # Re-queue with same priority
                    self._queue.put(task)
                else:
                    task.status = "failed"
                    self._bus.publish("task.failed", {
                        "task_id": task.task_id, "name": task.name,
                        "error": str(e)
                    }, source="task_queue")
            finally:
                self._queue.task_done()