"""
Migration 002: Add start_time column to activity_metrics

Adds the start_time column to store the full ISO timestamp of when
activities started, rather than just the date. This enables accurate
display of activity times in the UI.

Usage:
    python -m src.db.migrations.migration_002_start_time data/training.db
"""

import sqlite3
import sys
from typing import Optional

MIGRATION_VERSION = "002"
MIGRATION_NAME = "start_time"


def column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    """Check if a column exists in a table."""
    cursor = conn.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns


def add_column_if_not_exists(
    conn: sqlite3.Connection,
    table: str,
    column: str,
    column_type: str,
    default: Optional[str] = None
) -> bool:
    """Add a column to a table if it doesn't exist."""
    if column_exists(conn, table, column):
        return False

    default_clause = f" DEFAULT {default}" if default else ""
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}{default_clause}")
    return True


def migrate(db_path: str) -> dict:
    """
    Run the start_time migration on the specified database.

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

    try:
        # Add start_time column to activity_metrics
        if add_column_if_not_exists(conn, "activity_metrics", "start_time", "TEXT"):
            results["columns_added"].append("activity_metrics.start_time")

        conn.commit()
        print(f"Migration {MIGRATION_VERSION}_{MIGRATION_NAME} completed successfully")
        if results["columns_added"]:
            print(f"  Added columns: {', '.join(results['columns_added'])}")
        else:
            print("  No changes needed (column already exists)")

    except Exception as e:
        results["success"] = False
        results["errors"].append(str(e))
        print(f"Migration failed: {e}")
        conn.rollback()

    finally:
        conn.close()

    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m src.db.migrations.migration_002_start_time <db_path>")
        sys.exit(1)

    db_path = sys.argv[1]
    result = migrate(db_path)

    if not result["success"]:
        sys.exit(1)
