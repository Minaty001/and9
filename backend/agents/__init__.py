"""
app/agents/__init__.py — Agent registry.

Only 3 agent classes exist. Everything else is routed through internal methods or tools.
"""
from backend.agents.coding.coding_agent import CodingAgent
from backend.agents.research.research_agent import ResearchAgent
from backend.agents.assistant.assistant_agent import AssistantAgent

# Registry: agents are loaded by name
AGENT_REGISTRY = {
    "coding": CodingAgent,
    "research": ResearchAgent,
    "search": AssistantAgent,     # search is a tool, not a separate agent
    "image": AssistantAgent,       # image is a tool, not a separate agent
    "chat": AssistantAgent,
    "device": AssistantAgent,
}

__all__ = ["AGENT_REGISTRY", "CodingAgent", "ResearchAgent", "AssistantAgent"]
