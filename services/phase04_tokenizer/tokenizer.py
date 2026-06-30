"""
Phase 4 — Tokenization Engine.

Tokenizes normalized text into structured tokens with offsets,
token types, and metadata. Prepares text for intent detection
and embedding generation.

Supports:
    - Word-level tokenization (split on whitespace + punctuation)
    - Character-level tokenization (for neural network input)
    - Token metadata (type, offsets, stopword detection)
    - Configurable punctuation handling
"""

import re
import time
import logging
from typing import List, Optional, Tuple

from .config import TokenizerConfig
from .models import Token, TokenizerResult
from .normalizer import TextNormalizer
from .errors import InputTooLongError, EmptyInputError

logger = logging.getLogger(__name__)


class Tokenizer:
    """Tokenization engine for JARVIS.

    Usage:
        tokenizer = Tokenizer()
        result = tokenizer.tokenize("Hello, how are you?")
        print(result.tokens_text)  # ["hello", "how", "are", "you"]
    """

    # Common English stop words
    STOP_WORDS = {
        "a", "an", "the", "and", "or", "but", "in", "on", "at",
        "to", "for", "of", "with", "by", "from", "is", "are",
        "was", "were", "be", "been", "being", "have", "has",
        "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "i", "you",
        "he", "she", "it", "we", "they", "me", "him", "her",
        "us", "them", "my", "your", "his", "its", "our", "their",
        "this", "that", "these", "those", "what", "which", "who",
        "whom", "how", "when", "where", "why", "not", "no",
        "nor", "so", "if", "then", "than", "too", "very",
        "just", "about", "up", "down", "out", "off", "over",
        "under", "again", "further", "once", "here", "there",
        "all", "each", "every", "both", "few", "more", "most",
        "other", "some", "such", "only", "own", "same",
    }

    # Tokenization pattern: words, numbers, punctuation, symbols
    WORD_PATTERN = re.compile(r"([a-zA-Z0-9]+(?:[''][a-zA-Z]+)?|[^\s])")

    def __init__(self, config: Optional[TokenizerConfig] = None):
        self.config = config or TokenizerConfig()
        self.normalizer = TextNormalizer(
            enable_typo_correction=self.config.enable_typo_correction,
            enable_slang_expansion=self.config.enable_slang_expansion,
        )

    def tokenize(self, text: str) -> TokenizerResult:
        """Tokenize input text.

        Args:
            text: Raw input text.

        Returns:
            TokenizerResult with tokens, offsets, and metadata.

        Raises:
            EmptyInputError: If text is empty.
            InputTooLongError: If text exceeds max_input_length.
        """
        start = time.perf_counter()

        # Validate
        if not text or not text.strip():
            raise EmptyInputError()

        if len(text) > self.config.max_input_length:
            raise InputTooLongError(len(text), self.config.max_input_length)

        original = text

        # Normalize
        normalized, corrections = self.normalizer.normalize(text)
        has_multilingual = self.normalizer.is_multilingual(text) or \
                           self.normalizer.is_multilingual(normalized)

        # Tokenize
        tokens: List[Token] = []
        for match in self.WORD_PATTERN.finditer(normalized):
            token_text = match.group(1)
            start_char = match.start()
            end_char = match.end()

            # Determine token type
            token_type = self._classify_token(token_text)

            # Find offset in original text
            orig_start = self._find_original_offset(token_text, original)
            orig_end = orig_start + len(token_text) if orig_start >= 0 else start_char

            token = Token(
                text=token_text,
                start=orig_start if orig_start >= 0 else start_char,
                end=orig_end if orig_start >= 0 else end_char,
                type=token_type,
                is_punctuation=(token_type == "punctuation"),
                is_stopword=(token_text.lower() in self.STOP_WORDS),
                normalized=token_text,
            )
            tokens.append(token)

        # Build token text list
        if self.config.remove_punctuation:
            tokens_text = [t.text for t in tokens if not t.is_punctuation]
        else:
            tokens_text = [t.text for t in tokens]

        elapsed = (time.perf_counter() - start) * 1000

        return TokenizerResult(
            original=original,
            normalized=normalized,
            tokens=tokens,
            tokens_text=tokens_text,
            token_count=len(tokens),
            character_count=len(original),
            has_multilingual=has_multilingual,
            corrections=corrections,
            time_ms=round(elapsed, 2),
        )

    def tokenize_characters(self, text: str, max_length: int = 50) -> List[int]:
        """Convert text to character-level token IDs for neural network input.

        This produces the 128-dim character-frequency vector used by the
        TinyNeuralNetwork in the micro_brain.

        Args:
            text: Input text to convert.
            max_length: Maximum number of characters.

        Returns:
            List of character IDs (padded to max_length).
        """
        # Default character vocabulary (a-z, 0-9, common symbols)
        vocab = "abcdefghijklmnopqrstuvwxyz0123456789 .,!?-+()[]{}@#$%&*:;/\"'"
        char_to_id = {c: i + 1 for i, c in enumerate(vocab)}  # 0 = padding

        text = text.lower().strip()[:max_length]
        ids = [char_to_id.get(c, 0) for c in text]

        # Pad to max_length
        if len(ids) < max_length:
            ids.extend([0] * (max_length - len(ids)))

        return ids[:max_length]

    @staticmethod
    def _classify_token(token: str) -> str:
        """Classify a token into a type category."""
        if not token:
            return "whitespace"
        if token.isdigit():
            return "number"
        if re.match(r'^[^\w\s]+$', token):
            return "punctuation"
        if token in ("+", "-", "=", "@", "#", "$", "%", "&", "*"):
            return "symbol"
        return "word"

    @staticmethod
    def _find_original_offset(word: str, original: str) -> int:
        """Find the character offset of a word in the original text.

        Uses case-insensitive search.
        """
        lower_original = original.lower()
        lower_word = word.lower()
        idx = lower_original.find(lower_word)
        return idx
