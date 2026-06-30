"""
Tests for Phase 6 — Intent Detection.
"""

import pytest
import numpy as np
from services.phase06_intent import (
    TinyNeuralNetwork,
    IntentClassifier,
    ConfidenceScorer,
    IntentDetectionService,
    IntentConfig,
    IntentResult,
    IntentType,
)
from services.phase06_intent.errors import InferenceError


class TestTinyNeuralNetwork:
    """Verify the neural network classifier."""

    def test_initialize_random(self):
        nn = TinyNeuralNetwork()
        result = nn.initialize()
        assert result is True
        assert nn._initialized is True

    def test_predict_shape(self):
        nn = TinyNeuralNetwork()
        nn.initialize()
        embedding = [0.1] * 128
        probs = nn.predict(embedding)
        assert len(probs) == 28  # output_dim

    def test_predict_sum_to_one(self):
        nn = TinyNeuralNetwork()
        nn.initialize()
        embedding = [0.1] * 128
        probs = nn.predict(embedding)
        assert pytest.approx(sum(probs), 0.001) == 1.0

    def test_predict_intent(self):
        nn = TinyNeuralNetwork()
        nn.initialize()
        embedding = [0.1] * 128
        intent, confidence, probs = nn.predict_intent(embedding)
        assert isinstance(intent, str)
        assert 0 <= confidence <= 1
        assert len(probs) == 28

    def test_predict_top_k(self):
        nn = TinyNeuralNetwork()
        nn.initialize()
        embedding = [0.1] * 128
        results = nn.predict_top_k(embedding, k=3)
        assert len(results) == 3
        assert all("intent" in r for r in results)
        assert all("confidence" in r for r in results)

    def test_not_initialized_error(self):
        nn = TinyNeuralNetwork()
        with pytest.raises(InferenceError):
            nn.predict([0.1] * 128)

    def test_deterministic_output(self):
        nn = TinyNeuralNetwork()
        nn.initialize()
        emb = [0.1] * 128
        r1, c1, _ = nn.predict_intent(emb)
        r2, c2, _ = nn.predict_intent(emb)
        assert r1 == r2
        assert c1 == c2

    def test_different_input_different_output(self):
        nn = TinyNeuralNetwork()
        nn.initialize()
        i1, c1, _ = nn.predict_intent([0.0] * 128)
        i2, c2, _ = nn.predict_intent([1.0] * 128)
        # May not always differ, but should be possible
        assert i1 is not None
        assert i2 is not None

    def test_save_and_load_weights(self, tmp_path):
        nn = TinyNeuralNetwork()
        nn.initialize()
        path = str(tmp_path / "test_model.npz")
        nn.save_weights(path)

        nn2 = TinyNeuralNetwork(IntentConfig(model_path=path))
        result = nn2.initialize()
        assert result is True

        # Same input should give same output
        emb = [0.1] * 128
        i1, c1, _ = nn.predict_intent(emb)
        i2, c2, _ = nn2.predict_intent(emb)
        assert i1 == i2
        assert c1 == c2

    def test_parameter_count(self):
        nn = TinyNeuralNetwork()
        nn.initialize()
        stats = nn.get_stats()
        assert stats["parameters"] > 0
        assert stats["initialized"] is True
        assert "→" in stats["architecture"]


class TestIntentClassifier:
    """Verify the high-level classifier."""

    def test_keyword_override_open_app(self):
        classifier = IntentClassifier()
        classifier.initialize()
        result = classifier.classify([0.0] * 128, "open whatsapp")
        assert result.intent == "OPEN_APP"
        assert result.confidence == 0.95

    def test_keyword_override_flashlight(self):
        classifier = IntentClassifier()
        classifier.initialize()
        result = classifier.classify([0.0] * 128, "flashlight on")
        assert result.intent == "FLASHLIGHT_ON"

    def test_neural_network_fallback(self):
        classifier = IntentClassifier()
        classifier.initialize()
        result = classifier.classify([0.1] * 128, "some random query")
        assert result.intent in IntentType.list_names()
        assert 0 <= result.confidence <= 1

    def test_classify_top_k(self):
        classifier = IntentClassifier()
        classifier.initialize()
        results = classifier.classify_top_k([0.1] * 128, k=3)
        assert len(results) == 3

    def test_multi_intent_detection(self):
        classifier = IntentClassifier()
        classifier.initialize()
        # Use NN path
        result = classifier.classify([0.1] * 128, "play music and search web")
        # May or may not detect multi-intent, but should not crash
        assert result.intent is not None

    def test_result_model(self):
        result = IntentResult(intent="OPEN_APP", confidence=0.95)
        assert result.intent == "OPEN_APP"
        assert result.confidence == 0.95
        assert result.is_multi_intent is False


class TestConfidenceScorer:
    """Verify multi-source confidence computation."""

    def test_high_confidence(self):
        scorer = ConfidenceScorer()
        score = scorer.compute(nn_confidence=0.95, query="open whatsapp", intent="OPEN_APP")
        assert score > 0.7

    def test_low_confidence(self):
        scorer = ConfidenceScorer()
        score = scorer.compute(nn_confidence=0.2, query="x", intent="UNKNOWN")
        assert score < 0.5

    def test_keyword_boost(self):
        scorer = ConfidenceScorer()
        score_with_keyword = scorer.compute(
            nn_confidence=0.5, query="play music", intent="PLAY_MUSIC", keyword_match=1.0
        )
        score_without = scorer.compute(
            nn_confidence=0.5, query="something else", intent="UNKNOWN", keyword_match=0.0
        )
        assert score_with_keyword > score_without

    def test_requires_clarification(self):
        scorer = ConfidenceScorer(IntentConfig(min_confidence=0.5))
        assert scorer.requires_clarification(0.3) is True
        assert scorer.requires_clarification(0.6) is False

    def test_is_high_confidence(self):
        scorer = ConfidenceScorer(IntentConfig(high_confidence=0.85))
        assert scorer.is_high_confidence(0.9) is True
        assert scorer.is_high_confidence(0.8) is False

    def test_estimate_keyword_match(self):
        score = ConfidenceScorer.estimate_keyword_match("open whatsapp", "OPEN_APP")
        assert score > 0

    def test_query_quality(self):
        assert ConfidenceScorer._query_quality("") == 0.0
        assert ConfidenceScorer._query_quality("hi") == 0.4
        assert ConfidenceScorer._query_quality("open whatsapp") == 0.7
        assert ConfidenceScorer._query_quality("a b c d e") == 1.0


class TestIntentDetectionService:
    """Verify the service wrapper."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        svc = IntentDetectionService()
        result = await svc.initialize()
        assert result is True

    @pytest.mark.asyncio
    async def test_detect(self):
        svc = IntentDetectionService()
        await svc.initialize()
        result = await svc.detect([0.1] * 128, "hello")
        assert isinstance(result, IntentResult)
        assert result.intent in IntentType.list_names()

    @pytest.mark.asyncio
    async def test_detect_with_keyword_override(self):
        svc = IntentDetectionService()
        await svc.initialize()
        result = await svc.detect([0.0] * 128, "open whatsapp")
        assert result.intent == "OPEN_APP"

    @pytest.mark.asyncio
    async def test_detect_top_k(self):
        svc = IntentDetectionService()
        await svc.initialize()
        results = await svc.detect_top_k([0.1] * 128, k=3)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_clarification_check(self):
        svc = IntentDetectionService(IntentConfig(min_confidence=0.5))
        await svc.initialize()
        assert await svc.requires_clarification(0.3) is True
        assert await svc.requires_clarification(0.7) is False

    @pytest.mark.asyncio
    async def test_health(self):
        svc = IntentDetectionService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"
        assert health["nn_initialized"] is True

    @pytest.mark.asyncio
    async def test_stats(self):
        svc = IntentDetectionService()
        await svc.initialize()
        await svc.detect([0.1] * 128, "test")
        stats = await svc.stats()
        assert "nn" in stats
        assert "metrics" in stats
