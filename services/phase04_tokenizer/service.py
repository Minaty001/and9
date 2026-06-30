"""
Phase 4 — Tokenizer Service.

Wraps the Tokenizer in a ServiceBase with lifecycle management.
"""

import time
import logging
from typing import Any, Dict, Optional

from services.base.service_base import ServiceBase
from .config import TokenizerConfig
from .tokenizer import Tokenizer
from .models import TokenizerResult
from .errors import TokenizerError

logger = logging.getLogger(__name__)


class TokenizerService(ServiceBase):
    """Tokenizer service wrapping the Tokenization Engine.

    Provides text normalization, tokenization, and character-level
    encoding for downstream neural network processing.
    """

    def __init__(self, config: Optional[TokenizerConfig] = None):
        super().__init__(name="jarvis_tokenizer", version="1.0.0")
        self.config = config or TokenizerConfig()
        self.tokenizer = Tokenizer(config=self.config)
        self._start_time = 0.0

    async def initialize(self) -> bool:
        """Initialize the tokenizer service."""
        self._start_time = time.time()
        try:
            self._metrics.reset()
            self._initialized = True
            elapsed = (time.time() - self._start_time) * 1000
            logger.info("TokenizerService initialized in %.0fms", elapsed)
            return True
        except Exception as e:
            logger.error("TokenizerService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        """Shut down the service."""
        logger.info("TokenizerService shutting down...")
        self._initialized = False

    async def tokenize(self, text: str) -> TokenizerResult:
        """Tokenize input text.

        Args:
            text: Raw input text.

        Returns:
            TokenizerResult with tokens and metadata.
        """
        try:
            result = self.tokenizer.tokenize(text)
            self._metrics.counter("texts_tokenized")
            self._metrics.histogram("token_count", result.token_count)
            self._metrics.histogram("tokenize_time_ms", result.time_ms)
            return result
        except TokenizerError:
            raise
        except Exception as e:
            logger.error("Tokenization failed: %s", e)
            raise TokenizerError(f"Tokenization failed: {e}")

    async def tokenize_characters(self, text: str, max_length: int = 50) -> list:
        """Convert text to character-level token IDs.

        Args:
            text: Input text.
            max_length: Maximum character length.

        Returns:
            List of character IDs.
        """
        return self.tokenizer.tokenize_characters(text, max_length)

    async def health(self) -> Dict[str, Any]:
        """Return service health."""
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service_name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
        }

    async def stats(self) -> Dict[str, Any]:
        """Return service statistics."""
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            "metrics": self._metrics.snapshot(),
        }
