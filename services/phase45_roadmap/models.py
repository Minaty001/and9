"""
Phase 45 — Roadmap Models.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentSpec(BaseModel):
    """Specification for an agent in the multi-agent system."""

    id: str = Field(..., description="Unique agent identifier")
    name: str = Field(..., description="Human-readable agent name")
    role: str = Field(..., description="Agent role (assistant, researcher, etc.)")
    capabilities: List[str] = Field(default_factory=list, description="List of agent capabilities")
    priority: int = Field(default=0, ge=0, description="Task assignment priority (higher = more preferred)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Registration timestamp")


class AgentTask(BaseModel):
    """A task assigned to an agent."""

    id: str = Field(..., description="Unique task identifier")
    agent_id: str = Field(..., description="Agent assigned to this task")
    description: str = Field(..., description="Task description")
    status: str = Field(default="pending", description="Task status: pending, running, completed, failed")
    priority: int = Field(default=0, ge=0, description="Task priority")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Completion timestamp")
    result: Optional[Any] = Field(default=None, description="Task result data")


class MultimodalInput(BaseModel):
    """Input data for multimodal processing."""

    type: str = Field(..., description="Input type: image, audio, video, text")
    data: str = Field(..., description="Base64-encoded data or raw text")
    mime_type: str = Field(default="", description="MIME type of the data")


class PluginListing(BaseModel):
    """A plugin available in the marketplace."""

    id: str = Field(..., description="Unique plugin identifier")
    name: str = Field(..., description="Plugin display name")
    version: str = Field(default="1.0.0", description="Plugin version")
    author: str = Field(default="unknown", description="Plugin author")
    description: str = Field(default="", description="Plugin description")
    rating: float = Field(default=0.0, ge=0.0, le=5.0, description="Average user rating")
    downloads: int = Field(default=0, ge=0, description="Download count")
    categories: List[str] = Field(default_factory=list, description="Plugin categories")
    installed: bool = Field(default=False, description="Whether the plugin is installed")


class WorkflowStep(BaseModel):
    """A single step in a workflow."""

    id: str = Field(..., description="Unique step identifier")
    name: str = Field(..., description="Step name")
    action: str = Field(..., description="Action to perform")
    params: Dict[str, Any] = Field(default_factory=dict, description="Step parameters")
    status: str = Field(default="pending", description="Step status: pending, running, completed, failed, paused")
    depends_on: List[str] = Field(default_factory=list, description="Step IDs that must complete first")
    result: Optional[Any] = Field(default=None, description="Step result data")


class Workflow(BaseModel):
    """A workflow consisting of multiple steps."""

    id: str = Field(..., description="Unique workflow identifier")
    name: str = Field(..., description="Workflow name")
    description: str = Field(default="", description="Workflow description")
    steps: List[WorkflowStep] = Field(default_factory=list, description="Workflow steps")
    status: str = Field(default="pending", description="Workflow status: pending, running, paused, completed, failed")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Last update timestamp")
