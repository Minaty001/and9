"""
Phase 44 — Continuous Improvement Models.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Feedback(BaseModel):
    """User feedback entry."""

    id: str = Field(..., description="Unique feedback identifier")
    user_id: str = Field(..., description="User who submitted feedback")
    session_id: str = Field(default="", description="Session identifier")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 (worst) to 5 (best)")
    category: str = Field(default="other", description="Category: accuracy, speed, usability, feature, or other")
    comment: str = Field(default="", description="Free-text comment")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Submission timestamp")
    resolved: bool = Field(default=False, description="Whether this feedback has been addressed")


class BenchmarkResult(BaseModel):
    """Result of a single benchmark run."""

    id: str = Field(..., description="Unique benchmark result identifier")
    benchmark_name: str = Field(..., description="Name of the benchmark")
    score: float = Field(default=0.0, description="Benchmark score (higher is better)")
    latency_ms: float = Field(default=0.0, ge=0.0, description="Average latency in milliseconds")
    accuracy: float = Field(default=0.0, ge=0.0, le=1.0, description="Accuracy score (0.0-1.0)")
    memory_bytes: int = Field(default=0, ge=0, description="Memory used in bytes")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Run timestamp")
    version: str = Field(default="", description="Software version when benchmark was run")
    environment: Dict[str, str] = Field(default_factory=dict, description="Environment details")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")


class PromptVersion(BaseModel):
    """A versioned prompt template."""

    id: str = Field(..., description="Unique identifier for this version")
    prompt_name: str = Field(..., description="Logical name of the prompt")
    version: int = Field(default=1, ge=1, description="Version number")
    content: str = Field(..., description="Prompt template content")
    parent_version: Optional[int] = Field(default=None, description="Parent version this was derived from")
    change_reason: str = Field(default="", description="Reason for this version's changes")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    performance_delta: Optional[float] = Field(default=None, description="Change in performance vs parent")
    is_active: bool = Field(default=True, description="Whether this is the active version")


class ABTest(BaseModel):
    """A/B test definition and results."""

    id: str = Field(..., description="Unique test identifier")
    name: str = Field(..., description="Human-readable test name")
    variant_a: Dict[str, Any] = Field(default_factory=dict, description="Control variant configuration")
    variant_b: Dict[str, Any] = Field(default_factory=dict, description="Treatment variant configuration")
    metric: str = Field(default="accuracy", description="Metric being compared")
    sample_size: int = Field(default=0, ge=0, description="Number of samples collected")
    results: Dict[str, Any] = Field(default_factory=dict, description="Results per variant")
    winner: Optional[str] = Field(default=None, description="Winning variant, if determined")
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Test start time")
    ended_at: Optional[datetime] = Field(default=None, description="Test end time")
