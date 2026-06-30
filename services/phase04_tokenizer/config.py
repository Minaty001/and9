"""
Phase 4 — Tokenizer Configuration.
"""

from pydantic import Field
from services.base.config_base import BaseConfig


class TokenizerConfig(BaseConfig):
    """Configuration for the tokenization engine."""

    service_name: str = Field(default="jarvis_tokenizer", description="Tokenizer service name")
    lowercase: bool = Field(default=True, description="Convert text to lowercase")
    remove_punctuation: bool = Field(default=False, description="Remove punctuation tokens")
    preserve_symbols: str = Field(
        default="+-=@#$%&*",
        description="Symbols to preserve during cleaning",
    )
    max_token_length: int = Field(default=100, description="Maximum characters per token")
    max_input_length: int = Field(default=1000, description="Maximum input characters")
    enable_typo_correction: bool = Field(default=True, description="Enable typo correction")
    enable_slang_expansion: bool = Field(default=True, description="Enable slang expansion")
    language_support: list = Field(
        default=["en", "hi"],
        description="Supported languages",
    )

    class Config:
        env_prefix = "JARVIS_TOKEN_"
