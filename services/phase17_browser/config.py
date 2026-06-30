"""
Phase 17 — Browser Controller Configuration.
"""

from pydantic import Field
from services.base.config_base import BaseConfig


class BrowserConfig(BaseConfig):
    """Configuration for the browser controller service."""

    service_name: str = Field(default="jarvis_browser", description="Browser controller service name")
    default_search_engine: str = Field(default="google", description="Default search engine")
    enable_captcha_detection: bool = Field(default=True, description="Enable CAPTCHA detection")
    max_page_size_chars: int = Field(default=50000, description="Maximum page size to process in characters")
    extract_timeout_ms: int = Field(default=10000, description="Extraction timeout in milliseconds")
    enable_summarization: bool = Field(default=True, description="Enable page summarization")
    user_agent: str = Field(default="Mozilla/5.0 JARVIS", description="User agent string")
    enable_navigation_history: bool = Field(default=True, description="Enable navigation history tracking")
    max_history: int = Field(default=100, description="Maximum navigation history entries")

    model_config = {"env_prefix": "JARVIS_PHASE17_"}
