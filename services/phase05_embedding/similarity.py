"""
Phase 5 — Similarity Functions.

Provides cosine similarity and top-k search for embedding vectors.
"""

import math
import numpy as np
from typing import List, Tuple

from .errors import DimensionMismatchError


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Compute cosine similarity between two vectors.

    Args:
        vec_a: First vector.
        vec_b: Second vector.

    Returns:
        Cosine similarity in range [-1.0, 1.0].

    Raises:
        DimensionMismatchError: If vectors have different dimensions.
    """
    if len(vec_a) != len(vec_b):
        raise DimensionMismatchError(len(vec_a), len(vec_b))

    if not vec_a or not vec_b:
        return 0.0

    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


def cosine_similarity_np(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """Compute cosine similarity using NumPy (faster for large vectors)."""
    if vec_a.shape != vec_b.shape:
        raise DimensionMismatchError(int(vec_a.shape[0]), int(vec_b.shape[0]))

    dot = float(np.dot(vec_a, vec_b))
    norm_a = float(np.linalg.norm(vec_a))
    norm_b = float(np.linalg.norm(vec_b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


def top_k_similar(
    query_vector: List[float],
    candidates: List[Tuple[str, List[float]]],
    k: int = 5,
    threshold: float = 0.0,
) -> List[Tuple[str, float]]:
    """Find top-k most similar vectors to a query vector.

    Args:
        query_vector: Query embedding.
        candidates: List of (text, vector) tuples.
        k: Maximum number of results to return.
        threshold: Minimum similarity threshold.

    Returns:
        List of (text, score) tuples sorted by descending similarity.
    """
    scored: List[Tuple[str, float]] = []
    for text, vec in candidates:
        if len(vec) != len(query_vector):
            continue
        score = cosine_similarity(query_vector, vec)
        if score >= threshold:
            scored.append((text, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:k]
