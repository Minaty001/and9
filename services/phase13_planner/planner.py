"""
Phase 13 — Planner Core Logic.

Decomposes goals into subtask DAGs with cycle detection and topological sort.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict, deque

from .config import PlannerConfig
from .models import SubTask, SubTaskStatus, SubTaskType, ExecutionPlan, ExecutionPlanStatus

logger = logging.getLogger(__name__)


class Planner:
    """Core planner that decomposes goals into executable subtask DAGs.

    Creates execution plans with dependency resolution, cycle detection,
    and deterministic topological ordering for execution.
    """

    def __init__(self, config: Optional[PlannerConfig] = None):
        self.config = config or PlannerConfig()

    # ── Public API ──────────────────────────────────────────────────

    def create_plan(self, goal: str, context: Optional[Dict[str, Any]] = None) -> ExecutionPlan:
        """Decompose a goal into an executable ExecutionPlan.

        Args:
            goal: The high-level goal to decompose.
            context: Optional context information to guide decomposition.

        Returns:
            An ExecutionPlan with subtasks, dependencies, and execution order.
        """
        now = datetime.now(timezone.utc)
        subtasks = self._decompose(goal, context)
        plan = ExecutionPlan(
            goal=goal,
            tasks=subtasks,
            total_steps=len(subtasks),
            status=ExecutionPlanStatus.PENDING,
            created_at=now,
            execution_order=[],
        )
        self.resolve_dependencies(plan)
        plan.execution_order = self.get_execution_order(plan)
        return plan

    def plan_subtasks(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[SubTask]:
        """Build the task graph for a given goal.

        Args:
            goal: The goal to decompose.
            context: Optional context.

        Returns:
            A list of SubTask instances representing the task graph.
        """
        return self._decompose(goal, context)

    def resolve_dependencies(self, plan: ExecutionPlan) -> None:
        """Resolve and validate dependencies in a plan.

        Performs DFS-based cycle detection. If a cycle is found,
        the conflicting dependency is removed and a warning is logged.

        Args:
            plan: The execution plan to validate.
        """
        task_ids = {t.id for t in plan.tasks}
        for task in plan.tasks:
            valid_deps = [
                dep for dep in task.dependencies
                if dep in task_ids and dep != task.id
            ]
            task.dependencies = valid_deps

        # Detect cycles via DFS and break them
        visited: Set[str] = set()
        recursion_stack: Set[str] = set()

        def _has_cycle(node_id: str, path: List[str]) -> bool:
            visited.add(node_id)
            recursion_stack.add(node_id)
            task = plan.get_task(node_id)
            if task:
                for dep in list(task.dependencies):
                    if dep not in visited:
                        if _has_cycle(dep, path + [dep]):
                            return True
                    elif dep in recursion_stack:
                        # Cycle detected, remove this dependency
                        logger.warning(
                            "Cycle detected: %s depends on %s — removing dependency",
                            node_id, dep,
                        )
                        task.dependencies.remove(dep)
                        return True
            recursion_stack.discard(node_id)
            return False

        for task in plan.tasks:
            _has_cycle(task.id, [task.id])

    def get_execution_order(self, plan: ExecutionPlan) -> List[str]:
        """Return topological execution order using Kahn's algorithm.

        Args:
            plan: The execution plan.

        Returns:
            List of subtask IDs in execution order.

        Raises:
            ValueError: If a cycle remains after resolution.
        """
        # Build adjacency and in-degree maps
        in_degree: Dict[str, int] = {t.id: 0 for t in plan.tasks}
        adjacency: Dict[str, List[str]] = {t.id: [] for t in plan.tasks}

        for task in plan.tasks:
            for dep in task.dependencies:
                if dep in adjacency:
                    adjacency[dep].append(task.id)
                    in_degree[task.id] = in_degree.get(task.id, 0) + 1

        # Kahn's algorithm
        queue = deque([tid for tid, deg in in_degree.items() if deg == 0])
        order: List[str] = []

        while queue:
            node = queue.popleft()
            order.append(node)
            for neighbor in adjacency.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(plan.tasks):
            missing = set(plan.get_task(t).id for t in order if plan.get_task(t))
            unresolved = [t.id for t in plan.tasks if t.id not in missing]
            logger.error("Cycle detected after resolution: %s", unresolved)
            raise ValueError(
                f"Cannot resolve execution order: cycle remaining among {unresolved}"
            )

        return order

    def get_parallel_levels(self, plan: ExecutionPlan) -> List[List[str]]:
        """Group execution order into parallelizable levels.

        Args:
            plan: The execution plan with resolved execution_order.

        Returns:
            List of levels, where each level is a list of task IDs
            that can be executed in parallel.
        """
        if not plan.execution_order:
            plan.execution_order = self.get_execution_order(plan)

        # Build a set of completed dependencies for each position
        completed: Set[str] = set()
        levels: List[List[str]] = []
        level_map: Dict[str, int] = {}

        for task_id in plan.execution_order:
            task = plan.get_task(task_id)
            if not task:
                continue
            # Determine the earliest level this task can go into
            if not task.dependencies:
                level = 0
            else:
                level = max(level_map.get(dep, -1) for dep in task.dependencies) + 1

            # Ensure the level list exists
            while len(levels) <= level:
                levels.append([])
            levels[level].append(task_id)
            level_map[task_id] = level
            completed.add(task_id)

        return levels

    # ── Internal ────────────────────────────────────────────────────

    def _decompose(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[SubTask]:
        """Decompose a goal into subtasks based on heuristic patterns.

        In a production system this would use an LLM; here we use a
        heuristic decomposition that creates well-structured task DAGs.

        Args:
            goal: The goal to decompose.
            context: Optional context.

        Returns:
            A list of SubTask instances.
        """
        now = datetime.now(timezone.utc)
        subtasks: List[SubTask] = []
        goal_lower = goal.lower()

        # Determine decomposition strategy based on keywords
        if "research" in goal_lower or "analyze" in goal_lower:
            subtasks = self._decompose_research(goal, now)
        elif "build" in goal_lower or "create" in goal_lower or "develop" in goal_lower:
            subtasks = self._decompose_build(goal, now)
        elif "plan" in goal_lower or "organize" in goal_lower:
            subtasks = self._decompose_plan(goal, now)
        elif "fix" in goal_lower or "debug" in goal_lower or "repair" in goal_lower:
            subtasks = self._decompose_debug(goal, now)
        else:
            # Default decomposition
            subtasks = self._decompose_generic(goal, now)

        # Apply limits
        max_tasks = self.config.max_subtasks
        if len(subtasks) > max_tasks:
            subtasks = subtasks[:max_tasks]

        return subtasks

    @staticmethod
    def _decompose_research(goal: str, now: datetime) -> List[SubTask]:
        """Decompose a research/analysis goal."""
        return [
            SubTask(id="research_1", description="Define research objectives and scope",
                    type=SubTaskType.SEQUENTIAL, max_retries=2, confidence=0.9,
                    created_at=now),
            SubTask(id="research_2", description="Gather relevant information and data",
                    dependencies=["research_1"], type=SubTaskType.SEQUENTIAL,
                    max_retries=3, confidence=0.8, created_at=now),
            SubTask(id="research_3", description="Analyze gathered data",
                    dependencies=["research_2"], type=SubTaskType.SEQUENTIAL,
                    max_retries=2, confidence=0.7, created_at=now),
            SubTask(id="research_4", description="Synthesize findings and draw conclusions",
                    dependencies=["research_3"], type=SubTaskType.SEQUENTIAL,
                    max_retries=2, confidence=0.8, created_at=now),
            SubTask(id="research_5", description="Prepare final report",
                    dependencies=["research_4"], type=SubTaskType.SEQUENTIAL,
                    max_retries=1, confidence=0.9, created_at=now),
        ]

    @staticmethod
    def _decompose_build(goal: str, now: datetime) -> List[SubTask]:
        """Decompose a build/create goal with parallel phases."""
        return [
            SubTask(id="build_1", description="Design architecture",
                    type=SubTaskType.SEQUENTIAL, max_retries=2, confidence=0.85,
                    created_at=now),
            SubTask(id="build_2", description="Set up project structure and dependencies",
                    dependencies=["build_1"], type=SubTaskType.SEQUENTIAL,
                    max_retries=2, confidence=0.9, created_at=now),
            SubTask(id="build_3", description="Implement core logic",
                    dependencies=["build_2"], type=SubTaskType.SEQUENTIAL,
                    max_retries=3, confidence=0.75, created_at=now),
            SubTask(id="build_4", description="Write unit tests",
                    dependencies=["build_3"], type=SubTaskType.PARALLEL,
                    max_retries=2, confidence=0.8, created_at=now),
            SubTask(id="build_5", description="Write integration tests",
                    dependencies=["build_3"], type=SubTaskType.PARALLEL,
                    max_retries=2, confidence=0.8, created_at=now),
            SubTask(id="build_6", description="Build and verify",
                    dependencies=["build_4", "build_5"], type=SubTaskType.SEQUENTIAL,
                    max_retries=2, confidence=0.85, created_at=now),
            SubTask(id="build_7", description="Deploy or package",
                    dependencies=["build_6"], type=SubTaskType.SEQUENTIAL,
                    max_retries=1, confidence=0.9, created_at=now),
        ]

    @staticmethod
    def _decompose_plan(goal: str, now: datetime) -> List[SubTask]:
        """Decompose a planning/organizing goal."""
        return [
            SubTask(id="plan_1", description="Identify requirements and constraints",
                    type=SubTaskType.SEQUENTIAL, max_retries=2, confidence=0.9,
                    created_at=now),
            SubTask(id="plan_2", description="Research available options",
                    dependencies=["plan_1"], type=SubTaskType.SEQUENTIAL,
                    max_retries=2, confidence=0.8, created_at=now),
            SubTask(id="plan_3", description="Create detailed action plan",
                    dependencies=["plan_2"], type=SubTaskType.SEQUENTIAL,
                    max_retries=2, confidence=0.85, created_at=now),
            SubTask(id="plan_4", description="Review and refine plan",
                    dependencies=["plan_3"], type=SubTaskType.SEQUENTIAL,
                    max_retries=2, confidence=0.9, created_at=now),
            SubTask(id="plan_5", description="Present final plan",
                    dependencies=["plan_4"], type=SubTaskType.SEQUENTIAL,
                    max_retries=1, confidence=0.95, created_at=now),
        ]

    @staticmethod
    def _decompose_debug(goal: str, now: datetime) -> List[SubTask]:
        """Decompose a fix/debug goal."""
        return [
            SubTask(id="debug_1", description="Reproduce the issue",
                    type=SubTaskType.SEQUENTIAL, max_retries=2, confidence=0.9,
                    created_at=now),
            SubTask(id="debug_2", description="Identify root cause",
                    dependencies=["debug_1"], type=SubTaskType.SEQUENTIAL,
                    max_retries=3, confidence=0.7, created_at=now),
            SubTask(id="debug_3", description="Implement fix",
                    dependencies=["debug_2"], type=SubTaskType.SEQUENTIAL,
                    max_retries=3, confidence=0.75, created_at=now),
            SubTask(id="debug_4", description="Verify fix resolves issue",
                    dependencies=["debug_3"], type=SubTaskType.SEQUENTIAL,
                    max_retries=2, confidence=0.85, created_at=now),
            SubTask(id="debug_5", description="Run regression tests",
                    dependencies=["debug_4"], type=SubTaskType.SEQUENTIAL,
                    max_retries=2, confidence=0.8, created_at=now),
        ]

    @staticmethod
    def _decompose_generic(goal: str, now: datetime) -> List[SubTask]:
        """Generic decomposition for any goal."""
        return [
            SubTask(id="task_1", description=f"Understand goal: {goal[:100]}",
                    type=SubTaskType.SEQUENTIAL, max_retries=2, confidence=0.9,
                    created_at=now),
            SubTask(id="task_2", description="Break down into manageable steps",
                    dependencies=["task_1"], type=SubTaskType.SEQUENTIAL,
                    max_retries=2, confidence=0.85, created_at=now),
            SubTask(id="task_3", description="Execute primary work",
                    dependencies=["task_2"], type=SubTaskType.SEQUENTIAL,
                    max_retries=3, confidence=0.7, created_at=now),
            SubTask(id="task_4", description="Review and validate results",
                    dependencies=["task_3"], type=SubTaskType.SEQUENTIAL,
                    max_retries=2, confidence=0.8, created_at=now),
            SubTask(id="task_5", description="Finalize and deliver",
                    dependencies=["task_4"], type=SubTaskType.SEQUENTIAL,
                    max_retries=1, confidence=0.9, created_at=now),
        ]
