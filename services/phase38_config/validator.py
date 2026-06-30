"""
Phase 38 — Config Validator.

Type checking, range, regex, allowed values validation.
"""

from __future__ import annotations

import re
import logging
from typing import Any, Dict, List, Optional, Union

from .models import ValidationError

logger = logging.getLogger(__name__)


class ConfigValidator:
    """Validate configuration values against rules.

    Usage:
        validator = ConfigValidator()
        errors = validator.validate("port", 8080, {"type": "int", "min": 1024, "max": 65535})
    """

    def __init__(self):
        self._validators = {
            "type": self._validate_type,
            "allowed": self._validate_allowed,
            "min": self._validate_min,
            "max": self._validate_max,
            "min_length": self._validate_min_length,
            "max_length": self._validate_max_length,
            "pattern": self._validate_pattern,
            "range": self._validate_range,
        }

    def validate(self, key: str, value: Any, rules: Union[str, Dict[str, Any]]) -> List[ValidationError]:
        """Validate a value against rules.

        Args:
            key: Config key name.
            value: Value to validate.
            rules: Validation rules dict or JSON string.

        Returns:
            List of ValidationError (empty if valid).
        """
        if isinstance(rules, str):
            try:
                rules = json.loads(rules)
            except (json.JSONDecodeError, TypeError):
                import json
                return []

        if not isinstance(rules, dict):
            return []

        errors = []
        for rule_name, rule_value in rules.items():
            validator = self._validators.get(rule_name)
            if validator:
                error = validator(key, value, rule_value)
                if error:
                    errors.append(error)

        return errors

    def _validate_type(self, key: str, value: Any, expected_type: str) -> Optional[ValidationError]:
        """Validate the type of a value."""
        type_map = {
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "number": (int, float),
        }
        py_type = type_map.get(expected_type)
        if py_type is None:
            return None
        if not isinstance(value, py_type):
            return ValidationError(
                key=key,
                value=value,
                expected_type=expected_type,
                rule=f"type:{expected_type}",
                message=f"Expected type '{expected_type}', got '{type(value).__name__}'",
            )
        return None

    def _validate_allowed(self, key: str, value: Any, allowed: List[Any]) -> Optional[ValidationError]:
        """Validate that value is in a list of allowed values."""
        if value not in allowed:
            return ValidationError(
                key=key,
                value=value,
                rule=f"allowed:{allowed}",
                message=f"Value '{value}' not in allowed list: {allowed}",
            )
        return None

    def _validate_min(self, key: str, value: Any, min_val: Union[int, float]) -> Optional[ValidationError]:
        """Validate minimum value (for numbers)."""
        if isinstance(value, (int, float)) and value < min_val:
            return ValidationError(
                key=key,
                value=value,
                rule=f"min:{min_val}",
                message=f"Value {value} is less than minimum {min_val}",
            )
        return None

    def _validate_max(self, key: str, value: Any, max_val: Union[int, float]) -> Optional[ValidationError]:
        """Validate maximum value (for numbers)."""
        if isinstance(value, (int, float)) and value > max_val:
            return ValidationError(
                key=key,
                value=value,
                rule=f"max:{max_val}",
                message=f"Value {value} is greater than maximum {max_val}",
            )
        return None

    def _validate_min_length(self, key: str, value: Any, min_len: int) -> Optional[ValidationError]:
        """Validate minimum length (for strings/lists)."""
        if isinstance(value, (str, list)) and len(value) < min_len:
            return ValidationError(
                key=key,
                value=value,
                rule=f"min_length:{min_len}",
                message=f"Length {len(value)} is less than minimum {min_len}",
            )
        return None

    def _validate_max_length(self, key: str, value: Any, max_len: int) -> Optional[ValidationError]:
        """Validate maximum length (for strings/lists)."""
        if isinstance(value, (str, list)) and len(value) > max_len:
            return ValidationError(
                key=key,
                value=value,
                rule=f"max_length:{max_len}",
                message=f"Length {len(value)} exceeds maximum {max_len}",
            )
        return None

    def _validate_pattern(self, key: str, value: Any, pattern: str) -> Optional[ValidationError]:
        """Validate string against a regex pattern."""
        if isinstance(value, str):
            try:
                if not re.match(pattern, value):
                    return ValidationError(
                        key=key,
                        value=value,
                        rule=f"pattern:{pattern}",
                        message=f"Value '{value}' does not match pattern '{pattern}'",
                    )
            except re.error:
                pass
        return None

    def _validate_range(self, key: str, value: Any, rng: List[Union[int, float]]) -> Optional[ValidationError]:
        """Validate that a number is within a range [min, max]."""
        if isinstance(value, (int, float)) and len(rng) == 2:
            if value < rng[0] or value > rng[1]:
                return ValidationError(
                    key=key,
                    value=value,
                    rule=f"range:[{rng[0]}, {rng[1]}]",
                    message=f"Value {value} is outside range [{rng[0]}, {rng[1]}]",
                )
        return None


import json  # needed for json.loads in validate()
