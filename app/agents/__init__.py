"""
app/agents/__init__.py — Unified agent system.

Combines the original 3-agent JARVIS agent registry with the AND9
AgentBase/AgentRegistry multi-agent system. Both coexist under one
package — the original AGENT_REGISTRY dict routes by name, while
the AgentRegistry provides full lifecycle management.
"""
from app.agents.coding_agent import CodingAgent
from app.agents.research_agent import ResearchAgent
from app.agents.assistant_agent import AssistantAgent

# Original JARVIS agent registry (simple name-based routing)
AGENT_REGISTRY = {
    "coding": CodingAgent,
    "research": ResearchAgent,
    "search": AssistantAgent,
    "image": AssistantAgent,
    "chat": AssistantAgent,
    "device": AssistantAgent,
}

# AND9 AgentBase system (full lifecycle, metrics, tool binding)
from app.agents.base import AgentBase, AgentResult, AgentStatus, AgentMemory
from app.agents.registry import AgentRegistry
from app.agents.core_agents import (
    ExecutiveAgent, ConversationAgent, PlanningAgent,
)
from app.agents.knowledge_agents import (
    ResearchAgent as KnowledgeResearchAgent,
    CodingAgent as KnowledgeCodingAgent,
    DebugAgent,
)
from app.agents.memory_agents import MemoryAgent, LearningAgent, ReflectionAgent
from app.agents.device_agents import AndroidAgent, VoiceAgent, BrowserAgent
from app.agents.system_agents import (
    SchedulerAgent, HealthAgent, SecurityAgent, AutomationAgent,
)
from app.agents.integration_agents import (
    ToolAgent, IntegrationAgent, WorkflowAgent, NotificationAgent,
)


def create_agent_system(auto_init: bool = False,
                         create_orchestrator: bool = False) -> AgentRegistry:
    """Create and return a fully-populated AgentRegistry.

    Args:
        auto_init: If True, initialize all agents after registration.
        create_orchestrator: If True, create and link an AgentOrchestrator
                             to the executive agent.

    Returns:
        AgentRegistry with all AND9 agent types registered.
    """
    registry = AgentRegistry()

    registry.register(ExecutiveAgent())
    registry.register(ConversationAgent())
    registry.register(PlanningAgent())
    registry.register(KnowledgeResearchAgent())
    registry.register(KnowledgeCodingAgent())
    registry.register(DebugAgent())
    registry.register(MemoryAgent())
    registry.register(LearningAgent())
    registry.register(ReflectionAgent())
    registry.register(AndroidAgent())
    registry.register(VoiceAgent())
    registry.register(BrowserAgent())
    registry.register(SchedulerAgent())
    registry.register(HealthAgent())
    registry.register(SecurityAgent())
    registry.register(AutomationAgent())
    registry.register(ToolAgent())
    registry.register(NotificationAgent())
    registry.register(IntegrationAgent())
    registry.register(WorkflowAgent())

    if auto_init:
        registry.initialize_all()

    if create_orchestrator:
        from app.orchestrator import AgentOrchestrator
        orch = AgentOrchestrator(registry)
        executive = registry.get("executive")
        if executive:
            executive._orchestrator = orch

    return registry


__all__ = [
    "AGENT_REGISTRY",
    "CodingAgent",
    "ResearchAgent",
    "AssistantAgent",
    "AgentBase",
    "AgentResult",
    "AgentStatus",
    "AgentMemory",
    "AgentRegistry",
    "create_agent_system",
    "ExecutiveAgent",
    "ConversationAgent",
    "PlanningAgent",
    "KnowledgeResearchAgent",
    "KnowledgeCodingAgent",
    "DebugAgent",
    "MemoryAgent",
    "LearningAgent",
    "ReflectionAgent",
    "AndroidAgent",
    "VoiceAgent",
    "BrowserAgent",
    "SchedulerAgent",
    "HealthAgent",
    "SecurityAgent",
    "AutomationAgent",
    "ToolAgent",
    "NotificationAgent",
    "IntegrationAgent",
    "WorkflowAgent",
]
