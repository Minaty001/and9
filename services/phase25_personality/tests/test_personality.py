"""
Tests for Phase 25 — Personality Engine.
"""

import pytest
from services.phase25_personality import (
    PersonalityConfig,
    Persona,
    PersonalityProfile,
    PersonalityEngine,
    PersonalityEngineService,
)


class TestPersonalityConfig:
    """Verify PersonalityConfig creation."""

    def test_default_config(self):
        config = PersonalityConfig()
        assert config.service_name == "jarvis_personality"
        assert config.active_persona == "jarvis_default"
        assert config.max_response_length == 500

    def test_custom_config(self):
        config = PersonalityConfig(
            active_persona="jarvis_casual",
            enable_persona_switching=False,
            default_tone="friendly",
        )
        assert config.active_persona == "jarvis_casual"
        assert config.enable_persona_switching is False
        assert config.default_tone == "friendly"

    def test_env_prefix(self):
        assert PersonalityConfig.model_config["env_prefix"] == "JARVIS_PHASE25_"


class TestPersona:
    """Verify Persona creation."""

    def test_create_persona(self):
        p = Persona(id="test_persona", name="Test Persona")
        assert p.id == "test_persona"
        assert p.name == "Test Persona"
        assert p.tone == "helpful"
        assert p.formality_level == 5

    def test_custom_persona(self):
        p = Persona(
            id="custom",
            name="Custom",
            tone="formal",
            formality_level=10,
            emoji_usage="never",
        )
        assert p.formality_level == 10
        assert p.emoji_usage == "never"

    def test_persona_defaults(self):
        p = Persona(id="p1", name="P1")
        assert p.vocabulary_whitelist == []
        assert p.vocabulary_blacklist == []
        assert p.emoji_usage == "normal"
        assert p.metadata == {}


class TestPersonalityProfile:
    """Verify PersonalityProfile creation."""

    def test_create_profile(self):
        profile = PersonalityProfile(active_persona_id="jarvis_default")
        assert profile.active_persona_id == "jarvis_default"
        assert profile.response_count == 0
        assert profile.greeting_history == []

    def test_profile_defaults(self):
        profile = PersonalityProfile(active_persona_id="test")
        assert profile.tone_scores == {}
        assert profile.style_attributes == {}


class TestPersonalityEngine:
    """Verify PersonalityEngine behavior."""

    def test_initial_persona(self):
        engine = PersonalityEngine()
        persona = engine.get_persona()
        assert persona is not None
        assert persona.id == "jarvis_default"

    def test_set_persona(self):
        engine = PersonalityEngine()
        assert engine.set_persona("jarvis_casual") is True
        assert engine.get_persona().id == "jarvis_casual"

    def test_set_invalid_persona(self):
        engine = PersonalityEngine()
        assert engine.set_persona("nonexistent") is False
        assert engine.get_persona().id == "jarvis_default"

    def test_list_personas(self):
        engine = PersonalityEngine()
        personas = engine.list_personas()
        assert len(personas) == 3
        assert "jarvis_default" in personas
        assert "jarvis_casual" in personas
        assert "jarvis_professional" in personas

    def test_register_persona(self):
        engine = PersonalityEngine()
        p = Persona(id="custom", name="Custom")
        assert engine.register_persona(p) is True
        personas = engine.list_personas()
        assert len(personas) == 4

    def test_apply_tone_formal(self):
        engine = PersonalityEngine()
        persona = Persona(id="formal", name="Formal", formality_level=10, tone="formal")
        adjusted = engine.apply_tone("i'm going to the store", persona)
        assert "I am" in adjusted or "I'm" in adjusted

    def test_apply_tone_default(self):
        engine = PersonalityEngine()
        persona = engine.get_persona()
        adjusted = engine.apply_tone("hello world", persona)
        # Default has formality 7 - should capitalize first letter
        assert adjusted == "Hello world"

    def test_generate_greeting_default(self):
        engine = PersonalityEngine()
        greeting = engine.generate_greeting()
        assert "Hello" in greeting
        assert "JARVIS" in greeting

    def test_generate_greeting_casual(self):
        engine = PersonalityEngine()
        engine.set_persona("jarvis_casual")
        greeting = engine.generate_greeting()
        assert "Hey" in greeting

    def test_generate_greeting_professional(self):
        engine = PersonalityEngine()
        engine.set_persona("jarvis_professional")
        greeting = engine.generate_greeting()
        assert "Good day" in greeting

    def test_generate_greeting_time_based(self):
        engine = PersonalityEngine()
        greeting = engine.generate_greeting(context={"time_of_day": "morning"})
        assert "Good morning" in greeting

    def test_constrain_response_length(self):
        engine = PersonalityEngine()
        persona = Persona(
            id="short", name="Short",
            response_constraints={"max_length": 20},
        )
        long_text = "This is a very long response that should be truncated"
        constrained = engine.constrain_response(long_text, persona)
        assert len(constrained) <= 25  # ~20 + "..."

    def test_constrain_response_blacklist(self):
        engine = PersonalityEngine()
        persona = Persona(
            id="clean", name="Clean",
            vocabulary_blacklist=["badword"],
        )
        text = "This contains a badword in it"
        constrained = engine.constrain_response(text, persona)
        assert "badword" not in constrained

    def test_constrain_response_no_emoji(self):
        engine = PersonalityEngine()
        persona = Persona(
            id="noemoji", name="No Emoji",
            emoji_usage="never",
        )
        text = "Hello 😊 world 😄"
        constrained = engine.constrain_response(text, persona)
        assert "😊" not in constrained
        assert "😄" not in constrained

    def test_detect_tone_formal(self):
        engine = PersonalityEngine()
        tone = engine.detect_tone("Regarding your request, therefore we suggest...")
        assert tone == "formal"

    def test_detect_tone_casual(self):
        engine = PersonalityEngine()
        tone = engine.detect_tone("Hey dude, cool stuff!")
        assert tone == "casual"

    def test_detect_tone_helpful(self):
        engine = PersonalityEngine()
        tone = engine.detect_tone("Let me help you with that")
        assert tone == "helpful"

    def test_detect_tone_neutral(self):
        engine = PersonalityEngine()
        tone = engine.detect_tone("The sky is blue.")
        assert tone == "neutral"

    def test_get_profile(self):
        engine = PersonalityEngine()
        profile = engine.get_profile()
        assert profile is not None
        assert profile.active_persona_id == "jarvis_default"


class TestPersonalityEngineService:
    """Verify service wrapper."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        svc = PersonalityEngineService()
        assert await svc.initialize() is True

    @pytest.mark.asyncio
    async def test_shutdown(self):
        svc = PersonalityEngineService()
        await svc.initialize()
        await svc.shutdown()
        assert not svc.is_initialized()

    @pytest.mark.asyncio
    async def test_health(self):
        svc = PersonalityEngineService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"
        assert health["service_name"] == "jarvis_personality"

    @pytest.mark.asyncio
    async def test_stats(self):
        svc = PersonalityEngineService()
        await svc.initialize()
        stats = await svc.stats()
        assert stats["service"] == "jarvis_personality"
        assert "metrics" in stats

    @pytest.mark.asyncio
    async def test_apply_tone(self):
        svc = PersonalityEngineService()
        await svc.initialize()
        result = await svc.apply_tone("hello world")
        assert result is not None

    @pytest.mark.asyncio
    async def test_generate_greeting(self):
        svc = PersonalityEngineService()
        await svc.initialize()
        greeting = await svc.generate_greeting()
        assert "Hello" in greeting

    @pytest.mark.asyncio
    async def test_generate_greeting_with_context(self):
        svc = PersonalityEngineService()
        await svc.initialize()
        greeting = await svc.generate_greeting({"time_of_day": "evening"})
        assert "Good evening" in greeting

    @pytest.mark.asyncio
    async def test_constrain_response(self):
        svc = PersonalityEngineService()
        await svc.initialize()
        result = await svc.constrain_response("Test response")
        assert result is not None

    @pytest.mark.asyncio
    async def test_set_persona(self):
        svc = PersonalityEngineService()
        await svc.initialize()
        assert await svc.set_persona("jarvis_casual") is True
        persona = await svc.get_persona()
        assert persona.id == "jarvis_casual"

    @pytest.mark.asyncio
    async def test_set_persona_disabled(self):
        svc = PersonalityEngineService(config=PersonalityConfig(enable_persona_switching=False))
        await svc.initialize()
        assert await svc.set_persona("jarvis_casual") is False

    @pytest.mark.asyncio
    async def test_get_persona_by_id(self):
        svc = PersonalityEngineService()
        await svc.initialize()
        persona = await svc.get_persona("jarvis_casual")
        assert persona is not None
        assert persona.id == "jarvis_casual"

    @pytest.mark.asyncio
    async def test_get_persona_invalid(self):
        svc = PersonalityEngineService()
        await svc.initialize()
        persona = await svc.get_persona("nonexistent")
        assert persona is None

    @pytest.mark.asyncio
    async def test_detect_tone(self):
        svc = PersonalityEngineService()
        await svc.initialize()
        tone = await svc.detect_tone("Hey there!")
        assert tone == "casual"

    @pytest.mark.asyncio
    async def test_list_personas(self):
        svc = PersonalityEngineService()
        await svc.initialize()
        personas = await svc.list_personas()
        assert len(personas) == 3

    @pytest.mark.asyncio
    async def test_register_persona(self):
        svc = PersonalityEngineService()
        await svc.initialize()
        p = Persona(id="custom_test", name="Custom Test")
        assert await svc.register_persona(p) is True
        personas = await svc.list_personas()
        assert len(personas) == 4

    @pytest.mark.asyncio
    async def test_get_profile(self):
        svc = PersonalityEngineService()
        await svc.initialize()
        profile = await svc.get_profile()
        assert profile is not None
        assert profile.active_persona_id == "jarvis_default"

    @pytest.mark.asyncio
    async def test_apply_tone_not_initialized(self):
        svc = PersonalityEngineService()
        with pytest.raises(RuntimeError, match="not initialized"):
            await svc.apply_tone("hello")
