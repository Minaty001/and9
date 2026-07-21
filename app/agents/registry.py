"""AND9 — Agent Registry: Central directory for all agents."""

import logging
from typing import Optional

from app.agents.base import AgentBase, AgentResult, AgentStatus

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Central directory and coordinator for all AND9 agents."""

    # Routing keyword map
    ROUTING_KEYWORDS: dict[str, str] = {
        "code": "coding", "program": "coding", "debug": "debug", "fix": "debug",
        "bug": "debug", "research": "research", "search": "research",
        "plan": "planning", "schedule": "scheduler", "remind": "scheduler",
        "alarm": "scheduler", "timer": "scheduler", "remember": "memory",
        "save": "memory", "learn": "learning", "android": "android",
        "phone": "android", "device": "android", "app": "android",
        "browser": "browser", "web": "browser", "notify": "notification",
        "alert": "notification", "health": "health", "status": "health",
        "security": "security", "permission": "security", "voice": "voice",
        "speak": "voice", "talk": "voice", "workflow": "workflow",
        "automate": "automation", "integration": "integration",
        "connect": "integration", "reflect": "reflection",
        "improve": "learning",
    }

    def __init__(self) -> None:
        self.agents: dict[str, AgentBase] = {}
        self._initialized = False

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
        logger.info("Registered agent '%s' (role: %s)", agent.name, agent.role)
        return agent.name

    def get(self, name: str) -> Optional[AgentBase]:
        """Look up an agent by name."""
        return self.agents.get(name)

    def list_agents(self) -> list[dict]:
        """List all registered agents with summary info."""
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
        """Initialize all registered agents."""
        logger.info("Initializing all %d agents...", len(self.agents))
        errors = []
        for name, agent in self.agents.items():
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


