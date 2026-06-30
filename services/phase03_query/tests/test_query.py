"""
Tests for Phase 3 — Query Understanding Pipeline.
"""

import pytest
from services.phase03_query import (
    QueryPipeline,
    QueryUnderstandingService,
    QueryConfig,
    QueryRequest,
    QueryResult,
    PipelineStage,
    StageResult,
)


class TestQueryPipeline:
    """Verify the pipeline orchestrator."""

    @pytest.mark.asyncio
    async def test_default_stages(self):
        pipeline = QueryPipeline()
        stages = pipeline.registered_stages
        assert PipelineStage.INPUT.value in stages
        assert PipelineStage.NORMALIZE.value in stages
        assert PipelineStage.INTENT.value in stages
        assert PipelineStage.ROUTE.value in stages

    @pytest.mark.asyncio
    async def test_process_basic(self):
        pipeline = QueryPipeline()
        result = await pipeline.process("hello")
        assert result.query == "hello"
        assert result.success is True
        assert len(result.trace) > 0

    @pytest.mark.asyncio
    async def test_process_trace_order(self):
        pipeline = QueryPipeline()
        result = await pipeline.process("test")
        stage_names = [t.stage for t in result.trace]
        # Should follow PipelineStage enum order
        assert stage_names[0] == PipelineStage.INPUT.value

    @pytest.mark.asyncio
    async def test_custom_stage_handler(self):
        pipeline = QueryPipeline()

        async def custom_normalize(ctx):
            ctx["normalized"] = ctx["query"].upper()
            return StageResult(
                stage=PipelineStage.NORMALIZE,
                data={"normalized": ctx["query"].upper()},
            )

        pipeline.register_stage(PipelineStage.NORMALIZE, custom_normalize)
        result = await pipeline.process("hello")
        assert result.normalized == "HELLO"

    @pytest.mark.asyncio
    async def test_stage_fails_early(self):
        pipeline = QueryPipeline()

        async def failing_stage(ctx):
            return StageResult(
                stage=PipelineStage.INTENT,
                success=False,
                error="Something went wrong",
            )

        pipeline.register_stage(PipelineStage.INTENT, failing_stage)
        result = await pipeline.process("test")
        assert result.success is False
        # Should stop at INTENT stage
        stages_after_intent = [
            t for t in result.trace
            if t.success is False
        ]
        assert len(stages_after_intent) >= 1

    @pytest.mark.asyncio
    async def test_clarification_stops_pipeline(self):
        pipeline = QueryPipeline()

        async def low_confidence_intent(ctx):
            ctx["requires_clarification"] = True
            ctx["clarification_reason"] = "Ambiguous query"
            return StageResult(
                stage=PipelineStage.INTENT,
                confidence=0.3,
                data={
                    "requires_clarification": True,
                    "clarification_reason": "Ambiguous query",
                },
            )

        pipeline.register_stage(PipelineStage.INTENT, low_confidence_intent)
        result = await pipeline.process("test")
        assert result.requires_clarification is True
        assert result.clarification_reason == "Ambiguous query"

    @pytest.mark.asyncio
    async def test_confidence_threshold_triggers_clarification(self):
        config = QueryConfig(clarification_confidence_threshold=0.6, enable_fallback=True)
        pipeline = QueryPipeline(config=config)

        async def low_conf_intent(ctx):
            return StageResult(
                stage=PipelineStage.INTENT,
                confidence=0.3,
                data={"intent": "unknown", "confidence": 0.3},
            )

        pipeline.register_stage(PipelineStage.INTENT, low_conf_intent)
        result = await pipeline.process("vague")
        assert result.requires_clarification is True
        assert "confidence" in result.clarification_reason.lower()

    def test_stage_enum_values(self):
        assert PipelineStage.INPUT.value == "input"
        assert PipelineStage.INTENT.value == "intent"
        assert PipelineStage.ROUTE.value == "route"
        assert PipelineStage.COMPLETE.value == "complete"

    def test_stage_result_defaults(self):
        r = StageResult(stage=PipelineStage.INPUT)
        assert r.success is True
        assert r.confidence == 1.0
        assert r.error is None
        assert r.data == {"passed": True}  # passthrough default
        assert r.time_ms == 0.0


class TestQueryUnderstandingService:
    """Verify the service wrapper."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        svc = QueryUnderstandingService()
        result = await svc.initialize()
        assert result is True

    @pytest.mark.asyncio
    async def test_health(self):
        svc = QueryUnderstandingService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_stats(self):
        svc = QueryUnderstandingService()
        await svc.initialize()
        stats = await svc.stats()
        assert "pipeline_stages" in stats

    @pytest.mark.asyncio
    async def test_process_empty(self):
        svc = QueryUnderstandingService()
        await svc.initialize()
        result = await svc.process("")
        assert result.success is False
        assert result.requires_clarification is True

    @pytest.mark.asyncio
    async def test_process_valid(self):
        svc = QueryUnderstandingService()
        await svc.initialize()
        result = await svc.process("hello jarvis")
        assert result.success is True
        assert result.query == "hello jarvis"

    @pytest.mark.asyncio
    async def test_register_stage_handler(self):
        svc = QueryUnderstandingService()
        await svc.initialize()

        async def custom_handler(ctx):
            ctx["normalized"] = "CUSTOM"
            return StageResult(
                stage=PipelineStage.NORMALIZE,
                data={"normalized": "CUSTOM"},
            )

        await svc.register_stage_handler(PipelineStage.NORMALIZE, custom_handler)
        result = await svc.process("test")
        assert result.normalized == "CUSTOM"

    @pytest.mark.asyncio
    async def test_shutdown(self):
        svc = QueryUnderstandingService()
        await svc.initialize()
        await svc.shutdown()
        assert svc.is_initialized() is False


class TestQueryModels:
    """Verify Pydantic models."""

    def test_query_request(self):
        req = QueryRequest(query="hello")
        assert req.query == "hello"
        assert req.context == {}
        assert req.session_id is None

    def test_query_request_validation(self):
        with pytest.raises(Exception):
            QueryRequest(query="")  # min_length=1

    def test_query_result_defaults(self):
        r = QueryResult(query="test")
        assert r.query == "test"
        assert r.success is True
        assert r.requires_clarification is False

    def test_pipeline_trace(self):
        t = PipelineTrace(stage="test", success=True, confidence=0.95, time_ms=10.5)
        assert t.stage == "test"
        assert t.confidence == 0.95
        assert t.time_ms == 10.5
