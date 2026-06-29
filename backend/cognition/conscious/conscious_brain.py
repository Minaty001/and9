"""
AND9 — Conscious Brain: Dataset-Trained Neural Reasoning.

The Conscious Brain handles complex queries using the micro_brain's
TinyNeuralNetwork — a <2MB, NumPy-based model trained on intent data.

This replaces the old LLM-powered Orchestrator. No external API calls.
Responses typically take <50ms instead of 1-5s.

Pipeline:
    1. NeuralBridge.process(query) → intent classification + template response
    2. For SEARCH_WEB intent: DuckDuckGo inline results
    3. For REMINDER intent: route to events system
    4. For other intents: template response + action dispatch
"""
import logging
import time
from typing import Optional

from backend.cognition.planner.brain_types import BrainResult, BrainType, IntentType

logger = logging.getLogger(__name__)


class ConsciousBrain:
    """AND9's dataset-trained neural reasoning layer.

    Uses the micro_brain's TinyNeuralNetwork for intent classification.
    No external API calls, no LLM dependency.

    Attributes:
        bridge: Lazy-loaded NeuralBridge instance.
    """

    # ── Intent string → IntentType enum ──────────────────────────
    INTENT_MAP = {
        "OPEN_APP":          IntentType.OPEN_APP,
        "CLOSE_APP":         IntentType.CLOSE_APP,
        "PLAY_MUSIC":        IntentType.PLAY_MUSIC,
        "PAUSE_MUSIC":       IntentType.PAUSE_MUSIC,
        "SEARCH_WEB":        IntentType.SEARCH,
        "WEATHER":           IntentType.SEARCH,
        "TIME":              IntentType.TIME,
        "DATE":              IntentType.DATE,
        "REMINDER":          IntentType.SET_REMINDER,
        "CALL":              IntentType.CALL,
        "MESSAGE":           IntentType.MESSAGE,
        "CAMERA":            IntentType.CAMERA,
        "FLASHLIGHT_ON":     IntentType.FLASHLIGHT,
        "FLASHLIGHT_OFF":    IntentType.FLASHLIGHT,
        "VOLUME_UP":         IntentType.VOLUME_UP,
        "VOLUME_DOWN":       IntentType.VOLUME_DOWN,
        "HOME":              IntentType.GO_HOME,
        "BACK":              IntentType.GO_BACK,
        "SETTING":           IntentType.OPEN_SETTINGS,
    }
    DEFAULT_INTENT = IntentType.CHAT

    def __init__(self):
        self._bridge = None
        self._loaded = False

    def execute(self, query: str) -> BrainResult:
        """Process a query using the dataset-trained neural network.

        Args:
            query: The user query.

        Returns:
            BrainResult with response text, action, payload.
        """
        start = time.perf_counter()
        try:
            bridge = self._get_bridge()
            result = bridge.process(query)

            elapsed = (time.perf_counter() - start) * 1000
            intent_type = self.INTENT_MAP.get(
                result.get("intent", ""), self.DEFAULT_INTENT
            )

            return BrainResult(
                response=result.get("response", ""),
                action=result.get("action", "chat"),
                payload={},
                brain=BrainType.CONSCIOUS,
                intent=intent_type,
                execution_time_ms=elapsed,
                success=result.get("success", True),
            )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            logger.error("Conscious brain error: %s", e, exc_info=True)
            return BrainResult(
                response="Mujhe samajhne mein problem aa rahi hai. Thodi der baad try karo! 😅",
                action="chat",
                brain=BrainType.CONSCIOUS,
                intent=IntentType.CHAT,
                execution_time_ms=elapsed,
                success=False,
            )

    def _get_bridge(self):
        """Lazy-load the NeuralBridge."""
        if not self._loaded:
            from backend.cognition.neural.bridge import NeuralBridge
            self._bridge = NeuralBridge()
            self._loaded = True
        return self._bridge
