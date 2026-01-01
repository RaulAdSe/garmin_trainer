#!/usr/bin/env python3
"""
Generate Security Keys for Training Analyzer

This script generates cryptographically secure keys required for the
Training Analyzer application:

1. JWT_SECRET_KEY: Used for signing and verifying JSON Web Tokens (JWT)
   for user authentication sessions.

2. CREDENTIAL_ENCRYPTION_KEY: Used for encrypting sensitive credentials
   (like Garmin passwords) stored in the database using Fernet symmetric
   encryption.

Usage:
    python generate_security_keys.py

    Or make executable and run directly:
    chmod +x generate_security_keys.py
    ./generate_security_keys.py

Security Notes:
    - Never commit these keys to version control
    - Store them securely in environment variables or a secrets manager
    - Rotate keys periodically according to your security policy
    - Keep backups of CREDENTIAL_ENCRYPTION_KEY - losing it means losing
      access to encrypted credentials
"""

import secrets
import sys
from datetime import datetime


def generate_jwt_secret() -> str:
    """
    Generate a secure JWT secret key.

    Uses secrets.token_urlsafe(32) which generates a 32-byte (256-bit)
    random string encoded in URL-safe base64. This provides sufficient
    entropy for HMAC-SHA256 signing.

    Returns:
        A URL-safe base64-encoded random string.
    """
    return secrets.token_urlsafe(32)


def generate_fernet_key() -> str:
    """
    Generate a Fernet encryption key.

    Fernet is a symmetric encryption method that uses AES-128-CBC
    with HMAC-SHA256 for authentication. The key is 32 bytes
    encoded in URL-safe base64.

    Returns:
        A Fernet-compatible encryption key as a string.

    Raises:
        ImportError: If cryptography package is not installed.
    """
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        print("Error: cryptography package is required.")
        print("Install it with: pip install cryptography")
        sys.exit(1)

    return Fernet.generate_key().decode('utf-8')


def main() -> None:
    """Generate and display security keys with usage instructions."""
    print("=" * 60)
    print("Training Analyzer Security Key Generator")
    print("=" * 60)
    print(f"\nGenerated at: {datetime.now().isoformat()}")
    print("\n" + "-" * 60)

    # Generate keys
    jwt_secret = generate_jwt_secret()
    encryption_key = generate_fernet_key()

    # Output in .env format
    print("\nAdd the following to your .env file:")
    print("-" * 60)
    print(f"\n# JWT Authentication Secret (generated {datetime.now().strftime('%Y-%m-%d')})")
    print(f"JWT_SECRET_KEY={jwt_secret}")
    print(f"\n# Credential Encryption Key (generated {datetime.now().strftime('%Y-%m-%d')})")
    print(f"CREDENTIAL_ENCRYPTION_KEY={encryption_key}")
    print("\n" + "-" * 60)

    # Security instructions
    print("\nSECURITY INSTRUCTIONS:")
    print("-" * 60)
    print("""
1. NEVER commit these keys to version control
   - Add .env to your .gitignore file
   - Use .env.example with placeholder values for documentation

2. SECURE STORAGE OPTIONS:
   - Development: Store in local .env file (not committed)
   - Production: Use a secrets manager such as:
     * AWS Secrets Manager
     * Google Cloud Secret Manager
     * HashiCorp Vault
     * Azure Key Vault
   - CI/CD: Use encrypted environment variables

3. KEY ROTATION:
   - Rotate JWT_SECRET_KEY periodically (e.g., every 90 days)
   - When rotating JWT key, existing sessions will be invalidated
   - CREDENTIAL_ENCRYPTION_KEY rotation requires re-encrypting
     all stored credentials

4. BACKUP CONSIDERATIONS:
   - CRITICAL: Back up CREDENTIAL_ENCRYPTION_KEY securely
   - Losing this key means losing access to all encrypted
     credentials in the database
   - Store backups in a separate secure location

5. ACCESS CONTROL:
   - Limit access to these keys to essential personnel only
   - Audit access to secrets regularly
   - Use principle of least privilege
""")

    print("=" * 60)
    print("Key generation complete. Store these keys securely!")
    print("=" * 60)


if __name__ == "__main__":
    main()
