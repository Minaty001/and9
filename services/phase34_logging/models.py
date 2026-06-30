"""
Phase 34 — Logging Models.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class LogEntry(BaseModel):
    """A single structured log entry."""

    level: str = Field(default="INFO", description="Log level")
    service_name: str = Field(default="", description="Service name")
    message: str = Field(default="", description="Log message")
    trace_id: str = Field(default="", description="Trace ID for request tracking")
    module: str = Field(default="", description="Source module")
    function: str = Field(default="", description="Source function")
    line: int = Field(default=0, description="Source line number")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    duration_ms: float = Field(default=0.0, description="Duration in milliseconds")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")
    tags: list = Field(default_factory=list, description="Log entry tags")
    category: str = Field(default="general", description="Log entry category")
    correlation_id: str = Field(default="", description="Correlation ID")
    user_id: str = Field(default="", description="User ID")


class LogQuery(BaseModel):
    """Query parameters for log retrieval."""

    levels: List[str] = Field(default_factory=list, description="Filter by levels")
    start_time: Optional[datetime] = Field(default=None, description="Start time filter")
    end_time: Optional[datetime] = Field(default=None, description="End time filter")
    service_name: str = Field(default="", description="Filter by service name")
    trace_id: str = Field(default="", description="Filter by trace ID")
    correlation_id: str = Field(default="", description="Filter by correlation ID")
    user_id: str = Field(default="", description="Filter by user ID")
    tags: list = Field(default_factory=list, description="Filter by tags")
    search: str = Field(default="", description="Full-text search string")
    limit: int = Field(default=100, ge=1, le=10000, description="Max results")
    offset: int = Field(default=0, ge=0, description="Result offset")


class LogQueryResult(BaseModel):
    """Result of a log query."""

    entries: List[LogEntry] = Field(default_factory=list, description="Matching log entries")
    total_found: int = Field(default=0, description="Total matching entries")
    query_time_ms: float = Field(default=0.0, description="Query execution time")
    truncated: bool = Field(default=False, description="Whether results were truncated")
