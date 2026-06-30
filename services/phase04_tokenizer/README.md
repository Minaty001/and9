# Phase 4: Tokenization Engine

## Overview

Normalizes and tokenizes user input for downstream processing. Handles multilingual text (English, Hindi/Hinglish), typo correction, slang expansion, and noise removal.

## Pipeline

```
Input → Unicode NFKC → Lowercase → Noise Removal → Typo Correction
       → Slang Expansion → Hinglish Normalization → Tokenization → Output
```

## Components

### TextNormalizer
```python
normalizer = TextNormalizer()
text, corrections = normalizer.normalize("kya haal hai")
# text: "what is is"
# corrections: [{"type": "hinglish", "original": "kya", "corrected": "what"}, ...]
```

Features:
- Unicode NFKC normalization
- Hinglish → English mapping (100+ terms)
- Typo correction (40+ common typos)
- Slang expansion (20+ abbreviations)
- URL/mention/hashtag noise removal

### Tokenizer
```python
tokenizer = Tokenizer()
result = tokenizer.tokenize("Hello, how are you?")
print(result.tokens_text)  # ["hello", "how", "are", "you"]
print(result.tokens[0].type)  # "word"
```

Features:
- Word-level with character offsets
- Token type classification (word, number, punctuation, symbol)
- Stop word detection
- Character-level encoding for neural network input

## Models

### TokenizerResult
```python
result = TokenizerResult(
    original="Hello! Kya haal hai?",
    normalized="hello what is is",
    tokens=[Token(text="hello", start=0, end=5, type="word"), ...],
    tokens_text=["hello", "what", "is", "is"],
    token_count=4,
    character_count=20,
    has_multilingual=True,
    corrections=[{"type": "hinglish", "original": "kya", "corrected": "what"}],
    time_ms=1.5
)
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `JARVIS_TOKEN_LOWERCASE` | true | Lowercase conversion |
| `JARVIS_TOKEN_ENABLE_TYPO_CORRECTION` | true | Enable typo correction |
| `JARVIS_TOKEN_ENABLE_SLANG_EXPANSION` | true | Enable slang expansion |
| `JARVIS_TOKEN_MAX_INPUT_LENGTH` | 1000 | Maximum input characters |

## Integration

```python
from services.phase04_tokenizer import TokenizerService

svc = TokenizerService()
await svc.initialize()
result = await svc.tokenize("open whatsapp")
print(result.normalized)  # "open whatsapp"
print(result.tokens_text)  # ["open", "whatsapp"]
```
