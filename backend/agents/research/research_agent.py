"""
app/agents/research_agent.py — Deep multi-source research agent.

LLM-free: uses DuckDuckGo for search, extractive text for summaries.
"""
from backend.skills.internet.research import search_sources, synthesize_answer


class ResearchAgent:
    name = "ResearchAgent"
    description = "Multi-source research with citations"

    def run(self, query: str, **kwargs) -> dict:
        sources_data = search_sources(query, num=4)
        if not sources_data:
            return {"agent": self.name, "success": False, "result": "No search results found.", "metadata": {}}

        result = synthesize_answer(query, sources_data)
        return {"agent": self.name, "success": True, "result": result, "metadata": {"sources": sources_data[:4]}}
