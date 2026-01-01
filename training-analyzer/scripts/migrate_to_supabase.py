#!/usr/bin/env python3
"""
SQLite to Supabase Migration Script

This script migrates data from the local SQLite database to Supabase (PostgreSQL).
It handles the transformation of data types and schema differences between the
two database systems.

Usage:
    # Dry run (preview what would be migrated)
    python scripts/migrate_to_supabase.py --dry-run

    # Full migration
    python scripts/migrate_to_supabase.py

    # Migrate specific tables only
    python scripts/migrate_to_supabase.py --tables activity_metrics,fitness_metrics

    # Set batch size for large tables
    python scripts/migrate_to_supabase.py --batch-size 500

Environment Variables Required:
    SUPABASE_URL          - Your Supabase project URL
    SUPABASE_SERVICE_KEY  - Service role key (bypasses RLS)
    TRAINING_DB_PATH      - Path to SQLite database (optional)

See DATABASE_SCALING_PLAN.md for the full migration strategy.
"""

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# =============================================================================
# Configuration
# =============================================================================

# Tables to migrate, in order of dependencies
MIGRATION_TABLES = [
    "users",
    "subscription_plans",
    "user_subscriptions",
    "user_usage",
    "user_profile",
    "activity_metrics",
    "fitness_metrics",
    "garmin_fitness_data",
    "workouts",
    "training_plans",
    "workout_analyses",
    "race_goals",
    "weekly_summaries",
    "achievements",
    "user_achievements",
    "user_progress",
    "strava_credentials",
    "strava_preferences",
    "strava_activity_sync",
    "garmin_credentials",
    "garmin_sync_config",
    "garmin_sync_history",
]

# Column type transformations: SQLite -> PostgreSQL
TYPE_TRANSFORMATIONS = {
    # Booleans: SQLite uses 0/1, PostgreSQL uses true/false
    "is_active": lambda x: bool(x) if x is not None else None,
    "is_admin": lambda x: bool(x) if x is not None else None,
    "is_valid": lambda x: bool(x) if x is not None else None,
    "is_recovery_week": lambda x: bool(x) if x is not None else None,
    "auto_sync_enabled": lambda x: bool(x) if x is not None else None,
    "sync_activities": lambda x: bool(x) if x is not None else None,
    "sync_wellness": lambda x: bool(x) if x is not None else None,
    "sync_fitness_metrics": lambda x: bool(x) if x is not None else None,
    "email_verified": lambda x: bool(x) if x is not None else None,
    "cancel_at_period_end": lambda x: bool(x) if x is not None else None,
    "auto_update_description": lambda x: bool(x) if x is not None else None,
    "include_score": lambda x: bool(x) if x is not None else None,
    "include_summary": lambda x: bool(x) if x is not None else None,
    "include_link": lambda x: bool(x) if x is not None else None,
    "use_extended_format": lambda x: bool(x) if x is not None else None,
    "description_updated": lambda x: bool(x) if x is not None else None,
    "is_cached": lambda x: bool(x) if x is not None else None,
}

# Columns to skip during migration (auto-generated in PostgreSQL)
SKIP_COLUMNS = {
    # Auto-increment columns that will be SERIAL in PostgreSQL
    # (keep if they have foreign key references)
}

# Default user ID for migrating single-user data to multi-user schema
DEFAULT_USER_ID = "default"


# =============================================================================
# Data Transformation Functions
# =============================================================================

def transform_row(
    table_name: str,
    row: Dict[str, Any],
    default_user_id: str = DEFAULT_USER_ID
) -> Dict[str, Any]:
    """Transform a SQLite row for PostgreSQL compatibility.

    Args:
        table_name: Name of the table
        row: Dictionary of column -> value
        default_user_id: User ID to assign for single-user data

    Returns:
        Transformed row dictionary
    """
    transformed = {}

    for column, value in row.items():
        # Skip columns that should be auto-generated
        if column in SKIP_COLUMNS.get(table_name, set()):
            continue

        # Apply type transformation if defined
        if column in TYPE_TRANSFORMATIONS:
            value = TYPE_TRANSFORMATIONS[column](value)

        # Handle JSON columns (stored as TEXT in SQLite)
        if column.endswith("_json") and isinstance(value, str):
            try:
                value = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                pass  # Keep as string if not valid JSON

        # Handle timestamps
        if column in ("created_at", "updated_at", "expires_at", "started_at",
                      "completed_at", "last_login_at", "last_validation_at"):
            if value and not value.endswith("Z"):
                # Ensure ISO format with timezone
                try:
                    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                    value = dt.isoformat()
                except ValueError:
                    pass

        transformed[column] = value

    # Add user_id for tables that need multi-tenant support
    tables_needing_user_id = {
        "activity_metrics", "fitness_metrics", "garmin_fitness_data",
        "workouts", "training_plans", "workout_analyses", "race_goals",
        "weekly_summaries", "user_achievements",
    }

    if table_name in tables_needing_user_id and "user_id" not in transformed:
        transformed["user_id"] = default_user_id

    return transformed


def get_sqlite_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Get SQLite database connection."""
    if db_path is None:
        db_path = os.environ.get("TRAINING_DB_PATH")
        if not db_path:
            # Default path
            db_path = str(Path(__file__).parent.parent / "training.db")

    if not Path(db_path).exists():
        raise FileNotFoundError(f"SQLite database not found: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_supabase_client():
    """Get Supabase client."""
    try:
        from supabase import create_client
    except ImportError:
        print("ERROR: supabase package not installed.")
        print("Install with: pip install supabase")
        sys.exit(1)

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")

    if not url or not key:
        print("ERROR: Missing Supabase credentials.")
        print("Set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables.")
        sys.exit(1)

    return create_client(url, key)


# =============================================================================
# Migration Functions
# =============================================================================

def get_table_info(conn: sqlite3.Connection, table_name: str) -> List[Dict]:
    """Get column information for a table."""
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    return [
        {
            "cid": row[0],
            "name": row[1],
            "type": row[2],
            "notnull": row[3],
            "dflt_value": row[4],
            "pk": row[5],
        }
        for row in cursor.fetchall()
    ]


def get_row_count(conn: sqlite3.Connection, table_name: str) -> int:
    """Get total row count for a table."""
    cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
    return cursor.fetchone()[0]


def fetch_all_rows(
    conn: sqlite3.Connection,
    table_name: str,
    batch_size: int = 1000,
    offset: int = 0
) -> List[Dict]:
    """Fetch rows from SQLite table with pagination."""
    cursor = conn.execute(
        f"SELECT * FROM {table_name} LIMIT {batch_size} OFFSET {offset}"
    )
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def migrate_table(
    sqlite_conn: sqlite3.Connection,
    supabase_client,
    table_name: str,
    batch_size: int = 100,
    dry_run: bool = False,
    default_user_id: str = DEFAULT_USER_ID
) -> Tuple[int, int]:
    """Migrate a single table from SQLite to Supabase.

    Args:
        sqlite_conn: SQLite connection
        supabase_client: Supabase client
        table_name: Name of table to migrate
        batch_size: Number of rows per insert batch
        dry_run: If True, don't actually insert data
        default_user_id: User ID for single-user data

    Returns:
        Tuple of (migrated_count, error_count)
    """
    # Check if table exists in SQLite
    cursor = sqlite_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    if not cursor.fetchone():
        print(f"  Table '{table_name}' does not exist in SQLite, skipping.")
        return 0, 0

    total_rows = get_row_count(sqlite_conn, table_name)
    if total_rows == 0:
        print(f"  Table '{table_name}' is empty, skipping.")
        return 0, 0

    print(f"  Migrating {total_rows} rows from '{table_name}'...")

    migrated = 0
    errors = 0
    offset = 0

    while offset < total_rows:
        # Fetch batch
        rows = fetch_all_rows(sqlite_conn, table_name, batch_size, offset)
        if not rows:
            break

        # Transform rows
        transformed_rows = [
            transform_row(table_name, row, default_user_id)
            for row in rows
        ]

        if dry_run:
            print(f"    [DRY RUN] Would insert {len(transformed_rows)} rows")
            migrated += len(transformed_rows)
        else:
            try:
                # Insert into Supabase
                # Note: upsert handles conflicts based on primary key
                result = supabase_client.table(table_name).upsert(
                    transformed_rows
                ).execute()

                migrated += len(transformed_rows)
                print(f"    Inserted batch: {offset + 1}-{offset + len(rows)}")

            except Exception as e:
                errors += len(transformed_rows)
                print(f"    ERROR inserting batch: {e}")

                # Try inserting one by one to identify problematic rows
                for i, row in enumerate(transformed_rows):
                    try:
                        supabase_client.table(table_name).upsert([row]).execute()
                        migrated += 1
                        errors -= 1
                    except Exception as row_error:
                        print(f"      Row {offset + i} failed: {row_error}")

        offset += batch_size

    return migrated, errors


def run_migration(
    tables: Optional[List[str]] = None,
    batch_size: int = 100,
    dry_run: bool = False,
    sqlite_path: Optional[str] = None,
    default_user_id: str = DEFAULT_USER_ID
) -> Dict[str, Any]:
    """Run the full migration.

    Args:
        tables: List of tables to migrate (None = all)
        batch_size: Number of rows per insert batch
        dry_run: If True, don't actually insert data
        sqlite_path: Path to SQLite database
        default_user_id: User ID for single-user data

    Returns:
        Migration results summary
    """
    print("=" * 60)
    print("SQLite to Supabase Migration")
    print("=" * 60)

    if dry_run:
        print("\n*** DRY RUN MODE - No data will be written ***\n")

    # Connect to databases
    print("Connecting to SQLite...")
    sqlite_conn = get_sqlite_connection(sqlite_path)

    if not dry_run:
        print("Connecting to Supabase...")
        supabase_client = get_supabase_client()
    else:
        supabase_client = None

    # Determine tables to migrate
    migration_tables = tables if tables else MIGRATION_TABLES

    print(f"\nTables to migrate: {len(migration_tables)}")
    print("-" * 40)

    results = {
        "start_time": datetime.utcnow().isoformat(),
        "dry_run": dry_run,
        "tables": {},
        "total_migrated": 0,
        "total_errors": 0,
    }

    for table_name in migration_tables:
        print(f"\n[{migration_tables.index(table_name) + 1}/{len(migration_tables)}] {table_name}")

        migrated, errors = migrate_table(
            sqlite_conn=sqlite_conn,
            supabase_client=supabase_client,
            table_name=table_name,
            batch_size=batch_size,
            dry_run=dry_run,
            default_user_id=default_user_id,
        )

        results["tables"][table_name] = {
            "migrated": migrated,
            "errors": errors,
        }
        results["total_migrated"] += migrated
        results["total_errors"] += errors

    sqlite_conn.close()

    results["end_time"] = datetime.utcnow().isoformat()

    # Print summary
    print("\n" + "=" * 60)
    print("Migration Summary")
    print("=" * 60)
    print(f"Total rows migrated: {results['total_migrated']}")
    print(f"Total errors: {results['total_errors']}")

    if results["total_errors"] > 0:
        print("\nTables with errors:")
        for table, stats in results["tables"].items():
            if stats["errors"] > 0:
                print(f"  {table}: {stats['errors']} errors")

    return results


# =============================================================================
# PostgreSQL Schema Generation
# =============================================================================

def generate_postgresql_schema() -> str:
    """Generate PostgreSQL schema from SQLite schema.

    This function shows the schema differences and can be used to
    create the initial PostgreSQL tables in Supabase.
    """
    schema = """
-- =============================================================================
-- PostgreSQL Schema for Training Analyzer (Supabase)
-- =============================================================================
-- Generated from SQLite schema with the following transformations:
--   - AUTOINCREMENT -> SERIAL
--   - INTEGER (boolean) -> BOOLEAN
--   - TEXT (dates) -> DATE/TIMESTAMPTZ
--   - Added user_id for multi-tenant support
--   - Added Row-Level Security (RLS) policies
-- =============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- Users Table (extends Supabase auth.users)
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    display_name TEXT,
    avatar_url TEXT,
    timezone TEXT DEFAULT 'UTC',
    max_hr INTEGER,
    rest_hr INTEGER,
    threshold_hr INTEGER,
    gender TEXT DEFAULT 'male',
    age INTEGER,
    weight_kg DOUBLE PRECISION,
    subscription_tier TEXT DEFAULT 'free',
    stripe_customer_id TEXT,
    garmin_connected BOOLEAN DEFAULT FALSE,
    strava_connected BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view own profile"
    ON public.user_profiles FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
    ON public.user_profiles FOR UPDATE
    USING (auth.uid() = id);

-- =============================================================================
-- Activity Metrics Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.activity_metrics (
    activity_id TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    start_time TIMESTAMPTZ,
    activity_type TEXT,
    activity_name TEXT,
    hrss DOUBLE PRECISION,
    trimp DOUBLE PRECISION,
    avg_hr INTEGER,
    max_hr INTEGER,
    duration_min DOUBLE PRECISION,
    distance_km DOUBLE PRECISION,
    pace_sec_per_km DOUBLE PRECISION,
    zone1_pct DOUBLE PRECISION,
    zone2_pct DOUBLE PRECISION,
    zone3_pct DOUBLE PRECISION,
    zone4_pct DOUBLE PRECISION,
    zone5_pct DOUBLE PRECISION,
    sport_type TEXT,
    avg_power INTEGER,
    max_power INTEGER,
    normalized_power INTEGER,
    tss DOUBLE PRECISION,
    intensity_factor DOUBLE PRECISION,
    variability_index DOUBLE PRECISION,
    avg_speed_kmh DOUBLE PRECISION,
    elevation_gain_m DOUBLE PRECISION,
    cadence INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for efficient queries
CREATE INDEX idx_activity_user_date ON public.activity_metrics(user_id, date DESC);
CREATE INDEX idx_activity_date ON public.activity_metrics(date DESC);
CREATE INDEX idx_activity_type ON public.activity_metrics(activity_type);
CREATE INDEX idx_activity_sport ON public.activity_metrics(sport_type);

-- Enable RLS
ALTER TABLE public.activity_metrics ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view own activities"
    ON public.activity_metrics FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own activities"
    ON public.activity_metrics FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own activities"
    ON public.activity_metrics FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own activities"
    ON public.activity_metrics FOR DELETE
    USING (auth.uid() = user_id);

-- =============================================================================
-- Fitness Metrics Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.fitness_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    daily_load DOUBLE PRECISION,
    ctl DOUBLE PRECISION,
    atl DOUBLE PRECISION,
    tsb DOUBLE PRECISION,
    acwr DOUBLE PRECISION,
    risk_zone TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, date)
);

-- Indexes
CREATE INDEX idx_fitness_user_date ON public.fitness_metrics(user_id, date DESC);

-- Enable RLS
ALTER TABLE public.fitness_metrics ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own fitness metrics"
    ON public.fitness_metrics FOR ALL
    USING (auth.uid() = user_id);

-- =============================================================================
-- Subscription Plans Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.subscription_plans (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    price_cents INTEGER DEFAULT 0,
    stripe_price_id TEXT,
    ai_analyses_per_month INTEGER,
    ai_plans_limit INTEGER,
    ai_chat_messages_per_day INTEGER,
    ai_workouts_per_month INTEGER,
    history_days INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default plans
INSERT INTO public.subscription_plans (id, name, price_cents, ai_analyses_per_month, ai_plans_limit, ai_chat_messages_per_day, ai_workouts_per_month, history_days)
VALUES
    ('free', 'Free', 0, 5, 1, 10, 3, 180),
    ('pro', 'Pro', 999, NULL, NULL, NULL, NULL, NULL)
ON CONFLICT (id) DO NOTHING;

-- Note: Additional tables (workouts, training_plans, garmin_credentials, etc.)
-- follow the same pattern with:
--   1. user_id column for multi-tenant support
--   2. RLS enabled with appropriate policies
--   3. Proper indexes for common queries
--   4. TIMESTAMPTZ for all timestamps
--   5. BOOLEAN instead of INTEGER for boolean values
"""
    return schema


# =============================================================================
# CLI Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Migrate SQLite database to Supabase (PostgreSQL)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Preview migration
    python migrate_to_supabase.py --dry-run

    # Full migration
    python migrate_to_supabase.py

    # Migrate specific tables
    python migrate_to_supabase.py --tables activity_metrics,fitness_metrics

    # Generate PostgreSQL schema
    python migrate_to_supabase.py --generate-schema

Environment Variables:
    SUPABASE_URL          - Your Supabase project URL
    SUPABASE_SERVICE_KEY  - Service role key (required for migration)
    TRAINING_DB_PATH      - Path to SQLite database (optional)
        """
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview migration without writing data"
    )

    parser.add_argument(
        "--tables",
        type=str,
        help="Comma-separated list of tables to migrate"
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of rows per insert batch (default: 100)"
    )

    parser.add_argument(
        "--sqlite-path",
        type=str,
        help="Path to SQLite database file"
    )

    parser.add_argument(
        "--user-id",
        type=str,
        default=DEFAULT_USER_ID,
        help=f"User ID for single-user data (default: {DEFAULT_USER_ID})"
    )

    parser.add_argument(
        "--generate-schema",
        action="store_true",
        help="Generate PostgreSQL schema and exit"
    )

    parser.add_argument(
        "--output",
        type=str,
        help="Output file for schema or results (default: stdout)"
    )

    args = parser.parse_args()

    # Generate schema mode
    if args.generate_schema:
        schema = generate_postgresql_schema()
        if args.output:
            with open(args.output, "w") as f:
                f.write(schema)
            print(f"Schema written to {args.output}")
        else:
            print(schema)
        return

    # Parse tables
    tables = None
    if args.tables:
        tables = [t.strip() for t in args.tables.split(",")]

    # Run migration
    results = run_migration(
        tables=tables,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        sqlite_path=args.sqlite_path,
        default_user_id=args.user_id,
    )

    # Output results
    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults written to {args.output}")

    # Exit with error code if there were errors
    if results["total_errors"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
