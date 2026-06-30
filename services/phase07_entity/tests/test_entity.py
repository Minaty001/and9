"""
Tests for Phase 7 — Entity Extraction.
"""

import pytest
from services.phase07_entity import (
    AppExtractor,
    ContactExtractor,
    TimeExtractor,
    LocationExtractor,
    MediaExtractor,
    EntityValidator,
    EntityExtractionService,
    EntityConfig,
    Entity,
    EntityResult,
)


class TestAppExtractor:
    """Verify app name extraction."""

    def test_extract_known_app(self):
        ex = AppExtractor()
        entities = ex.extract("open whatsapp")
        assert len(entities) == 1
        assert entities[0].type == "app"
        assert entities[0].value == "com.whatsapp"
        assert entities[0].confidence == 0.95

    def test_extract_unknown_app(self):
        ex = AppExtractor()
        entities = ex.extract("open mycustomapp")
        assert len(entities) >= 1
        assert entities[0].type == "app"

    def test_extract_multiple_apps(self):
        ex = AppExtractor()
        entities = ex.extract("open whatsapp and youtube")
        types = [e.value for e in entities]
        assert "com.whatsapp" in types
        assert "com.google.android.youtube" in types

    def test_resolve_package(self):
        ex = AppExtractor()
        assert ex.resolve_package("whatsapp") == "com.whatsapp"
        assert ex.resolve_package("WHATSAPP") == "com.whatsapp"
        assert ex.resolve_package("unknown_app") is None


class TestContactExtractor:
    """Verify contact extraction."""

    def test_extract_call_contact(self):
        ex = ContactExtractor()
        entities = ex.extract("call mom")
        assert len(entities) == 1
        assert entities[0].type == "contact"
        assert entities[0].value == "mom"

    def test_extract_message_contact(self):
        ex = ContactExtractor()
        entities = ex.extract("message john")
        assert len(entities) == 1
        assert entities[0].type == "contact"
        assert "john" in entities[0].value

    def test_no_contact_in_generic_query(self):
        ex = ContactExtractor()
        entities = ex.extract("what is the weather")
        assert len(entities) == 0


class TestTimeExtractor:
    """Verify time/date extraction."""

    def test_absolute_time(self):
        ex = TimeExtractor()
        entities = ex.extract("set alarm for 7am")
        assert len(entities) >= 1
        time_ents = [e for e in entities if e.type == "time"]
        assert len(time_ents) >= 1

    def test_relative_time(self):
        ex = TimeExtractor()
        entities = ex.extract("remind me in 10 minutes")
        time_ents = [e for e in entities if e.type == "time"]
        assert len(time_ents) >= 1

    def test_named_time(self):
        ex = TimeExtractor()
        entities = ex.extract("wake me up at morning")
        time_ents = [e for e in entities if e.type == "time"]
        assert len(time_ents) >= 1

    def test_date_extraction(self):
        ex = TimeExtractor()
        entities = ex.extract("what is the date tomorrow")
        date_ents = [e for e in entities if e.type == "date"]
        assert len(date_ents) >= 1

    def test_duration_extraction(self):
        ex = TimeExtractor()
        entities = ex.extract("timer for 5 minutes")
        dur_ents = [e for e in entities if e.type == "duration"]
        assert len(dur_ents) >= 1

    def test_normalize_time_empty(self):
        assert TimeExtractor._normalize_time(
            type("MockMatch", (), {"groups": lambda self: None})()
        ) == ""


class TestLocationExtractor:
    """Verify location extraction."""

    def test_known_city(self):
        ex = LocationExtractor()
        entities = ex.extract("weather in delhi")
        assert len(entities) >= 1
        locs = [e for e in entities if e.type == "location"]
        assert len(locs) >= 1
        assert "Delhi" in locs[0].value

    def test_unknown_location(self):
        ex = LocationExtractor()
        entities = ex.extract("weather in smalltown")
        assert len(entities) >= 1
        assert entities[0].type == "location"

    def test_resolve_city(self):
        ex = LocationExtractor()
        assert ex.resolve_city("mumbai") is not None
        assert ex.resolve_city("unknown_city") is None


class TestMediaExtractor:
    """Verify media extraction."""

    def test_song_extraction(self):
        ex = MediaExtractor()
        entities = ex.extract("play despacito")
        assert len(entities) >= 1
        assert entities[0].type == "media"
        assert "despacito" in entities[0].value

    def test_platform_detection(self):
        ex = MediaExtractor()
        entities = ex.extract("play despacito on youtube")
        media_ents = [e for e in entities if e.type == "media"]
        assert len(media_ents) >= 1


class TestEntityValidator:
    """Verify entity validation."""

    def test_valid_app(self):
        v = EntityValidator()
        valid, errors = v.validate([
            Entity(type="app", value="com.whatsapp", original="whatsapp")
        ])
        assert valid is True
        assert len(errors) == 0

    def test_invalid_contact(self):
        v = EntityValidator()
        valid, errors = v.validate([
            Entity(type="contact", value="", original="")
        ])
        assert valid is False
        assert len(errors) >= 1

    def test_valid_time(self):
        v = EntityValidator()
        valid, errors = v.validate([
            Entity(type="time", value="14:30", original="2:30pm")
        ])
        assert valid is True

    def test_invalid_time_hour(self):
        v = EntityValidator()
        valid, errors = v.validate([
            Entity(type="time", value="25:00", original="25:00")
        ])
        assert valid is False


class TestEntityExtractionService:
    """Verify service wrapper."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        svc = EntityExtractionService()
        result = await svc.initialize()
        assert result is True

    @pytest.mark.asyncio
    async def test_extract_app(self):
        svc = EntityExtractionService()
        await svc.initialize()
        result = await svc.extract("open whatsapp")
        assert len(result.entities) >= 1
        assert "app" in result.grouped

    @pytest.mark.asyncio
    async def test_extract_multiple_types(self):
        svc = EntityExtractionService()
        await svc.initialize()
        result = await svc.extract("call mom at 5pm")
        assert len(result.entities) >= 2
        assert "contact" in result.grouped
        assert "time" in result.grouped or "date" in result.grouped

    @pytest.mark.asyncio
    async def test_validation(self):
        svc = EntityExtractionService(EntityConfig(require_validation=True))
        await svc.initialize()
        result = await svc.extract("open whatsapp")
        assert result.validated is True

    @pytest.mark.asyncio
    async def test_health(self):
        svc = EntityExtractionService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"
