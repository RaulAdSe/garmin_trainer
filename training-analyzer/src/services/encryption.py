"""Credential encryption service using Fernet symmetric encryption.

Provides secure storage for sensitive credentials like Garmin Connect
email/password using industry-standard encryption (AES-128-CBC via Fernet).
"""

import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken


class CredentialEncryptionError(Exception):
    """Raised when encryption/decryption operations fail."""
    pass


class CredentialEncryption:
    """Secure credential encryption using Fernet (AES-128-CBC).

    Uses a symmetric encryption key stored in environment variables.
    The key must be a valid Fernet key (32 bytes, URL-safe base64 encoded).

    Usage:
        encryption = CredentialEncryption()
        encrypted = encryption.encrypt("my_secret")
        decrypted = encryption.decrypt(encrypted)
    """

    def __init__(self, key: Optional[str] = None):
        """Initialize the encryption service.

        Args:
            key: Optional encryption key. If not provided, reads from
                 CREDENTIAL_ENCRYPTION_KEY environment variable.

        Raises:
            CredentialEncryptionError: If no key is provided or found.
        """
        self._key = key or os.getenv("CREDENTIAL_ENCRYPTION_KEY")
        if not self._key:
            raise CredentialEncryptionError(
                "CREDENTIAL_ENCRYPTION_KEY not set. "
                "Generate one with: CredentialEncryption.generate_key()"
            )

        try:
            self._fernet = Fernet(self._key.encode())
        except Exception as e:
            raise CredentialEncryptionError(
                f"Invalid encryption key format: {e}. "
                "Key must be a valid Fernet key (32 bytes, URL-safe base64 encoded)."
            )

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string value.

        Args:
            plaintext: The string to encrypt.

        Returns:
            The encrypted value as a base64-encoded string.

        Raises:
            CredentialEncryptionError: If encryption fails.
        """
        if not plaintext:
            raise CredentialEncryptionError("Cannot encrypt empty string")

        try:
            encrypted_bytes = self._fernet.encrypt(plaintext.encode('utf-8'))
            return encrypted_bytes.decode('utf-8')
        except Exception as e:
            raise CredentialEncryptionError(f"Encryption failed: {e}")

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt an encrypted value.

        Args:
            ciphertext: The encrypted string to decrypt.

        Returns:
            The decrypted plaintext string.

        Raises:
            CredentialEncryptionError: If decryption fails (e.g., wrong key,
                                       corrupted data, or tampered ciphertext).
        """
        if not ciphertext:
            raise CredentialEncryptionError("Cannot decrypt empty string")

        try:
            decrypted_bytes = self._fernet.decrypt(ciphertext.encode('utf-8'))
            return decrypted_bytes.decode('utf-8')
        except InvalidToken:
            raise CredentialEncryptionError(
                "Decryption failed: invalid token. "
                "The data may be corrupted, tampered with, or encrypted with a different key."
            )
        except Exception as e:
            raise CredentialEncryptionError(f"Decryption failed: {e}")

    @staticmethod
    def generate_key() -> str:
        """Generate a new Fernet encryption key.

        This generates a cryptographically secure random key suitable
        for use with Fernet encryption.

        Returns:
            A new Fernet key as a URL-safe base64-encoded string.

        Example:
            key = CredentialEncryption.generate_key()
            # Store securely in .env file as CREDENTIAL_ENCRYPTION_KEY
        """
        return Fernet.generate_key().decode('utf-8')

    def is_valid_key(self) -> bool:
        """Check if the current encryption key is valid.

        Performs a round-trip encryption/decryption test.

        Returns:
            True if the key can encrypt and decrypt successfully.
        """
        try:
            test_value = "test_encryption_validation"
            encrypted = self.encrypt(test_value)
            decrypted = self.decrypt(encrypted)
            return decrypted == test_value
        except CredentialEncryptionError:
            return False
