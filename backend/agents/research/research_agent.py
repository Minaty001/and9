"""
app/agents/research_agent.py — Deep multi-source research agent.

Fetches web pages, summarizes with LLM, synthesizes final answer with citations.
"""
from backend.integrations.groq.brain import ask_llm
from backend.skills.internet.research import search_sources, fetch_page, summarize_source

SYNTH_SYSTEM = """You are a research analyst. Given multiple source excerpts about a topic,
synthesize a comprehensive, accurate, well-structured answer.
Format: Start with a clear answer, then provide details, then list key facts.
Cite sources inline like [Source 1]. Be factual and concise."""


class ResearchAgent:
    name = "ResearchAgent"
    description = "Multi-source research with citations"

    def run(self, query: str, **kwargs) -> dict:
        sources_data = search_sources(query, num=4)
        if not sources_data:
            return {"agent": self.name, "success": False, "result": "No search results found.", "metadata": {}}

        summaries = []
        sources = []
        for i, item in enumerate(sources_data[:4], 1):
            url = item.get("link", "")
            title = item.get("title", f"Source {i}")
            content = fetch_page(url)
            if content:
                summary = summarize_source(content, query, source_num=i)
                summaries.append(f"[Source {i}] {title}:\n{summary}")
                sources.append({"num": i, "title": title, "url": url})

        if not summaries:
            return {"agent": self.name, "success": False, "result": "Could not retrieve content.", "metadata": {}}

        combined = "\n\n".join(summaries)
        final = ask_llm(
            [{"role": "user", "content": f"Research question: {query}\n\nSource summaries:\n{combined}\n\nProvide a comprehensive answer with citations."}],
            system=SYNTH_SYSTEM,
            max_tokens=4096,
        )

        source_lines = "\n".join([f"  [{s['num']}] {s['title']} — {s['url']}" for s in sources])
        full = f"{final}\n\nSources:\n{source_lines}"

        return {"agent": self.name, "success": True, "result": full, "metadata": {"sources": sources}}
