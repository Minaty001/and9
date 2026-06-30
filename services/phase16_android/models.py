"""
Phase 16 — Android Controller Models.

Data models for Android actions and their results.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AndroidAction(BaseModel):
    """Represents an action to perform on the Android device."""

    action_type: str = Field(
        ...,
        description="Type of action: launch_app / media_control / notification / clipboard / volume / brightness / accessibility",
    )
    target: str = Field(default="", description="Target of the action (app name, media command, etc.)")
    params: Dict[str, Any] = Field(default_factory=dict, description="Additional parameters for the action")
    timeout_ms: Optional[int] = Field(default=None, description="Action-specific timeout override")
    require_confirmation: bool = Field(default=False, description="Whether user confirmation is required")


class AndroidActionResult(BaseModel):
    """Result of executing an Android action."""

    success: bool = Field(default=True, description="Whether the action succeeded")
    action_type: str = Field(..., description="The type of action that was executed")
    target: str = Field(default="", description="The target of the action")
    result_data: Optional[Any] = Field(default=None, description="Result data (text, dict, etc.)")
    message: str = Field(default="", description="Human-readable result message")
    duration_ms: float = Field(default=0.0, description="Execution duration in milliseconds")
    error: Optional[str] = Field(default=None, description="Error message if action failed")
