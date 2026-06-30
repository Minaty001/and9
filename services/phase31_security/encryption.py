"""
Phase 31 — Encryption Manager.

Mock AES-256-GCM symmetric encryption for development and testing.
Uses hashlib + base64 instead of PyCryptodome.
"""

from __future__ import annotations

import os
import base64
import hashlib
import logging
from typing import Tuple, Optional

from .config import SecurityConfig

logger = logging.getLogger(__name__)


class EncryptionManager:
    """Mock AES-256-GCM symmetric encryption.

    Uses a simple XOR + SHA-256 based approach for development.
    In production, this would use a proper key management system.

    Usage:
        mgr = EncryptionManager()
        ciphertext, iv = mgr.encrypt("sensitive data")
        plaintext = mgr.decrypt(ciphertext, iv)
    """

    def __init__(self, key_or_config=None):
        """Initialize with an optional key or SecurityConfig.

        Args:
            key_or_config: A bytes key, a SecurityConfig (ignored), or None.
        """
        if isinstance(key_or_config, bytes):
            self._key = key_or_config
        else:
            # Accept SecurityConfig for backward compatibility but ignore it
            self._key = hashlib.sha256(b"jarvis_default_key").digest()

    def encrypt(self, data: str) -> Tuple[str, str]:
        """Encrypt a string using mock encryption.

        Args:
            data: Plaintext string to encrypt.

        Returns:
            Tuple of (ciphertext_base64, iv_base64).
        """
        iv = os.urandom(12)
        # Embed a hash of the plaintext for integrity verification
        plain_bytes = data.encode("utf-8")
        plain_hash = hashlib.sha256(plain_bytes).digest()[:4]
        # Simple XOR for mock encryption
        combined = plain_hash + plain_bytes
        cipher = bytes([b ^ self._key[i % len(self._key)] for i, b in enumerate(combined)])
        return base64.b64encode(cipher).decode(), base64.b64encode(iv).decode()

    def decrypt(self, ciphertext: str, iv: str) -> str:
        """Decrypt a string using mock decryption.

        Args:
            ciphertext_b64: Base64-encoded ciphertext.
            iv_b64: Base64-encoded initialization vector.

        Returns:
            Decrypted plaintext string.

        Raises:
            ValueError: If decryption fails (wrong key or tampered data).
        """
        try:
            cipher = base64.b64decode(ciphertext)
            # XOR decrypt
            plain = bytes([b ^ self._key[i % len(self._key)] for i, b in enumerate(cipher)])
            stored_hash = plain[:4]
            plain_bytes = plain[4:]
            # Verify integrity
            expected_hash = hashlib.sha256(plain_bytes).digest()[:4]
            if stored_hash != expected_hash:
                raise ValueError("Decryption failed: integrity check failed (wrong key or tampered data)")
            return plain_bytes.decode("utf-8")
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")

    def generate_key(self) -> str:
        """Generate a new random 256-bit key and return as base64.

        Returns:
            Base64-encoded key string.
        """
        new_key = os.urandom(32)
        self._key = new_key
        return base64.b64encode(new_key).decode("utf-8")
