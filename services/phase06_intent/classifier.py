"""
Phase 6 — Intent Classifier with TinyNeuralNetwork.

NumPy-only neural network:
    Input(128) → Dense(64, ReLU) → Dense(32, ReLU) → Dense(28, Softmax)

Based on the proven architecture from ai/micro_brain/brain/neural.py
Supports both softmax classification and raw probability output.
"""

import math
import json
import time
import logging
from typing import Dict, List, Optional, Tuple

import numpy as np

from .config import IntentConfig
from .models import IntentResult, IntentType
from .errors import ModelLoadError, InferenceError

logger = logging.getLogger(__name__)


class TinyNeuralNetwork:
    """Minimal NumPy neural network for intent classification.

    Architecture: 128 → 64 (ReLU) → 32 (ReLU) → 28 (Softmax)

    Usage:
        nn = TinyNeuralNetwork()
        nn.initialize()
        probs = nn.predict(embedding_vector)
        intent = nn.predict_intent(embedding_vector)
    """

    def __init__(self, config: Optional[IntentConfig] = None):
        self.config = config or IntentConfig()
        self._weights: Dict[str, np.ndarray] = {}
        self._biases: Dict[str, np.ndarray] = {}
        self._intent_names = IntentType.list_names()
        self._initialized = False

    def initialize(self) -> bool:
        """Initialize the neural network with random weights or load from file.

        Returns:
            True if initialization succeeded.
        """
        try:
            if self.config.model_path:
                self._load_weights(self.config.model_path)
            else:
                self._init_random_weights()

            self._initialized = True
            logger.info("TinyNeuralNetwork initialized: %s params",
                        self._count_parameters())
            return True
        except Exception as e:
            logger.error("TinyNeuralNetwork init failed: %s", e)
            return False

    def _init_random_weights(self):
        """Initialize weights with Xavier initialization."""
        dims = [
            (self.config.input_dim, self.config.hidden_1),
            (self.config.hidden_1, self.config.hidden_2),
            (self.config.hidden_2, self.config.output_dim),
        ]
        for i, (in_dim, out_dim) in enumerate(dims):
            scale = math.sqrt(2.0 / in_dim)
            self._weights[f"w{i+1}"] = np.random.randn(in_dim, out_dim).astype(np.float32) * scale
            self._biases[f"b{i+1}"] = np.zeros((1, out_dim), dtype=np.float32)

    def _load_weights(self, path: str):
        """Load pretrained weights from an npz file."""
        try:
            data = np.load(path)
            self._weights["w1"] = data["w1"]
            self._biases["b1"] = data["b1"]
            self._weights["w2"] = data["w2"]
            self._biases["b2"] = data["b2"]
            self._weights["w3"] = data["w3"]
            self._biases["b3"] = data["b3"]
            logger.info("Loaded model weights from '%s'", path)
        except Exception as e:
            raise ModelLoadError(path, str(e))

    # ── Forward Pass ────────────────────────────────────────────

    def predict(self, embedding: List[float]) -> np.ndarray:
        """Run forward pass and return softmax probabilities.

        Args:
            embedding: 128-dim input vector.

        Returns:
            np.ndarray of shape (28,) with softmax probabilities.
        """
        if not self._initialized:
            raise InferenceError("Neural network not initialized")

        x = np.array(embedding, dtype=np.float32).reshape(1, -1)

        # Layer 1: 128 → 64, ReLU
        z1 = np.dot(x, self._weights["w1"]) + self._biases["b1"]
        a1 = np.maximum(0, z1)  # ReLU

        # Layer 2: 64 → 32, ReLU
        z2 = np.dot(a1, self._weights["w2"]) + self._biases["b2"]
        a2 = np.maximum(0, z2)  # ReLU

        # Layer 3: 32 → 28, Softmax
        z3 = np.dot(a2, self._weights["w3"]) + self._biases["b3"]
        exp_z3 = np.exp(z3 - np.max(z3))  # numerical stability
        probs = exp_z3 / np.sum(exp_z3)

        return probs.flatten()

    def predict_intent(self, embedding: List[float]) -> Tuple[str, float, np.ndarray]:
        """Predict the most likely intent.

        Args:
            embedding: 128-dim input vector.

        Returns:
            Tuple of (intent_name, confidence, all_probabilities).
        """
        probs = self.predict(embedding)
        max_idx = int(np.argmax(probs))
        confidence = float(probs[max_idx])
        intent_name = self._intent_names[max_idx] if max_idx < len(self._intent_names) else "UNKNOWN"
        return intent_name, confidence, probs

    def predict_top_k(self, embedding: List[float], k: int = 3) -> List[dict]:
        """Return top-k intent predictions.

        Args:
            embedding: 128-dim input vector.
            k: Number of top intents to return.

        Returns:
            List of {"intent": str, "confidence": float} dicts.
        """
        probs = self.predict(embedding)
        indices = np.argsort(probs)[::-1][:k]
        return [
            {
                "intent": self._intent_names[i] if i < len(self._intent_names) else "UNKNOWN",
                "confidence": float(probs[i]),
            }
            for i in indices
        ]

    # ── Serialization ───────────────────────────────────────────

    def save_weights(self, path: str) -> None:
        """Save weights to an npz file."""
        np.savez_compressed(
            path,
            w1=self._weights["w1"],
            b1=self._biases["b1"],
            w2=self._weights["w2"],
            b2=self._biases["b2"],
            w3=self._weights["w3"],
            b3=self._biases["b3"],
        )
        logger.info("Saved model weights to '%s'", path)

    # ── Introspection ───────────────────────────────────────────

    def _count_parameters(self) -> int:
        if not self._weights:
            return 0
        return sum(w.size for w in self._weights.values())

    def get_stats(self) -> dict:
        """Return network statistics."""
        if not self._initialized:
            return {"initialized": False, "parameters": 0}
        return {
            "initialized": True,
            "parameters": self._count_parameters(),
            "architecture": f"{self.config.input_dim}→{self.config.hidden_1}→{self.config.hidden_2}→{self.config.output_dim}",
            "intents": len(self._intent_names),
        }


class IntentClassifier:
    """High-level intent classifier that combines the neural network
    with keyword-based fallback for known commands.

    Usage:
        classifier = IntentClassifier()
        classifier.initialize()
        result = classifier.classify(embedding_vector, original_text)
        print(result.intent, result.confidence)
    """

    # Keyword → intent overrides (fast path, no NN needed)
    KEYWORD_OVERRIDES: Dict[str, str] = {
        # Apps
        "open whatsapp": "OPEN_APP", "open youtube": "OPEN_APP",
        "open chrome": "OPEN_APP", "open camera": "OPEN_APP",
        "open settings": "SETTING", "open gallery": "OPEN_APP",
        # Navigation
        "go home": "HOME", "go back": "BACK", "back": "BACK",
        # Flashlight
        "flashlight on": "FLASHLIGHT_ON", "torch on": "FLASHLIGHT_ON",
        "flashlight off": "FLASHLIGHT_OFF", "torch off": "FLASHLIGHT_OFF",
        # Volume
        "volume up": "VOLUME_UP", "volume down": "VOLUME_DOWN",
        # Media
        "play music": "PLAY_MUSIC", "pause music": "PAUSE_MUSIC",
        # System
        "close app": "CLOSE_APP",
    }

    def __init__(self, config: Optional[IntentConfig] = None):
        self.config = config or IntentConfig()
        self.nn = TinyNeuralNetwork(config=self.config)

    def initialize(self) -> bool:
        """Initialize the classifier including the neural network."""
        return self.nn.initialize()

    def classify(self, embedding: List[float], text: str = "") -> IntentResult:
        """Classify intent from embedding vector and optional original text.

        Uses keyword override first (fast path), falls back to NN.

        Args:
            embedding: 128-dim embedding vector.
            text: Original text for keyword matching.

        Returns:
            IntentResult with intent name, confidence, and probabilities.
        """
        t0 = time.perf_counter()

        # Fast path: keyword override
        if text:
            text_lower = text.lower().strip()
            if text_lower in self.KEYWORD_OVERRIDES:
                intent = self.KEYWORD_OVERRIDES[text_lower]
                elapsed = (time.perf_counter() - t0) * 1000
                return IntentResult(
                    intent=intent,
                    confidence=0.95,
                    all_probabilities={intent: 0.95},
                    time_ms=round(elapsed, 2),
                    metadata={"source": "keyword_override"},
                )

        # Neural network path
        intent_name, confidence, probs = self.nn.predict_intent(embedding)

        # Build probability dict
        prob_dict = {}
        intent_names = IntentType.list_names()
        for i, p in enumerate(probs):
            name = intent_names[i] if i < len(intent_names) else f"CLASS_{i}"
            prob_dict[name] = round(float(p), 4)

        # Check for multi-intent
        threshold = 0.1
        secondary = []
        for i, p in enumerate(probs):
            name = intent_names[i] if i < len(intent_names) else f"CLASS_{i}"
            if name != intent_name and float(p) >= threshold:
                secondary.append({"intent": name, "confidence": round(float(p), 4)})

        elapsed = (time.perf_counter() - t0) * 1000

        return IntentResult(
            intent=intent_name,
            confidence=round(confidence, 4),
            all_probabilities=prob_dict,
            is_multi_intent=len(secondary) > 0,
            secondary_intents=sorted(secondary, key=lambda x: x["confidence"], reverse=True)[:3],
            time_ms=round(elapsed, 2),
            metadata={"source": "neural_network"},
        )

    def classify_top_k(self, embedding: List[float], k: int = 3) -> List[dict]:
        """Return top-k intent predictions.

        Args:
            embedding: 128-dim embedding vector.
            k: Number of predictions.

        Returns:
            List of {"intent": str, "confidence": float}.
        """
        return self.nn.predict_top_k(embedding, k=k)
