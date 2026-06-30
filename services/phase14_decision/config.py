"""
Phase 14 — Decision Engine Configuration.
"""

from pydantic import Field
from services.base.config_base import BaseConfig


class DecisionConfig(BaseConfig):
    """Configuration for the decision engine service."""

    service_name: str = Field(default="jarvis_decision", description="Decision engine service name")

    # ── Confidence thresholds ──────────────────────────────────────
    reflex_confidence_threshold: float = Field(default=0.9, ge=0.0, le=1.0,
                                               description="Min confidence to route to reflex brain")
    habit_confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0,
                                              description="Min confidence to route to habit brain")
    conscious_min_confidence: float = Field(default=0.5, ge=0.0, le=1.0,
                                            description="Min confidence for conscious brain routing")

    # ── Routing settings ──────────────────────────────────────────
    enable_escalation: bool = Field(default=True, description="Allow escalation through brain tiers")
    max_decision_time_ms: int = Field(default=500, ge=10, le=30000,
                                      description="Max decision latency before fallback")

    # ── Monitoring ─────────────────────────────────────────────────
    track_latency: bool = Field(default=True, description="Track routing decision latency")
    cost_aware_routing: bool = Field(default=True, description="Consider cost in routing decisions")
    max_cost_per_decision: float = Field(default=0.05, ge=0.0, le=10.0,
                                         description="Max cost in USD per decision")

    model_config = {"env_prefix": "JARVIS_PHASE14_"}
