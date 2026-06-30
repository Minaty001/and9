"""
Phase 14 — Decision Engine Data Models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ── Data Classes ───────────────────────────────────────────────────────


@dataclass
class DecisionRequest:
    """A request to decide which brain should handle a query."""

    query: str
    intent: str = ""
    confidence: float = 0.5
    entities: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    available_brains: List[str] = field(default_factory=lambda: ["reflex", "habit", "conscious"])
    latency_budget_ms: int = 1000
    max_cost: float = 0.05

    def has_brain(self, brain: str) -> bool:
        """Check if a brain is available."""
        return brain in self.available_brains


@dataclass
class DecisionResult:
    """The result of a routing decision."""

    selected_brain: str = ""
    confidence: float = 0.0
    reasoning: str = ""
    routing_path: List[str] = field(default_factory=list)
    latency_ms: float = 0.0
    estimated_cost: float = 0.0
