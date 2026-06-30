"""
app/agents/__init__.py — Agent registry.

Only ResearchAgent remains; coding and assistant agents were removed
(LLM-dependent). Device actions are handled directly by the conscious
brain pipeline via NeuralBridge.
"""
from app.agents.research.research_agent import ResearchAgent

AGENT_REGISTRY = {
    "research": ResearchAgent,
}

__all__ = ["AGENT_REGISTRY", "ResearchAgent"]
