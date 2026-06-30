"""
Integration tests for the full 20-phase service pipeline.

Tests each phase independently and in combination to verify
the full processing pipeline works end-to-end.

Run with:
    pytest tests/integration/test_services_pipeline.py -v
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Phase 1 — Core (models & errors)
# ---------------------------------------------------------------------------

class TestPhase1Core:
    """Core models and error hierarchy."""

    def test_processing_result(self):
        from services.phase01_core import ProcessingResult, BrainType
        r = ProcessingResult(
            query="hello",
            brain=BrainType.REFLEX,
        )
        assert r.query == "hello"
        assert r.success is True
        assert r.brain == BrainType.REFLEX

    def test_error_hierarchy(self):
        from services.phase01_core import JarvisError, ServiceError, ValidationError
        e = ServiceError("test error")
        assert isinstance(e, JarvisError)
        v = ValidationError("invalid")
        assert isinstance(v, JarvisError)
        assert v.code == "VALIDATION_ERROR"
        assert "invalid" in v.to_dict()["message"]


# ---------------------------------------------------------------------------
# Phase 2 — Architecture (event bus)
# ---------------------------------------------------------------------------

class TestPhase2Architecture:
    """Event bus and module registry."""

    @pytest.mark.asyncio
    async def test_event_bus(self):
        from services.phase02_architecture import EventBus, Event
        bus = EventBus()
        received = []

        async def handler(event):
            received.append(event.payload.get("msg"))

        bus.subscribe("test.event", handler)
        await bus.emit(Event(type="test.event", payload={"msg": "hello"}))
        assert len(received) == 1
        assert received[0] == "hello"

    @pytest.mark.asyncio
    async def test_architecture_service(self):
        from services.phase02_architecture import ArchitectureService
        svc = ArchitectureService()
        result = await svc.initialize()
        assert result is True
        health = await svc.health()
        assert health["status"] == "healthy"


# ---------------------------------------------------------------------------
# Phase 3 — Query Understanding
# ---------------------------------------------------------------------------

class TestPhase3Query:
    """Query understanding pipeline."""

    @pytest.mark.asyncio
    async def test_query_pipeline(self):
        from services.phase03_query import QueryUnderstandingService
        svc = QueryUnderstandingService()
        await svc.initialize()
        result = await svc.process("set alarm for 7am")
        assert result is not None
        assert result.success is True

    @pytest.mark.asyncio
    async def test_pipeline_stages(self):
        from services.phase03_query import QueryPipeline, PipelineStage, StageResult
        pipe = QueryPipeline()
        results = []

        async def stage1(ctx):
            results.append("stage1")
            return StageResult(stage=PipelineStage.INPUT, data=ctx, success=True)

        async def stage2(ctx):
            results.append("stage2")
            return StageResult(stage=PipelineStage.NORMALIZE, data=ctx, success=True)

        pipe.register_stage(PipelineStage.INPUT, stage1)
        pipe.register_stage(PipelineStage.NORMALIZE, stage2)

        await pipe.process("hello")
        assert results == ["stage1", "stage2"]


# ---------------------------------------------------------------------------
# Phase 4 — Tokenizer
# ---------------------------------------------------------------------------

class TestPhase4Tokenizer:
    """Tokenizer and normalizer."""

    def test_normalizer(self):
        from services.phase04_tokenizer import TextNormalizer
        n = TextNormalizer()
        text, meta = n.normalize("kya haal hai")
        # At minimum, should produce output
        assert len(text) > 0

    @pytest.mark.asyncio
    async def test_tokenizer_service(self):
        from services.phase04_tokenizer import TokenizerService
        svc = TokenizerService()
        await svc.initialize()
        result = await svc.tokenize("hello world")
        assert len(result.tokens) == 2
        assert result.token_count == 2

    def test_character_tokenization(self):
        from services.phase04_tokenizer import Tokenizer
        t = Tokenizer()
        result = t.tokenize_characters("hello")
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Phase 5 — Embedding
# ---------------------------------------------------------------------------

class TestPhase5Embedding:
    """Hybrid embedding engine."""

    @pytest.mark.asyncio
    async def test_embedding_vector(self):
        from services.phase05_embedding import EmbeddingService
        svc = EmbeddingService()
        await svc.initialize()
        result = await svc.embed("weather in delhi")
        assert len(result.vector) == 128
        assert result.dimension == 128

    def test_cosine_similarity(self):
        from services.phase05_embedding import HybridEmbedding, cosine_similarity
        e = HybridEmbedding()
        v1 = e.embed("weather")
        v2 = e.embed("climate")
        v3 = e.embed("alarm")
        sim_same = cosine_similarity(v1, v1)
        assert abs(sim_same - 1.0) < 0.001
        sim_diff = cosine_similarity(v1, v3)
        assert sim_diff < sim_same


# ---------------------------------------------------------------------------
# Phase 6 — Intent Detection
# ---------------------------------------------------------------------------

class TestPhase6Intent:
    """Intent detection with neural network."""

    @pytest.mark.asyncio
    async def test_intent_detection(self):
        from services.phase06_intent import IntentDetectionService
        from services.phase05_embedding import HybridEmbedding
        svc = IntentDetectionService()
        await svc.initialize()
        embedder = HybridEmbedding()
        embedding = embedder.embed("set alarm for 7am")
        result = await svc.detect(embedding, "set alarm for 7am")
        assert result.intent is not None
        assert result.confidence > 0

    def test_keyword_override(self):
        from services.phase06_intent import IntentClassifier
        clf = IntentClassifier()
        clf.initialize()
        import numpy as np
        dummy_embedding = np.zeros(128, dtype=np.float32).tolist()
        result = clf.classify(dummy_embedding, "play music")
        assert result.intent == "PLAY_MUSIC"
        assert result.confidence == 0.95

    def test_tiny_neural_network(self):
        from services.phase06_intent import TinyNeuralNetwork
        import numpy as np
        nn = TinyNeuralNetwork()
        nn.initialize()
        inp = np.random.randn(128).astype(np.float32)
        output = nn.predict(inp)
        assert output.shape == (28,)
        assert abs(output.sum() - 1.0) < 0.01  # softmax


# ---------------------------------------------------------------------------
# Phase 7 — Entity Extraction
# ---------------------------------------------------------------------------

class TestPhase7Entity:
    """Entity extraction."""

    @pytest.mark.asyncio
    async def test_entity_extraction(self):
        from services.phase07_entity import EntityExtractionService
        svc = EntityExtractionService()
        await svc.initialize()
        result = await svc.extract("call mom at 5pm")
        assert len(result.entities) >= 2
        assert "contact" in result.grouped or "time" in result.grouped

    def test_app_extractor(self):
        from services.phase07_entity import AppExtractor
        ex = AppExtractor()
        entities = ex.extract("open whatsapp")
        assert len(entities) == 1
        assert entities[0].value == "com.whatsapp"

    def test_time_extractor(self):
        from services.phase07_entity import TimeExtractor
        ex = TimeExtractor()
        entities = ex.extract("set alarm for 7am")
        assert len(entities) >= 1


# ---------------------------------------------------------------------------
# Phase 8 — Context Builder
# ---------------------------------------------------------------------------

class TestPhase8Context:
    """Context builder."""

    @pytest.mark.asyncio
    async def test_context_accumulation(self):
        from services.phase08_context import ContextBuilderService
        svc = ContextBuilderService()
        await svc.initialize()
        s1 = await svc.process("weather in delhi", intent="weather_query",
                               entities={"location": ["Delhi"]})
        assert s1.turn_count == 1

        s2 = await svc.process("and in mumbai")
        assert s2.turn_count == 2
        assert "Delhi" in s2.active_entities.get("location", [])

    @pytest.mark.asyncio
    async def test_relevance_search(self):
        from services.phase08_context import ContextBuilderService
        svc = ContextBuilderService()
        await svc.initialize()
        await svc.process("what's the weather", intent="weather_query")
        await svc.process("play despacito", intent="play_music")
        results = await svc.search("weather")
        assert len(results) >= 1
        assert results[0].turn.intent == "weather_query"


# ---------------------------------------------------------------------------
# Phase 9 — Memory System
# ---------------------------------------------------------------------------

class TestPhase9Memory:
    """Memory system."""

    @pytest.mark.asyncio
    async def test_memory_lifecycle(self):
        from services.phase09_memory import MemoryService
        svc = MemoryService()
        await svc.initialize()

        await svc.store("user_name", "Alice", memory_type="long_term", importance=0.9)
        await svc.store("last_query", "hello", tags=["session"])

        results = await svc.recall("alice")
        assert len(results) >= 1
        assert results[0].value == "Alice"

        stats = await svc.get_stats()
        assert stats.total_items >= 2

    @pytest.mark.asyncio
    async def test_consolidation(self):
        from services.phase09_memory import MemoryService, MemoryConfig
        svc = MemoryService(MemoryConfig(
            consolidation_importance_threshold=0.7,
            auto_consolidate_on_store=False,
        ))
        await svc.initialize()
        await svc.store("important_fact", "secret", importance=0.9)
        await svc.store("trivial_fact", "whatever", importance=0.3)
        count = await svc.consolidate()
        assert count == 1


# ---------------------------------------------------------------------------
# Phase 10 — Reflex Brain
# ---------------------------------------------------------------------------

class TestPhase10Reflex:
    """Reflex brain."""

    @pytest.mark.asyncio
    async def test_reflex_match(self):
        from services.phase10_reflex import ReflexService
        svc = ReflexService()
        await svc.initialize()
        result = await svc.process("hello")
        assert result.matched is True
        assert result.intent == "greeting"

    @pytest.mark.asyncio
    async def test_reflex_no_match(self):
        from services.phase10_reflex import ReflexService
        svc = ReflexService()
        await svc.initialize()
        result = await svc.process("xyznonexistent")
        assert result.matched is False

    @pytest.mark.asyncio
    async def test_custom_action(self):
        from services.phase10_reflex import ReflexService
        svc = ReflexService()
        await svc.initialize()
        await svc.add_action("custom_test", r"my command", intent="custom", response="Done!")
        result = await svc.process("my command test")
        assert result.matched is True
        assert result.intent == "custom"
        assert result.response == "Done!"


# ---------------------------------------------------------------------------
# End-to-End Pipeline
# ---------------------------------------------------------------------------

class TestEndToEndPipeline:
    """Full processing pipeline across multiple phases."""

    @pytest.mark.asyncio
    async def test_reflex_to_context_pipeline(self):
        """Test: reflex → query → tokenize → embed → detect → extract → context."""
        from services.phase10_reflex import ReflexService
        from services.phase03_query import QueryUnderstandingService
        from services.phase04_tokenizer import TokenizerService
        from services.phase05_embedding import EmbeddingService, HybridEmbedding
        from services.phase06_intent import IntentDetectionService
        from services.phase07_entity import EntityExtractionService
        from services.phase08_context import ContextBuilderService

        # Initialize all services
        reflex = ReflexService()
        query = QueryUnderstandingService()
        tokenizer = TokenizerService()
        embedder_svc = EmbeddingService()
        intent = IntentDetectionService()
        entity = EntityExtractionService()
        context = ContextBuilderService()

        for svc in (reflex, query, tokenizer, embedder_svc, intent, entity, context):
            assert await svc.initialize() is True

        # Process "hello" — should match reflex
        reflex_result = await reflex.process("hello")
        assert reflex_result.matched is True

        # Process "set alarm for 7am" through full pipeline
        query_text = "set alarm for 7am"

        # Query pipeline
        query_result = await query.process(query_text)
        assert query_result.success is True

        # Tokenize
        token_result = await tokenizer.tokenize(query_text)
        assert token_result.token_count >= 3

        # Embed (service returns EmbeddingVector with .vector)
        embed_result = await embedder_svc.embed(query_text)
        assert len(embed_result.vector) == 128
        assert embed_result.dimension == 128

        # Intent (service needs embedding first, then text)
        intent_result = await intent.detect(embed_result.vector, query_text)
        assert intent_result.intent is not None

        # Entity
        entity_result = await entity.extract(query_text, intent_result.intent)
        assert len(entity_result.entities) >= 1

        # Context
        ctx = await context.process(
            query=query_text,
            intent=intent_result.intent,
            entities={t: [e.value for e in ents] for t, ents in entity_result.grouped.items()},
        )
        assert ctx.turn_count == 1

        # Health check all
        for svc in (reflex, query, tokenizer, embedder_svc, intent, entity, context):
            health = await svc.health()
            assert health["status"] == "healthy"

        # Shutdown all
        for svc in (reflex, query, tokenizer, embedder_svc, intent, entity, context):
            await svc.shutdown()

    @pytest.mark.asyncio
    async def test_multi_turn_scenario(self):
        """Simulate a conversation across multiple turns with context and memory."""
        from services.phase05_embedding import HybridEmbedding
        from services.phase06_intent import IntentDetectionService
        from services.phase07_entity import EntityExtractionService
        from services.phase08_context import ContextBuilderService
        from services.phase09_memory import MemoryService

        # Initialize
        embedder = HybridEmbedding()
        intent_svc = IntentDetectionService()
        entity_svc = EntityExtractionService()
        context_svc = ContextBuilderService()
        memory_svc = MemoryService()

        for svc in (intent_svc, entity_svc, context_svc, memory_svc):
            assert await svc.initialize() is True

        # Turn 1: "weather in delhi"
        text1 = "weather in delhi"
        emb1 = embedder.embed(text1)
        intent1 = await intent_svc.detect(emb1, text1)
        entities1 = await entity_svc.extract(text1, intent1.intent)
        ctx1 = await context_svc.process(
            text1, intent=intent1.intent,
            entities={t: [e.value for e in ents] for t, ents in entities1.grouped.items()},
        )
        await memory_svc.store("last_intent", intent1.intent, tags=["session"])
        assert ctx1.turn_count == 1

        # Turn 2: "and in mumbai" (follow-up)
        text2 = "and in mumbai"
        emb2 = embedder.embed(text2)
        intent2 = await intent_svc.detect(emb2, text2)
        entities2 = await entity_svc.extract(text2, intent2.intent)
        ctx2 = await context_svc.process(
            text2, intent=intent2.intent,
            entities={t: [e.value for e in ents] for t, ents in entities2.grouped.items()},
        )
        await memory_svc.store("last_intent", intent2.intent, tags=["session"])
        assert ctx2.turn_count == 2

        # Context should have accumulated entities from both turns
        all_locations = ctx2.active_entities.get("location", [])
        assert any("mumbai" in loc.lower() for loc in all_locations)

        # Memory should have stored intents
        recall = await memory_svc.recall("intent")
        assert len(recall) >= 1

        # Shutdown
        for svc in (intent_svc, entity_svc, context_svc, memory_svc):
            await svc.shutdown()


# ---------------------------------------------------------------------------
# Phase 11 — Habit Brain
# ---------------------------------------------------------------------------

class TestPhase11Habit:
    """Habit brain — pattern learning and suggestion."""

    @pytest.mark.asyncio
    async def test_habit_tracking(self):
        from services.phase11_habit import HabitBrainService
        svc = HabitBrainService()
        await svc.initialize()

        # Observe the same event multiple times
        pattern = await svc.observe("play music", intent="play_music",
                                    hour=9, day_of_week=0, location="home")
        assert pattern.frequency >= 1

        for _ in range(5):
            await svc.observe("play music", intent="play_music",
                              hour=9, day_of_week=0, location="home")

        suggestions = await svc.suggest(hour=9, day_of_week=0, location="home")
        assert len(suggestions) >= 1
        assert suggestions[0].confidence > 0

    @pytest.mark.asyncio
    async def test_habit_service_lifecycle(self):
        from services.phase11_habit import HabitBrainService
        svc = HabitBrainService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"
        stats = await svc.stats()
        assert "metrics" in stats
        await svc.shutdown()
        assert svc.is_initialized() is False


# ---------------------------------------------------------------------------
# Phase 12 — Conscious Brain
# ---------------------------------------------------------------------------

class TestPhase12Conscious:
    """Conscious brain — LLM-powered reasoning."""

    @pytest.mark.asyncio
    async def test_conscious_service_lifecycle(self):
        from services.phase12_conscious import ConsciousBrainService
        svc = ConsciousBrainService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"
        assert health["service_name"] == "jarvis_conscious"

        # Should have default prompt templates
        templates = svc.list_prompt_templates()
        names = {t["name"] for t in templates}
        assert "reasoning" in names
        assert "planning" in names

        # Reason method should not crash without API key
        result = await svc.reason("What is 2+2?")
        assert result.final_answer is not None

        await svc.shutdown()

    @pytest.mark.asyncio
    async def test_conscious_prompt_templates(self):
        from services.phase12_conscious import ConsciousBrainService
        svc = ConsciousBrainService()
        await svc.initialize()
        svc.register_prompt_template(
            name="custom_integration",
            system="You are {role}.",
            user="{query}",
            description="Integration test template",
        )
        templates = svc.list_prompt_templates()
        names = {t["name"] for t in templates}
        assert "custom_integration" in names


# ---------------------------------------------------------------------------
# Phase 13 — Planner
# ---------------------------------------------------------------------------

class TestPhase13Planner:
    """Planner — goal decomposition."""

    @pytest.mark.asyncio
    async def test_plan_creation(self):
        from services.phase13_planner import PlannerService
        svc = PlannerService()
        await svc.initialize()
        plan = await svc.plan("build a web app", {"stack": "python"})
        assert plan.goal == "build a web app"
        assert len(plan.tasks) > 0
        assert plan.status in ("pending", "active")

    @pytest.mark.asyncio
    async def test_planner_service_lifecycle(self):
        from services.phase13_planner import PlannerService
        svc = PlannerService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"
        stats = await svc.stats()
        assert "max_subtasks" in stats
        await svc.shutdown()


# ---------------------------------------------------------------------------
# Phase 14 — Decision Engine
# ---------------------------------------------------------------------------

class TestPhase14Decision:
    """Decision engine — brain routing."""

    @pytest.mark.asyncio
    async def test_decision_routing(self):
        from services.phase14_decision import DecisionEngineService, DecisionRequest
        svc = DecisionEngineService()
        await svc.initialize()

        # High confidence → reflex
        request = DecisionRequest(
            query="hello",
            confidence=0.95,
            available_brains=["reflex", "habit", "conscious"],
        )
        result = await svc.decide(request)
        assert result.selected_brain == "reflex"
        assert result.confidence >= 0.9

        # Low confidence → conscious (only conscious available)
        request = DecisionRequest(
            query="complex query",
            confidence=0.3,
            available_brains=["conscious"],
        )
        result = await svc.decide(request)
        assert result.selected_brain == "conscious"

    @pytest.mark.asyncio
    async def test_decision_service_lifecycle(self):
        from services.phase14_decision import DecisionEngineService
        svc = DecisionEngineService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"
        await svc.shutdown()


# ---------------------------------------------------------------------------
# Phase 15 — Skill Router
# ---------------------------------------------------------------------------

class TestPhase15Skill:
    """Skill router — plugin registry."""

    @pytest.mark.asyncio
    async def test_skill_registration_and_routing(self):
        from services.phase15_skill import SkillRouterService, SkillDefinition
        svc = SkillRouterService()
        await svc.initialize()

        weather_def = SkillDefinition(
            id="weather_skill",
            name="Weather",
            version="1.0",
            intents=["weather_query", "get_weather"],
            required_entities=["location"],
            priority=10,
        )
        ok = svc.register_skill(weather_def)
        assert ok is True

        alarm_def = SkillDefinition(
            id="alarm_skill",
            name="Alarm",
            version="1.0",
            intents=["set_alarm"],
            required_entities=["time"],
        )
        ok = svc.register_skill(alarm_def)
        assert ok is True

        results = svc.route(
            intent="weather_query",
            entities={"location": ["Delhi"]},
        )
        assert len(results) >= 1
        assert results[0].skill_id == "weather_skill"

        await svc.shutdown()

    @pytest.mark.asyncio
    async def test_skill_service_lifecycle(self):
        from services.phase15_skill import SkillRouterService
        svc = SkillRouterService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"
        assert len(svc.list_skills()) == 0
        await svc.shutdown()


# ---------------------------------------------------------------------------
# Phase 16 — Android Controller
# ---------------------------------------------------------------------------

class TestPhase16Android:
    """Android controller — device actions."""

    @pytest.mark.asyncio
    async def test_app_launch(self):
        from services.phase16_android import AndroidControllerService, AndroidAction
        svc = AndroidControllerService()
        await svc.initialize()

        action = AndroidAction(
            action_type="launch_app",
            target="whatsapp",
        )
        result = svc.execute(action)
        assert result.success is True
        assert result.action_type == "launch_app"

    @pytest.mark.asyncio
    async def test_hardware_control(self):
        from services.phase16_android import AndroidControllerService
        svc = AndroidControllerService()
        await svc.initialize()

        vol = svc.set_volume(75)
        assert vol is True

        brightness = svc.set_brightness(50)
        assert brightness is True

    @pytest.mark.asyncio
    async def test_android_service_lifecycle(self):
        from services.phase16_android import AndroidControllerService
        svc = AndroidControllerService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"
        await svc.shutdown()


# ---------------------------------------------------------------------------
# Phase 17 — Browser Controller
# ---------------------------------------------------------------------------

class TestPhase17Browser:
    """Browser controller — web actions."""

    @pytest.mark.asyncio
    async def test_search(self):
        from services.phase17_browser import BrowserControllerService
        svc = BrowserControllerService()
        await svc.initialize()

        result = await svc.search("python programming")
        assert result.success is True
        assert result.action_type == "search"
        assert result.content_preview is not None

    @pytest.mark.asyncio
    async def test_browser_service_lifecycle(self):
        from services.phase17_browser import BrowserControllerService
        svc = BrowserControllerService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"
        await svc.shutdown()


# ---------------------------------------------------------------------------
# Phase 18 — Media Controller
# ---------------------------------------------------------------------------

class TestPhase18Media:
    """Media controller — playback."""

    @pytest.mark.asyncio
    async def test_playback_cycle(self):
        from services.phase18_media import MediaControllerService, Track
        svc = MediaControllerService()
        await svc.initialize()

        state = await svc.get_state()
        assert state.status == "stopped"

        # Play with a track
        track = Track(id="1", title="Test Song", artist="Test Artist", duration_seconds=180)
        ok = await svc.play(track)
        assert ok is True

        state = await svc.get_state()
        assert state.status == "playing"

        ok = await svc.pause()
        assert ok is True

        state = await svc.get_state()
        assert state.status == "paused"

        await svc.shutdown()

    @pytest.mark.asyncio
    async def test_media_service_lifecycle(self):
        from services.phase18_media import MediaControllerService
        svc = MediaControllerService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"
        await svc.shutdown()


# ---------------------------------------------------------------------------
# Phase 19 — YouTube Controller
# ---------------------------------------------------------------------------

class TestPhase19YouTube:
    """YouTube controller — video platform."""

    @pytest.mark.asyncio
    async def test_youtube_search(self):
        from services.phase19_youtube import YouTubeControllerService
        svc = YouTubeControllerService()
        await svc.initialize()

        results = await svc.search("never gonna give")
        assert len(results) >= 1
        assert results[0].title is not None

        await svc.shutdown()

    @pytest.mark.asyncio
    async def test_youtube_service_lifecycle(self):
        from services.phase19_youtube import YouTubeControllerService
        svc = YouTubeControllerService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"
        await svc.shutdown()


# ---------------------------------------------------------------------------
# Phase 20 — Search Engine
# ---------------------------------------------------------------------------

class TestPhase20Search:
    """Search engine — coordinated multi-source search."""

    @pytest.mark.asyncio
    async def test_search_from_all_sources(self):
        from services.phase20_search import SearchEngineService
        svc = SearchEngineService()
        await svc.initialize()

        results = await svc.search("python")
        assert len(results) > 0
        # Should include results from at least one source
        sources = {r.source for r in results}
        assert len(sources) >= 1

        await svc.shutdown()

    @pytest.mark.asyncio
    async def test_search_service_lifecycle(self):
        from services.phase20_search import SearchEngineService
        svc = SearchEngineService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"
        stats = await svc.stats()
        assert "cache_size" in stats
        await svc.shutdown()


# ---------------------------------------------------------------------------
# End-to-End 20-Phase Pipeline
# ---------------------------------------------------------------------------

class TestEndToEnd20PhasePipeline:
    """Full processing pipeline across Phases 1-20."""

    @pytest.mark.asyncio
    async def test_full_pipeline(self):
        """Test all 20 services initialize, produce health, and shut down."""
        from services.phase01_core import CoreService
        from services.phase02_architecture import ArchitectureService
        from services.phase03_query import QueryUnderstandingService
        from services.phase04_tokenizer import TokenizerService
        from services.phase05_embedding import EmbeddingService, HybridEmbedding
        from services.phase06_intent import IntentDetectionService
        from services.phase07_entity import EntityExtractionService
        from services.phase08_context import ContextBuilderService
        from services.phase09_memory import MemoryService
        from services.phase10_reflex import ReflexService
        from services.phase11_habit import HabitBrainService
        from services.phase12_conscious import ConsciousBrainService
        from services.phase13_planner import PlannerService
        from services.phase14_decision import DecisionEngineService
        from services.phase15_skill import SkillRouterService
        from services.phase16_android import AndroidControllerService
        from services.phase17_browser import BrowserControllerService
        from services.phase18_media import MediaControllerService
        from services.phase19_youtube import YouTubeControllerService
        from services.phase20_search import SearchEngineService

        services = [
            ("Core", CoreService()),
            ("Architecture", ArchitectureService()),
            ("Query", QueryUnderstandingService()),
            ("Tokenizer", TokenizerService()),
            ("Embedding", EmbeddingService()),
            ("Intent", IntentDetectionService()),
            ("Entity", EntityExtractionService()),
            ("Context", ContextBuilderService()),
            ("Memory", MemoryService()),
            ("Reflex", ReflexService()),
            ("Habit", HabitBrainService()),
            ("Conscious", ConsciousBrainService()),
            ("Planner", PlannerService()),
            ("Decision", DecisionEngineService()),
            ("Skill", SkillRouterService()),
            ("Android", AndroidControllerService()),
            ("Browser", BrowserControllerService()),
            ("Media", MediaControllerService()),
            ("YouTube", YouTubeControllerService()),
            ("Search", SearchEngineService()),
        ]

        # Initialize all
        for name, svc in services:
            ok = await svc.initialize()
            assert ok is True, f"{name} failed to initialize"

        # Health and stats check all
        for name, svc in services:
            health = await svc.health()
            assert health["status"] == "healthy", f"{name} not healthy: {health}"
            assert health["service_name"] is not None
            stats = await svc.stats()
            assert stats["service"] == health["service_name"], \
                f"{name}: stats.service={stats['service']} != health.service_name={health['service_name']}"

        # Shutdown all
        for name, svc in services:
            await svc.shutdown()
            assert svc.is_initialized() is False, f"{name} shutdown failed"
