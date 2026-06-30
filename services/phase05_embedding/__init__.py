"""
Phase 5 — Embedding Engine
============================

Generate semantic vectors for retrieval and intent detection.
Maintains an embedding cache with TTL.
Uses cosine similarity for semantic search.
Integrates with long-term memory.

Key features:
    - 128-dim hybrid embedding (char freq, bigrams, keywords)
    - LRU embedding cache with TTL
    - Cosine similarity for vector comparison
    - Batch embedding for efficiency
"""

from .embedder import Embedder, HybridEmbedding
from .cache import EmbeddingCache
from .similarity import cosine_similarity, top_k_similar
from .service import EmbeddingService
from .config import EmbeddingConfig
from .models import EmbeddingVector, SearchResult

__all__ = [
    "Embedder",
    "HybridEmbedding",
    "EmbeddingCache",
    "cosine_similarity",
    "top_k_similar",
    "EmbeddingService",
    "EmbeddingConfig",
    "EmbeddingVector",
    "SearchResult",
]
