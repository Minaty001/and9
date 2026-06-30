"""
Phase 5 — Embedding Engine / Embedder.

Generates 128-dim hybrid embedding vectors combining:
    - Character frequency (26-dim)
    - Bigram frequency (26-dim)
    - Word-level features (40-dim)
    - Direction/opposition indicators (10-dim)
    - Structural features (6-dim)
    - Intent-specific keyword groups (20-dim)

Based on the proven embedding from ai/micro_brain/brain/neural.py
"""

import math
import time
import logging
from typing import Dict, List, Optional, Tuple

from .config import EmbeddingConfig
from .models import EmbeddingVector
from .cache import EmbeddingCache
from .errors import EmbeddingError

logger = logging.getLogger(__name__)


class HybridEmbedding:
    """128-dim hybrid text embedding for intent detection and retrieval.

    Combines multiple signal types to produce a dense vector representation
    suitable for neural network classification and cosine similarity search.

    Usage:
        embedder = HybridEmbedding()
        vector = embedder.embed("open whatsapp")
        print(len(vector))  # 128
    """

    # Intent-specific keyword groups (20 groups, each contributes 1 dim)
    INTENT_KEYWORD_GROUPS: List[Tuple[str, List[str]]] = [
        ("app_launch", ["open", "launch", "start", "run", "kholo", "chalao"]),
        ("app_close", ["close", "exit", "band", "kill", "stop"]),
        ("music", ["music", "song", "gaana", "play", "pause", "bajao"]),
        ("search", ["search", "google", "find", "dhoondho", "look"]),
        ("weather", ["weather", "mausam", "temperature", "rain"]),
        ("time", ["time", "samay", "baje", "bajaa", "clock"]),
        ("date", ["date", "tareekh", "day", "din"]),
        ("reminder", ["remind", "reminder", "yaad", "dila"]),
        ("call", ["call", "phone", "dial", "fone", "phone karo"]),
        ("message", ["message", "text", "sms", "msg"]),
        ("camera", ["camera", "photo", "picture", "selfie", "click"]),
        ("flashlight", ["flashlight", "torch", "flash", "light"]),
        ("volume", ["volume", "sound", "aawaz", "louder"]),
        ("navigation", ["home", "back", "go back", "peeche", "wapis"]),
        ("settings", ["setting", "settings", "configure"]),
        ("help", ["help", "capability", "can you", "kya kar sakte"]),
        ("coding", ["code", "python", "program", "function"]),
        ("knowledge", ["what", "who", "why", "how", "explain", "meaning"]),
        ("chat", ["hello", "hi", "hey", "namaste", "how are you"]),
        ("emergency", ["emergency", "help", "danger", "save", "bachao"]),
    ]

    def __init__(self, config: Optional[EmbeddingConfig] = None):
        self.config = config or EmbeddingConfig()
        self.dim = self.config.embedding_dim  # 128
        self._validate_dimension()

    def _validate_dimension(self):
        """Ensure the configured dimension matches our hardcoded 128."""
        expected = self._compute_expected_dimension()
        if self.dim != expected:
            raise EmbeddingError(
                f"Embedding dimension mismatch: configured {self.dim}, "
                f"expected {expected} (char_freq=26 + bigram=26 + "
                f"word=40 + direction=10 + structural=6 + keywords=20)"
            )

    @staticmethod
    def _compute_expected_dimension() -> int:
        return 26 + 26 + 40 + 10 + 6 + 20  # = 128

    def embed(self, text: str) -> List[float]:
        """Generate a 128-dim hybrid embedding vector.

        Args:
            text: Input text (will be lowercased).

        Returns:
            List of 128 floats.
        """
        text = text.lower().strip()
        if not text:
            return [0.0] * self.dim

        vector: List[float] = []

        # 1. Character frequency (26 dims: a-z)
        vector.extend(self._char_frequency(text))

        # 2. Character bigram frequency (26 dims: aa-az, ba-bz, ...)
        vector.extend(self._bigram_frequency(text))

        # 3. Word-level features (40 dims)
        vector.extend(self._word_features(text))

        # 4. Direction / opposition indicators (10 dims)
        vector.extend(self._direction_features(text))

        # 5. Structural features (6 dims)
        vector.extend(self._structural_features(text))

        # 6. Intent-specific keyword groups (20 dims)
        vector.extend(self._keyword_group_features(text))

        return vector

    # ── Feature Components ──────────────────────────────────────

    @staticmethod
    def _char_frequency(text: str) -> List[float]:
        """26-dim: normalized frequency of a-z characters."""
        freq = [0.0] * 26
        letters = sum(1 for c in text if "a" <= c <= "z")
        if letters == 0:
            return freq
        for c in text:
            if "a" <= c <= "z":
                freq[ord(c) - ord("a")] += 1
        return [f / letters for f in freq]

    @staticmethod
    def _bigram_frequency(text: str) -> List[float]:
        """26-dim: bigram first-letter frequency (next char after each letter)."""
        bigram = [0.0] * 26
        count = 0
        for i in range(len(text) - 1):
            if "a" <= text[i] <= "z" and "a" <= text[i + 1] <= "z":
                bigram[ord(text[i + 1]) - ord("a")] += 1
                count += 1
        if count > 0:
            bigram = [b / count for b in bigram]
        return bigram

    @staticmethod
    def _word_features(text: str) -> List[float]:
        """40-dim: word-level features.

        Components:
            - First 26: word start character frequency (a-z) weighted by position
            - Next 10: word length distribution (1-10+ chars)
            - Last 4: word count, avg word length, unique word ratio, caps ratio
        """
        words = text.split()
        if not words:
            return [0.0] * 40

        features = [0.0] * 40

        # Word-start character freq
        for i, word in enumerate(words):
            if word and "a" <= word[0] <= "z":
                idx = ord(word[0]) - ord("a")
                position_weight = 1.0 / (i + 1)
                features[idx] += position_weight
        # Normalize
        total_weight = sum(features[:26])
        if total_weight > 0:
            features[:26] = [f / total_weight for f in features[:26]]

        # Word length distribution
        for word in words:
            length = min(len(word), 10)
            features[26 + min(length - 1, 9)] += 1
        total_words = len(words)
        features[26:36] = [f / total_words for f in features[26:36]]

        # Aggregate stats
        features[36] = min(total_words / 20.0, 1.0)  # word count
        features[37] = min(sum(len(w) for w in words) / (total_words * 20.0), 1.0)  # avg length
        unique_ratio = len(set(words)) / total_words if total_words > 0 else 0
        features[38] = unique_ratio
        caps = sum(1 for w in words if w and w[0].isupper()) / total_words if total_words > 0 else 0
        features[39] = caps

        return features

    @staticmethod
    def _direction_features(text: str) -> List[float]:
        """10-dim: direction/opposition indicators.

        Components:
            - up/down, on/off, in/out, yes/no, forward/backward,
              open/close, start/stop, increase/decrease, add/remove, enable/disable
        """
        words = set(text.lower().split())
        pairs = [
            ("up", "down"), ("on", "off"), ("in", "out"),
            ("yes", "no"), ("forward", "back"), ("open", "close"),
            ("start", "stop"), ("increase", "decrease"),
            ("add", "remove"), ("enable", "disable"),
        ]
        features = [0.0] * 10
        for i, (pos, neg) in enumerate(pairs):
            if pos in words:
                features[i] += 1.0
            if neg in words:
                features[i] -= 1.0
        return features

    @staticmethod
    def _structural_features(text: str) -> List[float]:
        """6-dim: structural features.

        Components:
            - Query length (normalized)
            - Word count (normalized)
            - Question mark presence
            - Exclamation presence
            - Contains digits
            - Contains special symbols
        """
        features = [0.0] * 6
        features[0] = min(len(text) / 100.0, 1.0)  # normalized length
        features[1] = min(len(text.split()) / 20.0, 1.0)  # normalized word count
        features[2] = 1.0 if "?" in text else 0.0
        features[3] = 1.0 if "!" in text else 0.0
        features[4] = 1.0 if any(c.isdigit() for c in text) else 0.0
        features[5] = 1.0 if any(c in "+-=@#$%&*" for c in text) else 0.0
        return features

    def _keyword_group_features(self, text: str) -> List[float]:
        """20-dim: intent-specific keyword group activation.

        Each dimension corresponds to a keyword group (0-1 activation).
        """
        words = set(text.lower().split())
        text_lower = text.lower()
        features = [0.0] * len(self.INTENT_KEYWORD_GROUPS)

        for i, (group_name, keywords) in enumerate(self.INTENT_KEYWORD_GROUPS):
            for kw in keywords:
                if kw in words or kw in text_lower:
                    features[i] = max(features[i], 1.0)
                    break
                # Partial match for multi-word keywords
                if " " in kw and kw in text_lower:
                    features[i] = max(features[i], 0.8)

        return features


class Embedder:
    """High-level embedding service with caching.

    Usage:
        embedder = Embedder()
        vector = embedder.embed("hello world")
        print(len(vector))  # 128
    """

    def __init__(self, config: Optional[EmbeddingConfig] = None):
        self.config = config or EmbeddingConfig()
        self._engine = HybridEmbedding(config=self.config)
        self._cache = EmbeddingCache(
            max_size=self.config.cache_size,
            ttl_seconds=self.config.cache_ttl_seconds,
        )

    def embed(self, text: str, use_cache: bool = True) -> EmbeddingVector:
        """Generate an embedding vector for text.

        Args:
            text: Input text.
            use_cache: Whether to use the LRU cache.

        Returns:
            EmbeddingVector with vector and metadata.
        """
        # Check cache
        if use_cache:
            cached = self._cache.get(text)
            if cached is not None:
                return EmbeddingVector(
                    vector=cached,
                    dimension=len(cached),
                    text=text,
                    created_at=time.time(),
                    metadata={"cached": True},
                )

        # Generate embedding
        raw_vector = self._engine.embed(text)

        # Normalize
        magnitude = math.sqrt(sum(v * v for v in raw_vector))
        if magnitude > 0:
            vector = [v / magnitude for v in raw_vector]
        else:
            vector = raw_vector

        # Store in cache
        if use_cache:
            self._cache.put(text, vector)

        return EmbeddingVector(
            vector=vector,
            dimension=len(vector),
            text=text,
            created_at=time.time(),
            metadata={"cached": False},
        )

    def embed_batch(self, texts: List[str]) -> List[EmbeddingVector]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of input texts.

        Returns:
            List of EmbeddingVector instances.
        """
        return [self.embed(t) for t in texts]
