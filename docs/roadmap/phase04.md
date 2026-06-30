# Phase 04: Tokenization Engine

## Purpose
Normalizes and tokenizes user input for downstream processing. Handles multilingual text (English, Hindi/Hinglish), typo correction (40+ common typos), slang expansion (20+ abbreviations), and noise removal via `TextNormalizer`. The `Tokenizer` produces word-level tokens with offsets, types, stop-word detection, and character-level encoding for neural network input.

## Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `JARVIS_TOKEN_LOWERCASE` | true | Lowercase conversion |
| `JARVIS_TOKEN_ENABLE_TYPO_CORRECTION` | true | Enable typo correction |
| `JARVIS_TOKEN_ENABLE_SLANG_EXPANSION` | true | Enable slang expansion |
| `JARVIS_TOKEN_MAX_INPUT_LENGTH` | 1000 | Maximum input characters |

## Architecture
```
Input → Unicode NFKC → Lowercase → Noise Removal → Typo Correction
       → Slang Expansion → Hinglish Normalization → Tokenization → Output
```

## Code
```python
class TextNormalizer:
    HINGLISH_MAP = {"kya": "what", "kaise": "how", ...}  # 100+ terms
    TYPO_MAP = {"teh": "the", "watsapp": "whatsapp", ...}  # 40+ typos

    def normalize(self, text) -> Tuple[str, List[dict]]:
        text = unicodedata.normalize("NFKC", text)
        text = text.lower()
        text = self._correct_typos(text, corrections)
        # Hinglish mapping per word
        words = [self.HINGLISH_MAP.get(w, w) for w in text.split()]
        return " ".join(words), corrections

class Tokenizer:
    def tokenize(self, text) -> TokenizerResult:
        normalized, corrections = self.normalizer.normalize(text)
        for match in WORD_PATTERN.finditer(normalized):
            tokens.append(Token(text=..., start=..., type=..., is_stopword=...))
        return TokenizerResult(original=text, normalized=normalized, tokens=tokens, ...)
```

## Location
`app/brain/neural/` or `app/core/` — tokenization feeds into neural/intent pipeline
