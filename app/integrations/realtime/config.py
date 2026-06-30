"""
app/integrations/realtime/config.py — Real-Time Info Engine Configuration.
"""

from pydantic import BaseModel, Field


class RealtimeConfig(BaseModel):
    """Configuration for the real-time info engine."""

    service_name: str = Field(default="jarvis_realtime", description="Real-time info service name")
    enable_live_fetch: bool = Field(default=True, description="Enable live data fetching")
    default_cache_ttl_seconds: int = Field(default=120, ge=1, le=86400, description="Default cache TTL")
    enable_source_metadata: bool = Field(default=True, description="Enable source metadata tracking")
    max_concurrent_requests: int = Field(default=5, ge=1, le=50, description="Max concurrent requests")
    freshness_timeout_ms: int = Field(default=3000, ge=100, le=60000, description="Freshness timeout in ms")

    model_config = {"env_prefix": "JARVIS_PHASE22_"}
