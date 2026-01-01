"""
Migration 006: Add credential security tracking

This migration adds security features to the garmin_credentials table:
- Adds failed_validation_count column to track failed validation attempts
- Used by the credential endpoint rate limiting and lockout logic

This migration is idempotent and safe to run multiple times.

Usage:
    python -m src.db.migrations.migration_006_credential_security data/training.db
"""

import sqlite3
import sys
from typing import Optional

MIGRATION_VERSION = "006"
MIGRATION_NAME = "credential_security"


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


def migrate(db_path: str) -> dict:
    """
    Run the credential security migration on the specified database.

    Adds failed_validation_count column for tracking failed credential validations.

    Args:
        db_path: Path to the SQLite database file

    Returns:
        dict with migration results including:
        - success: bool
        - columns_added: list of columns added
        - errors: list of any errors encountered
    """
    results = {
        "success": True,
        "migration": f"{MIGRATION_VERSION}_{MIGRATION_NAME}",
        "columns_added": [],
        "errors": []
    }

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        # =================================================================
        # Step 1: Add failed_validation_count column to garmin_credentials
        # =================================================================
        if not table_exists(conn, "garmin_credentials"):
            # Table doesn't exist yet, no migration needed
            # The column will be created with the table when it's first accessed
            print(f"  Table garmin_credentials does not exist yet, skipping migration")
            return results

        # Add failed_validation_count column
        if add_column_if_not_exists(
            conn, "garmin_credentials", "failed_validation_count", "INTEGER", "0"
        ):
            results["columns_added"].append("garmin_credentials.failed_validation_count")

        conn.commit()

        # Print summary
        print(f"Migration {MIGRATION_VERSION}_{MIGRATION_NAME} completed successfully")
        if results["columns_added"]:
            print(f"  Columns added: {', '.join(results['columns_added'])}")
        else:
            print("  No changes needed (schema already up to date)")

    except Exception as e:
        results["success"] = False
        results["errors"].append(f"Migration failed: {str(e)}")
        print(f"Migration failed: {e}")
        conn.rollback()

    finally:
        conn.close()

    return results


def rollback(db_path: str) -> dict:
    """
    Rollback the credential security migration.

    This removes the failed_validation_count column.

    Args:
        db_path: Path to the SQLite database file

    Returns:
        dict with rollback results
    """
    results = {
        "success": True,
        "columns_dropped": [],
        "errors": []
    }

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        if not table_exists(conn, "garmin_credentials"):
            return results

        # Check SQLite version for DROP COLUMN support
        sqlite_version = sqlite3.sqlite_version_info

        if sqlite_version >= (3, 35, 0):
            # SQLite 3.35+ supports DROP COLUMN
            if column_exists(conn, "garmin_credentials", "failed_validation_count"):
                conn.execute("ALTER TABLE garmin_credentials DROP COLUMN failed_validation_count")
                results["columns_dropped"].append("failed_validation_count")
        else:
            # For older SQLite, we can't easily drop columns
            # Just set all values to 0 as a soft rollback
            if column_exists(conn, "garmin_credentials", "failed_validation_count"):
                conn.execute("UPDATE garmin_credentials SET failed_validation_count = 0")
                results["columns_dropped"].append("failed_validation_count (reset to 0)")
                print("  Note: SQLite < 3.35 - column reset to 0 instead of dropped")

        conn.commit()
        print(f"Rollback completed: {len(results['columns_dropped'])} column(s) affected")

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
        print("Usage: python -m src.db.migrations.migration_006_credential_security <db_path> [rollback]")
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
