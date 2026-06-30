"""
Phase 33 — Recovery Workflow.

Multi-step recovery execution with conditional branching,
retry policies, and progress tracking.
"""

from __future__ import annotations

import time
import logging
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from .models import ErrorContext
from .rollback_manager import RollbackManager

logger = logging.getLogger(__name__)


class StepState(str, Enum):
    """State of a recovery workflow step."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class RetryPolicy(str, Enum):
    """Policy when a step fails."""
    SKIP = "skip"          # Skip this step, continue to next
    RETRY = "retry"        # Retry the step (up to max_retries)
    ROLLBACK = "rollback"  # Roll back all completed steps and stop
    STOP = "stop"          # Stop execution without rollback


class WorkflowStep:
    """A single step in a recovery workflow."""

    def __init__(
        self,
        name: str,
        func: Callable,
        retry_policy: str = "skip",
        max_retries: int = 0,
    ):
        self.name = name
        self.func = func
        self.retry_policy = retry_policy
        self.max_retries = max_retries
        self.state = StepState.PENDING
        self.result: Any = None
        self.error: Optional[str] = None
        self.duration_ms: float = 0.0
        self.attempts: int = 0


class RecoveryWorkflow:
    """Multi-step recovery workflow with conditional branching.

    Steps execute in order. If a step fails, the retry_policy determines
    whether to skip, retry, stop, or roll back all completed steps.

    Usage:
        wf = RecoveryWorkflow("my_workflow")
        wf.add_step("step1", func1, retry_policy="retry")
        wf.add_step("step2", func2, retry_policy="skip")
        wf.add_step("step3", func3, retry_policy="rollback")
        result = wf.execute(context)
        progress = wf.get_progress()
    """

    def __init__(
        self,
        name: str = "default",
        rollback_manager: Optional[RollbackManager] = None,
    ):
        self.name = name
        self.rollback_manager = rollback_manager or RollbackManager()
        self._steps: List[WorkflowStep] = []
        self._current_step_index: int = -1
        self._completed_steps: List[str] = []
        self._start_time: float = 0.0
        self._total_duration_ms: float = 0.0

    def add_step(
        self,
        name: str,
        func: Callable,
        retry_policy: str = "skip",
        max_retries: int = 0,
    ) -> None:
        """Add a step to the workflow.

        Args:
            name: Step name (must be unique within the workflow).
            func: Callable that takes (context) as argument.
            retry_policy: "skip", "retry", "rollback", or "stop".
            max_retries: Max retry attempts (only used when retry_policy="retry").
        """
        step = WorkflowStep(
            name=name,
            func=func,
            retry_policy=retry_policy,
            max_retries=max_retries,
        )
        self._steps.append(step)
        logger.debug("Workflow %s: added step %s (policy=%s)", self.name, name, retry_policy)

    def execute(self, context: ErrorContext) -> Tuple[bool, ErrorContext]:
        """Execute the workflow steps in order.

        Args:
            context: The ErrorContext to pass to each step.

        Returns:
            Tuple of (success, context).
        """
        self._start_time = time.perf_counter()
        logger.info("Workflow %s: starting execution with %d steps", self.name, len(self._steps))

        success = True
        for i, step in enumerate(self._steps):
            self._current_step_index = i
            step.state = StepState.RUNNING
            step.attempts += 1

            t0 = time.perf_counter()
            try:
                logger.debug("Workflow %s: executing step %s", self.name, step.name)
                step.result = step.func(context)
                step.state = StepState.SUCCESS
                step.duration_ms = (time.perf_counter() - t0) * 1000
                self._completed_steps.append(step.name)
                logger.debug("Workflow %s: step %s succeeded", self.name, step.name)
            except Exception as e:
                step.duration_ms = (time.perf_counter() - t0) * 1000
                step.error = str(e)
                step.state = StepState.FAILED
                logger.warning(
                    "Workflow %s: step %s failed: %s",
                    self.name, step.name, e,
                )

                # Apply retry policy
                if step.retry_policy == RetryPolicy.RETRY:
                    if step.attempts <= step.max_retries:
                        # Re-run this step
                        logger.debug(
                            "Workflow %s: retrying step %s (attempt %d/%d)",
                            self.name, step.name, step.attempts, step.max_retries,
                        )
                        self._steps.insert(i + 1, step)  # re-insert for retry
                        continue
                    else:
                        logger.warning(
                            "Workflow %s: step %s exhausted retries",
                            self.name, step.name,
                        )
                        success = False
                        break

                elif step.retry_policy == RetryPolicy.SKIP:
                    logger.debug("Workflow %s: skipping step %s", self.name, step.name)
                    step.state = StepState.SKIPPED
                    continue

                elif step.retry_policy == RetryPolicy.ROLLBACK:
                    logger.warning(
                        "Workflow %s: rolling back due to step %s failure",
                        self.name, step.name,
                    )
                    self.rollback()
                    success = False
                    break

                elif step.retry_policy == RetryPolicy.STOP:
                    logger.warning(
                        "Workflow %s: stopping due to step %s failure",
                        self.name, step.name,
                    )
                    success = False
                    break

        self._total_duration_ms = (time.perf_counter() - self._start_time) * 1000
        logger.info(
            "Workflow %s: finished (success=%s, duration=%.2fms)",
            self.name, success, self._total_duration_ms,
        )
        return success, context

    def get_progress(self) -> dict:
        """Get the current workflow progress.

        Returns:
            Dict with workflow name, step statuses, duration, etc.
        """
        return {
            "workflow_name": self.name,
            "total_steps": len(self._steps),
            "completed_steps": list(self._completed_steps),
            "current_step_index": self._current_step_index,
            "steps": [
                {
                    "name": s.name,
                    "state": s.state.value,
                    "duration_ms": round(s.duration_ms, 2),
                    "error": s.error,
                    "attempts": s.attempts,
                }
                for s in self._steps
            ],
            "total_duration_ms": round(self._total_duration_ms, 2),
        }

    def rollback(self) -> bool:
        """Roll back all completed steps using the rollback manager.

        Returns:
            True if all rollbacks succeeded.
        """
        logger.info("Workflow %s: rolling back %d completed steps", self.name, len(self._completed_steps))
        # Roll back in reverse order
        for step_name in reversed(self._completed_steps):
            if self.rollback_manager.has_compensation(step_name):
                self.rollback_manager.rollback(step_name)
        return True

    def reset(self) -> None:
        """Reset the workflow to initial state."""
        for step in self._steps:
            step.state = StepState.PENDING
            step.result = None
            step.error = None
            step.duration_ms = 0.0
            step.attempts = 0
        self._completed_steps.clear()
        self._current_step_index = -1
        self._start_time = 0.0
        self._total_duration_ms = 0.0
        logger.debug("Workflow %s: reset", self.name)
