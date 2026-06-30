"""
Input Validator.

Validates input text against length limits, blocked characters,
and dangerous patterns (SQL injection, XSS, shell injection).
"""

from __future__ import annotations

import re
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

# Dangerous patterns
SQL_INJECTION_PATTERNS = [
    re.compile(r"\bSELECT\b.*\bFROM\b", re.IGNORECASE),
    re.compile(r"\bDROP\b\s+\bTABLE\b", re.IGNORECASE),
    re.compile(r"\bDELETE\b\s+\bFROM\b", re.IGNORECASE),
    re.compile(r"\bINSERT\b\s+\bINTO\b", re.IGNORECASE),
    re.compile(r"\bUNION\b\s+\bSELECT\b", re.IGNORECASE),
    re.compile(r"\bOR\b\s+1\s*=\s*1", re.IGNORECASE),
    re.compile(r"--\s*$", re.MULTILINE),
    re.compile(r";\s*\bDROP\b", re.IGNORECASE),
]

XSS_PATTERNS = [
    re.compile(r"<script[^>]*>", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"onerror\s*=", re.IGNORECASE),
    re.compile(r"onload\s*=", re.IGNORECASE),
    re.compile(r"onclick\s*=", re.IGNORECASE),
    re.compile(r"onmouseover\s*=", re.IGNORECASE),
    re.compile(r"<iframe[^>]*>", re.IGNORECASE),
    re.compile(r"<embed[^>]*>", re.IGNORECASE),
    re.compile(r"<object[^>]*>", re.IGNORECASE),
    re.compile(r"<img[^>]*onerror", re.IGNORECASE),
    re.compile(r"alert\s*\(", re.IGNORECASE),
]

PROMPT_INJECTION_PATTERNS = [
    re.compile(r"\bignore\s+(previous|all|above)\s+(instructions|commands|directions)\b", re.IGNORECASE),
    re.compile(r"\bignore all instructions\b", re.IGNORECASE),
    re.compile(r"\byou are now\b", re.IGNORECASE),
    re.compile(r"\bpretend you are\b", re.IGNORECASE),
    re.compile(r"\bfrom now on\b.*\b(you are|you will|you must)\b", re.IGNORECASE),
    re.compile(r"\bsystem prompt\b", re.IGNORECASE),
    re.compile(r"\bforget everything\b", re.IGNORECASE),
    re.compile(r"\byour new role is\b", re.IGNORECASE),
    re.compile(r"\byour new purpose is\b", re.IGNORECASE),
    re.compile(r"\bdo not follow\b", re.IGNORECASE),
    re.compile(r"\boverride\b.*\b(instructions|commands|prompt)\b", re.IGNORECASE),
    re.compile(r"\bdisregard\b.*\b(previous|instructions)\b", re.IGNORECASE),
    re.compile(r"\bnew system message\b", re.IGNORECASE),
    re.compile(r"\bDAN\b", re.IGNORECASE),
    re.compile(r"\bjailbreak\b", re.IGNORECASE),
    re.compile(r"\byou must ignore\b", re.IGNORECASE),
    re.compile(r"\byou are free from\b", re.IGNORECASE),
    re.compile(r"\bno restrictions\b", re.IGNORECASE),
    re.compile(r"\bremove all restrictions\b", re.IGNORECASE),
    re.compile(r"\bunfiltered\b", re.IGNORECASE),
]

SHELL_INJECTION_PATTERNS = [
    re.compile(r"[;|&`$]", re.IGNORECASE),
    re.compile(r"\brm\s+-rf\b", re.IGNORECASE),
    re.compile(r"\bwget\b", re.IGNORECASE),
    re.compile(r"\bcurl\b\s+-[oO]", re.IGNORECASE),
    re.compile(r">\s*/dev/", re.IGNORECASE),
    re.compile(r"\|\s*bash\b", re.IGNORECASE),
    re.compile(r"\|\s*sh\b", re.IGNORECASE),
]


class ValidationResult:
    """Result of input validation."""

    def __init__(self, is_valid=True, errors=None, sanitized_input="",
                 risk_score=0.0, blocked_chars_found=None, warnings=None,
                 prompt_injection_detected=False, prompt_injection_patterns=None):
        self.is_valid = is_valid
        self.errors = errors or []
        self.sanitized_input = sanitized_input
        self.risk_score = risk_score
        self.blocked_chars_found = blocked_chars_found or []
        self.warnings = warnings or []
        self.prompt_injection_detected = prompt_injection_detected
        self.prompt_injection_patterns = prompt_injection_patterns or []


class InputValidator:
    """Validates input text for security threats.

    Usage:
        validator = InputValidator(max_length=4096)
        result = validator.validate("some user input")
        if result.is_valid:
            print("Input is safe")
    """

    def __init__(self, max_length: int = 4096, blocked_chars: Optional[List[str]] = None):
        self.max_input_length = max_length
        self.blocked_chars = blocked_chars or ["<", ">", "&", "'", '"', ";", "|", "`", "$", "(", ")", "{", "}", "\\", "\x00"]

    def validate(self, input_text: str) -> ValidationResult:
        """Validate input text against security rules.

        Args:
            input_text: The text to validate.

        Returns:
            ValidationResult with validation details.
        """
        errors: List[str] = []
        warnings: List[str] = []
        blocked_chars_found: List[str] = []
        risk_score = 0.0

        # Check length
        if len(input_text) > self.max_input_length:
            errors.append(f"Input exceeds max length of {self.max_input_length}")
            risk_score = 1.0
            return ValidationResult(
                is_valid=False,
                errors=errors,
                sanitized_input=input_text[: self.max_input_length],
                risk_score=risk_score,
                blocked_chars_found=blocked_chars_found,
                warnings=warnings,
            )

        # Check blocked characters
        for char in self.blocked_chars:
            if char in input_text:
                blocked_chars_found.append(char)
                risk_score = min(1.0, risk_score + 0.15)

        # Check SQL injection patterns
        for pattern in SQL_INJECTION_PATTERNS:
            if pattern.search(input_text):
                warnings.append(f"Potential SQL injection pattern detected: {pattern.pattern}")
                risk_score = min(1.0, risk_score + 0.3)

        # Check XSS patterns
        for pattern in XSS_PATTERNS:
            if pattern.search(input_text):
                warnings.append(f"Potential XSS pattern detected: {pattern.pattern}")
                risk_score = min(1.0, risk_score + 0.3)

        # Check shell injection patterns
        for pattern in SHELL_INJECTION_PATTERNS:
            if pattern.search(input_text):
                warnings.append(f"Potential shell injection pattern detected: {pattern.pattern}")
                risk_score = min(1.0, risk_score + 0.3)

        # Check prompt injection patterns
        prompt_injection_detected, prompt_injection_patterns = self._check_prompt_injection(input_text)
        if prompt_injection_detected:
            for pat in prompt_injection_patterns:
                warnings.append(f"Potential prompt injection pattern detected: {pat}")
            risk_score = min(1.0, risk_score + 0.4)

        is_valid = risk_score < 0.7

        if risk_score > 0 and not is_valid:
            errors.append("Input risk score exceeds threshold")

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            sanitized_input=input_text,
            risk_score=round(risk_score, 2),
            blocked_chars_found=blocked_chars_found,
            warnings=warnings,
            prompt_injection_detected=prompt_injection_detected,
            prompt_injection_patterns=prompt_injection_patterns,
        )

    def _check_prompt_injection(self, input_text: str):
        """Check input for prompt injection patterns."""
        detected = False
        patterns_found = []
        for pat in PROMPT_INJECTION_PATTERNS:
            if pat.search(input_text):
                patterns_found.append(pat.pattern)
                detected = True
        return detected, patterns_found
