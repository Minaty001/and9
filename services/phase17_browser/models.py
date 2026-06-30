"""
Phase 17 — Browser Controller Models.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class BrowserActionResult(BaseModel):
    """Result of a browser action (search, open page, extract, summarize, navigate)."""

    success: bool = Field(default=False, description="Whether the action succeeded")
    action_type: str = Field(default="", description="Type of action (search/open_page/extract/summarize/navigate)")
    url: Optional[str] = Field(default=None, description="URL involved in the action")
    title: Optional[str] = Field(default=None, description="Page title")
    content_preview: Optional[str] = Field(default=None, description="First 500 chars of content")
    extracted_text: Optional[str] = Field(default=None, description="Full extracted text")
    summary: Optional[str] = Field(default=None, description="Generated summary")
    captcha_detected: bool = Field(default=False, description="Whether a CAPTCHA was detected")
    duration_ms: float = Field(default=0.0, description="Action duration in milliseconds")
    error: Optional[str] = Field(default=None, description="Error message if action failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
