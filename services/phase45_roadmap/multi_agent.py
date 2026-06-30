"""
Phase 45 — Multi-Agent Orchestrator.

Manages a pool of agents, assigns tasks, and tracks agent status.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from .models import AgentSpec, AgentTask
from .config import RoadmapConfig

logger = logging.getLogger(__name__)


class MultiAgentOrchestrator:
    """Orchestrates multiple agents in a multi-agent system.

    Usage:
        mao = MultiAgentOrchestrator()
        agent = AgentSpec(id='a1', name='Helper', role='assistant', capabilities=['search'])
        mao.register_agent(agent)
        task = mao.assign_task('a1', 'Search the web')
        status = mao.get_agent_status('a1')
    """

    def __init__(self, config: Optional[RoadmapConfig] = None):
        self.config = config or RoadmapConfig()
        self._agents: Dict[str, AgentSpec] = {}
        self._tasks: Dict[str, AgentTask] = {}

    def register_agent(self, agent: AgentSpec) -> str:
        """Register a new agent.

        Args:
            agent: The AgentSpec to register.

        Returns:
            The agent ID.
        """
        if len(self._agents) >= self.config.multi_agent_max_agents:
            raise RuntimeError(f"Maximum number of agents ({self.config.multi_agent_max_agents}) reached")
        self._agents[agent.id] = agent
        logger.info("Registered agent '%s' (id=%s, role=%s)", agent.name, agent.id, agent.role)
        return agent.id

    def assign_task(self, agent_id: str, description: str, priority: int = 0) -> AgentTask:
        """Assign a task to an agent.

        Args:
            agent_id: The agent to assign the task to.
            description: Task description.
            priority: Task priority.

        Returns:
            The created AgentTask.
        """
        if agent_id not in self._agents:
            raise ValueError(f"Agent not found: {agent_id}")

        task_id = uuid.uuid4().hex[:12]
        task = AgentTask(
            id=task_id,
            agent_id=agent_id,
            description=description,
            priority=priority,
        )
        self._tasks[task_id] = task
        logger.info("Assigned task '%s' to agent '%s'", task_id, agent_id)
        return task

    def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """Get the status of an agent.

        Args:
            agent_id: The agent to query.

        Returns:
            Dict with agent info and current task count.
        """
        agent = self._agents.get(agent_id)
        if not agent:
            return {"error": f"Agent not found: {agent_id}"}

        active_tasks = [t for t in self._tasks.values() if t.agent_id == agent_id and t.status in ("pending", "running")]
        return {
            "agent_id": agent.id,
            "agent_name": agent.name,
            "role": agent.role,
            "capabilities": agent.capabilities,
            "active_tasks": len(active_tasks),
            "total_tasks": sum(1 for t in self._tasks.values() if t.agent_id == agent_id),
        }

    def orchestrate(self, description: str, required_capabilities: Optional[List[str]] = None) -> Optional[AgentTask]:
        """Find the best agent for a task and assign it.

        Args:
            description: Task description.
            required_capabilities: Capabilities the agent must have.

        Returns:
            The assigned AgentTask, or None if no suitable agent found.
        """
        candidates = list(self._agents.values())
        if required_capabilities:
            candidates = [
                a for a in candidates
                if all(cap in a.capabilities for cap in required_capabilities)
            ]

        if not candidates:
            logger.warning("No suitable agent found for task: %s", description)
            return None

        # Pick the agent with the highest priority and fewest active tasks
        def sort_key(agent: AgentSpec) -> tuple:
            active = sum(1 for t in self._tasks.values() if t.agent_id == agent.id and t.status == "running")
            return (-agent.priority, active)

        best = sorted(candidates, key=sort_key)[0]
        return self.assign_task(best.id, description)

    def list_agents(self) -> List[AgentSpec]:
        """List all registered agents."""
        return list(self._agents.values())

    def list_tasks(self, agent_id: Optional[str] = None) -> List[AgentTask]:
        """List tasks, optionally filtered by agent."""
        if agent_id:
            return [t for t in self._tasks.values() if t.agent_id == agent_id]
        return list(self._tasks.values())
