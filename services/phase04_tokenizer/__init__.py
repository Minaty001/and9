"""
Phase 4 — Tokenization Engine
===============================

Normalize text, lowercase, remove noise, preserve important symbols.
Support multilingual input, typo correction, slang expansion.
Produce tokens, offsets, normalized query and metadata.
Prepare text for intent detection and embeddings.
"""

from .tokenizer import Tokenizer
from .normalizer import TextNormalizer
from .service import TokenizerService
from .config import TokenizerConfig
from .models import TokenizerResult, Token

__all__ = [
    "Tokenizer",
    "TextNormalizer",
    "TokenizerService",
    "TokenizerConfig",
    "TokenizerResult",
    "Token",
]
