"""
Phase 3 — Query Understanding Pipeline.

Orchestrates the full processing flow:
    Input → Normalize → Tokenize → Intent → Entities → Context → Planner → Skill Router

Each stage is a discrete step that returns StageResult with confidence.
The pipeline stops early if confidence falls below thresholds.

Usage:
    pipeline = QueryPipeline()
    result = await pipeline.process("open whatsapp")
    print(result.intent, result.confidence)
"""

import time
import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Awaitable

from .config import QueryConfig
from .models import QueryRequest, QueryResult, PipelineTrace

logger = logging.getLogger(__name__)


class PipelineStage(str, Enum):
    """Stages in the query understanding pipeline."""

    INPUT = "input"
    NORMALIZE = "normalize"
    TOKENIZE = "tokenize"
    INTENT = "intent"
    ENTITIES = "entities"
    CONTEXT = "context"
    PLAN = "plan"
    ROUTE = "route"
    COMPLETE = "complete"


@dataclass
class StageResult:
    """Result from a single pipeline stage."""

    stage: PipelineStage
    success: bool = True
    confidence: float = 1.0
    error: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    time_ms: float = 0.0


# Type alias for pipeline stage handlers
StageHandler = Callable[[Dict[str, Any]], Awaitable[StageResult]]


class QueryPipeline:
    """Configurable query understanding pipeline.

    Stages are registered and executed sequentially.
    Each stage receives and returns a shared context dict.
    """

    def __init__(self, config: Optional[QueryConfig] = None):
        self.config = config or QueryConfig()
        self._stages: List[tuple[PipelineStage, StageHandler]] = []
        self._setup_default_stages()

    def _setup_default_stages(self):
        """Register default pipeline stages as pass-throughs.

        Each stage can be overridden by registering a handler.
        """
        # Default: pass-through stages that just record the stage
        for stage in PipelineStage:
            if stage != PipelineStage.COMPLETE:
                self.register_stage(stage, self._passthrough_stage(stage))

    @staticmethod
    def _passthrough_stage(stage: PipelineStage) -> StageHandler:
        """Create a pass-through handler for a stage."""
        async def handler(ctx: Dict[str, Any]) -> StageResult:
            return StageResult(stage=stage, data={"passed": True})
        return handler

    def register_stage(self, stage: PipelineStage, handler: StageHandler) -> None:
        """Register or override a handler for a pipeline stage.

        Args:
            stage: The stage to register.
            handler: Async function that receives the context dict
                     and returns a StageResult.

        The context dict carries data between stages.
        Key entries:
            "query": str — the input query
            "normalized": str — normalized query
            "tokens": List[str] — tokenized output
            "intent": str — detected intent
            "confidence": float — intent confidence
            "entities": dict — extracted entities
            "context": dict — built context
            "skill": str — routed skill
        """
        # Remove existing handler for this stage if any
        self._stages = [(s, h) for s, h in self._stages if s != stage]
        self._stages.append((stage, handler))
        logger.debug("Pipeline: registered stage '%s'", stage.value)

    # ── Main Processing ─────────────────────────────────────────

    async def process(self, query: str, **kwargs) -> QueryResult:
        """Process a query through the full pipeline.

        Args:
            query: Raw user input.
            **kwargs: Additional context (session_id, etc.)

        Returns:
            QueryResult with full pipeline trace.
        """
        start = time.perf_counter()
        result = QueryResult(query=query)
        ctx: Dict[str, Any] = {
            "query": query,
            "normalized": None,
            "tokens": None,
            "intent": None,
            "confidence": 0.0,
            "entities": {},
            "built_context": {},
            "skill": None,
            "requires_clarification": False,
            "clarification_reason": None,
            **kwargs,
        }

        # Execute stages in order
        for stage_name, handler in self._stages:
            t0 = time.perf_counter()

            try:
                stage_result = await handler(ctx)

                elapsed = (time.perf_counter() - t0) * 1000
                stage_result.time_ms = elapsed

                # Merge stage data into context
                if stage_result.data:
                    ctx.update(stage_result.data)

                # Record trace
                result.trace.append(PipelineTrace(
                    stage=stage_result.stage.value,
                    success=stage_result.success,
                    confidence=stage_result.confidence,
                    time_ms=elapsed,
                    error=stage_result.error,
                    output=stage_result.data,
                ))

                # Check for early stop: low confidence or clarification
                if not stage_result.success:
                    logger.debug("Pipeline stopped at '%s': %s",
                                 stage_result.stage.value, stage_result.error)
                    result.success = False
                    break

                if ctx.get("requires_clarification"):
                    logger.debug("Pipeline stopped at '%s': clarification needed",
                                 stage_result.stage.value)
                    result.requires_clarification = True
                    result.clarification_reason = ctx.get("clarification_reason")
                    break

                # Check timeout
                if elapsed > self.config.pipeline_timeout_ms:
                    logger.warning("Pipeline stage '%s' exceeded timeout (%.0fms)",
                                   stage_result.stage.value, elapsed)
                    result.success = False
                    break

            except Exception as e:
                elapsed = (time.perf_counter() - t0) * 1000
                result.trace.append(PipelineTrace(
                    stage=stage_name.value,
                    success=False,
                    time_ms=elapsed,
                    error=str(e),
                ))
                result.success = False
                logger.error("Pipeline stage '%s' failed: %s", stage_name.value, e)
                break

        # Populate result from context
        result.normalized = ctx.get("normalized")
        result.tokens = ctx.get("tokens")
        result.intent = ctx.get("intent")
        result.intent_confidence = ctx.get("confidence", 0.0)
        result.entities = ctx.get("entities", {})
        result.context = ctx.get("built_context", {})
        result.skill = ctx.get("skill")
        result.requires_clarification = ctx.get("requires_clarification", False)
        result.clarification_reason = ctx.get("clarification_reason")
        result.total_time_ms = (time.perf_counter() - start) * 1000

        # Check overall confidence for clarification
        if (result.intent_confidence < self.config.clarification_confidence_threshold
                and self.config.enable_fallback
                and not result.requires_clarification):
            result.requires_clarification = True
            result.clarification_reason = (
                f"Low confidence ({result.intent_confidence:.2f})"
            )

        return result

    # ── Introspection ───────────────────────────────────────────

    @property
    def registered_stages(self) -> List[str]:
        """Return list of registered stage names in order."""
        return [s.value for s, _ in self._stages]

    def reset(self) -> None:
        """Clear all stage handlers and reset to defaults."""
        self._stages.clear()
        self._setup_default_stages()
