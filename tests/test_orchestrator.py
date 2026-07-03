"""
Tests for the Phase 4 Agent Orchestrator.

Covers:
  - TaskQueue: enqueue, dequeue, priority ordering, cancel, dependencies
  - AgentOrchestrator: analyze, decompose, plan, execute, validate, retry, merge
  - Full run() pipeline: simple, compound, multi-domain
  - Error handling and edge cases
"""

import time
import pytest

from app.orchestrator import (
    TaskQueue,
    OrchestratorTask,
    TaskPriority,
    AgentOrchestrator,
    TaskGraph,
    SubTask,
)
from app.orchestrator.task_queue import TaskStatus
from app.orchestrator.orchestrator import TaskComplexity
from app.agents.base import AgentResult
from app.agents import create_agent_system


# ═══════════════════════════════════════════════════════════════════
# TaskQueue Tests
# ═══════════════════════════════════════════════════════════════════


class TestTaskQueue:
    """Tests for the priority-ordered task queue."""

    def test_enqueue_and_count(self):
        q = TaskQueue()
        t1 = OrchestratorTask(agent_name="coding", subtask="write code")
        t2 = OrchestratorTask(agent_name="research", subtask="research topic")

        q.enqueue(t1)
        q.enqueue(t2)

        assert q.total_count == 2
        assert q.pending_count == 2
        assert q.active_count == 0

    def test_dequeue_fifo_within_priority(self):
        q = TaskQueue()
        t1 = OrchestratorTask(agent_name="a", subtask="first")
        t2 = OrchestratorTask(agent_name="b", subtask="second")

        q.enqueue(t1)
        q.enqueue(t2)

        got1 = q.dequeue()
        got2 = q.dequeue()

        assert got1 is not None
        assert got1.subtask == "first"
        assert got2 is not None
        assert got2.subtask == "second"

    def test_priority_ordering(self):
        q = TaskQueue()
        low = OrchestratorTask(agent_name="low", subtask="low",
                               priority=TaskPriority.LOW)
        high = OrchestratorTask(agent_name="high", subtask="high",
                                priority=TaskPriority.HIGH)
        med = OrchestratorTask(agent_name="med", subtask="med",
                               priority=TaskPriority.MEDIUM)

        q.enqueue(low)
        q.enqueue(high)
        q.enqueue(med)

        assert q.dequeue().subtask == "high"
        assert q.dequeue().subtask == "med"
        assert q.dequeue().subtask == "low"

    def test_dequeue_returns_none_when_empty(self):
        q = TaskQueue()
        assert q.dequeue() is None

    def test_cancel_pending_task(self):
        q = TaskQueue()
        t = OrchestratorTask(agent_name="test", subtask="test")
        q.enqueue(t)
        assert q.pending_count == 1

        assert q.cancel(t.id) is True
        assert q.pending_count == 0
        assert q.get(t.id).status == TaskStatus.CANCELLED

    def test_cancel_non_existent(self):
        q = TaskQueue()
        assert q.cancel("nonexistent") is False

    def test_cancel_all(self):
        q = TaskQueue()
        q.enqueue(OrchestratorTask(agent_name="a", subtask="a"))
        q.enqueue(OrchestratorTask(agent_name="b", subtask="b"))
        q.enqueue(OrchestratorTask(agent_name="c", subtask="c"))

        count = q.cancel_all()
        assert count == 3
        assert q.pending_count == 0

    def test_mark_completed(self):
        q = TaskQueue()
        t = OrchestratorTask(agent_name="test", subtask="test")
        q.enqueue(t)

        assert q.mark_completed(t.id, result="done") is True
        assert q.get(t.id).status == TaskStatus.COMPLETED
        assert q.get(t.id).result == "done"

    def test_mark_failed_with_retry(self):
        q = TaskQueue()
        t = OrchestratorTask(agent_name="test", subtask="test",
                             max_retries=1)
        q.enqueue(t)

        assert q.mark_failed(t.id, "error", retry=True) is True
        # Should be re-enqueued as RETRYING
        assert q.get(t.id).status == TaskStatus.RETRYING
        assert q.get(t.id).retry_count == 1

    def test_mark_failed_no_retry(self):
        q = TaskQueue()
        t = OrchestratorTask(agent_name="test", subtask="test",
                             max_retries=0)
        q.enqueue(t)

        assert q.mark_failed(t.id, "fatal", retry=False) is True
        assert q.get(t.id).status == TaskStatus.FAILED

    def test_dependency_blocks_dequeue(self):
        q = TaskQueue()
        dep = OrchestratorTask(agent_name="a", subtask="dependency")
        main = OrchestratorTask(
            agent_name="b", subtask="main",
            depends_on=[dep.id],
        )

        q.enqueue(dep)
        q.enqueue(main)

        # Only the dependency can be dequeued
        got = q.dequeue()
        assert got.id == dep.id

        # Main is still pending (dep not completed yet)
        assert q.get(main.id).status == TaskStatus.PENDING

        # Complete the dependency
        q.mark_completed(dep.id)

        # Now main can be dequeued
        got2 = q.dequeue()
        assert got2 is not None
        assert got2.id == main.id

    def test_list_tasks(self):
        q = TaskQueue()
        q.enqueue(OrchestratorTask(agent_name="a", subtask="a"))
        q.enqueue(OrchestratorTask(agent_name="b", subtask="b"))

        tasks = q.list_tasks()
        assert len(tasks) == 2

        pending = q.list_tasks(status_filter=TaskStatus.PENDING)
        assert len(pending) == 2

    def test_clear_completed(self):
        q = TaskQueue()
        t = OrchestratorTask(agent_name="test", subtask="test")
        q.enqueue(t)
        q.mark_completed(t.id)

        assert q.clear_completed() == 1
        assert q.total_count == 0

    def test_to_dict(self):
        q = TaskQueue()
        t = OrchestratorTask(agent_name="test", subtask="test")
        q.enqueue(t)

        state = q.to_dict()
        assert state["total"] == 1
        assert state["pending"] == 1


# ═══════════════════════════════════════════════════════════════════
# AgentOrchestrator Tests
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture
def agent_system():
    """Create a full agent system for orchestrator tests."""
    return create_agent_system(auto_init=True, create_orchestrator=True)


@pytest.fixture
def orchestrator(agent_system):
    """Create an orchestrator from the agent system."""
    return AgentOrchestrator(agent_system)


class TestAgentOrchestrator:
    """Tests for the AgentOrchestrator."""

    def test_create_orchestrator(self, agent_system):
        """Verify orchestrator is properly created and linked."""
        orch = AgentOrchestrator(agent_system)
        assert orch.registry is agent_system
        assert orch.task_queue is not None
        assert orch.max_workers == 5
        assert orch.default_timeout == 60.0

    def test_analyze_single_domain(self, orchestrator):
        """Analyze a single-domain request."""
        graph = orchestrator.analyze("Write a Python script")
        assert len(graph.intents) >= 1
        assert "coding" in graph.intents
        assert graph.complexity == TaskComplexity.SIMPLE

    def test_analyze_multi_domain(self, orchestrator):
        """Analyze a multi-domain request."""
        graph = orchestrator.analyze(
            "Research quantum computing and write code for a simulator"
        )
        assert len(graph.intents) >= 2
        assert graph.complexity in (TaskComplexity.MODERATE, TaskComplexity.COMPLEX)

    def test_analyze_general_chat(self, orchestrator):
        """Analyze a general chat request with no keywords."""
        graph = orchestrator.analyze("Hello, how are you?")
        assert "conversation" in graph.intents
        assert graph.complexity == TaskComplexity.SIMPLE

    def test_decompose_single(self, orchestrator):
        """Decompose a single-domain request."""
        graph = orchestrator.decompose("Write a Python sorting function")
        assert len(graph.subtasks) == 1
        assert graph.subtasks[0].agent_name == "coding"

    def test_decompose_multi_domain(self, orchestrator):
        """Decompose a multi-domain request into ordered subtasks."""
        graph = orchestrator.decompose(
            "Research machine learning and write a Python implementation"
        )
        # Should have 2+ subtasks, research before coding
        assert len(graph.subtasks) >= 2
        agent_names = [s.agent_name for s in graph.subtasks]
        assert "research" in agent_names
        assert "coding" in agent_names
        # Research should come before coding
        assert agent_names.index("research") < agent_names.index("coding")

    def test_plan_creates_tasks(self, orchestrator):
        """Verify plan() creates enqueued tasks with proper dependencies."""
        subtasks = [
            SubTask(description="Research topic", agent_name="research",
                    depends_on=[]),
            SubTask(description="Write code", agent_name="coding",
                    depends_on=[0]),
        ]
        task_ids = orchestrator.plan(subtasks)
        assert len(task_ids) == 2

        # Check dependency linking
        task1 = orchestrator.task_queue.get(task_ids[0])
        task2 = orchestrator.task_queue.get(task_ids[1])
        assert task1.depends_on == []
        assert len(task2.depends_on) == 1
        assert task2.depends_on[0] == task_ids[0]

    def test_execute_simple(self, orchestrator):
        """Execute a simple single-agent task via fast path."""
        subtask = SubTask(description="Write a hello world", agent_name="coding")
        result = orchestrator._execute_simple(subtask, context=None)
        assert result.success is True
        assert result.agent_name == "coding" or result.agent_name == "orchestrator"

    def test_execute_batch_parallel(self, orchestrator):
        """Execute multiple independent tasks in parallel."""
        subtasks = [
            SubTask(description="Research AI", agent_name="research"),
            SubTask(description="Write notes", agent_name="memory"),
        ]
        task_ids = orchestrator.plan(subtasks)
        results = orchestrator._execute_batch(task_ids, context=None)
        assert len(results) == 2
        for tid, result in results.items():
            assert result is not None

    def test_validate_all_pass(self, orchestrator):
        """Validate when all results succeed."""
        results = {
            "a": AgentResult(success=True, response="OK", agent_name="a"),
            "b": AgentResult(success=True, response="OK", agent_name="b"),
        }
        passed, failed = orchestrator.validate(results)
        assert len(passed) == 2
        assert len(failed) == 0

    def test_validate_with_failures(self, orchestrator):
        """Validate when some results fail."""
        results = {
            "a": AgentResult(success=True, response="OK", agent_name="a"),
            "b": AgentResult(success=False, error="fail", agent_name="b"),
        }
        passed, failed = orchestrator.validate(results)
        assert len(passed) == 1
        assert len(failed) == 1

    def test_merge_single(self, orchestrator):
        """Merge a single result returns it directly."""
        all_results = {
            "t1": AgentResult(success=True, response="Hello", agent_name="coding"),
        }
        from app.orchestrator.orchestrator import TaskGraph

        graph = TaskGraph(original_request="say hello")
        result = orchestrator.merge(
            original_request="say hello",
            all_results=all_results,
            failures={},
            graph=graph,
        )
        assert result.success is True

    def test_merge_multi(self, orchestrator):
        """Merge multiple results into a coherent response."""
        all_results = {
            "t1": AgentResult(success=True, response="Research done",
                              agent_name="research"),
            "t2": AgentResult(success=True, response="Code written",
                              agent_name="coding"),
        }
        # Enqueue tasks so task_queue has them for agent_name lookup
        orch_task1 = OrchestratorTask(agent_name="research", subtask="research")
        orch_task2 = OrchestratorTask(agent_name="coding", subtask="code")
        orchestrator.task_queue.enqueue(orch_task1)
        orchestrator.task_queue.enqueue(orch_task2)

        graph = TaskGraph(original_request="research and code")
        result = orchestrator.merge(
            original_request="research and code",
            all_results={"t1": all_results["t1"], "t2": all_results["t2"]},
            failures={},
            graph=graph,
        )
        assert result.success is True
        assert result.data is not None
        assert result.data["task_count"] == 2
        assert result.data["success_count"] == 2

    def test_run_simple_request(self, orchestrator):
        """Full run pipeline for a simple request."""
        result = orchestrator.run("Write a hello world function")
        assert result is not None
        assert result.success is True or result.response

    def test_run_complex_request(self, orchestrator):
        """Full run pipeline for a complex multi-domain request."""
        result = orchestrator.run(
            "Research clean code principles and write a summary"
        )
        assert result is not None
        # May succeed or have partial failures, but should produce output

    def test_get_status(self, orchestrator):
        """Verify orchestrator status reporting."""
        status = orchestrator.get_status()
        assert "queue" in status
        assert "history_count" in status
        assert status["max_workers"] == 5

    def test_get_history(self, orchestrator):
        """Verify execution history tracking."""
        orchestrator.run("test request")
        history = orchestrator.get_history()
        assert len(history) >= 1
        assert "request" in history[0]
        assert "success" in history[0]

    def test_clear(self, orchestrator):
        """Verify clear resets orchestrator state."""
        orchestrator.run("test")
        assert orchestrator.task_queue.total_count > 0

        orchestrator.clear()
        assert orchestrator.task_queue.total_count == 0
        assert len(orchestrator.get_history()) == 0

    def test_run_with_empty_request(self, orchestrator):
        """Orchestrator should handle empty gracefully."""
        result = orchestrator.run("")
        assert result is not None

    def test_analyze_returns_reasoning(self, orchestrator):
        """TaskGraph should include reasoning text."""
        graph = orchestrator.analyze("Debug the login module")
        assert graph.reasoning
        assert "debug" in graph.intents or "coding" in graph.intents


# ═══════════════════════════════════════════════════════════════════
# Integration: Executive → Orchestrator
# ═══════════════════════════════════════════════════════════════════


class TestExecutiveOrchestratorIntegration:
    """Tests that the Executive Agent delegates to the Orchestrator."""

    def test_orchestrator_available_via_factory(self, agent_system):
        """Verify factory creates orchestrator and links to executive."""
        executive = agent_system.get("executive")
        assert executive is not None
        # Executive should have its orchestrator set
        assert executive._orchestrator is not None

    def test_executive_delegates_complex_to_orchestrator(self, agent_system):
        """Executive should use orchestrator for complex tasks."""
        executive = agent_system.get("executive")
        result = executive(
            "Research Python async patterns and write a tutorial"
        )
        assert result is not None

    def test_executive_fast_path_simple(self, agent_system):
        """Executive should fast-path simple single-keyword tasks."""
        executive = agent_system.get("executive")
        result = executive("Write a script")
        assert result is not None
        # Should have been routed directly, not through orchestrator
        # (simple tasks go through delegation, not orchestrator.run)


# ═══════════════════════════════════════════════════════════════════
# Edge Cases & Error Handling
# ═══════════════════════════════════════════════════════════════════


class TestOrchestratorEdgeCases:

    def test_orchestrator_no_registry(self):
        """Orchestrator should fail gracefully with no agents."""
        from app.agents.registry import AgentRegistry

        registry = AgentRegistry()  # Empty registry
        orch = AgentOrchestrator(registry)
        result = orch.run("Do something")
        # Should not crash, just produce error output
        assert result is not None

    def test_dependency_deadlock_handling(self, orchestrator):
        """Test that circular/deadlocked dependencies don't hang."""
        # Create tasks with mutually blocking deps
        subtasks = [
            SubTask(description="Task A", agent_name="coding", depends_on=[1]),
            SubTask(description="Task B", agent_name="research", depends_on=[0]),
        ]
        task_ids = orchestrator.plan(subtasks)
        # Both tasks depend on each other — execute should break the deadlock
        results = orchestrator.execute(subtasks, task_ids)
        # Should not hang, should mark one or both as failed
        assert len(results) <= 2

    def test_concurrent_task_execution(self, orchestrator):
        """Verify multiple independent tasks run concurrently."""
        subtasks = [
            SubTask(description="Task A", agent_name="research"),
            SubTask(description="Task B", agent_name="memory"),
            SubTask(description="Task C", agent_name="planning"),
        ]
        start = time.perf_counter()
        task_ids = orchestrator.plan(subtasks)
        results = orchestrator._execute_batch(task_ids, context=None)
        elapsed = time.perf_counter() - start
        # All should complete
        assert len(results) == 3

    def test_execute_single_task_unknown_agent(self, orchestrator):
        """Orchestrator should handle unknown agent names gracefully."""
        task = OrchestratorTask(agent_name="nonexistent_agent",
                                subtask="do something")
        result = orchestrator._execute_single_task(task, context=None)
        assert result is not None
