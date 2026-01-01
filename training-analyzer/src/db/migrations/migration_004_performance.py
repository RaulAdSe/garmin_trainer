"""
Migration 004: Performance optimizations with database indexes

This migration adds performance-focused indexes documented in DATABASE_SCALING_PLAN.md:
- Pagination indexes for efficient list queries
- Partial indexes for filtered queries
- Covering index for list queries to avoid table lookups

This migration is idempotent and safe to run multiple times.

Usage:
    python -m src.db.migrations.migration_004_performance data/training.db
"""

import sqlite3
import sys
from typing import Optional

MIGRATION_VERSION = "004"
MIGRATION_NAME = "performance"


def index_exists(conn: sqlite3.Connection, index_name: str) -> bool:
    """Check if an index exists."""
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
        (index_name,)
    )
    return cursor.fetchone() is not None


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    """Check if a table exists."""
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,)
    )
    return cursor.fetchone() is not None


def create_index_if_not_exists(
    conn: sqlite3.Connection,
    index_name: str,
    create_statement: str
) -> bool:
    """
    Create an index if it doesn't exist.

    Args:
        conn: Database connection
        index_name: Name of the index to check/create
        create_statement: Full CREATE INDEX statement

    Returns:
        True if index was created, False if it already existed
    """
    if index_exists(conn, index_name):
        return False
    conn.execute(create_statement)
    return True


def migrate(db_path: str) -> dict:
    """
    Run the performance optimization migration on the specified database.

    Adds the following indexes from DATABASE_SCALING_PLAN.md:
    1. idx_activity_metrics_date_id - Pagination index (date DESC, activity_id)
    2. idx_activity_metrics_type_date - Type filtering with date ordering
    3. idx_activity_metrics_hrss - Partial index for HRSS queries
    4. idx_strava_sync_pending - Partial index for pending sync queries
    5. idx_activity_metrics_list - Covering index for list queries

    Args:
        db_path: Path to the SQLite database file

    Returns:
        dict with migration results including:
        - success: bool
        - indexes_created: list of indexes created
        - indexes_skipped: list of indexes that already existed
        - errors: list of any errors encountered
    """
    results = {
        "success": True,
        "migration": f"{MIGRATION_VERSION}_{MIGRATION_NAME}",
        "indexes_created": [],
        "indexes_skipped": [],
        "errors": []
    }

    conn = sqlite3.connect(db_path)

    try:
        # =================================================================
        # Index 1: Pagination index for activity listing
        # Used for: ORDER BY date DESC with efficient pagination
        # =================================================================
        if table_exists(conn, "activity_metrics"):
            index_name = "idx_activity_metrics_date_id"
            create_sql = """
                CREATE INDEX idx_activity_metrics_date_id
                ON activity_metrics(date DESC, activity_id)
            """
            if create_index_if_not_exists(conn, index_name, create_sql):
                results["indexes_created"].append(index_name)
            else:
                results["indexes_skipped"].append(index_name)

        # =================================================================
        # Index 2: Activity type with date ordering
        # Used for: Filtering by activity type with date-based pagination
        # =================================================================
        if table_exists(conn, "activity_metrics"):
            index_name = "idx_activity_metrics_type_date"
            create_sql = """
                CREATE INDEX idx_activity_metrics_type_date
                ON activity_metrics(activity_type, date DESC)
            """
            if create_index_if_not_exists(conn, index_name, create_sql):
                results["indexes_created"].append(index_name)
            else:
                results["indexes_skipped"].append(index_name)

        # =================================================================
        # Index 3: Partial index for HRSS queries
        # Used for: Queries that filter on HRSS (only rows with HRSS values)
        # =================================================================
        if table_exists(conn, "activity_metrics"):
            index_name = "idx_activity_metrics_hrss"
            create_sql = """
                CREATE INDEX idx_activity_metrics_hrss
                ON activity_metrics(hrss DESC)
                WHERE hrss IS NOT NULL
            """
            if create_index_if_not_exists(conn, index_name, create_sql):
                results["indexes_created"].append(index_name)
            else:
                results["indexes_skipped"].append(index_name)

        # =================================================================
        # Index 4: Partial index for pending Strava sync
        # Used for: Finding pending sync items efficiently
        # =================================================================
        if table_exists(conn, "strava_activity_sync"):
            index_name = "idx_strava_sync_pending"
            create_sql = """
                CREATE INDEX idx_strava_sync_pending
                ON strava_activity_sync(sync_status, created_at)
                WHERE sync_status = 'pending'
            """
            if create_index_if_not_exists(conn, index_name, create_sql):
                results["indexes_created"].append(index_name)
            else:
                results["indexes_skipped"].append(index_name)

        # =================================================================
        # Index 5: Covering index for activity list queries
        # Used for: List queries that need multiple fields without table lookup
        # Includes: date, activity_id, activity_name, activity_type,
        #           duration_min, distance_km
        # =================================================================
        if table_exists(conn, "activity_metrics"):
            index_name = "idx_activity_metrics_list"
            create_sql = """
                CREATE INDEX idx_activity_metrics_list
                ON activity_metrics(date DESC, activity_id, activity_name,
                                    activity_type, duration_min, distance_km)
            """
            if create_index_if_not_exists(conn, index_name, create_sql):
                results["indexes_created"].append(index_name)
            else:
                results["indexes_skipped"].append(index_name)

        conn.commit()

        # Print summary
        print(f"Migration {MIGRATION_VERSION}_{MIGRATION_NAME} completed successfully")
        if results["indexes_created"]:
            print(f"  Indexes created: {', '.join(results['indexes_created'])}")
        if results["indexes_skipped"]:
            print(f"  Indexes skipped (already exist): {', '.join(results['indexes_skipped'])}")
        if not results["indexes_created"] and not results["indexes_skipped"]:
            print("  No changes needed (tables don't exist yet)")

    except Exception as e:
        results["success"] = False
        results["errors"].append(f"Migration failed: {str(e)}")
        print(f"Migration failed: {e}")
        conn.rollback()

    finally:
        conn.close()

    # Set success to False if there were any errors
    if results["errors"]:
        results["success"] = False

    return results


def rollback(db_path: str) -> dict:
    """
    Rollback the performance optimization migration.

    Drops all indexes created by this migration.

    Args:
        db_path: Path to the SQLite database file

    Returns:
        dict with rollback results
    """
    results = {
        "success": True,
        "indexes_dropped": [],
        "errors": []
    }

    conn = sqlite3.connect(db_path)

    try:
        indexes_to_drop = [
            "idx_activity_metrics_date_id",
            "idx_activity_metrics_type_date",
            "idx_activity_metrics_hrss",
            "idx_strava_sync_pending",
            "idx_activity_metrics_list",
        ]

        for index_name in indexes_to_drop:
            if index_exists(conn, index_name):
                conn.execute(f"DROP INDEX {index_name}")
                results["indexes_dropped"].append(index_name)

        conn.commit()
        print(f"Rollback completed: dropped {len(results['indexes_dropped'])} indexes")
        if results["indexes_dropped"]:
            print(f"  Indexes dropped: {', '.join(results['indexes_dropped'])}")

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
        print("Usage: python -m src.db.migrations.migration_004_performance <db_path> [rollback]")
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
