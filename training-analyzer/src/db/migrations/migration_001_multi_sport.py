"""
Migration 001: Multi-sport schema extensions

This migration adds support for multi-sport activities including:
- Power metrics for cycling/running (with power meters)
- Swimming-specific metrics
- Power zone configuration

This migration is idempotent and safe to run multiple times.
"""

import sqlite3
from pathlib import Path
from typing import Optional


MIGRATION_VERSION = "001"
MIGRATION_NAME = "multi_sport"


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
    if column_exists(conn, table, column):
        return False

    default_clause = f" DEFAULT {default}" if default else ""
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}{default_clause}")
    return True


def migrate(db_path: str) -> dict:
    """
    Run the multi-sport migration on the specified database.

    Args:
        db_path: Path to the SQLite database file

    Returns:
        dict with migration results including:
        - success: bool
        - columns_added: list of columns added to activity_metrics
        - tables_created: list of new tables created
        - errors: list of any errors encountered
    """
    results = {
        "success": True,
        "migration": f"{MIGRATION_VERSION}_{MIGRATION_NAME}",
        "columns_added": [],
        "tables_created": [],
        "indexes_created": [],
        "errors": []
    }

    conn = sqlite3.connect(db_path)

    try:
        # =================================================================
        # Add new columns to activity_metrics table
        # =================================================================
        new_columns = [
            ("sport_type", "TEXT", None),
            ("avg_power", "INTEGER", None),
            ("max_power", "INTEGER", None),
            ("normalized_power", "INTEGER", None),
            ("tss", "REAL", None),
            ("intensity_factor", "REAL", None),
            ("variability_index", "REAL", None),
            ("avg_speed_kmh", "REAL", None),
            ("elevation_gain_m", "REAL", None),
            ("cadence", "INTEGER", None),
        ]

        for col_name, col_type, default in new_columns:
            try:
                if add_column_if_not_exists(conn, "activity_metrics", col_name, col_type, default):
                    results["columns_added"].append(f"activity_metrics.{col_name}")
            except Exception as e:
                results["errors"].append(f"Error adding {col_name}: {str(e)}")

        # =================================================================
        # Create power_zones table
        # =================================================================
        if not table_exists(conn, "power_zones"):
            conn.execute("""
                CREATE TABLE power_zones (
                    athlete_id TEXT PRIMARY KEY,
                    ftp INTEGER,
                    zone1_max INTEGER,
                    zone2_max INTEGER,
                    zone3_max INTEGER,
                    zone4_max INTEGER,
                    zone5_max INTEGER,
                    zone6_max INTEGER,
                    zone7_max INTEGER,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            results["tables_created"].append("power_zones")

        # =================================================================
        # Create swim_metrics table
        # =================================================================
        if not table_exists(conn, "swim_metrics"):
            conn.execute("""
                CREATE TABLE swim_metrics (
                    activity_id TEXT PRIMARY KEY,
                    pool_length_m INTEGER,
                    total_strokes INTEGER,
                    avg_swolf REAL,
                    avg_stroke_rate REAL,
                    css_pace_sec INTEGER,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (activity_id) REFERENCES activity_metrics(activity_id)
                )
            """)
            results["tables_created"].append("swim_metrics")

        # =================================================================
        # Create indexes if they don't exist
        # =================================================================
        try:
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_activity_metrics_sport_type "
                "ON activity_metrics(sport_type)"
            )
            results["indexes_created"].append("idx_activity_metrics_sport_type")
        except Exception as e:
            if "already exists" not in str(e).lower():
                results["errors"].append(f"Error creating sport_type index: {str(e)}")

        try:
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_swim_metrics_activity "
                "ON swim_metrics(activity_id)"
            )
            results["indexes_created"].append("idx_swim_metrics_activity")
        except Exception as e:
            if "already exists" not in str(e).lower():
                results["errors"].append(f"Error creating swim_metrics index: {str(e)}")

        conn.commit()

    except Exception as e:
        results["success"] = False
        results["errors"].append(f"Migration failed: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

    # Set success to False if there were any errors
    if results["errors"]:
        results["success"] = False

    return results


def rollback(db_path: str) -> dict:
    """
    Rollback the multi-sport migration.

    Note: SQLite doesn't support DROP COLUMN in older versions,
    so this only removes the new tables.

    Args:
        db_path: Path to the SQLite database file

    Returns:
        dict with rollback results
    """
    results = {
        "success": True,
        "tables_dropped": [],
        "indexes_dropped": [],
        "errors": []
    }

    conn = sqlite3.connect(db_path)

    try:
        # Drop swim_metrics table
        if table_exists(conn, "swim_metrics"):
            conn.execute("DROP TABLE swim_metrics")
            results["tables_dropped"].append("swim_metrics")

        # Drop power_zones table
        if table_exists(conn, "power_zones"):
            conn.execute("DROP TABLE power_zones")
            results["tables_dropped"].append("power_zones")

        # Drop indexes (will be dropped with tables, but try anyway)
        try:
            conn.execute("DROP INDEX IF EXISTS idx_activity_metrics_sport_type")
            results["indexes_dropped"].append("idx_activity_metrics_sport_type")
        except Exception:
            pass

        conn.commit()

    except Exception as e:
        results["success"] = False
        results["errors"].append(f"Rollback failed: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

    return results


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python 001_multi_sport.py <db_path> [rollback]")
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
