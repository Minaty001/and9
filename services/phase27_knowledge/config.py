"""
Phase 27 — Knowledge Base Configuration.
"""

from pydantic import Field
from services.base.config_base import BaseConfig


class KnowledgeConfig(BaseConfig):
    """Configuration for the knowledge base."""

    service_name: str = Field(default="jarvis_knowledge", description="Knowledge base service name")
    storage_type: str = Field(default="memory", description="Storage type: memory")
    max_entries: int = Field(default=1000, ge=10, le=100000, description="Max knowledge entries")
    enable_tagging: bool = Field(default=True, description="Enable tag-based organization")
    enable_confidence_scoring: bool = Field(default=True, description="Enable confidence scoring")
    default_confidence_threshold: float = Field(default=0.3, ge=0.0, le=1.0, description="Default confidence threshold")
    enable_import_export: bool = Field(default=True, description="Enable import/export")
    enable_auto_linking: bool = Field(default=True, description="Enable automatic entry linking")

    model_config = {"env_prefix": "JARVIS_PHASE27_"}
