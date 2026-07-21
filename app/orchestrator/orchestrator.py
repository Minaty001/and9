"""
AND9 — Agent Orchestrator: Multi-Agent Task Coordination Engine.

The AgentOrchestrator is the central coordination engine for the AND9
multi-agent system. It implements a complete execution pipeline:

    analyze → decompose → enqueue → execute_parallel → validate
    → retry → merge → respond

Design principles:
    - Pure Python 3.11+ stdlib (no external dependencies)
    - ThreadPoolExecutor for parallel execution
    - Priority-ordered task queue with dependency tracking
    - Automatic retry with configurable attempts
    - Result validation and coherent merging
    - Full observability via task/result logging

Architecture:
    AgentOrchestrator
        ├── TaskQueue (owned)
        ├── AgentRegistry (reference, not owned)
        ├── run(request) → AgentResult          # Main entry point
        ├── analyze(request) → TaskGraph        # Understand the request
        ├── decompose(task) → list[SubTask]     # Break into pieces
        ├── plan(subtasks) → task_ids           # Enqueue with deps
        ├── execute() → dict                    # Run in parallel
        ├── validate(results) → (ok, fail)      # Check outputs
        ├── retry(failed) → dict                # Retry failures
        ├── merge(results) → AgentResult        # Combine outputs
        └── respond(result) → str               # Format final answer

Usage:
    from app.orchestrator import AgentOrchestrator

    orchestrator = AgentOrchestrator(registry)
    result = orchestrator.run("Research X and write code for Y")
    print(result.response)
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from app.agents.base import AgentResult
from app.agents.registry import AgentRegistry
from app.orchestrator.task_queue import (
    OrchestratorTask,
    TaskPriority,
    TaskQueue,
)

logger = logging.getLogger(__name__)


# ── Supporting Types ────────────────────────────────────────────────


class TaskComplexity(Enum):
    """Complexity level of a task for scheduling decisions."""
    SIMPLE = "simple"          # Single agent, no decomposition
    MODERATE = "moderate"      # 2-3 agents, light coordination
    COMPLEX = "complex"        # 4+ agents, full orchestration


@dataclass
class SubTask:
    """A single unit of work produced during task decomposition.

    Attributes:
        description: What needs to be done.
        agent_name: The target agent for this subtask.
        priority: Importance level.
        depends_on: Indices of subtasks that must complete first.
        timeout_s: Max execution time.
        max_retries: How many times to retry on failure.
        metadata: Arbitrary extra data.
    """
    description: str
    agent_name: str
    priority: TaskPriority = TaskPriority.MEDIUM
    depends_on: list[int] = field(default_factory=list)
    timeout_s: float = 60.0
    max_retries: int = 2
    metadata: dict = field(default_factory=dict)


@dataclass
class TaskGraph:
    """The decomposition graph for a user request.

    Attributes:
        original_request: The raw user input.
        complexity: Estimated complexity.
        intents: List of detected intents/domains.
        subtasks: List of SubTask units.
        reasoning: Short explanation of the decomposition logic.
    """
    original_request: str
    complexity: TaskComplexity = TaskComplexity.SIMPLE
    intents: list[str] = field(default_factory=list)
    subtasks: list[SubTask] = field(default_factory=list)
    reasoning: str = ""


# ── Orchestrator ────────────────────────────────────────────────────


class AgentOrchestrator:
    """Central orchestration engine for the multi-agent system.

    The orchestrator receives a user request, analyzes it, decomposes
    it into subtasks, enqueues them, executes them in parallel (with
    dependency ordering), validates results, retries failures, and
    merges everything into a coherent final response.

    This is the "CEO" of the agent system.
    """

    # Keyword → agent mapping for task decomposition
    DOMAIN_MAP: dict[str, str] = {
        "code": "coding",
        "program": "coding",
        "write": "coding",
        "implement": "coding",
        "debug": "debug",
        "fix": "debug",
        "bug": "debug",
        "research": "research",
        "search": "research",
        "find": "research",
        "plan": "planning",
        "schedule": "scheduler",
        "remind": "scheduler",
        "remember": "memory",
        "save": "memory",
        "learn": "learning",
        "android": "android",
        "phone": "android",
        "browser": "browser",
        "web": "browser",
        "workflow": "workflow",
        "automate": "automation",
        "routine": "automation",
        "security": "security",
        "voice": "voice",
        "reflect": "reflection",
        "improve": "reflection",
        "integrate": "integration",
        "connect": "integration",
        "notify": "notification",
        "alert": "notification",
        "health": "health",
        "monitor": "health",
        "tool": "tool",
    }

    # Compound patterns: two keywords that together suggest one agent
    COMPOUND_PATTERNS: list[tuple[set[str], str]] = [
        ({"research", "code"}, "coding"),     # research then code
        ({"research", "write"}, "coding"),
        ({"research", "plan"}, "planning"),   # research then plan
        ({"debug", "code"}, "debug"),
        ({"schedule", "remind"}, "scheduler"),
    ]

    def __init__(self, registry: AgentRegistry,
                 max_workers: int = 5,
                 default_timeout: float = 60.0,
                 max_retries: int = 2) -> None:
        """Initialize the orchestrator.

        Args:
            registry: The AgentRegistry with all registered agents.
            max_workers: Max parallel threads for task execution.
            default_timeout: Default timeout per task in seconds.
            max_retries: Default retry count per task.
        """
        self.registry = registry
        self.max_workers = max_workers
        self.default_timeout = default_timeout
        self.max_retries = max_retries
        self.task_queue = TaskQueue()

        # Execution history for observability
        self._execution_history: list[dict] = []
        self._max_history = 50

        logger.info(
            "AgentOrchestrator created (workers=%d, timeout=%ds, retries=%d)",
            max_workers, default_timeout, max_retries,
        )

    # ── Main Entry Point ────────────────────────────────────────────

    def run(self, request: str,
            context: Optional[dict] = None) -> AgentResult:
        """Process a user request end-to-end.

        This is the main entry point. It runs the full pipeline:
        analyze → decompose → plan → execute → validate → retry → merge.

        Args:
            request: The user's request string.
            context: Optional execution context.

        Returns:
            AgentResult with the merged final response.
        """
        start_time = time.perf_counter()
        logger.info("Orchestrator received request: %s", request[:80])

        try:
            # Step 1: Analyze the request
            graph = self.analyze(request)

            # Step 2: If simple, route directly (fast path)
            if graph.complexity == TaskComplexity.SIMPLE and len(graph.subtasks) == 1:
                result = self._execute_simple(graph.subtasks[0], context)
                self._record_execution(request, result, time.perf_counter() - start_time)
                return result

            # Step 3: Decompose into subtasks
            if not graph.subtasks:
                graph = self.decompose(request, graph)

            if not graph.subtasks:
                # Fallback: treat as a general conversation
                result = self._route_to_conversation(request, context)
                self._record_execution(request, result, time.perf_counter() - start_time)
                return result

            # Step 4: Plan — enqueue tasks with dependencies
            task_ids = self.plan(graph.subtasks)

            # Step 5: Execute — run all tasks respecting dependencies
            all_results = self.execute(graph.subtasks, task_ids, context)

            # Step 6: Validate results
            passed, failed = self.validate(all_results)

            # Step 7: Retry failures
            if failed and graph.complexity != TaskComplexity.SIMPLE:
                logger.info("Retrying %d failed tasks...", len(failed))
                retry_results = self.retry(failed, context)
                all_results.update(retry_results)
                passed, failed = self.validate(all_results)

            # Step 8: Merge results
            final_result = self.merge(
                original_request=request,
                all_results=all_results,
                failures=failed,
                graph=graph,
            )

            elapsed = time.perf_counter() - start_time
            self._record_execution(request, final_result, elapsed)
            logger.info(
                "Orchestrator completed in %.2fs (success=%s)",
                elapsed, final_result.success,
            )
            return final_result

        except Exception as e:
            elapsed = time.perf_counter() - start_time
            logger.exception("Orchestrator execution error: %s", e)
            error_result = AgentResult(
                success=False,
                response=f"I encountered an error while processing your request: {e}",
                agent_name="orchestrator",
                latency_ms=elapsed * 1000,
                error=str(e),
            )
            self._record_execution(request, error_result, elapsed)
            return error_result

    # ── Step 1: Analyze ─────────────────────────────────────────────

    def analyze(self, request: str) -> TaskGraph:
        """Analyze a request to determine intent, complexity, and domains.

        Args:
            request: The user's request string.

        Returns:
            TaskGraph with detected intents and complexity estimate.
        """
        request_lower = request.lower().strip()
        words = set(request_lower.split())

        # Detect intents/domains via keyword matching
        detected_intents = []
        for keyword, agent_name in self.DOMAIN_MAP.items():
            if keyword in request_lower:
                if agent_name not in detected_intents:
                    detected_intents.append(agent_name)

        # Check compound patterns
        for keywords, agent_name in self.COMPOUND_PATTERNS:
            if keywords.issubset(words) and agent_name not in detected_intents:
                detected_intents.append(agent_name)

        # Determine complexity
        num_intents = len(detected_intents)
        if num_intents == 0:
            complexity = TaskComplexity.SIMPLE
            # General conversation — no specific domain
            detected_intents = ["conversation"]
        elif num_intents == 1:
            complexity = TaskComplexity.SIMPLE
        elif num_intents <= 3:
            complexity = TaskComplexity.MODERATE
        else:
            complexity = TaskComplexity.COMPLEX

        graph = TaskGraph(
            original_request=request,
            complexity=complexity,
            intents=detected_intents,
            reasoning=(
                f"Detected {num_intents} domain(s): {', '.join(detected_intents)}. "
                f"Complexity: {complexity.value}."
            ),
        )
        logger.debug("Analysis: %s", graph.reasoning)
        return graph

    # ── Step 2: Decompose ───────────────────────────────────────────

    def decompose(self, request: str,
                  graph: Optional[TaskGraph] = None) -> TaskGraph:
        """Decompose a request into executable subtasks.

        For simple requests (single domain), creates one subtask.
        For multi-domain requests, creates one subtask per detected
        intent, with dependencies where they make sense.

        Args:
            request: The user's request string.
            graph: Optional TaskGraph from analyze().

        Returns:
            TaskGraph with populated subtasks list.
        """
        if graph is None:
            graph = self.analyze(request)

        intents = graph.intents
        subtasks = []

        if len(intents) == 1:
            # Single intent → single subtask
            agent = intents[0]
            if agent in self.registry.agents or agent == "conversation":
                subtasks.append(SubTask(
                    description=request,
                    agent_name=agent,
                    priority=TaskPriority.HIGH,
                ))
        else:
            # Multi-intent → one subtask per domain
            # Research-like tasks come first, then coding, then rest
            ordered = self._order_intents(intents)
            for i, agent_name in enumerate(ordered):
                if agent_name in self.registry.agents:
                    # Create a focused subtask description
                    sub_desc = self._build_subtask_description(request, agent_name)
                    deps = [j for j in range(i)]  # Sequential dependency chain
                    subtasks.append(SubTask(
                        description=sub_desc,
                        agent_name=agent_name,
                        priority=TaskPriority.HIGH if i == 0 else TaskPriority.MEDIUM,
                        depends_on=deps,
                    ))

        graph.subtasks = subtasks
        logger.debug(
            "Decomposed into %d subtasks: %s",
            len(subtasks),
            [f"{s.agent_name}:{s.description[:30]}" for s in subtasks],
        )
        return graph

    def _order_intents(self, intents: list[str]) -> list[str]:
        """Order intents for logical execution sequence."""
        order_map = {
            "research": 0,
            "planning": 1,
            "coding": 2,
            "debug": 3,
            "memory": 4,
            "reflection": 5,
        }
        return sorted(intents, key=lambda x: order_map.get(x, 9))

    def _build_subtask_description(self, request: str,
                                    agent_name: str) -> str:
        """Build a focused subtask description for a specific agent."""
        return f"{agent_name.title()} task: {request}"

    # ── Step 3: Plan ────────────────────────────────────────────────

    def plan(self, subtasks: list[SubTask]) -> list[str]:
        """Convert SubTask list into enqueued OrchestratorTasks.

        Args:
            subtasks: List of SubTask from decompose().

        Returns:
            List of task IDs in the same order as subtasks.
        """
        task_ids = []
        for i, st in enumerate(subtasks):
            # Map SubTask depends_on indices to actual task IDs
            dep_ids = [task_ids[d] for d in st.depends_on if d < len(task_ids)]

            task = OrchestratorTask(
                agent_name=st.agent_name,
                subtask=st.description,
                priority=st.priority,
                timeout_s=st.timeout_s or self.default_timeout,
                max_retries=st.max_retries or self.max_retries,
                depends_on=dep_ids,
                metadata={"subtask_index": i},
            )
            self.task_queue.enqueue(task)
            task_ids.append(task.id)

        logger.debug("Planned %d tasks with %d dependencies",
                     len(task_ids), sum(len(st.depends_on) for st in subtasks))
        return task_ids

    # ── Step 4: Execute ─────────────────────────────────────────────

    def execute(self, subtasks: list[SubTask],
                task_ids: list[str],
                context: Optional[dict] = None) -> dict[str, AgentResult]:
        """Execute all tasks, respecting dependency ordering.

        Uses ThreadPoolExecutor for parallel execution where possible.
        Tasks with unmet dependencies are deferred until their
        dependencies complete.

        Args:
            subtasks: The original subtask list.
            task_ids: Corresponding task IDs from plan().
            context: Optional execution context.

        Returns:
            Dict of task_id → AgentResult.
        """
        results: dict[str, AgentResult] = {}
        remaining = set(task_ids)
        completed = set()

        while remaining:
            # Find tasks whose dependencies are met
            ready = []
            for tid in remaining:
                task = self.task_queue.get(tid)
                if task is None:
                    continue
                deps_met = all(d in completed for d in task.depends_on)
                if deps_met:
                    ready.append(tid)

            if not ready:
                # Deadlock or all remaining tasks have unmet deps
                for tid in remaining:
                    task = self.task_queue.get(tid)
                    if task and not all(d in completed for d in task.depends_on):
                        # Mark as failed due to dependency failure
                        dep_failures = [
                            d for d in task.depends_on
                            if d in results and not results[d].success
                        ]
                        if dep_failures:
                            results[tid] = AgentResult(
                                success=False,
                                response=f"Dependency failed: {dep_failures[0][:16]}",
                                agent_name=task.agent_name,
                                error="dependency_failed",
                            )
                            self.task_queue.mark_completed(tid, results[tid])
                            completed.add(tid)
                remaining -= completed
                if not ready:
                    break
                continue

            # Execute ready tasks in parallel
            batch_results = self._execute_batch(ready, context)
            results.update(batch_results)

            # Track completion
            for tid in ready:
                completed.add(tid)
                remaining.discard(tid)

        return results

    def _execute_batch(self, task_ids: list[str],
                       context: Optional[dict]) -> dict[str, AgentResult]:
        """Execute a batch of tasks in parallel using threads.

        Args:
            task_ids: List of task IDs whose deps are all met.
            context: Optional execution context.

        Returns:
            Dict of task_id → AgentResult.
        """
        batch_results: dict[str, AgentResult] = {}
        max_workers = min(self.max_workers, len(task_ids))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {}
            for tid in task_ids:
                task = self.task_queue.get(tid)
                if task is None:
                    continue
                future = executor.submit(
                    self._execute_single_task, task, context
                )
                future_map[future] = tid

            for future in as_completed(future_map):
                tid = future_map[future]
                task = self.task_queue.get(tid)
                try:
                    result = future.result()
                    batch_results[tid] = result
                    if result.success:
                        self.task_queue.mark_completed(tid, result)
                    else:
                        self.task_queue.mark_failed(
                            tid, result.error or "unknown_error",
                            retry=True,
                        )
                except Exception as e:
                    logger.error("Task '%s' threw exception: %s", tid[:16], e)
                    error_result = AgentResult(
                        success=False,
                        agent_name=task.agent_name if task else "unknown",
                        error=str(e),
                    )
                    batch_results[tid] = error_result
                    self.task_queue.mark_failed(
                        tid, str(e), retry=True,
                    )

        return batch_results

    def _execute_single_task(self, task: OrchestratorTask,
                              context: Optional[dict]) -> AgentResult:
        """Execute a single task by delegating to the appropriate agent.

        Args:
            task: The task to execute.
            context: Optional execution context.

        Returns:
            AgentResult from the executing agent.
        """
        agent_name = task.agent_name
        logger.debug("Executing task '%s' on agent '%s'",
                     task.id[:16], agent_name)

        # Try delegation through registry
        if agent_name in self.registry.agents:
            try:
                return self.registry.delegate(agent_name, task.subtask, context)
            except Exception as e:
                return AgentResult(
                    success=False,
                    agent_name=agent_name,
                    error=str(e),
                )

        # Fallback: route through registry
        try:
            return self.registry.route(task.subtask, context)
        except Exception as e:
            return AgentResult(
                success=False,
                agent_name="orchestrator",
                error=str(e),
            )

    def _execute_simple(self, subtask: SubTask,
                        context: Optional[dict]) -> AgentResult:
        """Fast path for simple single-agent tasks.

        Bypasses the queue/execute machinery for efficiency.
        """
        logger.debug("Fast path: executing '%s' on agent '%s'",
                     subtask.description[:40], subtask.agent_name)
        return self._execute_single_task(
            OrchestratorTask(
                agent_name=subtask.agent_name,
                subtask=subtask.description,
            ),
            context,
        )

    def _route_to_conversation(self, request: str,
                                context: Optional[dict]) -> AgentResult:
        """Fallback: route to conversation agent for general chat."""
        if "conversation" in self.registry.agents:
            return self.registry.delegate("conversation", request, context)
        return AgentResult(
            success=True,
            response=f"I understand. You said: \"{request}\"",
            agent_name="orchestrator",
        )

    # ── Step 5: Validate ────────────────────────────────────────────

    def validate(self, results: dict[str, AgentResult]) -> tuple[
            dict[str, AgentResult], dict[str, AgentResult]]:
        """Separate results into passed and failed.

        Args:
            results: Dict of task_id → AgentResult.

        Returns:
            (passed, failed) dicts.
        """
        passed = {}
        failed = {}
        for tid, result in results.items():
            if result.success:
                passed[tid] = result
            else:
                failed[tid] = result

        if failed:
            logger.warning("Validation: %d passed, %d failed",
                           len(passed), len(failed))
        return passed, failed

    # ── Step 6: Retry ───────────────────────────────────────────────

    def retry(self, failed: dict[str, AgentResult],
              context: Optional[dict]) -> dict[str, AgentResult]:
        """Retry failed tasks.

        For each failed task, checks if retries remain and re-executes.

        Args:
            failed: Dict of task_id → failed AgentResult.
            context: Optional execution context.

        Returns:
            Dict of task_id → (possibly retried) AgentResult.
        """
        retry_results = {}
        retry_ids = []

        for tid in failed:
            task = self.task_queue.get(tid)
            if task and task.retry_count < task.max_retries:
                retry_ids.append(tid)
                logger.info("Retrying task '%s' (attempt %d/%d)",
                            tid[:16], task.retry_count + 1, task.max_retries)

        if not retry_ids:
            return retry_results

        # Execute retries in parallel
        retry_results = self._execute_batch(retry_ids, context)
        return retry_results

    # ── Step 7: Merge ───────────────────────────────────────────────

    def merge(self, original_request: str,
              all_results: dict[str, AgentResult],
              failures: dict[str, AgentResult],
              graph: TaskGraph) -> AgentResult:
        """Merge all task results into a coherent final response.

        Combines outputs from multiple agents into a single,
        well-structured response.

        Args:
            original_request: Original user request.
            all_results: All task results (passed + failed).
            failures: Only the failed task results.
            graph: The task graph from analysis.

        Returns:
            Merged AgentResult.
        """
        if not all_results:
            return AgentResult(
                success=False,
                response=f"I couldn't process your request: \"{original_request}\"",
                agent_name="orchestrator",
                error="no_results",
            )

        # If single result, return it directly
        if len(all_results) == 1:
            tid = next(iter(all_results))
            result = all_results[tid]
            result.agent_name = "orchestrator"
            return result

        # Multi-result merge
        success_count = len(all_results) - len(failures)
        total_count = len(all_results)
        all_success = len(failures) == 0

        # Build merged response
        merged_parts = []
        for tid, result in all_results.items():
            task = self.task_queue.get(tid)
            agent_name = task.agent_name if task else "agent"

            if result.success:
                merged_parts.append(result.response)
            else:
                merged_parts.append(
                    f"[{agent_name.title()}] could not complete its part: {result.error}"
                )

        merged_response = "\n\n".join(merged_parts)

        # Build summary
        summary = (
            f"**Request:** {original_request}\n\n"
            f"**Completed:** {success_count}/{total_count} tasks\n"
        )

        if failures:
            summary += "\n**Issues encountered:**\n"
            for tid, result in failures.items():
                task = self.task_queue.get(tid)
                agent_name = task.agent_name if task else "agent"
                summary += f"- {agent_name.title()}: {result.error}\n"

        final_response = f"{summary}\n{merged_response}"

        return AgentResult(
            success=all_success,
            response=final_response,
            data={
                "original_request": original_request,
                "task_count": total_count,
                "success_count": success_count,
                "failure_count": len(failures),
                "complexity": graph.complexity.value,
                "intents": graph.intents,
                "results": {
                    tid: r.to_dict() for tid, r in all_results.items()
                },
            },
            agent_name="orchestrator",
        )

    # ── Observability ───────────────────────────────────────────────

    def _record_execution(self, request: str, result: AgentResult,
                           elapsed: float) -> None:
        """Record an execution in the history log."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "request": request[:100],
            "success": result.success,
            "latency_ms": round(elapsed * 1000, 2),
            "task_count": self.task_queue.total_count,
        }
        self._execution_history.append(entry)
        if len(self._execution_history) > self._max_history:
            self._execution_history = self._execution_history[-self._max_history:]

    def get_history(self, n: int = 10) -> list[dict]:
        """Get recent execution history."""
        return self._execution_history[-n:]

    def get_status(self) -> dict:
        """Get current orchestrator status."""
        return {
            "queue": self.task_queue.to_dict(),
            "history_count": len(self._execution_history),
            "max_workers": self.max_workers,
            "default_timeout_s": self.default_timeout,
            "max_retries": self.max_retries,
        }

    # ── Lifecycle ───────────────────────────────────────────────────

    def clear(self) -> None:
        """Reset the orchestrator state (queue + history)."""
        self.task_queue = TaskQueue()
        self._execution_history.clear()
        logger.info("Orchestrator state cleared")
