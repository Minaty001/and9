"""
app/brain/conscious.py — Deep reasoning brain for AND9

Wraps the existing LLM pipeline (app/core/brain.py).
Used for: research, coding, writing, complex planning,
          long conversations, multi-step workflows.

Target latency: 1-10 seconds depending on task.
"""

import logging
import time
from typing import Optional
from app.core.brain import ask_llm
from app.core.memory import get_memory
from app.core.context_builder import ContextBuilder
from app.core.understanding import MessageAnalysis

logger = logging.getLogger(__name__)


class ConsciousBrain:
    """
    LLM-powered deep reasoning engine.
    Uses Groq (primary) -> Opencode Zen (fallback).
    """

    def __init__(self):
        self._memory = get_memory()
        self._context_builder = ContextBuilder()

    def think(self, query: str, analysis: Optional[MessageAnalysis] = None,
              session_id: int = 0) -> dict:
        """
        Process a complex query using the LLM.
        Returns: {"success": bool, "response": str, "brain": "conscious", ...}
        """
        t_start = time.time()

        try:
            # Build memory context for the template
            if analysis:
                memory_ctx = self._memory.build_memory_context(
                    current_topic=analysis.topic, limit=5
                )
            else:
                memory_ctx = {}

            # Build context string using ContextBuilder
            context = self._context_builder.build(
                user_profile=memory_ctx.get("user_profile", {}),
                emotional_context=memory_ctx.get("emotional_context", {}),
                recent_episodes=memory_ctx.get("recent_episodes", []),
                relevant_past=memory_ctx.get("relevant_past", []),
                current_analysis=analysis,
            )

            # Get recent chat history and append current query
            messages = self._memory.get_recent_chat(4)
            messages = messages + [{"role": "user", "content": query}]

            # Ask LLM with context
            response = ask_llm(
                messages=messages,
                context=context,
            )

            latency_ms = int((time.time() - t_start) * 1000)
            return {
                "success": True,
                "response": response or "I couldn't generate a response. Please try again.",
                "brain": "conscious",
                "latency_ms": latency_ms,
            }

        except Exception as e:
            logger.error(f"ConsciousBrain.think failed: {e}", exc_info=True)
            return {
                "success": False,
                "response": "I encountered an error processing your request.",
                "brain": "conscious",
                "error": str(e),
                "latency_ms": int((time.time() - t_start) * 1000),
            }