"""
Migration 003: Multi-user schema with subscriptions, Garmin sync, and usage tracking

This migration adds comprehensive multi-user support including:
- Users and user_sessions tables for authentication
- Subscription plans and user subscriptions for billing (Stripe integration)
- User usage tracking for AI feature limits
- Garmin credentials, sync config, and sync history tables
- user_id column added to all user-specific existing tables

This migration is idempotent and safe to run multiple times.

Usage:
    python -m src.db.migrations.migration_003_multi_user data/training.db
"""

import sqlite3
import sys
from typing import Optional

MIGRATION_VERSION = "003"
MIGRATION_NAME = "multi_user"


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


def index_exists(conn: sqlite3.Connection, index_name: str) -> bool:
    """Check if an index exists."""
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
        (index_name,)
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


def create_index_if_not_exists(
    conn: sqlite3.Connection,
    index_name: str,
    table: str,
    columns: str
) -> bool:
    """Create an index if it doesn't exist."""
    if index_exists(conn, index_name):
        return False
    conn.execute(f"CREATE INDEX {index_name} ON {table}({columns})")
    return True


def migrate(db_path: str) -> dict:
    """
    Run the multi-user migration on the specified database.

    Args:
        db_path: Path to the SQLite database file

    Returns:
        dict with migration results including:
        - success: bool
        - tables_created: list of new tables created
        - columns_added: list of columns added to existing tables
        - indexes_created: list of indexes created
        - errors: list of any errors encountered
    """
    results = {
        "success": True,
        "migration": f"{MIGRATION_VERSION}_{MIGRATION_NAME}",
        "tables_created": [],
        "columns_added": [],
        "indexes_created": [],
        "data_inserted": [],
        "errors": []
    }

    conn = sqlite3.connect(db_path)

    try:
        # =================================================================
        # Create users table
        # =================================================================
        if not table_exists(conn, "users"):
            conn.execute("""
                CREATE TABLE users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    display_name TEXT,
                    avatar_url TEXT,
                    timezone TEXT DEFAULT 'UTC',
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            results["tables_created"].append("users")

        # Create users index
        if create_index_if_not_exists(conn, "idx_users_email", "users", "email"):
            results["indexes_created"].append("idx_users_email")

        # =================================================================
        # Create user_sessions table
        # =================================================================
        if not table_exists(conn, "user_sessions"):
            conn.execute("""
                CREATE TABLE user_sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    user_agent TEXT,
                    ip_address TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            results["tables_created"].append("user_sessions")

        # Create session indexes
        if create_index_if_not_exists(conn, "idx_sessions_user", "user_sessions", "user_id"):
            results["indexes_created"].append("idx_sessions_user")
        if create_index_if_not_exists(conn, "idx_sessions_expires", "user_sessions", "expires_at"):
            results["indexes_created"].append("idx_sessions_expires")

        # =================================================================
        # Create subscription_plans table
        # =================================================================
        if not table_exists(conn, "subscription_plans"):
            conn.execute("""
                CREATE TABLE subscription_plans (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    price_cents INTEGER DEFAULT 0,
                    stripe_price_id TEXT,
                    ai_analyses_per_month INTEGER,
                    ai_plans_limit INTEGER,
                    ai_chat_messages_per_day INTEGER,
                    ai_workouts_per_month INTEGER,
                    history_days INTEGER,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            results["tables_created"].append("subscription_plans")

            # Insert default plans
            conn.execute("""
                INSERT INTO subscription_plans
                (id, name, price_cents, ai_analyses_per_month, ai_plans_limit,
                 ai_chat_messages_per_day, ai_workouts_per_month, history_days)
                VALUES
                ('free', 'Free', 0, 5, 1, 10, 3, 180),
                ('pro', 'Pro', 999, NULL, NULL, NULL, NULL, NULL)
            """)
            results["data_inserted"].append("subscription_plans: free, pro")

        # =================================================================
        # Create user_subscriptions table
        # =================================================================
        if not table_exists(conn, "user_subscriptions"):
            conn.execute("""
                CREATE TABLE user_subscriptions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL UNIQUE,
                    plan_id TEXT NOT NULL DEFAULT 'free',
                    status TEXT DEFAULT 'active',
                    stripe_customer_id TEXT UNIQUE,
                    stripe_subscription_id TEXT UNIQUE,
                    current_period_start TEXT,
                    current_period_end TEXT,
                    cancel_at_period_end INTEGER DEFAULT 0,
                    trial_end TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (plan_id) REFERENCES subscription_plans(id)
                )
            """)
            results["tables_created"].append("user_subscriptions")

        # Create subscription indexes
        if create_index_if_not_exists(conn, "idx_subscriptions_user", "user_subscriptions", "user_id"):
            results["indexes_created"].append("idx_subscriptions_user")
        if create_index_if_not_exists(conn, "idx_subscriptions_status", "user_subscriptions", "status"):
            results["indexes_created"].append("idx_subscriptions_status")

        # =================================================================
        # Create user_usage table
        # =================================================================
        if not table_exists(conn, "user_usage"):
            conn.execute("""
                CREATE TABLE user_usage (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    period_start TEXT NOT NULL,
                    period_end TEXT NOT NULL,
                    ai_analyses_used INTEGER DEFAULT 0,
                    ai_chat_messages_used INTEGER DEFAULT 0,
                    ai_workouts_generated INTEGER DEFAULT 0,
                    ai_tokens_used INTEGER DEFAULT 0,
                    ai_cost_cents INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE(user_id, period_start)
                )
            """)
            results["tables_created"].append("user_usage")

        # Create usage index
        if create_index_if_not_exists(conn, "idx_user_usage_period", "user_usage", "user_id, period_start DESC"):
            results["indexes_created"].append("idx_user_usage_period")

        # =================================================================
        # Create garmin_credentials table
        # =================================================================
        if not table_exists(conn, "garmin_credentials"):
            conn.execute("""
                CREATE TABLE garmin_credentials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL UNIQUE,
                    encrypted_email TEXT NOT NULL,
                    encrypted_password TEXT NOT NULL,
                    encryption_key_id TEXT NOT NULL,
                    garmin_user_id TEXT,
                    garmin_display_name TEXT,
                    is_valid INTEGER DEFAULT 1,
                    last_validation_at TEXT,
                    validation_error TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            results["tables_created"].append("garmin_credentials")

        # Create garmin credentials index
        if create_index_if_not_exists(conn, "idx_garmin_creds_user", "garmin_credentials", "user_id"):
            results["indexes_created"].append("idx_garmin_creds_user")

        # =================================================================
        # Create garmin_sync_config table
        # =================================================================
        if not table_exists(conn, "garmin_sync_config"):
            conn.execute("""
                CREATE TABLE garmin_sync_config (
                    user_id TEXT PRIMARY KEY,
                    auto_sync_enabled INTEGER DEFAULT 1,
                    sync_frequency TEXT DEFAULT 'daily',
                    sync_time TEXT DEFAULT '06:00',
                    sync_activities INTEGER DEFAULT 1,
                    sync_wellness INTEGER DEFAULT 1,
                    sync_fitness_metrics INTEGER DEFAULT 1,
                    initial_sync_days INTEGER DEFAULT 365,
                    incremental_sync_days INTEGER DEFAULT 7,
                    min_sync_interval_minutes INTEGER DEFAULT 60,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            results["tables_created"].append("garmin_sync_config")

        # =================================================================
        # Create garmin_sync_history table
        # =================================================================
        if not table_exists(conn, "garmin_sync_history"):
            conn.execute("""
                CREATE TABLE garmin_sync_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    sync_type TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    duration_seconds INTEGER,
                    status TEXT DEFAULT 'running',
                    activities_synced INTEGER DEFAULT 0,
                    wellness_days_synced INTEGER DEFAULT 0,
                    fitness_days_synced INTEGER DEFAULT 0,
                    sync_from_date TEXT,
                    sync_to_date TEXT,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            results["tables_created"].append("garmin_sync_history")

        # Create sync history indexes
        if create_index_if_not_exists(conn, "idx_sync_history_user", "garmin_sync_history", "user_id"):
            results["indexes_created"].append("idx_sync_history_user")
        if create_index_if_not_exists(conn, "idx_sync_history_started", "garmin_sync_history", "started_at DESC"):
            results["indexes_created"].append("idx_sync_history_started")

        # =================================================================
        # Add user_id column to existing user-specific tables
        # =================================================================
        tables_needing_user_id = [
            "activity_metrics",
            "fitness_metrics",
            "workouts",
            "training_plans",
            "workout_analyses",
            "garmin_fitness_data",
            "race_goals",
            "weekly_summaries",
        ]

        for table in tables_needing_user_id:
            try:
                if add_column_if_not_exists(conn, table, "user_id", "TEXT", "'default'"):
                    results["columns_added"].append(f"{table}.user_id")
                    # Create index for user_id on this table
                    index_name = f"idx_{table}_user_id"
                    if create_index_if_not_exists(conn, index_name, table, "user_id"):
                        results["indexes_created"].append(index_name)
            except Exception as e:
                results["errors"].append(f"Error adding user_id to {table}: {str(e)}")

        conn.commit()
        print(f"Migration {MIGRATION_VERSION}_{MIGRATION_NAME} completed successfully")
        if results["tables_created"]:
            print(f"  Tables created: {', '.join(results['tables_created'])}")
        if results["columns_added"]:
            print(f"  Columns added: {', '.join(results['columns_added'])}")
        if results["indexes_created"]:
            print(f"  Indexes created: {', '.join(results['indexes_created'])}")
        if results["data_inserted"]:
            print(f"  Data inserted: {', '.join(results['data_inserted'])}")
        if not any([results["tables_created"], results["columns_added"], results["indexes_created"]]):
            print("  No changes needed (schema already up to date)")

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
    Rollback the multi-user migration.

    Note: This removes the new tables but cannot easily remove columns
    added to existing tables in SQLite.

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
        # Drop tables in reverse dependency order
        tables_to_drop = [
            "garmin_sync_history",
            "garmin_sync_config",
            "garmin_credentials",
            "user_usage",
            "user_subscriptions",
            "subscription_plans",
            "user_sessions",
            "users",
        ]

        for table in tables_to_drop:
            if table_exists(conn, table):
                conn.execute(f"DROP TABLE {table}")
                results["tables_dropped"].append(table)

        # Drop indexes for user_id columns on existing tables
        indexes_to_drop = [
            "idx_activity_metrics_user_id",
            "idx_fitness_metrics_user_id",
            "idx_workouts_user_id",
            "idx_training_plans_user_id",
            "idx_workout_analyses_user_id",
            "idx_garmin_fitness_data_user_id",
            "idx_race_goals_user_id",
            "idx_weekly_summaries_user_id",
        ]

        for index_name in indexes_to_drop:
            try:
                conn.execute(f"DROP INDEX IF EXISTS {index_name}")
                results["indexes_dropped"].append(index_name)
            except Exception:
                pass

        conn.commit()
        print(f"Rollback completed: dropped {len(results['tables_dropped'])} tables")

    except Exception as e:
        results["success"] = False
        results["errors"].append(f"Rollback failed: {str(e)}")
        conn.rollback()

    finally:
        conn.close()

    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m src.db.migrations.migration_003_multi_user <db_path> [rollback]")
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
