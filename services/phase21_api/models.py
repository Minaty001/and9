"""
Phase 21 — API Manager Models.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class ApiRequest(BaseModel):
    """An API request to be executed by an adapter."""

    endpoint: str = Field(..., description="API endpoint URL or path")
    method: str = Field(default="GET", description="HTTP method: GET/POST/PUT/DELETE")
    headers: Dict[str, str] = Field(default_factory=dict, description="Request headers")
    params: Dict[str, str] = Field(default_factory=dict, description="URL query parameters")
    body: Any = Field(default=None, description="Request body data")
    timeout_ms: Optional[int] = Field(default=None, description="Request-specific timeout in ms")
    retry_count: Optional[int] = Field(default=None, description="Request-specific retry count")
    adapter_name: Optional[str] = Field(default=None, description="Specific adapter to use")


class ApiResponse(BaseModel):
    """An API response returned by an adapter."""

    success: bool = Field(..., description="Whether the request succeeded")
    status_code: int = Field(default=200, description="HTTP status code")
    data: Any = Field(default=None, description="Response data payload")
    headers: Dict[str, str] = Field(default_factory=dict, description="Response headers")
    duration_ms: float = Field(default=0.0, description="Request duration in ms")
    cached: bool = Field(default=False, description="Whether response was from cache")
    error: Optional[str] = Field(default=None, description="Error message if request failed")
