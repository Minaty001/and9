"""
Phase 31 — Secret Manager.

Stores/retrieves secrets (API keys, passwords, tokens) with
in-memory encryption using EncryptionManager.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from .encryption import EncryptionManager

logger = logging.getLogger(__name__)


class SecretEntry:
    """An in-memory secret entry with encrypted value."""

    def __init__(
        self,
        name: str,
        encrypted_value: str,
        iv: str,
        scope: str = "global",
        created_at: Optional[datetime] = None,
    ):
        self.name = name
        self.encrypted_value = encrypted_value
        self.iv = iv
        self.scope = scope
        self.created_at = created_at or datetime.now(timezone.utc)
        self.revoked = False

    def __repr__(self) -> str:
        return f"SecretEntry(name={self.name}, scope={self.scope}, revoked={self.revoked})"


class SecretManager:
    """Manages secrets with in-memory encryption at rest.

    Secrets are encrypted via EncryptionManager before being stored
    in memory, and decrypted on retrieval.

    Usage:
        mgr = SecretManager(encryption_manager)
        mgr.store_secret("api_key", "sk-1234", scope="production")
        value = mgr.get_secret("api_key")  # "sk-1234"
        mgr.revoke_secret("api_key")
    """

    def __init__(self, encryption_manager: EncryptionManager):
        """Initialize the secret manager.

        Args:
            encryption_manager: An EncryptionManager instance for encrypting secrets.
        """
        self._encryption = encryption_manager
        self._secrets: Dict[str, SecretEntry] = {}

    def store_secret(self, name: str, value: str, scope: str = "global") -> bool:
        """Store a secret with encryption.

        Args:
            name: The secret name/key.
            value: The plaintext secret value.
            scope: The scope (e.g., "global", "production", "development").

        Returns:
            True if stored successfully.
        """
        encrypted_value, iv = self._encryption.encrypt(value)
        self._secrets[name] = SecretEntry(
            name=name,
            encrypted_value=encrypted_value,
            iv=iv,
            scope=scope,
        )
        logger.debug("Stored secret '%s' (scope=%s)", name, scope)
        return True

    def get_secret(self, name: str) -> Optional[str]:
        """Retrieve a decrypted secret value.

        Args:
            name: The secret name.

        Returns:
            Decrypted plaintext value, or None if not found or revoked.
        """
        entry = self._secrets.get(name)
        if not entry or entry.revoked:
            return None
        try:
            return self._encryption.decrypt(entry.encrypted_value, entry.iv)
        except Exception as e:
            logger.error("Failed to decrypt secret '%s': %s", name, e)
            return None

    def list_secrets(self) -> List[dict]:
        """List all stored secrets (metadata only, no plaintext values).

        Returns:
            List of dicts with name, scope, created_at, revoked.
        """
        return [
            {
                "name": entry.name,
                "scope": entry.scope,
                "created_at": entry.created_at.isoformat(),
                "revoked": entry.revoked,
            }
            for entry in self._secrets.values()
        ]

    def revoke_secret(self, name: str) -> bool:
        """Revoke a secret, making it unretrievable.

        Args:
            name: The secret name.

        Returns:
            True if the secret was found and revoked.
        """
        entry = self._secrets.get(name)
        if not entry:
            return False
        entry.revoked = True
        logger.debug("Revoked secret '%s'", name)
        return True

    def rotate_secret(self, name: str, new_value: str) -> bool:
        """Rotate a secret by replacing its value.

        Args:
            name: The secret name.
            new_value: The new plaintext value.

        Returns:
            True if the secret was rotated.
        """
        if name not in self._secrets:
            return False
        # Re-encrypt with new value (same scope preserved)
        encrypted_value, iv = self._encryption.encrypt(new_value)
        entry = self._secrets[name]
        entry.encrypted_value = encrypted_value
        entry.iv = iv
        entry.revoked = False
        logger.debug("Rotated secret '%s'", name)
        return True

    def clear(self) -> None:
        """Clear all secrets (for testing/reset)."""
        self._secrets.clear()
