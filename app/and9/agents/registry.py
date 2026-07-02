"""
AND9 — Agent Registry: Service Locator for All Agents.

The registry acts as a central directory and coordinator for every
agent in the system. It provides:

  - Registration / deregistration of agents
  - Agent lookup by name, role, or capability
  - Lifecycle management (init all, shutdown all)
  - Global health check across all agents
  - Routing to the right agent for a given task
  - Task delegation with context propagation

Architecture:
    AgentRegistry (singleton)
        ├── register(agent)        → add agent to directory
        ├── get(name)              → lookup by name
        ├── route(task, context)   → delegate to best-fit agent
        ├── health_report()        → aggregate health of all agents
        └── broadcast(event)       → notify all relevant agents
"""

import logging
from collections import defaultdict
from datetime import datetime
from typing import Optional

from app.and9.agents.base import AgentBase, AgentResult, AgentStatus

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Central registry and coordinator for all AND9 agents.

    Implements the Service Locator pattern. Agents register themselves
    and the registry provides discovery, routing, and lifecycle management.

    This is a concrete class (not a singleton) — instantiate one per
    application context. For most deployments, a single global registry
    is sufficient.

    Attributes:
        agents: Dict of agent_name → AgentBase instance.
        capability_index: Dict of capability → set of agent names.
        health_cache: Cached health check results.
    """

    # Routing keyword map — class-level constant
    ROUTING_KEYWORDS: dict[str, str] = {
        "code": "coding",
        "program": "coding",
        "write": "coding",
        "debug": "debug",
        "fix": "debug",
        "bug": "debug",
        "research": "research",
        "search": "research",
        "look up": "research",
        "find": "research",
        "plan": "planning",
        "schedule": "scheduler",
        "remind": "scheduler",
        "alarm": "scheduler",
        "timer": "scheduler",
        "remember": "memory",
        "save": "memory",
        "learn": "learning",
        "android": "android",
        "phone": "android",
        "device": "android",
        "app": "android",
        "browser": "browser",
        "web": "browser",
        "internet": "browser",
        "notify": "notification",
        "alert": "notification",
        "health": "health",
        "status": "health",
        "monitor": "health",
        "security": "security",
        "safe": "security",
        "permission": "security",
        "voice": "voice",
        "speak": "voice",
        "talk": "voice",
        "workflow": "workflow",
        "automate": "automation",
        "routine": "automation",
        "integration": "integration",
        "connect": "integration",
        "reflect": "reflection",
        "improve": "learning",
        "update": "learning",
    }

    def __init__(self) -> None:
        self.agents: dict[str, AgentBase] = {}
        self._capability_index: dict[str, set[str]] = defaultdict(set)
        self._registration_order: list[str] = []
        self._initialized = False
        logger.info("AgentRegistry created")

    # ── Registration ─────────────────────────────────────────────

    def register(self, agent: AgentBase) -> str:
        """Register an agent with the registry.

        Args:
            agent: An AgentBase instance.

        Returns:
            The agent's name (for chaining).

        Raises:
            ValueError: If an agent with the same name is already registered.
        """
        if agent.name in self.agents:
            raise ValueError(
                f"Agent '{agent.name}' is already registered. "
                f"Use deregister() first or choose a different name."
            )

        self.agents[agent.name] = agent
        self._registration_order.append(agent.name)

        # Index capabilities from tools
        for tool_name in agent.tools:
            self._capability_index[tool_name].add(agent.name)

        logger.info("Registered agent '%s' (role: %s)", agent.name, agent.role)
        return agent.name

    def deregister(self, name: str) -> bool:
        """Remove an agent from the registry.

        Args:
            name: Agent name to remove.

        Returns:
            True if removed, False if not found.
        """
        if name not in self.agents:
            return False

        agent = self.agents[name]
        agent.shutdown()

        del self.agents[name]
        # Remove from capability index
        for cap_set in self._capability_index.values():
            cap_set.discard(name)
        if name in self._registration_order:
            self._registration_order.remove(name)

        logger.info("Deregistered agent '%s'", name)
        return True

    # ── Lookup ────────────────────────────────────────────────────

    def get(self, name: str) -> Optional[AgentBase]:
        """Look up an agent by name.

        Args:
            name: Agent name (e.g., "executive", "coding", "research").

        Returns:
            Agent instance or None if not found.
        """
        return self.agents.get(name)

    def find_by_role(self, role_keyword: str) -> list[AgentBase]:
        """Find agents whose role contains a keyword.

        Args:
            role_keyword: Keyword to search for in agent roles.

        Returns:
            List of matching agents.
        """
        if not role_keyword:
            return []
        keyword = role_keyword.lower()
        return [
            a for a in self.agents.values()
            if keyword in a.role.lower()
        ]

    def find_by_capability(self, capability: str) -> list[AgentBase]:
        """Find agents that have a specific capability/tool.

        Args:
            capability: Tool or capability name.

        Returns:
            List of agents that have this capability.
        """
        agent_names = self._capability_index.get(capability, set())
        return [self.agents[n] for n in agent_names if n in self.agents]

    def list_agents(self) -> list[dict]:
        """List all registered agents with summary info.

        Returns:
            List of agent summary dicts.
        """
        return [
            {
                "name": a.name,
                "role": a.role,
                "status": a.status.value,
                "initialized": a.is_initialized,
                "invocations": a.metrics.total_invocations,
                "success_rate": round(a.metrics.success_rate, 3),
                "avg_latency_ms": round(a.metrics.avg_latency_ms, 2),
            }
            for a in self.agents.values()
        ]

    def count(self) -> int:
        """Return the number of registered agents."""
        return len(self.agents)

    # ── Lifecycle ─────────────────────────────────────────────────

    def initialize_all(self) -> None:
        """Initialize all registered agents.

        Calls initialize() on each agent. Agents that fail to initialize
        are marked ERROR but not removed.
        """
        logger.info("Initializing all %d agents...", len(self.agents))
        errors = []
        for name in self._registration_order:
            agent = self.agents[name]
            try:
                agent.initialize()
                logger.debug("Agent '%s' initialized OK", name)
            except Exception as e:
                logger.error("Failed to initialize agent '%s': %s", name, e)
                agent.status = AgentStatus.ERROR
                errors.append((name, str(e)))

        self._initialized = True

        if errors:
            logger.warning("Initialization complete with %d error(s)", len(errors))
        else:
            logger.info("All agents initialized successfully")

    def shutdown_all(self) -> None:
        """Shut down all agents gracefully."""
        logger.info("Shutting down all agents...")
        for name in reversed(self._registration_order):
            try:
                self.agents[name].shutdown()
            except Exception as e:
                logger.error("Error shutting down agent '%s': %s", name, e)
        logger.info("All agents shut down")

    # ── Routing ───────────────────────────────────────────────────

    def route(self, task: str, context: Optional[dict] = None,
              preferred_agent: Optional[str] = None) -> AgentResult:
        """Route a task to the most appropriate agent.

        The routing logic:
          1. If a preferred_agent is specified and available, use it.
          2. Check if any agent's name/role matches the task.
          3. Fall back to the executive agent for general tasks.
          4. Fall back to the conversation agent for chat.

        Args:
            task: The task description or input.
            context: Optional execution context.
            preferred_agent: Optional specific agent to route to.

        Returns:
            AgentResult from the selected agent.
        """
        if not task:
            return AgentResult(
                success=False,
                response="No task provided for routing.",
                agent_name="registry",
                error="empty_task",
            )
        task_lower = task.lower().strip() if isinstance(task, str) else str(task).lower().strip()

        # 1. Preferred agent
        if preferred_agent and preferred_agent in self.agents:
            logger.info("Routing to preferred agent '%s'", preferred_agent)
            try:
                return self.agents[preferred_agent](task, context)
            except Exception as e:
                logger.error("Preferred agent '%s' failed: %s", preferred_agent, e)
                return AgentResult(
                    success=False, agent_name=preferred_agent, error=str(e),
                )

        # 2. Keyword-based routing using class-level constant
        for keyword, agent_name in self.ROUTING_KEYWORDS.items():
            if keyword in task_lower and agent_name in self.agents:
                logger.info("Routing task '%s' to agent '%s' (keyword='%s')",
                            task[:50], agent_name, keyword)
                try:
                    return self.agents[agent_name](task, context)
                except Exception as e:
                    logger.error("Agent '%s' failed for task: %s", agent_name, e)
                    return AgentResult(
                        success=False, agent_name=agent_name, error=str(e),
                    )

        # 3. Executive agent (if available)
        if "executive" in self.agents:
            logger.info("Routing general task to executive agent")
            try:
                return self.agents["executive"](task, context)
            except Exception as e:
                logger.error("Executive agent failed: %s", e)
                return AgentResult(
                    success=False, agent_name="executive", error=str(e),
                )

        # 4. Fallback to conversation agent
        if "conversation" in self.agents:
            logger.info("Routing fallback to conversation agent")
            try:
                return self.agents["conversation"](task, context)
            except Exception as e:
                logger.error("Conversation agent failed: %s", e)
                return AgentResult(
                    success=False, agent_name="conversation", error=str(e),
                )

        # 5. No suitable agent
        logger.warning("No suitable agent found for task: %s", task[:50])
        return AgentResult(
            success=False,
            response="No suitable agent found for this task.",
            error="no_suitable_agent",
        )

    def route_to_all(self, task: str,
                     context: Optional[dict] = None) -> dict[str, AgentResult]:
        """Route a task to ALL agents (for broadcast/reflection).

        Args:
            task: The task description.
            context: Optional execution context.

        Returns:
            Dict of agent_name → AgentResult.
        """
        results = {}
        for name, agent in self.agents.items():
            try:
                results[name] = agent(task, context)
            except Exception as e:
                results[name] = AgentResult(
                    success=False,
                    agent_name=name,
                    error=str(e),
                )
        return results

    # ── Delegation (Executive Agent support) ──────────────────────

    def delegate(self, agent_name: str, subtask: str,
                 context: Optional[dict] = None) -> AgentResult:
        """Delegate a subtask to a specific agent.

        Used by the Executive Agent to split work across the swarm.

        Args:
            agent_name: Target agent name.
            subtask: The subtask description.
            context: Optional execution context.

        Returns:
            AgentResult from the target agent.
        """
        if agent_name not in self.agents:
            return AgentResult(
                success=False,
                response=f"Agent '{agent_name}' not found in registry.",
                agent_name="registry",
                error=f"agent_not_found:{agent_name}",
            )
        try:
            return self.agents[agent_name](subtask, context)
        except Exception as e:
            logger.error("Delegate to '%s' failed: %s", agent_name, e)
            return AgentResult(
                success=False,
                agent_name=agent_name,
                error=str(e),
            )

    def delegate_parallel(self, assignments: list[tuple[str, str]],
                          context: Optional[dict] = None) -> dict[str, AgentResult]:
        """Delegate multiple subtasks sequentially.

        Despite the name, this currently executes delegations sequentially.
        For true parallelism, use threading/asyncio in a future version.

        Args:
            assignments: List of (agent_name, subtask) tuples.
            context: Optional shared context.

        Returns:
            Dict of agent_name → AgentResult.
        """
        results = {}
        for agent_name, subtask in assignments:
            results[agent_name] = self.delegate(agent_name, subtask, context)
        return results

    # ── Health & Monitoring ───────────────────────────────────────

    def health_report(self) -> dict:
        """Aggregate health status of all agents.

        Returns:
            Dict with overall status and per-agent health info.
        """
        total = len(self.agents)
        healthy = sum(1 for a in self.agents.values()
                      if a.status == AgentStatus.HEALTHY)
        degraded = sum(1 for a in self.agents.values()
                       if a.status == AgentStatus.DEGRADED)
        error_count = sum(1 for a in self.agents.values()
                          if a.status == AgentStatus.ERROR)
        disabled = sum(1 for a in self.agents.values()
                       if a.status == AgentStatus.DISABLED)

        # Determine overall status
        if error_count > 0:
            overall = "error"
        elif degraded > 0:
            overall = "degraded"
        elif healthy == total and total > 0:
            overall = "healthy"
        elif disabled == total and total > 0:
            overall = "disabled"
        else:
            overall = "starting"

        return {
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall,
            "total_agents": total,
            "healthy": healthy,
            "degraded": degraded,
            "error": error_count,
            "disabled": disabled,
            "agents": {
                name: a.health_check()
                for name, a in self.agents.items()
            },
        }

    # ── Event Broadcasting ────────────────────────────────────────

    def broadcast(self, event: str, data: Optional[dict] = None) -> None:
        """Broadcast an event to all agents that have relevant capabilities.

        Args:
            event: Event type (e.g., "task_completed", "user_input").
            data: Event payload.
        """
        logger.debug("Broadcasting event '%s' to all agents", event)
        for agent in self.agents.values():
            try:
                handler = getattr(agent, 'on_event', None)
                if callable(handler):
                    handler(event, data or {})
            except Exception as e:
                logger.warning("Agent '%s' failed to handle event '%s': %s",
                               agent.name, event, e)

    # ── Serialization ─────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialize registry state."""
        return {
            "agent_count": self.count(),
            "initialized": self._initialized,
            "agents": self.list_agents(),
            "health": self.health_report(),
        }
