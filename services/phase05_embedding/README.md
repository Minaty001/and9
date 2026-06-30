# Phase 5: Embedding Engine

## Overview

Generates 128-dim semantic vectors for intent detection and retrieval. Maintains an LRU embedding cache with TTL and uses cosine similarity for semantic search.

## Architecture

### HybridEmbedding (128-dim)
Six feature components combined:

| Component | Dims | Description |
|-----------|------|-------------|
| Char frequency | 26 | Normalized a-z frequency |
| Bigram frequency | 26 | Next-char distribution |
| Word features | 40 | Start chars, length dist, stats |
| Direction indicators | 10 | Up/down, on/off, etc. |
| Structural features | 6 | Length, punctuation, digits |
| Keyword groups | 20 | Intent-specific keyword activation |

### EmbeddingCache
```python
cache = EmbeddingCache(max_size=500, ttl_seconds=300)
cache.put("hello", [0.1, 0.2, ...])
vector = cache.get("hello")  # or None if expired/missed
```

### Similarity
```python
score = cosine_similarity(vec_a, vec_b)  # [-1.0, 1.0]
results = top_k_similar(query_vec, candidates, k=5, threshold=0.7)
```

## Usage

```python
from services.phase05_embedding import EmbeddingService

svc = EmbeddingService()
await svc.initialize()

# Single embedding
vec = await svc.embed("open whatsapp")

# Similarity search
results = await svc.search("music", ["play song", "close app", "weather"], k=2)
for r in results:
    print(f"{r.text}: {r.score:.3f}")
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `JARVIS_EMBED_EMBEDDING_DIM` | 128 | Vector dimension |
| `JARVIS_EMBED_CACHE_SIZE` | 500 | Max cache entries |
| `JARVIS_EMBED_CACHE_TTL_SECONDS` | 300 | Cache TTL |
| `JARVIS_EMBED_SIMILARITY_THRESHOLD` | 0.7 | Search threshold |
