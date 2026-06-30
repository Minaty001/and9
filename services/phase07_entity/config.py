"""
Phase 7 — Entity Extraction Configuration.
"""

from pydantic import Field
from services.base.config_base import BaseConfig


class EntityConfig(BaseConfig):
    """Configuration for entity extraction."""

    service_name: str = Field(default="jarvis_entity", description="Entity extraction service name")
    enable_app_extraction: bool = Field(default=True, description="Enable app name extraction")
    enable_contact_extraction: bool = Field(default=True, description="Enable contact extraction")
    enable_time_extraction: bool = Field(default=True, description="Enable date/time extraction")
    enable_location_extraction: bool = Field(default=True, description="Enable location extraction")
    enable_media_extraction: bool = Field(default=True, description="Enable media extraction")
    min_confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Minimum entity confidence")
    require_validation: bool = Field(default=True, description="Validate entities before returning")

    model_config = {"env_prefix": "JARVIS_ENTITY_"}
