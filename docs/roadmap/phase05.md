# Phase 05: Embedding Engine

## Purpose
Generates 128-dim hybrid semantic vectors for intent detection and retrieval. Combines six feature components: character frequency (26), bigram frequency (26), word features (40), direction indicators (10), structural features (6), and intent-specific keyword groups (20). Maintains an LRU `EmbeddingCache` with TTL and cosine similarity search.

## Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `JARVIS_EMBED_EMBEDDING_DIM` | 128 | Vector dimension |
| `JARVIS_EMBED_CACHE_SIZE` | 500 | Max cache entries |
| `JARVIS_EMBED_CACHE_TTL_SECONDS` | 300 | Cache TTL |
| `JARVIS_EMBED_SIMILARITY_THRESHOLD` | 0.7 | Search threshold |

## Architecture
```
HybridEmbedding (128-dim)
  ├── char_frequency(text) → 26 floats (a-z normalized)
  ├── bigram_frequency(text) → 26 floats
  ├── word_features(text) → 40 floats (start chars, length dist, stats)
  ├── direction_features(text) → 10 floats (up/down, on/off...)
  ├── structural_features(text) → 6 floats (length, digits, symbols...)
  └── keyword_group_features(text) → 20 floats (intent group activation)
```

## Code
```python
class HybridEmbedding:
    def embed(self, text: str) -> List[float]:
        text = text.lower().strip()
        return (self._char_frequency(text) + self._bigram_frequency(text)
                + self._word_features(text) + self._direction_features(text)
                + self._structural_features(text) + self._keyword_group_features(text))
        # Sum = 128

class EmbeddingCache:
    def get(self, text) -> Optional[List[float]]:
        entry = self._cache.get(text)
        if not entry or time.time() > entry[1]: return None  # expired
        return entry[0]
```

## Location
`app/brain/neural/` — embedding vectors feed the intent classifier
