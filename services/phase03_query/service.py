"""
Phase 3 — Query Understanding Service.

Wraps the QueryPipeline in a ServiceBase interface with
lifecycle management, metrics, and health checks.
"""

import time
import logging
from typing import Any, Dict, Optional

from services.base.service_base import ServiceBase
from .config import QueryConfig
from .pipeline import QueryPipeline, PipelineStage
from .models import QueryRequest, QueryResult

logger = logging.getLogger(__name__)


class QueryUnderstandingService(ServiceBase):
    """Service for understanding user queries through a pipeline.

    Orchestrates normalization, tokenization, intent detection,
    entity extraction, context building, and skill routing.
    """

    def __init__(self, config: Optional[QueryConfig] = None):
        super().__init__(name="jarvis_query", version="1.0.0")
        self.config = config or QueryConfig()
        self.pipeline = QueryPipeline(config=self.config)
        self._start_time = 0.0

    # ── Lifecycle ───────────────────────────────────────────────

    async def initialize(self) -> bool:
        """Initialize the query understanding service."""
        self._start_time = time.time()
        try:
            self._metrics.reset()
            self._metrics.gauge("stages_registered", len(self.pipeline.registered_stages))
            self._initialized = True
            elapsed = (time.time() - self._start_time) * 1000
            logger.info("QueryUnderstandingService initialized in %.0fms with %d stages",
                        elapsed, len(self.pipeline.registered_stages))
            return True
        except Exception as e:
            logger.error("QueryUnderstandingService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        """Shut down the service."""
        logger.info("QueryUnderstandingService shutting down...")
        self._initialized = False

    # ── Processing ──────────────────────────────────────────────

    async def process(self, query: str, **kwargs) -> QueryResult:
        """Process a query through the understanding pipeline.

        Args:
            query: Raw user input.
            **kwargs: Additional context (session_id, etc.).

        Returns:
            QueryResult with pipeline trace.
        """
        if not query or not query.strip():
            return QueryResult(
                query=query,
                success=False,
                requires_clarification=True,
                clarification_reason="Empty query",
            )

        result = await self.pipeline.process(query, **kwargs)
        self._metrics.counter("queries_processed")

        if result.success:
            self._metrics.counter("queries_succeeded")
        elif result.requires_clarification:
            self._metrics.counter("queries_clarification")
        else:
            self._metrics.counter("queries_failed")

        self._metrics.histogram("pipeline_time_ms", result.total_time_ms)
        return result

    async def register_stage_handler(self, stage: PipelineStage, handler) -> None:
        """Register a custom handler for a pipeline stage.

        Args:
            stage: The PipelineStage to handle.
            handler: Async callable accepting a context dict and returning StageResult.
        """
        self.pipeline.register_stage(stage, handler)
        self._metrics.gauge("stages_registered", len(self.pipeline.registered_stages))

    # ── Health / Stats ──────────────────────────────────────────

    async def health(self) -> Dict[str, Any]:
        """Return service health."""
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service_name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
            "pipeline_stages": self.pipeline.registered_stages,
        }

    async def stats(self) -> Dict[str, Any]:
        """Return service statistics."""
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            "pipeline_stages": self.pipeline.registered_stages,
            "metrics": self._metrics.snapshot(),
        }
