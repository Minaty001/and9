"""
Phase 3 — Query Understanding Pipeline
========================================

Orchestrates the full query processing pipeline:
    Input → Normalize → Tokenize → Intent → Entities → Context → Planner → Skill Router

Every stage returns confidence and structured output.
Falls back to clarification when confidence is low.
"""

from .pipeline import QueryPipeline, PipelineStage, StageResult
from .service import QueryUnderstandingService
from .config import QueryConfig
from .models import QueryRequest, QueryResult, PipelineTrace

__all__ = [
    "QueryPipeline",
    "PipelineStage",
    "StageResult",
    "QueryUnderstandingService",
    "QueryConfig",
    "QueryRequest",
    "QueryResult",
    "PipelineTrace",
]
