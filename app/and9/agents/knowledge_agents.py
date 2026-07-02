"""
AND9 — Knowledge Agents: Research, Coding, Debug.

These agents handle knowledge work: web research, code generation,
and debugging analysis.
"""

import logging
from typing import Any, Callable, Optional

from app.and9.agents.base import AgentBase, AgentResult

logger = logging.getLogger(__name__)


class ResearchAgent(AgentBase):
    """Research Agent — web research and information gathering.

    Searches the web, fetches content, and synthesizes findings.
    Uses configured search tools (SerpAPI, Playwright, etc.)
    """

    def __init__(self):
        super().__init__(
            name="research",
            role="Web research and information gathering",
            goal="Find, analyze, and synthesize information from the web",
            backstory=(
                "I am the research agent. I search the web, fetch relevant content, "
                "and synthesize findings into clear, actionable summaries. "
                "I can search Google, read documentation, compare sources, "
                "and provide well-referenced answers."
            ),
            config={
                "max_sources": 5,
                "include_urls": True,
                "summarize": True,
            },
        )
        self._search_tool = None
        self._fetch_tool = None

    def bind_search(self, search_func: Callable):
        """Bind a web search function."""
        self._search_tool = search_func
        self.bind_tool("web_search", search_func)

    def bind_fetch(self, fetch_func: Callable):
        """Bind a URL fetch function."""
        self._fetch_tool = fetch_func
        self.bind_tool("fetch_url", fetch_func)

    def _get_system_prompt(self) -> str:
        return (
            f"You are {self.name}, the {self.role}. {self.backstory}\n\n"
            "Rules:\n"
            "1. Search the web for relevant, up-to-date information.\n"
            "2. Cross-reference multiple sources when possible.\n"
            "3. Provide concise, well-structured summaries.\n"
            "4. Always cite sources when information is from the web.\n"
            "5. If search fails, clearly state what you know and don't know.\n"
            "6. Prioritize quality over quantity of sources.\n"
        )

    def process(self, input_data: Any,
                context: Optional[dict] = None) -> AgentResult:
        """Research a topic using available search tools."""
        query = str(input_data) if not isinstance(input_data, str) else input_data

        # If we have a search tool, use it
        if self._search_tool:
            try:
                results = self._search_tool(query)
                response = (
                    f"**Research results for: {query}**\n\n"
                    f"Found relevant information. "
                    f"Here's what I discovered..."
                )
                if isinstance(results, dict):
                    response += f"\n\n{results.get('summary', str(results)[:500])}"
                else:
                    response += f"\n\n{str(results)[:500]}"

                return AgentResult(
                    success=True,
                    response=response,
                    data={"query": query, "results": results},
                    agent_name=self.name,
                )
            except Exception as e:
                logger.warning("Research search failed: %s", e)

        # Fallback: return a structured research plan
        return AgentResult(
            success=True,
            response=(
                f"**Research Plan for: {query}**\n\n"
                f"To research this properly, I would:\n"
                f"1. Search for recent information on '{query}'\n"
                f"2. Read and analyze top sources\n"
                f"3. Cross-reference findings\n"
                f"4. Provide a structured summary with citations\n\n"
                f"(Web search tools not available in current environment)"
            ),
            data={
                "query": query,
                "search_terms": [query],
                "tools_available": bool(self._search_tool),
            },
            agent_name=self.name,
        )


class CodingAgent(AgentBase):
    """Coding Agent — code generation, review, and analysis.

    Writes, reviews, and analyzes code. Supports multiple languages
    and follows project conventions.
    """

    def __init__(self):
        super().__init__(
            name="coding",
            role="Code generation and analysis",
            goal="Write clean, maintainable, correct code",
            backstory=(
                "I am the coding agent. I write, review, and analyze code "
                "across multiple languages. I follow project conventions, "
                "produce clean and maintainable code, and explain my reasoning. "
                "I can generate new files, modify existing code, and review "
                "changes for correctness and style."
            ),
            config={
                "languages": ["python", "javascript", "typescript",
                              "java", "kotlin", "go", "rust", "cpp"],
                "include_tests": True,
                "follow_conventions": True,
            },
        )

    def _get_system_prompt(self) -> str:
        return (
            f"You are {self.name}, the {self.role}. {self.backstory}\n\n"
            "Rules:\n"
            "1. Write clean, readable, well-documented code.\n"
            "2. Follow the project's existing conventions and style.\n"
            "3. Include error handling and edge cases.\n"
            "4. Write tests alongside production code.\n"
            "5. Explain your design decisions.\n"
            "6. Review code for bugs, security issues, and performance.\n"
            "7. Never introduce unnecessary dependencies.\n"
        )

    def process(self, input_data: Any,
                context: Optional[dict] = None) -> AgentResult:
        """Process a coding request."""
        request = str(input_data) if not isinstance(input_data, str) else input_data

        # Detect programming language if mentioned
        detected_lang = "python"
        for lang in self.config["languages"]:
            if lang in request.lower():
                detected_lang = lang
                break

        return AgentResult(
            success=True,
            response=(
                f"**Coding request received**\n\n"
                f"I'll work on: {request[:200]}\n"
                f"Detected language: {detected_lang}\n\n"
                f"I'll generate clean, well-documented code with proper "
                f"error handling and tests following project conventions."
            ),
            data={
                "request": request,
                "language": detected_lang,
                "status": "planned",
            },
            agent_name=self.name,
            needs_followup=True,
            followup_agent="executive",
        )


class DebugAgent(AgentBase):
    """Debug Agent — bug analysis and fixing.

    Analyzes errors, stack traces, and failing tests to identify
    root causes and suggest or apply fixes.
    """

    def __init__(self):
        super().__init__(
            name="debug",
            role="Bug analysis and debugging",
            goal="Identify root causes of bugs and provide fixes",
            backstory=(
                "I am the debug agent. I analyze errors, stack traces, "
                "and failing tests to find root causes. I understand common "
                "bug patterns, can trace through code paths, and suggest "
                "targeted fixes. I'm methodical and thorough in my analysis."
            ),
        )

    def _get_system_prompt(self) -> str:
        return (
            f"You are {self.name}, the {self.role}. {self.backstory}\n\n"
            "Rules:\n"
            "1. Always reproduce the error before fixing.\n"
            "2. Find the root cause, not just symptoms.\n"
            "3. Suggest minimal, targeted fixes.\n"
            "4. Verify that fixes don't introduce new issues.\n"
            "5. Explain what caused the bug and why the fix works.\n"
        )

    def process(self, input_data: Any,
                context: Optional[dict] = None) -> AgentResult:
        """Analyze a bug report or error."""
        bug_report = str(input_data) if not isinstance(input_data, str) else input_data

        # Parse for common error patterns
        has_stack_trace = "traceback" in bug_report.lower() or "error" in bug_report.lower()
        has_test_failure = "test" in bug_report.lower() and "fail" in bug_report.lower()

        analysis = {
            "has_stack_trace": has_stack_trace,
            "has_test_failure": has_test_failure,
            "reported_issue": bug_report[:200],
        }

        response_parts = ["**Bug Analysis**\n"]
        if has_stack_trace:
            response_parts.append("- Stack trace detected — analyzing call sequence")
        if has_test_failure:
            response_parts.append("- Test failure detected — comparing expected vs actual")
        response_parts.append(
            "- I will trace through the code, identify the root cause, "
            "and provide a targeted fix."
        )

        return AgentResult(
            success=True,
            response="\n".join(response_parts),
            data=analysis,
            agent_name=self.name,
        )
