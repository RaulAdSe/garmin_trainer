"""
Migration 005: Encrypt Strava OAuth tokens

This migration adds encryption support for Strava OAuth tokens:
- Adds encrypted_access_token, encrypted_refresh_token, encryption_key_id columns
- Migrates existing plaintext tokens to encrypted format
- Preserves plaintext columns during migration for rollback support

This migration is idempotent and safe to run multiple times.

Usage:
    python -m src.db.migrations.migration_005_encrypt_strava_tokens data/training.db
"""

import sqlite3
import sys
import os
from typing import Optional

MIGRATION_VERSION = "005"
MIGRATION_NAME = "encrypt_strava_tokens"


def column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    """Check if a column exists in a table."""
    cursor = conn.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    """Check if a table exists."""
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,)
    )
    return cursor.fetchone() is not None


def add_column_if_not_exists(
    conn: sqlite3.Connection,
    table: str,
    column: str,
    column_type: str,
    default: Optional[str] = None
) -> bool:
    """Add a column to a table if it doesn't exist."""
    if not table_exists(conn, table):
        return False
    if column_exists(conn, table, column):
        return False

    default_clause = f" DEFAULT {default}" if default else ""
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}{default_clause}")
    return True


def get_credential_encryption():
    """
    Get CredentialEncryption instance if available.

    Returns:
        CredentialEncryption instance or None if not configured
    """
    try:
        # Add parent path to import encryption module
        import sys
        from pathlib import Path

        # Navigate to src directory
        migration_dir = Path(__file__).parent
        src_dir = migration_dir.parent.parent
        if str(src_dir) not in sys.path:
            sys.path.insert(0, str(src_dir))

        from services.encryption import CredentialEncryption, CredentialEncryptionError

        try:
            return CredentialEncryption()
        except CredentialEncryptionError:
            return None
    except ImportError:
        return None


def migrate(db_path: str) -> dict:
    """
    Run the Strava token encryption migration on the specified database.

    Adds encrypted columns and migrates existing plaintext tokens.

    Args:
        db_path: Path to the SQLite database file

    Returns:
        dict with migration results including:
        - success: bool
        - columns_added: list of columns added
        - tokens_encrypted: number of tokens encrypted
        - errors: list of any errors encountered
    """
    results = {
        "success": True,
        "migration": f"{MIGRATION_VERSION}_{MIGRATION_NAME}",
        "columns_added": [],
        "tokens_encrypted": 0,
        "tokens_skipped": 0,
        "errors": []
    }

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        # =================================================================
        # Step 1: Add encrypted columns to strava_credentials table
        # =================================================================
        if not table_exists(conn, "strava_credentials"):
            results["errors"].append("Table strava_credentials does not exist")
            results["success"] = False
            return results

        # Add encrypted_access_token column
        if add_column_if_not_exists(
            conn, "strava_credentials", "encrypted_access_token", "TEXT"
        ):
            results["columns_added"].append("strava_credentials.encrypted_access_token")

        # Add encrypted_refresh_token column
        if add_column_if_not_exists(
            conn, "strava_credentials", "encrypted_refresh_token", "TEXT"
        ):
            results["columns_added"].append("strava_credentials.encrypted_refresh_token")

        # Add encryption_key_id column (for key rotation support)
        if add_column_if_not_exists(
            conn, "strava_credentials", "encryption_key_id", "TEXT"
        ):
            results["columns_added"].append("strava_credentials.encryption_key_id")

        conn.commit()

        # =================================================================
        # Step 2: Migrate existing plaintext tokens to encrypted format
        # =================================================================
        encryption = get_credential_encryption()

        if encryption is None:
            # Encryption not configured - columns added but no data migration
            results["errors"].append(
                "CREDENTIAL_ENCRYPTION_KEY not set. Schema updated but tokens not encrypted. "
                "Set the environment variable and re-run migration to encrypt existing tokens."
            )
            print("  Warning: Encryption key not configured, skipping token encryption")
        else:
            # Get all credentials that have plaintext tokens but no encrypted versions
            cursor = conn.execute("""
                SELECT user_id, access_token, refresh_token
                FROM strava_credentials
                WHERE access_token IS NOT NULL
                  AND (encrypted_access_token IS NULL OR encrypted_access_token = '')
            """)
            rows = cursor.fetchall()

            # Get current key identifier for key rotation tracking
            key_id = os.getenv("CREDENTIAL_ENCRYPTION_KEY_ID", "default")

            for row in rows:
                try:
                    user_id = row["user_id"]
                    access_token = row["access_token"]
                    refresh_token = row["refresh_token"]

                    # Encrypt tokens
                    encrypted_access = encryption.encrypt(access_token) if access_token else None
                    encrypted_refresh = encryption.encrypt(refresh_token) if refresh_token else None

                    # Update the record with encrypted values
                    conn.execute("""
                        UPDATE strava_credentials
                        SET encrypted_access_token = ?,
                            encrypted_refresh_token = ?,
                            encryption_key_id = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = ?
                    """, (encrypted_access, encrypted_refresh, key_id, user_id))

                    results["tokens_encrypted"] += 1

                except Exception as e:
                    results["tokens_skipped"] += 1
                    results["errors"].append(f"Failed to encrypt tokens for user {user_id}: {str(e)}")

            conn.commit()

        # Print summary
        print(f"Migration {MIGRATION_VERSION}_{MIGRATION_NAME} completed successfully")
        if results["columns_added"]:
            print(f"  Columns added: {', '.join(results['columns_added'])}")
        if results["tokens_encrypted"] > 0:
            print(f"  Tokens encrypted: {results['tokens_encrypted']}")
        if results["tokens_skipped"] > 0:
            print(f"  Tokens skipped (errors): {results['tokens_skipped']}")
        if not results["columns_added"] and results["tokens_encrypted"] == 0:
            print("  No changes needed (schema already up to date)")

    except Exception as e:
        results["success"] = False
        results["errors"].append(f"Migration failed: {str(e)}")
        print(f"Migration failed: {e}")
        conn.rollback()

    finally:
        conn.close()

    # Set success to False if there were critical errors
    if results["errors"] and results["tokens_skipped"] > 0:
        results["success"] = False

    return results


def rollback(db_path: str) -> dict:
    """
    Rollback the Strava token encryption migration.

    This removes the encrypted columns. Note that if plaintext tokens
    were cleared after migration, this will result in data loss.

    Args:
        db_path: Path to the SQLite database file

    Returns:
        dict with rollback results
    """
    results = {
        "success": True,
        "columns_dropped": [],
        "warnings": [],
        "errors": []
    }

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        if not table_exists(conn, "strava_credentials"):
            results["warnings"].append("Table strava_credentials does not exist")
            return results

        # Check if there are any rows with encrypted tokens but no plaintext
        cursor = conn.execute("""
            SELECT COUNT(*) as count
            FROM strava_credentials
            WHERE (encrypted_access_token IS NOT NULL AND encrypted_access_token != '')
              AND (access_token IS NULL OR access_token = '')
        """)
        orphaned_count = cursor.fetchone()["count"]

        if orphaned_count > 0:
            results["warnings"].append(
                f"WARNING: {orphaned_count} credential(s) have encrypted tokens but no plaintext. "
                "Rollback will result in data loss. Consider decrypting first."
            )
            print(f"  Warning: {orphaned_count} records may lose data on rollback")

        # SQLite doesn't support DROP COLUMN directly before 3.35.0
        # We need to recreate the table without the encrypted columns

        # Check SQLite version
        sqlite_version = sqlite3.sqlite_version_info

        if sqlite_version >= (3, 35, 0):
            # SQLite 3.35+ supports DROP COLUMN
            columns_to_drop = [
                "encrypted_access_token",
                "encrypted_refresh_token",
                "encryption_key_id"
            ]

            for column in columns_to_drop:
                if column_exists(conn, "strava_credentials", column):
                    conn.execute(f"ALTER TABLE strava_credentials DROP COLUMN {column}")
                    results["columns_dropped"].append(column)
        else:
            # For older SQLite, recreate table without encrypted columns
            if (column_exists(conn, "strava_credentials", "encrypted_access_token") or
                column_exists(conn, "strava_credentials", "encrypted_refresh_token") or
                column_exists(conn, "strava_credentials", "encryption_key_id")):

                # Create new table without encrypted columns
                conn.execute("""
                    CREATE TABLE strava_credentials_backup AS
                    SELECT user_id, access_token, refresh_token, expires_at,
                           athlete_id, athlete_name, scope, created_at, updated_at
                    FROM strava_credentials
                """)

                # Drop old table
                conn.execute("DROP TABLE strava_credentials")

                # Recreate original table structure
                conn.execute("""
                    CREATE TABLE strava_credentials (
                        user_id TEXT PRIMARY KEY DEFAULT 'default',
                        access_token TEXT NOT NULL,
                        refresh_token TEXT NOT NULL,
                        expires_at TEXT NOT NULL,
                        athlete_id TEXT,
                        athlete_name TEXT,
                        scope TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Copy data back
                conn.execute("""
                    INSERT INTO strava_credentials
                    SELECT * FROM strava_credentials_backup
                """)

                # Drop backup
                conn.execute("DROP TABLE strava_credentials_backup")

                results["columns_dropped"] = [
                    "encrypted_access_token",
                    "encrypted_refresh_token",
                    "encryption_key_id"
                ]

        conn.commit()
        print(f"Rollback completed: dropped {len(results['columns_dropped'])} columns")
        if results["columns_dropped"]:
            print(f"  Columns dropped: {', '.join(results['columns_dropped'])}")

    except Exception as e:
        results["success"] = False
        results["errors"].append(f"Rollback failed: {str(e)}")
        print(f"Rollback failed: {e}")
        conn.rollback()

    finally:
        conn.close()

    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m src.db.migrations.migration_005_encrypt_strava_tokens <db_path> [rollback]")
        sys.exit(1)

    db_path = sys.argv[1]
    action = sys.argv[2] if len(sys.argv) > 2 else "migrate"

    if action == "rollback":
        result = rollback(db_path)
        print(f"Rollback result: {result}")
    else:
        result = migrate(db_path)
        print(f"Migration result: {result}")

    sys.exit(0 if result["success"] else 1)
