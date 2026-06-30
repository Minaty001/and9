"""
AND9 — Neural Bridge: connects cognitive pipeline to micro_brain's TinyNeuralNetwork.

Loads the pre-trained model (<2MB, INT8 quantized), classifies intent,
returns structured result with action + response — zero external API calls.

Usage:
    bridge = NeuralBridge()
    result = bridge.process("hello")
    print(result["intent"], result["response"])
"""

import logging
import os
import sys
import time
from typing import Optional, Dict, Any

from app.brain.neural.responses import get_response, INTENT_TO_ACTION, INTENT_TO_TYPE
from app.brain.neural.rag import RAGEngine, get_rag_response

logger = logging.getLogger(__name__)


class NeuralBridge:
    """Bridge between the main cognitive pipeline and micro_brain neural network.

    On first use, lazy-loads the MicroNeuralBrain (loads model from disk).
    All subsequent calls are <50ms classification without any API call.

    Also includes RAG (Retrieval-Augmented Generation) via RAGEngine to
    personalize template responses with user profile facts.
    """

    def __init__(self):
        self._brain = None
        self._reflex = None
        self._rag = None
        self._loaded = False

    def _ensure_loaded(self):
        """Lazy-load (micro_brain was removed — stub)."""
        if self._loaded:
            return True

        logger.warning("NeuralBridge: micro_brain module removed, using stub")
        self._loaded = True
        return True
            return False

    def process(self, query: str) -> Dict[str, Any]:
        """Process a user query through the neural brain pipeline.

        Pipeline:
          1. Reflex brain (keyword match) — fastest path
          2. Neural brain (TinyNeuralNetwork) — intent classification
          3. Response selection from templates
          4. Action mapping

        Args:
            query: User input string.

        Returns:
            Dict with:
                intent:      micro_brain intent name (e.g. "OPEN_APP")
                confidence:  float 0-1
                action:      action type string (e.g. "open_app")
                response:    template response string
                brain_type:  "reflex" or "neural"
                success:     bool
        """
        start = time.perf_counter()

        if not query or not query.strip():
            return self._result("UNKNOWN", 0.0, "chat",
                                "Kya karu? Kuch type karo! 😊", "neural", start)

        if not self._ensure_loaded():
            return self._result("UNKNOWN", 0.0, "chat",
                                "Neural brain load nahi ho paya. 😅", "neural", start)

        # Step 1: Try reflex brain (instant keyword match)
        try:
            reflex_intent, reflex_conf, reflex_action = self._reflex.match_intent(query)
            if reflex_action and reflex_conf >= 0.8:
                # Execute the reflex action and get its result
                action_result = self._reflex.execute_action(reflex_action, query)
                msg = action_result.get("message", "Done! ✅")
                return self._result(
                    reflex_intent or "REFLEX",
                    float(reflex_conf),
                    reflex_action.name.lower() if reflex_action else "action",
                    msg,
                    "reflex",
                    start,
                )
        except Exception as e:
            logger.debug("NeuralBridge reflex failed: %s", e)

        # Step 2: Neural network intent classification
        try:
            nn_intent, nn_conf, _ = self._brain.neural.recognize_intent(query)
        except Exception as e:
            logger.warning("NeuralBridge neural classify failed: %s", e)
            return self._result("UNKNOWN", 0.0, "chat",
                                "Samajhne mein problem hui. 😅", "neural", start)

        # Step 3: Retrieve RAG context (user profile facts, relevant episodes)
        rag_ctx = self._get_rag_context(query, nn_intent)

        # Step 4: Map to action and response
        action = INTENT_TO_ACTION.get(nn_intent, "chat")
        default_response = get_response(nn_intent, query)

        # Step 5: Augment response with RAG (skip for search — DuckDuckGo replaces)
        if nn_intent in ("SEARCH_WEB", "WEATHER"):
            response = default_response
        else:
            response = get_rag_response(nn_intent, query, rag_ctx, default_response)

        # Special handling for search (needs DuckDuckGo)
        if nn_intent == "SEARCH_WEB" or nn_intent == "WEATHER":
            try:
                from app.integrations.duckduckgo import web_search
                results = web_search(query, max_results=4)
                if results:
                    lines = [f"🔍 Yeh rahe results:"]
                    for i, r in enumerate(results, 1):
                        lines.append(f"\n{i}. {r['title']}")
                        lines.append(f"   {r['body'][:150]}")
                    response = "\n".join(lines)
                    action = "search"
                else:
                    response = "Search results nahi mile. Kuch aur try karein? 🔍"
            except Exception as e:
                logger.warning("Search failed: %s", e)
                response = "Search karne mein problem hui. Baad mein try karein."

        return self._result(
            nn_intent,
            float(nn_conf),
            action,
            response,
            "neural",
            start,
        )

    def _get_rag_context(self, query: str, intent: str):
        """Lazy-load RAGEngine and retrieve context for the query."""
        if self._rag is None:
            try:
                self._rag = RAGEngine()
            except Exception as e:
                logger.debug("NeuralBridge: RAGEngine init failed: %s", e)
                from app.brain.neural.rag import RAGContext
                return RAGContext()
        try:
            return self._rag.augment(query, intent)
        except Exception as e:
            logger.debug("NeuralBridge: RAG retrieval failed: %s", e)
            from app.brain.neural.rag import RAGContext
            return RAGContext()

    def _result(self, intent: str, confidence: float, action: str,
                response: str, brain_type: str, start: float) -> Dict[str, Any]:
        """Build the result dict."""
        elapsed_ms = (time.perf_counter() - start) * 1000
        intent_type = INTENT_TO_TYPE.get(intent, "CHAT")
        return {
            "intent": intent,
            "intent_type": intent_type,
            "confidence": round(confidence, 4),
            "action": action,
            "response": response,
            "brain_type": brain_type,
            "success": True,
            "time_ms": round(elapsed_ms, 1),
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get neural bridge statistics."""
        stats = {"loaded": self._loaded}
        if self._loaded and self._brain:
            try:
                stats["neural"] = self._brain.neural.get_stats()
                stats["reflex"] = self._brain.reflex.get_stats()
            except Exception as e:
                stats["error"] = str(e)
        return stats
