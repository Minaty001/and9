"""
Phase 5 — Embedding Service.

Wraps the Embedder in a ServiceBase with lifecycle management.
"""

import time
import logging
from typing import Any, Dict, List, Optional

from services.base.service_base import ServiceBase
from .config import EmbeddingConfig
from .embedder import Embedder
from .models import EmbeddingVector, SearchResult
from .similarity import cosine_similarity, top_k_similar

logger = logging.getLogger(__name__)


class EmbeddingService(ServiceBase):
    """Embedding service wrapping the Embedder with lifecycle management.

    Provides vector generation, caching, similarity search,
    and integration with the memory system.
    """

    def __init__(self, config: Optional[EmbeddingConfig] = None):
        super().__init__(name="jarvis_embedding", version="1.0.0")
        self.config = config or EmbeddingConfig()
        self.embedder = Embedder(config=self.config)
        self._vector_store: List[EmbeddingVector] = []
        self._start_time = 0.0

    async def initialize(self) -> bool:
        """Initialize the embedding service."""
        self._start_time = time.time()
        try:
            self._metrics.reset()
            self._metrics.gauge("cache_size", 0)
            self._metrics.gauge("vector_store_size", 0)
            self._initialized = True
            elapsed = (time.time() - self._start_time) * 1000
            logger.info("EmbeddingService initialized in %.0fms", elapsed)
            return True
        except Exception as e:
            logger.error("EmbeddingService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        """Shut down the service."""
        logger.info("EmbeddingService shutting down...")
        self.embedder._cache.clear()
        self._vector_store.clear()
        self._initialized = False

    # ── Embedding ───────────────────────────────────────────────

    async def embed(self, text: str) -> EmbeddingVector:
        """Generate an embedding vector for text.

        Args:
            text: Input text.

        Returns:
            EmbeddingVector with 128-dim vector.
        """
        t0 = time.perf_counter()
        result = self.embedder.embed(text)
        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.counter("embeddings_generated")
        self._metrics.histogram("embed_time_ms", elapsed)
        self._metrics.gauge("cache_size", self.embedder._cache.size)
        return result

    async def embed_batch(self, texts: List[str]) -> List[EmbeddingVector]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of input texts.

        Returns:
            List of EmbeddingVector instances.
        """
        results = self.embedder.embed_batch(texts)
        self._metrics.counter("embeddings_generated", len(results))
        self._metrics.gauge("cache_size", self.embedder._cache.size)
        return results

    # ── Similarity ──────────────────────────────────────────────

    async def similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        """Compute cosine similarity between two vectors.

        Args:
            vec_a: First vector.
            vec_b: Second vector.

        Returns:
            Cosine similarity score.
        """
        return cosine_similarity(vec_a, vec_b)

    async def search(
        self,
        query: str,
        candidates: List[str],
        k: int = 5,
        threshold: float = 0.0,
    ) -> List[SearchResult]:
        """Search for similar texts.

        Args:
            query: Query text.
            candidates: List of candidate texts to search.
            k: Maximum results.
            threshold: Minimum similarity threshold.

        Returns:
            List of SearchResult sorted by descending similarity.
        """
        t0 = time.perf_counter()
        query_vec = (await self.embed(query)).vector

        candidate_vectors = []
        for text in candidates:
            vec = (await self.embed(text)).vector
            candidate_vectors.append((text, vec))

        results = top_k_similar(query_vec, candidate_vectors, k=k, threshold=threshold)
        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.histogram("search_time_ms", elapsed)
        self._metrics.counter("searches_performed")

        return [
            SearchResult(text=text, score=score)
            for text, score in results
        ]

    # ── Vector Store Management ─────────────────────────────────

    async def store_vector(self, vector: EmbeddingVector) -> None:
        """Store a vector for later retrieval.

        Args:
            vector: EmbeddingVector to store.
        """
        self._vector_store.append(vector)
        self._metrics.gauge("vector_store_size", len(self._vector_store))

    async def clear_store(self) -> None:
        """Clear the in-memory vector store."""
        self._vector_store.clear()
        self._metrics.gauge("vector_store_size", 0)

    # ── Health / Stats ──────────────────────────────────────────

    async def health(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service_name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
            "cache_size": self.embedder._cache.size,
            "vector_store_size": len(self._vector_store),
        }

    async def stats(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        cache_stats = self.embedder._cache.get_stats()
        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            "embedding_dim": self.config.embedding_dim,
            "cache": cache_stats,
            "vector_store_size": len(self._vector_store),
            "metrics": self._metrics.snapshot(),
        }
