"""
AND9 — Agent Orchestrator (Phase 4).

The Orchestrator is the "CEO" of the multi-agent system. It receives
user goals, analyzes them, decomposes complex tasks into subtasks,
enqueues them, executes them (in parallel where possible), validates
results, retries failures, merges outputs, and returns a coherent
final answer.

Architecture:
    AgentOrchestrator
        ├── TaskQueue (priority-ordered task queue)
        ├── analyze(request) → TaskGraph
        ├── decompose(task) → list[SubTask]
        ├── enqueue(subtasks) → task_ids
        ├── execute_parallel() → dict[task_id, Result]
        ├── validate(results) → (passed, failed)
        ├── retry(failed) → retried_results
        ├── merge(results) → AgentResult
        └── respond(result) → str

Usage:
    from app.and9.orchestrator import AgentOrchestrator, TaskQueue

    orchestrator = AgentOrchestrator(registry)
    result = orchestrator.run("Research quantum computing and write a summary")
"""

from app.and9.orchestrator.task_queue import TaskQueue, OrchestratorTask, TaskPriority
from app.and9.orchestrator.orchestrator import AgentOrchestrator, TaskGraph, SubTask

__all__ = [
    "TaskQueue",
    "OrchestratorTask",
    "TaskPriority",
    "AgentOrchestrator",
    "TaskGraph",
    "SubTask",
]
