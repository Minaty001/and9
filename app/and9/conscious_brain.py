"""
AND9 — Conscious Brain: LLM-Powered Reasoning.

The Conscious Brain handles complex, open-ended tasks that require
language understanding, planning, and creative generation. It wraps
the existing JARVIS Orchestrator (which uses Groq/Dolphin LLM) to
process chat, search, and goal management requests.

This is the "slow" brain — responses typically take 1-5 seconds
depending on LLM response time. It is only invoked when the priority
router determines that a reflex action is insufficient (Chat, Search,
Goal intents).

The Orchestrator is lazy-loaded to avoid import overhead when only
reflex actions are needed. Errors are caught and returned as friendly
Hinglish messages indicating the system is in degraded mode.
"""
import logging
import time
from typing import Optional

from app.and9.brain_types import BrainResult, BrainType, IntentType

logger = logging.getLogger(__name__)


class ConsciousBrain:
    """AND9's LLM-powered cognitive layer.

    Delegates complex queries to the existing JARVIS Orchestrator
    for natural language understanding, web search, goal management,
    and code generation.

    Attributes:
        orchestrator: Lazy-loaded JARVIS Orchestrator instance.
                      None until first execute() call.
    """

    def __init__(self):
        self.orchestrator = None
        self._initialized = False

    def execute(self, query: str) -> BrainResult:
        """Process a query using the JARVIS Orchestrator (LLM).

        Lazy-loads the Orchestrator on first call. Wraps the
        Orchestrator's response in a BrainResult with timing info.

        Args:
            query: The user query (may be Hindi, Hinglish, or English).

        Returns:
            BrainResult with the Orchestrator's response text,
            action, and payload. On error, returns a friendly error
            message indicating the LLM service is unavailable.
        """
        start = time.perf_counter()

        try:
            # Lazy-load orchestrator
            if not self._initialized:
                self._load_orchestrator()

            # Delegate to JARVIS orchestrator
            response = self.orchestrator.run(query)
            elapsed = (time.perf_counter() - start) * 1000

            # Parse orchestrator response
            if isinstance(response, dict):
                return BrainResult(
                    response=response.get("response", str(response)),
                    action=response.get("action") or "chat",
                    payload=response.get("payload"),
                    brain=BrainType.CONSCIOUS,
                    intent=IntentType.CHAT,
                    execution_time_ms=elapsed,
                    metadata={"raw_response": response},
                )

            return BrainResult(
                response=str(response),
                action="chat",
                brain=BrainType.CONSCIOUS,
                intent=IntentType.CHAT,
                execution_time_ms=elapsed,
            )

        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            logger.error("Conscious brain error: %s", e, exc_info=True)

            # Provide meaningful error message based on error type
            error_msg = str(e).lower()
            if "api_key" in error_msg or "api key" in error_msg:
                response_text = (
                    "Meri sochne wali battery low hai — LLM key set nahi hai. "
                    "Kripya GROQ_API_KEY environment variable set karo! 🧠⚡"
                )
            elif "network" in error_msg or "connection" in error_msg:
                response_text = (
                    "Internet connection nahi hai! Kuch der baad try karo. 🌐"
                )
            else:
                response_text = (
                    "Mujhe samajhne mein problem aa rahi hai. "
                    "Kripya thodi der baad try karo! 😅"
                )

            return BrainResult(
                response=response_text,
                action="chat",
                brain=BrainType.CONSCIOUS,
                intent=IntentType.CHAT,
                execution_time_ms=elapsed,
                success=False,
            )

    def _load_orchestrator(self):
        """Lazy-load the JARVIS Orchestrator.

        Loads on first use to avoid import overhead when only
        reflex brains are needed. Imports are done inline to
        keep the module-level imports minimal.

        Raises:
            ImportError: If the JARVIS module is not available.
            Exception: If Orchestrator initialization fails.
        """
        try:
            from app.core.orchestrator import Orchestrator

            self.orchestrator = Orchestrator()
            self._initialized = True
            logger.info("ConsciousBrain: Orchestrator loaded successfully")
        except ImportError as e:
            logger.warning("ConsciousBrain: JARVIS orchestrator not available: %s", e)
            raise
        except Exception as e:
            logger.error("ConsciousBrain: Failed to initialize orchestrator: %s", e)
            raise
