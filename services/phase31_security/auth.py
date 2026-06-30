"""
Phase 31 — Auth Manager.

Token-based authentication and authorization with a mock token store.
Supports token generation, validation, scope checking, and revocation.
"""

from __future__ import annotations

import uuid
import time
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List

from .config import SecurityConfig

logger = logging.getLogger(__name__)


class AuthManager:
    """Manages authentication tokens and scope-based authorization.

    Uses a mock in-memory token store for development.

    Usage:
        auth = AuthManager(config)
        token = auth.generate_token("user123", scope=["read", "write"])
        ok = auth.authenticate(token)
        user = auth.get_user_id(token)
    """

    def __init__(self, config: Optional[SecurityConfig] = None):
        self.config = config or SecurityConfig()
        self._tokens: Dict[str, dict] = {}  # token -> {user_id, scope, created_at, revoked}

    def authenticate(self, token: str) -> bool:
        """Validate a token.

        Args:
            token: The token string to validate.

        Returns:
            True if the token is valid and not revoked.
        """
        if not token or token not in self._tokens:
            return False
        info = self._tokens[token]
        if info.get("revoked", False):
            return False
        return True

    def generate_token(self, user_id: str, scope: Optional[List[str]] = None) -> str:
        """Generate a new authentication token for a user.

        Args:
            user_id: The user identifier.
            scope: List of permission scopes.

        Returns:
            A token string.
        """
        token = hashlib.sha256(f"{user_id}:{uuid.uuid4().hex}:{time.time()}".encode()).hexdigest()
        self._tokens[token] = {
            "user_id": user_id,
            "scope": scope or ["read"],
            "created_at": datetime.now(timezone.utc),
            "revoked": False,
        }
        logger.debug("Generated token for user %s", user_id)
        return token

    def validate_scope(self, token: str, required_scope: str) -> bool:
        """Check if a token has the required scope.

        Args:
            token: The token to check.
            required_scope: The scope required.

        Returns:
            True if the token has the required scope.
        """
        if not self.authenticate(token):
            return False
        info = self._tokens[token]
        return required_scope in info.get("scope", [])

    def revoke_token(self, token: str) -> bool:
        """Revoke a token, making it invalid.

        Args:
            token: The token to revoke.

        Returns:
            True if the token was found and revoked.
        """
        if token not in self._tokens:
            return False
        self._tokens[token]["revoked"] = True
        logger.debug("Revoked token %s...", token[:8])
        return True

    def get_user_id(self, token: str) -> str:
        """Get the user ID associated with a token.

        Args:
            token: The token.

        Returns:
            User ID string, or empty string if token is invalid.
        """
        if not self.authenticate(token):
            return ""
        return self._tokens[token].get("user_id", "")

    def clear_tokens(self) -> None:
        """Clear all tokens (for testing/reset)."""
        self._tokens.clear()
