"""
Phase 12 — Conscious Brain Configuration.
"""

from pydantic import Field
from services.base.config_base import BaseConfig


class ConsciousConfig(BaseConfig):
    """Configuration for the conscious brain (LLM invocation)."""

    service_name: str = Field(default="jarvis_conscious", description="Conscious brain service name")

    # ── Provider settings ────────────────────────────────────────
    provider: str = Field(default="openai", description="LLM provider: openai, anthropic, local")
    model: str = Field(default="gpt-4o", description="Model name")
    api_base: str = Field(default="", description="Custom API base URL")
    api_key_env: str = Field(default="JARVIS_LLM_API_KEY", description="Env var holding the API key")
    max_retries: int = Field(default=3, ge=0, le=10, description="Max invocation retries")
    retry_delay_ms: int = Field(default=1000, ge=100, le=60000, description="Base retry delay (ms)")
    timeout_ms: int = Field(default=30000, ge=1000, le=300000, description="Request timeout (ms)")

    # ── Generation params ────────────────────────────────────────
    temperature: float = Field(default=0.3, ge=0.0, le=2.0, description="LLM temperature")
    max_tokens: int = Field(default=4096, ge=64, le=32768, description="Max output tokens")
    top_p: float = Field(default=0.95, ge=0.0, le=1.0, description="Top-p sampling")
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="Frequency penalty")
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="Presence penalty")

    # ── Context management ───────────────────────────────────────
    max_context_tokens: int = Field(default=128000, ge=1024, le=1024000, description="Max context window")
    reserved_output_tokens: int = Field(default=4096, ge=512, le=32768, description="Tokens reserved for response")
    summary_threshold_tokens: int = Field(default=96000, ge=1024, le=512000, description="Tokens above which summarization triggers")

    # ── Reasoning ────────────────────────────────────────────────
    enable_chain_of_thought: bool = Field(default=True, description="Enable CoT reasoning")
    require_citations: bool = Field(default=True, description="Require citations in responses")
    require_provenance: bool = Field(default=True, description="Track tool provenance")
    max_reasoning_steps: int = Field(default=10, ge=1, le=50, description="Max reasoning steps")

    # ── Fallback ─────────────────────────────────────────────────
    fallback_provider: str = Field(default="", description="Fallback provider if primary fails")
    fallback_model: str = Field(default="", description="Fallback model name")
    enable_fallback: bool = Field(default=True, description="Enable fallback to simpler model")

    # ── Cost control ─────────────────────────────────────────────
    max_cost_per_call: float = Field(default=0.50, ge=0.0, le=100.0, description="Max USD per call before warning")
    budget_alert_threshold: float = Field(default=10.0, ge=0.0, le=1000.0, description="Daily budget alert (USD)")
    track_usage: bool = Field(default=True, description="Track token usage and cost")

    model_config = {"env_prefix": "JARVIS_CONSCIOUS_"}
