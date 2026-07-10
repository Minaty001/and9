"""
AND9 — Agent Base: Abstract Base Class for All AI Agents.

Defines the core contract that every agent in the system must fulfill.
Each agent has a role, goal, memory, tools, confidence tracking, logging,
metrics, and health status — forming a self-contained cognitive unit.

Architecture:
    AgentBase (abstract)
        ├── ExecutiveAgent      (CEO — orchestrates swarm)
        ├── ConversationAgent   (natural dialogue)
        ├── PlanningAgent       (task decomposition)
        ├── ResearchAgent       (web research)
        ├── CodingAgent         (code generation)
        ├── DebugAgent          (bug analysis)
        ├── AndroidAgent        (device control)
        ├── MemoryAgent         (memory management)
        ├── LearningAgent       (pattern learning)
        ├── VoiceAgent          (speech I/O)
        ├── BrowserAgent        (browser automation)
        ├── WorkflowAgent       (workflow execution)
        ├── SchedulerAgent      (scheduling)
        ├── AutomationAgent     (rule automation)
        ├── SecurityAgent       (security checks)
        ├── ReflectionAgent     (self-improvement)
        ├── ToolAgent           (tool management)
        ├── IntegrationAgent    (external integrations)
        ├── NotificationAgent   (notifications)
        └── HealthAgent         (system monitoring)
"""

import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Health status of an agent."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    ERROR = "error"
    DISABLED = "disabled"
    STARTING = "starting"


@dataclass
class AgentMemory:
    """Agent-specific memory store.

    Each agent maintains its own lightweight in-memory store for
    task-relevant information. This is distinct from the system-wide
    memory managed by MemoryAgent.

    Attributes:
        short_term: Dict of recent information (auto-expires).
        working_data: Current task working data.
        persistent: Dict of long-term key-value data.
    """
    short_term: dict = field(default_factory=dict)
    working_data: dict = field(default_factory=dict)
    persistent: dict = field(default_factory=dict)

    def remember(self, key: str, value: Any, ttl: int = 300):
        """Store a value with TTL in seconds."""
        self.short_term[key] = {
            "value": value,
            "expires_at": time.time() + ttl,
        }

    def recall(self, key: str) -> Optional[Any]:
        """Retrieve a value if not expired."""
        entry = self.short_term.get(key)
        if entry and entry["expires_at"] > time.time():
            return entry["value"]
        if entry:
            del self.short_term[key]
        return None

    def forget(self, key: str):
        """Remove a value from short-term memory."""
        self.short_term.pop(key, None)

    def clear(self):
        """Clear all memory including persistent data."""
        self.short_term.clear()
        self.working_data.clear()
        self.persistent.clear()


@dataclass
class AgentMetrics:
    """Performance metrics for an agent.

    Tracks invocation count, success/failure rates, average latency,
    and error breakdowns for monitoring and reflection.
    """
    total_invocations: int = 0
    successful_invocations: int = 0
    failed_invocations: int = 0
    total_latency_ms: float = 0.0
    last_invocation_time: Optional[str] = None
    errors: dict[str, int] = field(default_factory=dict)
    tool_usage: dict[str, int] = field(default_factory=dict)

    @property
    def avg_latency_ms(self) -> float:
        if self.total_invocations == 0:
            return 0.0
        return self.total_latency_ms / self.total_invocations

    @property
    def success_rate(self) -> float:
        if self.total_invocations == 0:
            return 1.0
        return self.successful_invocations / self.total_invocations

    def record_success(self, latency_ms: float, tool: Optional[str] = None):
        self.total_invocations += 1
        self.successful_invocations += 1
        self.total_latency_ms += latency_ms
        self.last_invocation_time = datetime.now().isoformat()
        if tool:
            self.tool_usage[tool] = self.tool_usage.get(tool, 0) + 1

    def record_failure(self, latency_ms: float, error: str,
                       tool: Optional[str] = None):
        self.total_invocations += 1
        self.failed_invocations += 1
        self.total_latency_ms += latency_ms
        self.last_invocation_time = datetime.now().isoformat()
        self.errors[error] = self.errors.get(error, 0) + 1
        if tool:
            self.tool_usage[tool] = self.tool_usage.get(tool, 0) + 1

    def to_dict(self) -> dict:
        return {
            "total_invocations": self.total_invocations,
            "successful": self.successful_invocations,
            "failed": self.failed_invocations,
            "success_rate": round(self.success_rate, 3),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "last_invocation": self.last_invocation_time,
            "errors": dict(self.errors),
            "tool_usage": dict(self.tool_usage),
        }


@dataclass
class AgentLog:
    """A single log entry for an agent action."""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    action: str = ""
    input: str = ""
    output: str = ""
    success: bool = True
    latency_ms: float = 0.0
    tool: Optional[str] = None


class AgentResult:
    """Standard result type returned by all agents.

    Attributes:
        success: Whether the agent completed its task.
        response: Natural language response.
        data: Structured data output.
        confidence: Confidence score (0.0 to 1.0).
        agent_name: Name of the agent that produced this result.
        latency_ms: Execution time in milliseconds.
        needs_followup: Whether more work is needed.
        followup_agent: Suggested agent for follow-up.
        error: Error message if failed.
    """

    def __init__(self, success: bool = True, response: str = "",
                 data: Any = None, confidence: float = 1.0,
                 agent_name: str = "", latency_ms: float = 0.0,
                 needs_followup: bool = False,
                 followup_agent: Optional[str] = None,
                 error: Optional[str] = None):
        self.success = success
        self.response = response
        self.data = data if data is not None else {}
        self.confidence = confidence
        self.agent_name = agent_name
        self.latency_ms = latency_ms
        self.needs_followup = needs_followup
        self.followup_agent = followup_agent
        self.error = error

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "response": self.response,
            "data": self.data,
            "confidence": self.confidence,
            "agent_name": self.agent_name,
            "latency_ms": round(self.latency_ms, 2),
            "needs_followup": self.needs_followup,
            "followup_agent": self.followup_agent,
            "error": self.error,
        }

    def __repr__(self) -> str:
        return (f"AgentResult(success={self.success}, "
                f"agent='{self.agent_name}', "
                f"conf={self.confidence:.2f}, "
                f"time={self.latency_ms:.1f}ms)")


class AgentBase(ABC):
    """Abstract base class for all AND9 agents.

    Every agent in the system extends this class and implements
    its abstract methods. The base provides:
      - Identity (name, role, goal)
      - Memory (short-term, working, persistent)
      - Metrics (latency, success rate, error tracking)
      - Logging (action history)
      - Lifecycle (initialize, shutdown, health check)
      - Tool binding

    Subclasses must implement:
      - process()  — main entry point for agent execution
      - _get_system_prompt() — the agent's persona/context prompt

    Usage:
        class MyAgent(AgentBase):
            def __init__(self):
                super().__init__(
                    name="my_agent",
                    role="Does X",
                    goal="Accomplish Y",
                )

            def _get_system_prompt(self) -> str:
                return "You are an agent that..."

            def process(self, input_data: Any) -> AgentResult:
                # Implement agent logic
                pass
    """

    def __init__(self, name: str, role: str, goal: str,
                 backstory: str = "", config: Optional[dict] = None):
        """Initialize the agent.

        Args:
            name: Unique identifier for this agent.
            role: Short description of the agent's purpose.
            goal: What the agent aims to achieve.
            backstory: Extended context about the agent.
            config: Optional configuration dict.
        """
        self.name = name
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.config = config or {}

        self.agent_id = f"{name}_{uuid.uuid4().hex[:8]}"
        self.memory = AgentMemory()
        self.metrics = AgentMetrics()
        self.logs: list[AgentLog] = []
        self.status = AgentStatus.STARTING
        self.tools: dict[str, Callable] = {}
        self._max_logs = 100
        self._initialized = False

        logger.info("Agent '%s' created (id=%s)", name, self.agent_id)

    # ── Abstract Methods ──────────────────────────────────────────

    @abstractmethod
    def process(self, input_data: Any, context: Optional[dict] = None) -> AgentResult:
        """Process input and return a result.

        This is the main entry point for agent execution. Subclasses
        must implement this with their specific logic.

        Args:
            input_data: The input to process (string, dict, etc.).
            context: Optional execution context (current task, user state, etc.).

        Returns:
            AgentResult with the outcome.
        """
        ...

    @abstractmethod
    def _get_system_prompt(self) -> str:
        """Return the system prompt defining this agent's persona.

        Returns:
            String with the agent's role, goals, and behavioral rules.
        """
        ...

    # ── Lifecycle ─────────────────────────────────────────────────

    def initialize(self):
        """Initialize the agent. Called once before first use.

        Override in subclasses for setup logic (loading models,
        connecting to services, etc.).
        """
        self._initialized = True
        self.status = AgentStatus.HEALTHY
        logger.info("Agent '%s' initialized", self.name)

    def shutdown(self):
        """Shutdown the agent. Called during system shutdown.

        Override in subclasses for cleanup (closing connections,
        saving state, etc.).
        """
        self.status = AgentStatus.DISABLED
        logger.info("Agent '%s' shut down", self.name)

    @property
    def is_initialized(self) -> bool:
        """Return whether this agent has been initialized."""
        return self._initialized

    def health_check(self) -> dict:
        """Perform a health check and return status.

        Returns:
            Dict with status, uptime, error count, success rate.
        """
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "status": self.status.value,
            "initialized": self._initialized,
            "total_invocations": self.metrics.total_invocations,
            "success_rate": round(self.metrics.success_rate, 3),
            "error_count": len(self.metrics.errors),
            "avg_latency_ms": round(self.metrics.avg_latency_ms, 2),
            "last_invocation": self.metrics.last_invocation_time,
        }

    # ── Tool Management ───────────────────────────────────────────

    def bind_tool(self, name: str, func: Callable):
        """Register a tool that this agent can use.

        Args:
            name: Tool identifier.
            func: Callable that implements the tool.
        """
        self.tools[name] = func
        logger.debug("Agent '%s' bound tool '%s'", self.name, name)

    def use_tool(self, name: str, *args, **kwargs) -> Any:
        """Execute a bound tool by name.

        Args:
            name: Tool identifier.
            args, kwargs: Passed to the tool function.

        Returns:
            Tool output.

        Raises:
            KeyError: If tool is not bound.
        """
        if name not in self.tools:
            raise KeyError(
                f"Agent '{self.name}' has no tool '{name}'. "
                f"Available: {list(self.tools.keys())}"
            )
        start = time.perf_counter()
        try:
            result = self.tools[name](*args, **kwargs)
            latency = (time.perf_counter() - start) * 1000
            self.metrics.record_success(latency, tool=name)
            logger.debug("Agent '%s' used tool '%s' (%dms)",
                         self.name, name, latency)
            return result
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            self.metrics.record_failure(latency, str(e), tool=name)
            raise

    # ── Logging ───────────────────────────────────────────────────

    def log_action(self, action: str, input_data: str = "",
                   output: str = "", success: bool = True,
                   latency_ms: float = 0.0, tool: Optional[str] = None):
        """Record an action in the agent's log.

        Args:
            action: Description of the action performed.
            input_data: Input that was processed.
            output: Result of the action.
            success: Whether the action succeeded.
            latency_ms: Execution time.
            tool: Tool used, if any.
        """
        entry = AgentLog(
            action=action,
            input=input_data[:200],
            output=str(output)[:500],
            success=success,
            latency_ms=latency_ms,
            tool=tool,
        )
        self.logs.append(entry)
        # Trim logs to max size
        if len(self.logs) > self._max_logs:
            self.logs = self.logs[-self._max_logs:]

    def get_recent_logs(self, n: int = 10) -> list[dict]:
        """Get the N most recent log entries as dicts."""
        return [{
            "timestamp": log.timestamp,
            "action": log.action,
            "success": log.success,
            "latency_ms": round(log.latency_ms, 1),
            "tool": log.tool,
        } for log in self.logs[-n:]]

    # ── Execution Helpers ─────────────────────────────────────────

    def _execute_safely(self, input_data: Any,
                        context: Optional[dict] = None) -> AgentResult:
        """Wrap process() with timing, error handling, and logging.

        This is the safe execution wrapper. External callers should
        use this instead of calling process() directly.

        Args:
            input_data: Input to process.
            context: Optional execution context.

        Returns:
            AgentResult with execution metadata.
        """
        start = time.perf_counter()
        action_desc = str(input_data)[:80]

        try:
            # Ensure initialized
            if not self._initialized:
                self.initialize()

            result = self.process(input_data, context)
            # Guard: ensure process() returned an AgentResult
            if not isinstance(result, AgentResult):
                result = AgentResult(
                    success=True,
                    response=str(result) if result is not None else "",
                    agent_name=self.name,
                )
            latency = (time.perf_counter() - start) * 1000
            result.agent_name = self.name
            result.latency_ms = latency

            if result.success:
                self.metrics.record_success(latency)
                self.status = AgentStatus.HEALTHY
            else:
                self.metrics.record_failure(latency, result.error or "unknown")
                self.status = AgentStatus.DEGRADED

            self.log_action(
                action=f"process:{action_desc}",
                input_data=str(input_data)[:200],
                output=result.response[:200],
                success=result.success,
                latency_ms=latency,
            )
            return result

        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            logger.exception("Agent '%s' execution error: %s", self.name, e)
            self.metrics.record_failure(latency, str(e))
            self.status = AgentStatus.ERROR

            self.log_action(
                action=f"process:{action_desc}",
                input_data=str(input_data)[:200],
                output=f"ERROR: {e}",
                success=False,
                latency_ms=latency,
            )

            return AgentResult(
                success=False,
                response=f"Agent '{self.name}' encountered an error: {e}",
                agent_name=self.name,
                latency_ms=latency,
                error=str(e),
            )

    def __call__(self, input_data: Any,
                 context: Optional[dict] = None) -> AgentResult:
        """Make the agent callable.

        Usage:
            result = my_agent("do something")
        """
        return self._execute_safely(input_data, context)

    # ── Serialization ─────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialize agent state to a dict for API/monitoring."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "goal": self.goal,
            "status": self.status.value,
            "initialized": self._initialized,
            "metrics": self.metrics.to_dict(),
            "tools": list(self.tools.keys()),
            "recent_logs": self.get_recent_logs(5),
        }

    def __repr__(self) -> str:
        return (f"<{self.__class__.__name__} name='{self.name}' "
                f"status={self.status.value} "
                f"tools={len(self.tools)}>")
