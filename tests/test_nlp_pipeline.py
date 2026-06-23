"""
Tests for the JARVIS NLP Pipeline (spaCy + NumPy).

Tests are organised by pipeline stage so each can be run independently:

  pytest tests/test_nlp_pipeline.py -v
  pytest tests/test_nlp_pipeline.py -v -k "test_intent"
  pytest tests/test_nlp_pipeline.py -v -k "test_spacy"

All tests degrade gracefully: when the spaCy model is not downloaded,
spaCy-specific tests are skipped automatically.
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Import guards
# ---------------------------------------------------------------------------
try:
    import spacy  # noqa: F401
    SPACY_INSTALLED = True
except ImportError:
    SPACY_INSTALLED = False

requires_spacy = pytest.mark.skipif(not SPACY_INSTALLED, reason="spaCy not installed")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def pipeline():
    """Shared NLPPipeline instance for all tests (loaded once per module)."""
    from app.core.nlp_pipeline import NLPPipeline
    return NLPPipeline()


@pytest.fixture(scope="module")
def spacy_pipeline():
    """NLPPipeline with spaCy model verified loaded."""
    from app.core.nlp_pipeline import NLPPipeline
    p = NLPPipeline()
    if not p._load_spacy():
        pytest.skip(
            "spaCy model 'en_core_web_sm' not downloaded. "
            "Run: python -m spacy download en_core_web_sm"
        )
    return p


# ---------------------------------------------------------------------------
# Stage 1 + 2: spaCy tokenization, POS, NER, noun chunks
# ---------------------------------------------------------------------------

class TestStageSpacy:
    """Tests for Stage 1 + 2: spaCy document processing and entity extraction."""

    @requires_spacy
    def test_tokens_populated(self, spacy_pipeline):
        result = spacy_pipeline.process("Set an alarm for 7am")
        assert len(result.tokens) > 0
        assert all(isinstance(t, str) for t in result.tokens)

    @requires_spacy
    def test_lemmas_populated(self, spacy_pipeline):
        result = spacy_pipeline.process("I am running tests")
        assert "run" in result.lemmas or "test" in result.lemmas

    @requires_spacy
    def test_pos_tags_structure(self, spacy_pipeline):
        result = spacy_pipeline.process("Open YouTube")
        assert len(result.pos_tags) > 0
        for word, tag in result.pos_tags:
            assert isinstance(word, str)
            assert isinstance(tag, str)

    @requires_spacy
    def test_ner_date_entity(self, spacy_pipeline):
        result = spacy_pipeline.process("My meeting is on Friday at 3pm")
        labels = [e.label for e in result.entities]
        assert any(lbl in labels for lbl in ("DATE", "TIME", "CARDINAL")), \
            f"Expected date/time entity, got labels: {labels}"

    @requires_spacy
    def test_ner_person_entity(self, spacy_pipeline):
        result = spacy_pipeline.process("Tell John that the meeting is cancelled")
        labels = [e.label for e in result.entities]
        assert "PERSON" in labels, f"Expected PERSON entity, got: {labels}"

    @requires_spacy
    def test_entity_dict_helper(self, spacy_pipeline):
        result = spacy_pipeline.process("Call Saif in Delhi tomorrow")
        d = result.entity_dict()
        assert isinstance(d, dict)
        for label, texts in d.items():
            assert isinstance(label, str)
            assert isinstance(texts, list)

    @requires_spacy
    def test_noun_chunks(self, spacy_pipeline):
        result = spacy_pipeline.process("The quick brown fox jumps over the lazy dog")
        assert len(result.noun_chunks) > 0

    @requires_spacy
    def test_root_verbs(self, spacy_pipeline):
        result = spacy_pipeline.process("Play music on YouTube")
        assert "play" in result.root_verbs or len(result.root_verbs) > 0

    @requires_spacy
    def test_pipeline_active_flag(self, spacy_pipeline):
        result = spacy_pipeline.process("Hello there")
        assert result.pipeline_active is True

    def test_fallback_mode_no_crash(self, pipeline):
        """Pipeline must not crash even when spaCy model is missing."""
        result = pipeline.process("This is a test message")
        assert result is not None
        assert isinstance(result.best_intent, str)


# ---------------------------------------------------------------------------
# Stage 3: NumPy cosine intent scoring
# ---------------------------------------------------------------------------

class TestStageIntentScoring:
    """Tests for Stage 3: NumPy TF-IDF cosine-similarity intent classification."""

    def test_intent_scores_populated(self, pipeline):
        result = pipeline.process("Set an alarm for 7am tomorrow")
        assert len(result.intent_scores) > 0

    def test_intent_scores_in_range(self, pipeline):
        result = pipeline.process("Play lofi music on YouTube")
        for score in result.intent_scores:
            assert 0.0 <= score.confidence <= 1.0, \
                f"Confidence out of range: {score.confidence}"

    def test_command_intent_detected(self, pipeline):
        result = pipeline.process("Set an alarm for 7am tomorrow")
        top3 = [s.intent for s in result.top_intents(3)]
        assert "command" in top3, f"Expected 'command' in top-3, got: {top3}"

    def test_question_intent_detected(self, pipeline):
        result = pipeline.process("What is the weather today in Paris?")
        top3 = [s.intent for s in result.top_intents(3)]
        assert "question" in top3, f"Expected 'question' in top-3, got: {top3}"

    def test_greeting_intent_detected(self, pipeline):
        result = pipeline.process("Hello Jarvis good morning")
        top3 = [s.intent for s in result.top_intents(3)]
        assert "greeting" in top3, f"Expected 'greeting' in top-3, got: {top3}"

    def test_memory_store_intent_detected(self, pipeline):
        result = pipeline.process("Remember that my birthday is in July")
        top3 = [s.intent for s in result.top_intents(3)]
        assert "memory_store" in top3, f"Expected 'memory_store' in top-3, got: {top3}"

    def test_emotional_intent_detected(self, pipeline):
        result = pipeline.process("I am feeling very stressed and tired today")
        top3 = [s.intent for s in result.top_intents(3)]
        assert "emotional" in top3, f"Expected 'emotional' in top-3, got: {top3}"

    def test_best_intent_matches_top_score(self, pipeline):
        result = pipeline.process("Open the camera app please")
        top = result.intent_scores[0]
        assert result.best_intent == top.intent
        assert abs(result.intent_confidence - top.confidence) < 1e-6

    def test_empty_string_safe(self, pipeline):
        result = pipeline.process("")
        assert result.best_intent == "casual"
        assert result.intent_confidence == 0.0

    def test_whitespace_only_safe(self, pipeline):
        result = pipeline.process("   ")
        assert result is not None


# ---------------------------------------------------------------------------
# Stage 4: Complexity & sentiment (pure Python + NumPy)
# ---------------------------------------------------------------------------

class TestStageComplexitySentiment:
    """Tests for Stage 4: sentence complexity and sentiment scoring."""

    def test_sentiment_positive(self, pipeline):
        result = pipeline.process("This is great I love it thank you so much")
        assert result.sentiment_score > 0, \
            f"Expected positive sentiment, got {result.sentiment_score}"

    def test_sentiment_negative(self, pipeline):
        result = pipeline.process("I hate this terrible broken error everything is wrong")
        assert result.sentiment_score < 0, \
            f"Expected negative sentiment, got {result.sentiment_score}"

    def test_sentiment_neutral(self, pipeline):
        result = pipeline.process("The cat sat on the mat")
        assert -0.3 <= result.sentiment_score <= 0.3, \
            f"Expected near-neutral sentiment, got {result.sentiment_score}"

    def test_complexity_non_negative(self, pipeline):
        result = pipeline.process("Hello")
        assert result.sentence_complexity >= 0.0

    def test_expertise_valid_values(self, pipeline):
        for text in [
            "hi",
            "Can you help me fix this bug please",
            "Implement a recursive memoized dynamic programming solution using LRU cache",
        ]:
            result = pipeline.process(text)
            assert result.expertise_level in ("beginner", "intermediate", "expert"), \
                f"Unexpected expertise_level: {result.expertise_level!r}"

    def test_word_count(self, pipeline):
        result = pipeline.process("Set an alarm for seven in the morning")
        assert result.word_count > 0


# ---------------------------------------------------------------------------
# NLPResult dataclass helpers
# ---------------------------------------------------------------------------

class TestNLPResult:
    """Tests for the NLPResult dataclass helpers."""

    def test_entities_by_label(self):
        from app.core.nlp_models import NLPResult, EntitySpan
        result = NLPResult(entities=[
            EntitySpan("Delhi", "GPE", 0, 1),
            EntitySpan("Saif", "PERSON", 2, 3),
            EntitySpan("Monday", "DATE", 4, 5),
        ])
        gpe = result.entities_by_label("GPE")
        assert len(gpe) == 1
        assert gpe[0].text == "Delhi"

    def test_top_intents_sorted(self, pipeline):
        result = pipeline.process("Set alarm for 7am and remind me to call mom")
        top = result.top_intents(3)
        confidences = [s.confidence for s in top]
        assert confidences == sorted(confidences, reverse=True)

    def test_entity_dict_grouping(self):
        from app.core.nlp_models import NLPResult, EntitySpan
        result = NLPResult(entities=[
            EntitySpan("London", "GPE", 0, 1),
            EntitySpan("Paris", "GPE", 2, 3),
            EntitySpan("Saif", "PERSON", 4, 5),
        ])
        d = result.entity_dict()
        assert sorted(d["GPE"]) == ["London", "Paris"]
        assert d["PERSON"] == ["Saif"]

    def test_summary_string(self, pipeline):
        result = pipeline.process("Hello Jarvis")
        summary = result.summary()
        assert "intent=" in summary
        assert "sentiment=" in summary


# ---------------------------------------------------------------------------
# Integration: UnderstandingEngine with NLP pipeline
# ---------------------------------------------------------------------------

class TestUnderstandingIntegration:
    """End-to-end tests: UnderstandingEngine.analyze() with NLPPipeline active."""

    @pytest.fixture(scope="class")
    def engine(self):
        from app.core.understanding import UnderstandingEngine
        return UnderstandingEngine()

    def test_analyze_returns_message_analysis(self, engine):
        from app.core.understanding import MessageAnalysis
        result = engine.analyze("Set an alarm for 7am")
        assert isinstance(result, MessageAnalysis)

    def test_analyze_attaches_nlp_result(self, engine):
        result = engine.analyze("Open YouTube and play music")
        assert hasattr(result, "nlp_result")
        assert hasattr(result, "nlp_confidence")

    def test_analyze_merges_spacy_entities(self, engine):
        """When spaCy is active, NER entities are merged into entities dict."""
        result = engine.analyze("Call Saif in Delhi tomorrow at 3pm")
        nlp_keys = [k for k in result.entities if k.startswith("nlp_")]
        if result.nlp_result is not None and result.nlp_result.pipeline_active:
            assert len(nlp_keys) > 0, \
                f"Expected merged NLP entities, got keys: {list(result.entities.keys())}"

    def test_analyze_hinglish(self, engine):
        """Hinglish text should not crash the pipeline."""
        result = engine.analyze("Yaad rakh mera meeting kal hai")
        assert result is not None
        assert result.intent in (
            "memory_store", "command", "casual", "question", "emotional",
            "greeting", "farewell", "creative", "memory_recall",
        )

    def test_analyze_empty_message_safe(self, engine):
        result = engine.analyze("")
        assert result is not None

    def test_nlp_confidence_zero_when_pipeline_off(self, engine):
        result = engine.analyze("Hello")
        if result.nlp_result is None:
            assert result.nlp_confidence == 0.0


# ---------------------------------------------------------------------------
# Model info
# ---------------------------------------------------------------------------

class TestModelInfo:
    def test_model_info_structure(self, pipeline):
        info = pipeline.model_info()
        assert "spacy_available" in info
        assert "model_loaded" in info
        assert "intent_classes" in info
        assert "vocab_size" in info
        assert isinstance(info["intent_classes"], list)
        assert len(info["intent_classes"]) > 0
        assert info["vocab_size"] > 0

    def test_no_scipy_in_model_info(self, pipeline):
        """Confirm scipy_available key is no longer present."""
        info = pipeline.model_info()
        assert "scipy_available" not in info
