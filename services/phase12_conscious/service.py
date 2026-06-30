"""
Phase 12 — Conscious Brain Service.

Wraps LLM client, prompt manager, and reasoning engine in a ServiceBase.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Dict, List, Optional

from services.base.service_base import ServiceBase
from .config import ConsciousConfig
from .llm_client import LLMClient
from .prompt_manager import PromptManager
from .reasoning_engine import ReasoningEngine, ReasoningResult
from .models import (
    Conversation, Message, Role, UsageStats, ReasoningStrategy,
)

logger = logging.getLogger(__name__)


class ConsciousBrainService(ServiceBase):
    """Conscious brain service wrapping LLM client and reasoning engine."""

    def __init__(self, config: Optional[ConsciousConfig] = None):
        super().__init__(name="jarvis_conscious", version="2.0.0")
        self.config = config or ConsciousConfig()
        self.llm_client = LLMClient(self.config)
        self.prompt_manager = PromptManager()
        self.reasoning_engine = ReasoningEngine(
            self.config, self.llm_client, self.prompt_manager,
        )
        self._start_time = 0.0

    async def initialize(self) -> bool:
        """Initialize the conscious brain service."""
        self._start_time = time.time()
        try:
            self._metrics.reset()
            ok = self.llm_client.initialize()
            if ok:
                self._initialized = True
                elapsed = (time.time() - self._start_time) * 1000
                logger.info("ConsciousBrainService initialized in %.0fms", elapsed)
            else:
                logger.error("ConsciousBrainService: LLM client init failed")
            return ok
        except Exception as e:
            logger.error("ConsciousBrainService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        """Shut down the service."""
        logger.info("ConsciousBrainService shutting down...")
        self._initialized = False

    # ── Core API ──────────────────────────────────────────────────

    async def reason(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        strategy: Optional[ReasoningStrategy] = None,
    ) -> ReasoningResult:
        """Execute reasoning on a query.

        Args:
            query: User query.
            context: Optional additional context.
            strategy: Reasoning strategy override.

        Returns:
            ReasoningResult with answer and provenance.
        """
        t0 = time.perf_counter()
        result = await self.reasoning_engine.reason(query, context, strategy)
        elapsed = (time.perf_counter() - t0) * 1000

        self._metrics.counter("reasoning_calls")
        self._metrics.histogram("reasoning_time_ms", elapsed)
        self._metrics.histogram("reasoning_steps", len(result.steps))

        return result

    async def complete(
        self,
        conversation: Conversation,
        **kwargs,
    ) -> Any:
        """Send a conversation directly to the LLM.

        Args:
            conversation: The conversation to complete.

        Returns:
            LLM response.
        """
        return await self.llm_client.complete(conversation, **kwargs)

    async def complete_str(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs,
    ) -> str:
        """Shortcut: single-turn prompt returning content string."""
        return await self.llm_client.complete_str(system_prompt, user_prompt, **kwargs)

    # ── Specialized API ───────────────────────────────────────────

    async def plan(
        self,
        goal: str,
        available_tools: List[str],
        context: str = "",
    ) -> ReasoningResult:
        """Create a plan from a goal."""
        return await self.reason(
            query=f"Plan the following: {goal}",
            context={
                "mode": "planning",
                "goal": goal,
                "available_tools": available_tools,
                "context": context,
            },
            strategy=ReasoningStrategy.PLAN_THEN_EXECUTE,
        )

    async def code(
        self,
        task: str,
        language: str = "python",
        constraints: str = "",
        code_context: str = "",
    ) -> ReasoningResult:
        """Generate code from a task description."""
        conv = self.prompt_manager.build_coding(task, language, constraints, code_context)
        result = ReasoningResult(strategy=ReasoningStrategy.DIRECT)

        try:
            response = await self.llm_client.complete(conv)
            result.final_answer = response.content
            result.usage = response.usage
            result.total_duration_ms = response.duration_ms
        except Exception as e:
            logger.warning("Code generation failed: %s", e)
            result.final_answer = f"LLM unavailable: {e}"

        self._metrics.counter("code_generations")
        return result

    async def summarize(
        self,
        content: str,
        focus: str = "key points",
        max_length: int = 200,
    ) -> ReasoningResult:
        """Summarize content."""
        conv = self.prompt_manager.build_summarization(content, focus, max_length)
        result = ReasoningResult(strategy=ReasoningStrategy.DIRECT)

        try:
            response = await self.llm_client.complete(conv)
            result.final_answer = response.content
            result.usage = response.usage
            result.total_duration_ms = response.duration_ms
        except Exception as e:
            logger.warning("Summarization failed: %s", e)
            result.final_answer = f"LLM unavailable: {e}"

        self._metrics.counter("summarizations")
        return result

    async def ask(
        self,
        query: str,
        system_prompt: str = "",
        temperature: Optional[float] = None,
    ) -> str:
        """Simple question-answering. Returns content string."""
        conv = Conversation(system_prompt=system_prompt)
        conv.add_message(Role.USER, query)
        try:
            response = await self.llm_client.complete(conv, temperature=temperature)
            return response.content
        except Exception as e:
            logger.warning("LLM ask failed: %s", e)
            return f"LLM unavailable: {e}"

    # ── Prompt management ─────────────────────────────────────────

    def register_prompt_template(self, name: str, system: str, user: str, **kwargs) -> None:
        """Register a custom prompt template."""
        from .prompt_manager import PromptTemplate
        template = PromptTemplate(
            name=name,
            system_template=system,
            user_template=user,
            **kwargs,
        )
        self.prompt_manager.register(template)

    def list_prompt_templates(self) -> List[Dict[str, Any]]:
        """List all registered prompt templates."""
        return self.prompt_manager.list_templates()

    # ── Health / Stats ────────────────────────────────────────────

    async def health(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        usage = self.llm_client.get_usage_summary()
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service_name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
            "provider": self.config.provider,
            "model": self.config.model,
            "llm_configured": bool(usage.get("provider")),
            "total_cost_usd": usage.get("total_cost_usd", 0),
        }

    async def stats(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        usage = self.llm_client.get_usage_summary()
        templates = self.prompt_manager.list_templates()
        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            "usage": usage,
            "templates": templates,
            "metrics": self._metrics.snapshot(),
        }
