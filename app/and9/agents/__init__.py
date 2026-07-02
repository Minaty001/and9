"""
AND9 — Multi-Agent System (Phase 3).

A coordinated team of 20+ specialized AI agents that work together
to handle any user request. Built on the AgentBase abstract class
with a central AgentRegistry for discovery and routing.

Architecture:
    AgentRegistry (service locator)
        ├── Core Agents
        │   ├── Executive      (CEO — orchestrates the swarm)
        │   ├── Conversation   (natural dialogue)
        │   └── Planning       (task decomposition)
        ├── Knowledge Agents
        │   ├── Research       (web research)
        │   ├── Coding         (code generation)
        │   └── Debug          (bug analysis)
        ├── Memory Agents
        │   ├── Memory         (information storage)
        │   ├── Learning       (pattern learning)
        │   └── Reflection     (self-improvement)
        ├── Device Agents
        │   ├── Android        (device control)
        │   ├── Voice          (speech I/O)
        │   └── Browser        (browser automation)
        ├── System Agents
        │   ├── Scheduler      (time-based tasks)
        │   ├── Automation     (rule automation)
        │   ├── Security       (security enforcement)
        │   └── Health         (system monitoring)
        └── Integration Agents
            ├── Tool           (tool registry)
            ├── Integration    (external services)
            ├── Notification   (alerting)
            └── Workflow       (multi-step execution)

Usage:
    from app.and9.agents import create_agent_system, AgentRegistry

    # Create the full system
    registry = create_agent_system()

    # Route a task
    result = registry.route("Write a Python script to sort files")

    # Or use a specific agent
    coding_agent = registry.get("coding")
    result = coding_agent("Write a sorting script")
"""

import logging
from typing import Optional

from app.and9.agents.base import AgentBase, AgentResult, AgentStatus, AgentMemory
from app.and9.agents.registry import AgentRegistry

# Import all agent classes for direct access
from app.and9.agents.core_agents import (
    ExecutiveAgent, ConversationAgent, PlanningAgent,
)
from app.and9.agents.knowledge_agents import (
    ResearchAgent, CodingAgent, DebugAgent,
)
from app.and9.agents.memory_agents import (
    MemoryAgent, LearningAgent, ReflectionAgent,
)
from app.and9.agents.device_agents import (
    AndroidAgent, VoiceAgent, BrowserAgent,
)
from app.and9.agents.system_agents import (
    SchedulerAgent, AutomationAgent, SecurityAgent, HealthAgent,
)
from app.and9.agents.integration_agents import (
    ToolAgent, IntegrationAgent, NotificationAgent, WorkflowAgent,
)

logger = logging.getLogger(__name__)


def create_agent_system(registry: Optional[AgentRegistry] = None,
                        auto_init: bool = True,
                        create_orchestrator: bool = True) -> AgentRegistry:
    """Create and register all agents in the system.

    This factory function instantiates all 20 agents, links them
    to the registry, optionally creates the orchestrator, and
    initializes all components.

    Args:
        registry: Optional existing registry. Creates a new one if None.
        auto_init: If True, call initialize() on all agents.
        create_orchestrator: If True, create AgentOrchestrator and
            link it to the Executive agent for complex task handling.

    Returns:
        Configured AgentRegistry with all agents registered.
    """
    if registry is None:
        registry = AgentRegistry()

    # ── Core Agents ──────────────────────────────────────────────
    executive = ExecutiveAgent()
    conversation = ConversationAgent()
    planning = PlanningAgent()

    registry.register(executive)
    registry.register(conversation)
    registry.register(planning)

    # Link executive to registry for delegation
    executive.set_registry(registry)

    # ── Knowledge Agents ─────────────────────────────────────────
    registry.register(ResearchAgent())
    registry.register(CodingAgent())
    registry.register(DebugAgent())

    # ── Memory Agents ────────────────────────────────────────────
    registry.register(MemoryAgent())
    registry.register(LearningAgent())
    registry.register(ReflectionAgent())

    # ── Device Agents ────────────────────────────────────────────
    registry.register(AndroidAgent())
    registry.register(VoiceAgent())
    registry.register(BrowserAgent())

    # ── System Agents ────────────────────────────────────────────
    registry.register(SchedulerAgent())
    registry.register(AutomationAgent())
    registry.register(SecurityAgent())
    registry.register(HealthAgent())

    # ── Integration Agents ───────────────────────────────────────
    registry.register(ToolAgent())
    registry.register(IntegrationAgent())
    registry.register(NotificationAgent())
    registry.register(WorkflowAgent())

    logger.info(
        "Agent system created with %d agents",
        registry.count(),
    )

    # ── Create Orchestrator ─────────────────────────────────────────
    if create_orchestrator:
        from app.and9.orchestrator import AgentOrchestrator

        orchestrator = AgentOrchestrator(registry)
        # Link orchestrator to executive agent
        executive.set_orchestrator(orchestrator)
        logger.info("Orchestrator created and linked to executive agent")
    else:
        orchestrator = None

    # Auto-initialize if requested
    if auto_init:
        registry.initialize_all()

    return registry


# ── Convenience Exports ──────────────────────────────────────────

__all__ = [
    # Core classes
    "AgentBase",
    "AgentResult",
    "AgentStatus",
    "AgentMemory",
    "AgentRegistry",

    # Factory
    "create_agent_system",

    # Agent classes (for direct instantiation if needed)
    "ExecutiveAgent",
    "ConversationAgent",
    "PlanningAgent",
    "ResearchAgent",
    "CodingAgent",
    "DebugAgent",
    "MemoryAgent",
    "LearningAgent",
    "ReflectionAgent",
    "AndroidAgent",
    "VoiceAgent",
    "BrowserAgent",
    "SchedulerAgent",
    "AutomationAgent",
    "SecurityAgent",
    "HealthAgent",
    "ToolAgent",
    "IntegrationAgent",
    "NotificationAgent",
    "WorkflowAgent",
]
