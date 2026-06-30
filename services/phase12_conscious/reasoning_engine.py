"""
Phase 12 — Reasoning Engine.

Structured multi-step reasoning with chain-of-thought, plan-then-execute,
and ReAct strategies. Tracks citations and tool provenance.
"""

from __future__ import annotations

import re
import time
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from .config import ConsciousConfig
from .llm_client import LLMClient
from .prompt_manager import PromptManager
from .models import (
    Conversation, Message, Role, Citation, CitationType,
    ToolCall, Provenance, UsageStats, ReasoningStrategy,
)

logger = logging.getLogger(__name__)


# ── Reasoning Step ──────────────────────────────────────────────────


@dataclass
class ReasoningStep:
    """A single step in the reasoning process."""
    step_number: int
    description: str
    strategy: ReasoningStrategy
    input_summary: str = ""
    output: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)
    citations: List[Citation] = field(default_factory=list)
    duration_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None


# ── Reasoning Result ────────────────────────────────────────────────


@dataclass
class ReasoningResult:
    """The complete result of a reasoning process."""
    final_answer: str = ""
    steps: List[ReasoningStep] = field(default_factory=list)
    provenance: Provenance = field(default_factory=Provenance)
    usage: UsageStats = field(default_factory=UsageStats)
    total_duration_ms: float = 0.0
    strategy: ReasoningStrategy = ReasoningStrategy.CHAIN_OF_THOUGHT

    def add_step(self, step: ReasoningStep) -> None:
        """Add a reasoning step."""
        self.steps.append(step)
        self.provenance.reasoning_steps.append(
            f"[{step.step_number}] {step.description}: {step.output[:200]}"
        )
        self.provenance.tool_calls.extend(step.tool_calls)
        self.provenance.citations.extend(step.citations)


# ── Reasoning Engine ────────────────────────────────────────────────


class ReasoningEngine:
    """Structured reasoning engine supporting multiple strategies."""

    # Pattern to extract citations from LLM output
    CITATION_RE = re.compile(r'\[(\d+)\]\s*(.*?)(?=\[\d+\]|\Z)', re.DOTALL)
    CITATION_INLINE_RE = re.compile(r'\[src:([^\]]+)\]')
    TOOL_CALL_RE = re.compile(r'```tool\n(.*?)```', re.DOTALL)

    def __init__(
        self,
        config: ConsciousConfig,
        llm_client: LLMClient,
        prompt_manager: PromptManager,
    ):
        self.config = config
        self.llm = llm_client
        self.prompts = prompt_manager

    # ── Main entry point ──────────────────────────────────────────

    async def reason(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        strategy: Optional[ReasoningStrategy] = None,
    ) -> ReasoningResult:
        """Execute a reasoning process on a query.

        Args:
            query: User query to reason about.
            context: Optional context (user info, history, etc.).
            strategy: Reasoning strategy to use.

        Returns:
            ReasoningResult with final answer and step details.
        """
        strategy = strategy or ReasoningStrategy.CHAIN_OF_THOUGHT
        t0 = time.perf_counter()
        result = ReasoningResult(strategy=strategy)

        try:
            if strategy == ReasoningStrategy.DIRECT:
                await self._execute_direct(query, context, result)
            elif strategy == ReasoningStrategy.CHAIN_OF_THOUGHT:
                await self._execute_cot(query, context, result)
            elif strategy == ReasoningStrategy.PLAN_THEN_EXECUTE:
                await self._execute_plan_then_execute(query, context, result)
            elif strategy == ReasoningStrategy.REACT:
                await self._execute_react(query, context, result)
            else:
                await self._execute_cot(query, context, result)

        except Exception as e:
            logger.error("Reasoning failed: %s", e)
            step = ReasoningStep(
                step_number=len(result.steps) + 1,
                description="Error handling",
                strategy=strategy,
                success=False,
                error=str(e),
            )
            result.add_step(step)
            result.final_answer = f"I encountered an error during reasoning: {e}"

        result.total_duration_ms = (time.perf_counter() - t0) * 1000
        return result

    # ── Strategy implementations ──────────────────────────────────

    async def _execute_direct(
        self,
        query: str,
        context: Optional[Dict[str, Any]],
        result: ReasoningResult,
    ) -> None:
        """Direct single-turn reasoning without explicit steps."""
        user_context_str = self._format_context(context)
        conv = self.prompts.build_reasoning(query, user_context_str)
        response = await self.llm.complete(conv)

        step = ReasoningStep(
            step_number=1,
            description="Direct response",
            strategy=ReasoningStrategy.DIRECT,
            output=response.content,
            duration_ms=response.duration_ms,
        )
        result.add_step(step)
        result.usage = response.usage
        result.final_answer = response.content

    async def _execute_cot(
        self,
        query: str,
        context: Optional[Dict[str, Any]],
        result: ReasoningResult,
    ) -> None:
        """Chain-of-thought reasoning with explicit thinking steps."""
        system_prompt = (
            "You are JARVIS, a reasoning AI. Think step by step. "
            "Provide your reasoning in a clear, structured manner. "
            "At the end, give a concise final answer.\n\n"
            f"User context: {self._format_context(context)}"
        )
        conv = Conversation(system_prompt=system_prompt)
        conv.add_message(
            Role.USER,
            f"{query}\n\nThink step by step, then provide your final answer.",
        )

        response = await self.llm.complete(conv)

        # Parse steps from the response
        raw = response.content
        steps = self._parse_cot_steps(raw)

        if not steps:
            # No clear step markers — treat whole response as one step
            step = ReasoningStep(
                step_number=1,
                description="Chain-of-thought reasoning",
                strategy=ReasoningStrategy.CHAIN_OF_THOUGHT,
                output=raw,
                duration_ms=response.duration_ms,
            )
            result.add_step(step)
            result.final_answer = raw
        else:
            for i, (desc, output) in enumerate(steps):
                step = ReasoningStep(
                    step_number=i + 1,
                    description=desc or f"Step {i + 1}",
                    strategy=ReasoningStrategy.CHAIN_OF_THOUGHT,
                    output=output,
                    duration_ms=response.duration_ms / max(len(steps), 1),
                )
                result.add_step(step)

            # Final answer is the last step's output
            result.final_answer = steps[-1][1]
            # If last step mentions "Answer:" or "Final:", use what follows
            if ": " in steps[-1][1] and any(
                tag in steps[-1][1].lower() for tag in ["answer", "final", "conclusion"]
            ):
                result.final_answer = steps[-1][1].split(": ", 1)[1]

        result.usage = response.usage

    async def _execute_plan_then_execute(
        self,
        query: str,
        context: Optional[Dict[str, Any]],
        result: ReasoningResult,
    ) -> None:
        """Plan-then-execute: create a plan first, then execute each step."""
        # Step 1: Create a plan
        plan_prompt = (
            f"Query: {query}\n\n"
            f"Context: {self._format_context(context)}\n\n"
            "Create a step-by-step plan to answer this query. "
            "List each step as 'Step N: description'."
        )
        conv = Conversation(system_prompt="You are JARVIS's planning subsystem.")
        conv.add_message(Role.USER, plan_prompt)
        plan_response = await self.llm.complete(conv)

        plan_step = ReasoningStep(
            step_number=1,
            description="Plan creation",
            strategy=ReasoningStrategy.PLAN_THEN_EXECUTE,
            output=plan_response.content,
            duration_ms=plan_response.duration_ms,
        )
        result.add_step(plan_step)
        result.usage = plan_response.usage

        # Step 2: Execute the plan
        execute_prompt = (
            f"Original query: {query}\n\n"
            f"Plan:\n{plan_response.content}\n\n"
            "Execute this plan and provide the final answer."
        )
        conv2 = Conversation(
            system_prompt="Execute the plan and provide a thorough answer."
        )
        conv2.add_message(Role.USER, execute_prompt)
        exec_response = await self.llm.complete(conv2)

        exec_step = ReasoningStep(
            step_number=2,
            description="Plan execution",
            strategy=ReasoningStrategy.PLAN_THEN_EXECUTE,
            output=exec_response.content,
            duration_ms=exec_response.duration_ms,
        )
        result.add_step(exec_step)

        # Accumulate usage
        result.usage.prompt_tokens += exec_response.usage.prompt_tokens
        result.usage.completion_tokens += exec_response.usage.completion_tokens
        result.usage.total_tokens += exec_response.usage.total_tokens

        result.final_answer = exec_response.content

    async def _execute_react(
        self,
        query: str,
        context: Optional[Dict[str, Any]],
        result: ReasoningResult,
    ) -> None:
        """ReAct-style reasoning (Reason + Act)."""
        system_prompt = (
            "You are JARVIS using the ReAct framework. "
            "For each step, output:\n"
            "Thought: <your reasoning>\n"
            "Action: <tool or action name>\n"
            "Observation: <result>\n"
            "...repeat until you have the answer.\n"
            "Final: <answer>\n\n"
            f"Context: {self._format_context(context)}"
        )
        conv = Conversation(system_prompt=system_prompt)
        conv.add_message(Role.USER, query)

        max_react_loops = min(self.config.max_reasoning_steps, 10)
        full_response = ""
        step_num = 0

        for _ in range(max_react_loops):
            response = await self.llm.complete(conv)
            full_response += response.content + "\n"
            step_num += 1

            # Accumulate usage
            result.usage.prompt_tokens += response.usage.prompt_tokens
            result.usage.completion_tokens += response.usage.completion_tokens
            result.usage.total_tokens += response.usage.total_tokens

            # Check for final answer
            if "Final:" in response.content:
                step = ReasoningStep(
                    step_number=step_num,
                    description=f"ReAct loop {step_num}",
                    strategy=ReasoningStrategy.REACT,
                    output=response.content,
                    duration_ms=response.duration_ms,
                )
                result.add_step(step)
                # Extract final answer
                final_idx = response.content.index("Final:")
                result.final_answer = response.content[final_idx + 6:].strip()
                return

            step = ReasoningStep(
                step_number=step_num,
                description=f"ReAct loop {step_num}",
                strategy=ReasoningStrategy.REACT,
                output=response.content,
                duration_ms=response.duration_ms,
            )
            result.add_step(step)

            # Add response to conversation for next iteration
            conv.add_message(Role.ASSISTANT, response.content)
            conv.add_message(Role.USER, "Continue your reasoning. What's the next step?")

        # If we exhausted loops, final answer is the accumulated content
        result.final_answer = full_response

    # ── Parsing helpers ───────────────────────────────────────────

    def _parse_cot_steps(self, text: str) -> List[Tuple[str, str]]:
        """Parse chain-of-thought text into (step_description, content) pairs."""
        steps: List[Tuple[str, str]] = []

        # Try numbered step markers: "Step 1:", "Step 2:", etc.
        step_pattern = re.compile(
            r'(?:Step\s*(\d+)|(\d+)[.\)])\s*[:\-]?\s*(.*?)(?=Step\s*\d|\d+[.\)]|\Z)',
            re.DOTALL | re.IGNORECASE,
        )
        matches = step_pattern.findall(text)
        if matches:
            for num, _, content in matches:
                desc = f"Step {num}" if num else ""
                content = content.strip()
                if content:
                    steps.append((desc, content))
            if steps:
                return steps

        # Try "Reasoning:" / "Answer:" split
        if "Answer:" in text or "Final Answer:" in text:
            parts = re.split(r'(?:Answer|Final Answer)\s*:', text, maxsplit=1)
            if len(parts) == 2:
                steps.append(("Reasoning", parts[0].strip()))
                steps.append(("Answer", parts[1].strip()))
                return steps

        return steps

    def extract_citations(self, text: str) -> List[Citation]:
        """Extract inline citations from text."""
        citations: List[Citation] = []
        for match in self.CITATION_INLINE_RE.finditer(text):
            src = match.group(1)
            citations.append(
                Citation(
                    source_id=src,
                    source_type=CitationType.SYSTEM,
                    excerpt=src,
                )
            )
        return citations

    # ── Utilities ─────────────────────────────────────────────────

    def _format_context(self, context: Optional[Dict[str, Any]]) -> str:
        """Format context dict for prompt inclusion."""
        if not context:
            return "No additional context"
        return json.dumps(context, indent=2, default=str)

    def get_stats(self) -> Dict[str, Any]:
        """Get reasoning engine statistics."""
        return {
            "strategy": self.config.enable_chain_of_thougt,
            "max_steps": self.config.max_reasoning_steps,
            "require_citations": self.config.require_citations,
            "require_provenance": self.config.require_provenance,
        }
