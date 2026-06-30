"""
Tests for Phase 13 — Planner.
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from services.phase13_planner.config import PlannerConfig
from services.phase13_planner.models import (
    SubTask, SubTaskStatus, SubTaskType,
    ExecutionPlan, ExecutionPlanStatus,
)
from services.phase13_planner.planner import Planner
from services.phase13_planner.service import PlannerService


# ── Fixtures ───────────────────────────────────────────────────────────


@pytest.fixture
def config() -> PlannerConfig:
    return PlannerConfig()


@pytest.fixture
def planner() -> Planner:
    return Planner()


@pytest.fixture
def sample_plan() -> ExecutionPlan:
    """Create a sample 3-task sequential plan."""
    now = datetime.now(timezone.utc)
    tasks = [
        SubTask(id="a", description="Task A", type=SubTaskType.SEQUENTIAL,
                created_at=now),
        SubTask(id="b", description="Task B", dependencies=["a"],
                type=SubTaskType.SEQUENTIAL, created_at=now),
        SubTask(id="c", description="Task C", dependencies=["b"],
                type=SubTaskType.SEQUENTIAL, created_at=now),
    ]
    return ExecutionPlan(
        goal="Test goal",
        tasks=tasks,
        total_steps=3,
        status=ExecutionPlanStatus.PENDING,
        created_at=now,
    )


# ── ExecutionPlan Tests ────────────────────────────────────────────────


class TestExecutionPlan:
    def test_creation(self):
        now = datetime.now(timezone.utc)
        plan = ExecutionPlan(
            goal="Build a website",
            total_steps=3,
            status=ExecutionPlanStatus.PENDING,
            created_at=now,
        )
        assert plan.goal == "Build a website"
        assert plan.total_steps == 3
        assert plan.status == ExecutionPlanStatus.PENDING
        assert plan.tasks == []
        assert plan.execution_order == []

    def test_with_tasks(self, sample_plan):
        assert len(sample_plan.tasks) == 3
        assert sample_plan.total_steps == 3
        assert sample_plan.goal == "Test goal"

    def test_get_task_found(self, sample_plan):
        task = sample_plan.get_task("b")
        assert task is not None
        assert task.id == "b"
        assert task.description == "Task B"

    def test_get_task_not_found(self, sample_plan):
        task = sample_plan.get_task("nonexistent")
        assert task is None

    def test_status_transitions(self):
        plan = ExecutionPlan(goal="test", total_steps=0,
                             status=ExecutionPlanStatus.PENDING)
        assert plan.status == ExecutionPlanStatus.PENDING
        plan.status = ExecutionPlanStatus.ACTIVE
        assert plan.status == ExecutionPlanStatus.ACTIVE
        plan.status = ExecutionPlanStatus.COMPLETED
        assert plan.status == ExecutionPlanStatus.COMPLETED

    def test_failed_status(self):
        plan = ExecutionPlan(goal="test", total_steps=0,
                             status=ExecutionPlanStatus.FAILED)
        assert plan.status == ExecutionPlanStatus.FAILED

    def test_rolled_back_status(self):
        plan = ExecutionPlan(goal="test", total_steps=0,
                             status=ExecutionPlanStatus.ROLLED_BACK)
        assert plan.status == ExecutionPlanStatus.ROLLED_BACK

    def test_execution_order_ordering(self):
        plan = ExecutionPlan(goal="test", total_steps=0,
                             execution_order=["a", "b", "c"])
        assert plan.execution_order == ["a", "b", "c"]

    def test_empty_plan(self):
        plan = ExecutionPlan(goal="empty")
        assert plan.total_steps == 0
        assert plan.tasks == []
        assert plan.execution_order == []


# ── SubTask Tests ──────────────────────────────────────────────────────


class TestSubTask:
    def test_creation(self):
        now = datetime.now(timezone.utc)
        task = SubTask(
            id="task_1",
            description="Do something",
            max_retries=3,
            confidence=0.85,
            created_at=now,
        )
        assert task.id == "task_1"
        assert task.description == "Do something"
        assert task.status == SubTaskStatus.PENDING
        assert task.dependencies == []
        assert task.max_retries == 3
        assert task.confidence == 0.85

    def test_with_dependencies(self):
        now = datetime.now(timezone.utc)
        task = SubTask(
            id="task_3",
            description="Final step",
            dependencies=["task_1", "task_2"],
            type=SubTaskType.PARALLEL,
            max_retries=2,
            confidence=0.9,
            created_at=now,
        )
        assert task.dependencies == ["task_1", "task_2"]
        assert task.type == SubTaskType.PARALLEL

    def test_status_default(self):
        task = SubTask(id="t1", description="test")
        assert task.status == SubTaskStatus.PENDING

    def test_completed_status(self):
        now = datetime.now(timezone.utc)
        task = SubTask(
            id="t1", description="test",
            status=SubTaskStatus.COMPLETED,
            result="Done",
            completed_at=now,
        )
        assert task.status == SubTaskStatus.COMPLETED
        assert task.result == "Done"

    def test_failed_with_error(self):
        task = SubTask(
            id="t1", description="test",
            status=SubTaskStatus.FAILED,
            error="Something went wrong",
        )
        assert task.status == SubTaskStatus.FAILED
        assert task.error == "Something went wrong"

    def test_retry_count(self):
        task = SubTask(
            id="t1", description="test",
            retry_count=2, max_retries=5,
        )
        assert task.retry_count == 2
        assert task.max_retries == 5


# ── Planner Tests ──────────────────────────────────────────────────────


class TestPlanner:
    def test_create_plan(self, planner):
        plan = planner.create_plan("Build a web application")
        assert plan.goal == "Build a web application"
        assert len(plan.tasks) > 0
        assert plan.status == ExecutionPlanStatus.PENDING
        assert plan.created_at is not None
        assert len(plan.execution_order) > 0

    def test_create_plan_research(self, planner):
        plan = planner.create_plan("Research quantum computing trends")
        assert len(plan.tasks) == 5
        ids = [t.id for t in plan.tasks]
        assert "research_1" in ids
        assert "research_5" in ids

    def test_create_plan_build(self, planner):
        plan = planner.create_plan("Create a mobile app")
        assert len(plan.tasks) == 7
        ids = [t.id for t in plan.tasks]
        assert "build_1" in ids
        assert "build_7" in ids
        # build_4 and build_5 should be parallel
        t4 = plan.get_task("build_4")
        t5 = plan.get_task("build_5")
        assert t4 is not None and t4.type == SubTaskType.PARALLEL
        assert t5 is not None and t5.type == SubTaskType.PARALLEL

    def test_create_plan_plan(self, planner):
        plan = planner.create_plan("Plan a conference schedule")
        assert len(plan.tasks) == 5
        ids = [t.id for t in plan.tasks]
        assert "plan_1" in ids

    def test_create_plan_debug(self, planner):
        plan = planner.create_plan("Fix the login bug")
        assert len(plan.tasks) == 5
        ids = [t.id for t in plan.tasks]
        assert "debug_1" in ids

    def test_create_plan_generic(self, planner):
        plan = planner.create_plan("Do something custom")
        assert len(plan.tasks) == 5
        ids = [t.id for t in plan.tasks]
        assert "task_1" in ids

    def test_create_plan_with_context(self, planner):
        context = {"user": "test_user", "priority": "high"}
        plan = planner.create_plan("Build a feature", context)
        assert plan.goal == "Build a feature"
        assert len(plan.tasks) > 0

    def test_resolve_dependencies(self, planner):
        now = datetime.now(timezone.utc)
        tasks = [
            SubTask(id="a", description="A", type=SubTaskType.SEQUENTIAL, created_at=now),
            SubTask(id="b", description="B", dependencies=["a"], type=SubTaskType.SEQUENTIAL, created_at=now),
            SubTask(id="c", description="C", dependencies=["b"], type=SubTaskType.SEQUENTIAL, created_at=now),
        ]
        plan = ExecutionPlan(goal="test", tasks=tasks, total_steps=3, created_at=now)
        planner.resolve_dependencies(plan)
        assert plan.get_task("b").dependencies == ["a"]
        assert plan.get_task("c").dependencies == ["b"]

    def test_cycle_detection(self, planner):
        """Direct A->B->C->A cycle should be broken."""
        now = datetime.now(timezone.utc)
        tasks = [
            SubTask(id="a", description="A", dependencies=["c"],
                    type=SubTaskType.SEQUENTIAL, created_at=now),
            SubTask(id="b", description="B", dependencies=["a"],
                    type=SubTaskType.SEQUENTIAL, created_at=now),
            SubTask(id="c", description="C", dependencies=["b"],
                    type=SubTaskType.SEQUENTIAL, created_at=now),
        ]
        plan = ExecutionPlan(goal="test", tasks=tasks, total_steps=3, created_at=now)
        # resolve_dependencies should break the cycle by removing one dependency
        planner.resolve_dependencies(plan)
        # After cycle breaking, we should be able to get a valid execution order
        order = planner.get_execution_order(plan)
        assert len(order) == 3

    def test_self_dependency_removed(self, planner):
        now = datetime.now(timezone.utc)
        tasks = [
            SubTask(id="a", description="A", dependencies=["a"],
                    type=SubTaskType.SEQUENTIAL, created_at=now),
        ]
        plan = ExecutionPlan(goal="test", tasks=tasks, total_steps=1, created_at=now)
        planner.resolve_dependencies(plan)
        assert plan.get_task("a").dependencies == []

    def test_invalid_dependency_removed(self, planner):
        now = datetime.now(timezone.utc)
        tasks = [
            SubTask(id="a", description="A", dependencies=["nonexistent"],
                    type=SubTaskType.SEQUENTIAL, created_at=now),
        ]
        plan = ExecutionPlan(goal="test", tasks=tasks, total_steps=1, created_at=now)
        planner.resolve_dependencies(plan)
        assert plan.get_task("a").dependencies == []

    def test_execution_order_topological(self, planner):
        plan = planner.create_plan("Build a mobile app")
        order = plan.execution_order
        # Verify that dependencies come before dependents
        for task_id in order:
            task = plan.get_task(task_id)
            if task and task.dependencies:
                for dep in task.dependencies:
                    assert order.index(dep) < order.index(task_id), \
                        f"{dep} should come before {task_id}"

    def test_execution_order_kahn(self, planner, sample_plan):
        order = planner.get_execution_order(sample_plan)
        assert order == ["a", "b", "c"]

    def test_get_parallel_levels(self, planner):
        plan = planner.create_plan("Create a mobile app")
        levels = planner.get_parallel_levels(plan)
        assert len(levels) > 0
        # All task IDs should appear exactly once across all levels
        all_tasks = [tid for level in levels for tid in level]
        assert len(all_tasks) == len(set(all_tasks)) == len(plan.tasks)

    def test_plan_subtasks(self, planner):
        tasks = planner.plan_subtasks("Research AI trends")
        assert len(tasks) == 5
        assert all(isinstance(t, SubTask) for t in tasks)

    def test_max_subtasks_limit(self):
        config = PlannerConfig(max_subtasks=2)
        p = Planner(config)
        plan = p.create_plan("Build a large application")
        assert len(plan.tasks) <= 2

    def test_planner_config_defaults(self):
        config = PlannerConfig()
        assert config.max_subtasks == 20
        assert config.max_depth == 5
        assert config.min_confidence == 0.5
        assert config.enable_parallel is True
        assert config.enable_rollback is True
        assert config.max_retries == 3

    def test_cycle_remaining_raises(self, planner):
        """If a cycle remains after resolution, get_execution_order should raise."""
        now = datetime.now(timezone.utc)
        # Create a plan where cycle detection can't fully resolve
        # (e.g., if we bypass resolve_dependencies)
        tasks = [
            SubTask(id="x", description="X", dependencies=["y"],
                    type=SubTaskType.SEQUENTIAL, created_at=now),
            SubTask(id="y", description="Y", dependencies=["x"],
                    type=SubTaskType.SEQUENTIAL, created_at=now),
        ]
        plan = ExecutionPlan(goal="test", tasks=tasks, total_steps=2, created_at=now)
        # resolve_dependencies should detect and break cycles
        # But let's test manually by creating a malformed plan
        with pytest.raises(ValueError):
            # Skip resolve_dependencies to simulate remaining cycle
            planner.get_execution_order(plan)


# ── PlannerService Tests ───────────────────────────────────────────────


class TestPlannerService:
    @pytest.mark.asyncio
    async def test_initialize(self):
        service = PlannerService()
        ok = await service.initialize()
        assert ok is True
        assert service.is_initialized() is True

    @pytest.mark.asyncio
    async def test_shutdown(self):
        service = PlannerService()
        await service.initialize()
        await service.shutdown()
        assert service.is_initialized() is False

    @pytest.mark.asyncio
    async def test_health_before_init(self):
        service = PlannerService()
        health = await service.health()
        assert health["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_health_after_init(self):
        service = PlannerService()
        await service.initialize()
        health = await service.health()
        assert health["status"] == "healthy"
        assert health["service_name"] == "jarvis_planner"
        assert health["version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_stats(self):
        service = PlannerService()
        await service.initialize()
        stats = await service.stats()
        assert stats["service"] == "jarvis_planner"
        assert stats["version"] == "1.0.0"
        assert "metrics" in stats
        assert "max_subtasks" in stats

    @pytest.mark.asyncio
    async def test_plan_method(self):
        service = PlannerService()
        await service.initialize()
        plan = await service.plan("Build a web application")
        assert isinstance(plan, ExecutionPlan)
        assert plan.goal == "Build a web application"
        assert len(plan.tasks) > 0
        assert len(plan.execution_order) > 0

    @pytest.mark.asyncio
    async def test_plan_with_context(self):
        service = PlannerService()
        await service.initialize()
        plan = await service.plan("Research topic", {"depth": "comprehensive"})
        assert plan.goal == "Research topic"
        assert len(plan.tasks) > 0

    @pytest.mark.asyncio
    async def test_double_initialize(self):
        service = PlannerService()
        await service.initialize()
        await service.initialize()  # Should not crash
        assert service.is_initialized() is True

    @pytest.mark.asyncio
    async def test_metrics_tracking(self):
        service = PlannerService()
        await service.initialize()
        await service.plan("Test goal")
        snap = service._metrics.snapshot()
        assert snap["counters"].get("plans_created", 0) >= 1
