"""
Phase 4 — Tokenizer Models.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class Token(BaseModel):
    """A single token from the tokenization process."""

    text: str = Field(..., description="Token text")
    start: int = Field(..., description="Start character offset in original query")
    end: int = Field(..., description="End character offset in original query")
    type: str = Field(default="word", description="Token type: word, number, symbol, whitespace, punctuation")
    is_punctuation: bool = Field(default=False, description="Whether this is a punctuation token")
    is_stopword: bool = Field(default=False, description="Whether this is a stop word")
    normalized: Optional[str] = Field(default=None, description="Normalized form of the token")


class TokenizerResult(BaseModel):
    """Output from the tokenization engine."""

    original: str = Field(..., description="Original input text")
    normalized: str = Field(..., description="Normalized text after cleaning")
    tokens: List[Token] = Field(..., description="List of tokens")
    tokens_text: List[str] = Field(..., description="List of token strings only")
    token_count: int = Field(..., description="Number of tokens")
    character_count: int = Field(..., description="Number of characters in original")
    has_multilingual: bool = Field(default=False, description="Whether input contained non-English text")
    corrections: List[dict] = Field(default_factory=list, description="Applied corrections")
    time_ms: float = Field(default=0.0, description="Processing time in milliseconds")
