"""
Phase 14 — Brain Router Core Logic.

Picks the appropriate brain (Reflex / Habit / Conscious) based on
confidence thresholds, latency budget, and cost awareness.
"""

from __future__ import annotations

import time
import logging
from typing import Dict, List, Optional, Tuple

from .config import DecisionConfig
from .models import DecisionRequest, DecisionResult

logger = logging.getLogger(__name__)

# Estimated cost per brain invocation (USD)
BRAIN_COST_ESTIMATES: Dict[str, float] = {
    "reflex": 0.001,
    "habit": 0.005,
    "conscious": 0.05,
}

# Estimated latency per brain invocation (ms)
BRAIN_LATENCY_ESTIMATES: Dict[str, int] = {
    "reflex": 10,
    "habit": 50,
    "conscious": 500,
}


class BrainRouter:
    """Routes requests to the appropriate brain based on confidence and constraints.

    Routing hierarchy:
        1. Reflex brain: confidence >= reflex_confidence_threshold (fastest, cheapest)
        2. Habit brain: confidence >= habit_confidence_threshold
        3. Conscious brain: otherwise (most capable, slowest, most expensive)
    """

    def __init__(self, config: Optional[DecisionConfig] = None):
        self.config = config or DecisionConfig()
        self._brain_order = ["reflex", "habit", "conscious"]

    def route(self, request: DecisionRequest) -> DecisionResult:
        """Pick the best brain for a request.

        Args:
            request: The decision request with query, confidence, and constraints.

        Returns:
            A DecisionResult with the selected brain, reasoning, and routing path.
        """
        t0 = time.perf_counter()
        result = DecisionResult()
        path: List[str] = []

        # Validate available brains
        if not request.available_brains:
            result.selected_brain = "conscious"
            result.confidence = request.confidence
            result.reasoning = "No brains specified, defaulting to conscious"
            result.routing_path = ["conscious"]
            return self._finalize(result, t0)

        # Check confidence-based routing
        selected, reasoning = self._route_by_confidence(request)
        path.append(selected)

        # Check latency budget
        if self.config.track_latency:
            estimated_latency = BRAIN_LATENCY_ESTIMATES.get(selected, 100)
            if estimated_latency > request.latency_budget_ms:
                reasoning += f" (latency {estimated_latency}ms exceeds budget {request.latency_budget_ms}ms)"
                if self.config.enable_escalation:
                    # Try a faster brain
                    faster_brain = self._find_faster_brain(selected, request)
                    if faster_brain:
                        path.append(faster_brain)
                        selected = faster_brain
                        reasoning = f"Latency budget exceeded, rerouted to {faster_brain}"
                        result.estimated_cost = BRAIN_COST_ESTIMATES.get(faster_brain, 0.001)

        # Check cost budget
        if self.config.cost_aware_routing:
            estimated_cost = BRAIN_COST_ESTIMATES.get(selected, 0.05)
            if estimated_cost > request.max_cost and result.estimated_cost == 0.0:
                reasoning += f" (cost {estimated_cost} exceeds budget {request.max_cost})"
                cheaper_brain = self._find_cheaper_brain(selected, request)
                if cheaper_brain:
                    path.append(cheaper_brain)
                    selected = cheaper_brain
                    reasoning = f"Cost budget exceeded, rerouted to {cheaper_brain}"

        if result.estimated_cost == 0.0:
            result.estimated_cost = BRAIN_COST_ESTIMATES.get(selected, 0.05)

        result.selected_brain = selected
        result.confidence = self._adjusted_confidence(selected, request.confidence)
        result.reasoning = reasoning
        result.routing_path = path

        return self._finalize(result, t0)

    def _route_by_confidence(self, request: DecisionRequest) -> Tuple[str, str]:
        """Determine the base brain selection by confidence level."""
        confidence = request.confidence
        threshold_reflex = self.config.reflex_confidence_threshold
        threshold_habit = self.config.habit_confidence_threshold
        threshold_conscious = self.config.conscious_min_confidence

        # Try reflex first (highest threshold)
        if confidence >= threshold_reflex and request.has_brain("reflex"):
            return "reflex", f"Confidence {confidence:.2f} >= {threshold_reflex}, routed to reflex"

        # Try habit next
        if confidence >= threshold_habit and request.has_brain("habit"):
            return "habit", f"Confidence {confidence:.2f} >= {threshold_habit}, routed to habit"

        # Try conscious
        if confidence >= threshold_conscious and request.has_brain("conscious"):
            return "conscious", f"Confidence {confidence:.2f} >= {threshold_conscious}, routed to conscious"

        # Fallback: use the lowest available brain
        for brain in ["reflex", "habit", "conscious"]:
            if request.has_brain(brain):
                return brain, f"Confidence {confidence:.2f} below thresholds, fallback to {brain}"

        # Ultimate fallback
        return "conscious", "No matching brain found, defaulting to conscious"

    def _find_faster_brain(self, current: str, request: DecisionRequest) -> Optional[str]:
        """Find a faster brain than the current one if available."""
        # Faster brains come earlier in the order
        for brain in reversed(self._brain_order):
            if brain == current:
                continue
            if request.has_brain(brain) and BRAIN_LATENCY_ESTIMATES.get(brain, 999) < BRAIN_LATENCY_ESTIMATES.get(current, 999):
                return brain
        return None

    def _find_cheaper_brain(self, current: str, request: DecisionRequest) -> Optional[str]:
        """Find a cheaper brain than the current one if available."""
        current_cost = BRAIN_COST_ESTIMATES.get(current, 0.05)
        for brain in reversed(self._brain_order):
            if brain == current:
                continue
            if request.has_brain(brain) and BRAIN_COST_ESTIMATES.get(brain, 0.05) < current_cost:
                return brain
        return None

    def _adjusted_confidence(self, brain: str, base_confidence: float) -> float:
        """Adjust confidence based on which brain was selected."""
        if brain == "reflex":
            return max(base_confidence, self.config.reflex_confidence_threshold)
        elif brain == "habit":
            return max(base_confidence, self.config.habit_confidence_threshold)
        else:
            return max(base_confidence, self.config.conscious_min_confidence)

    def _finalize(self, result: DecisionResult, start_time: float) -> DecisionResult:
        """Set latency and return."""
        if self.config.track_latency:
            result.latency_ms = round((time.perf_counter() - start_time) * 1000, 3)
        return result
