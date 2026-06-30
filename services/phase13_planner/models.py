"""
Phase 13 — Planner Data Models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum
from datetime import datetime


# ── Enums ──────────────────────────────────────────────────────────────


class SubTaskStatus(str, Enum):
    """Status of a subtask."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class SubTaskType(str, Enum):
    """Execution type for a subtask."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"


class ExecutionPlanStatus(str, Enum):
    """Status of the overall execution plan."""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


# ── Data Classes ───────────────────────────────────────────────────────


@dataclass
class SubTask:
    """A single task node in the plan DAG."""

    id: str
    description: str
    dependencies: List[str] = field(default_factory=list)
    status: SubTaskStatus = SubTaskStatus.PENDING
    type: SubTaskType = SubTaskType.SEQUENTIAL
    retry_count: int = 0
    max_retries: int = 3
    confidence: float = 1.0
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class ExecutionPlan:
    """Complete execution plan with tasks and ordering."""

    goal: str
    tasks: List[SubTask] = field(default_factory=list)
    total_steps: int = 0
    status: ExecutionPlanStatus = ExecutionPlanStatus.PENDING
    created_at: Optional[datetime] = None
    execution_order: List[str] = field(default_factory=list)

    def get_task(self, task_id: str) -> Optional[SubTask]:
        """Get a subtask by its id."""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None
