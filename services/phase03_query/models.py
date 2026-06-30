"""
Phase 3 — Query Understanding Models.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Input to the query understanding pipeline."""

    query: str = Field(..., min_length=1, max_length=500, description="Raw user input")
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class PipelineTrace(BaseModel):
    """Trace of a single pipeline stage."""

    stage: str = Field(..., description="Stage name")
    success: bool = Field(default=True, description="Whether stage succeeded")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Stage confidence")
    time_ms: float = Field(default=0.0, description="Stage execution time in ms")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    output: Optional[Dict[str, Any]] = Field(default=None, description="Stage output")


class QueryResult(BaseModel):
    """Structured output from the query understanding pipeline."""

    # Input
    query: str = Field(..., description="Original query")
    normalized: Optional[str] = Field(default=None, description="Normalized query")

    # Pipeline results
    tokens: Optional[List[str]] = Field(default=None, description="Tokenized query")
    intent: Optional[str] = Field(default=None, description="Detected intent name")
    intent_confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Intent confidence")
    entities: Dict[str, Any] = Field(default_factory=dict, description="Extracted entities")
    context: Dict[str, Any] = Field(default_factory=dict, description="Built context")

    # Routing
    skill: Optional[str] = Field(default=None, description="Routed skill name")
    requires_clarification: bool = Field(default=False, description="Whether clarification is needed")
    clarification_reason: Optional[str] = Field(default=None, description="Why clarification is needed")

    # Execution
    trace: List[PipelineTrace] = Field(default_factory=list, description="Full pipeline trace")
    total_time_ms: float = Field(default=0.0, description="Total processing time")
    success: bool = Field(default=True, description="Overall success")

    # Metadata
    session_id: Optional[str] = Field(default=None)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)
