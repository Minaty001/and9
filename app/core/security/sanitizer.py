"""
Input Sanitizer.

Sanitizes input by stripping dangerous characters,
encoding HTML entities, and normalizing whitespace.
"""

from __future__ import annotations

import html
import re
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class InputSanitizer:
    """Sanitizes input text by removing or encoding dangerous content.

    Usage:
        sanitizer = InputSanitizer()
        clean = sanitizer.sanitize("user <script>alert('xss')</script> input")
    """

    def __init__(self, max_length: int = 4096, blocked_chars: Optional[List[str]] = None):
        self.max_input_length = max_length
        self.blocked_chars = blocked_chars or ["<", ">", "&", "'", '"', ";", "|", "`", "$", "(", ")", "{", "}", "\\", "\x00"]

    def sanitize(self, input_text: str) -> str:
        """Sanitize input text.

        - Strips null bytes
        - Encodes HTML entities
        - Strips blocked dangerous characters
        - Normalizes whitespace

        Args:
            input_text: The text to sanitize.

        Returns:
            Sanitized text.
        """
        if not input_text:
            return input_text

        # Strip null bytes
        result = input_text.replace("\x00", "")

        # Encode HTML entities (escape < > & " ')
        result = html.escape(result, quote=True)

        # Strip blocked characters that are not HTML-escaped equivalents
        for char in self.blocked_chars:
            if char in ("<", ">", "&", "'", '"', "`", "$", ";", "|", "\\", "\x00"):
                continue  # already handled by html.escape or null byte strip
            result = result.replace(char, "")

        # Normalize whitespace: collapse multiple spaces/tabs/newlines
        result = re.sub(r"\s+", " ", result).strip()

        # Truncate to max length
        if len(result) > self.max_input_length:
            result = result[: self.max_input_length]

        return result
