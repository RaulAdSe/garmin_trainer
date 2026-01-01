"""SQLite-backed repository for subscription and usage management.

Provides operations for managing subscription plans, user subscriptions,
usage tracking, and feature access control for the multi-user platform.
"""

import sqlite3
from datetime import datetime, date
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from dataclasses import dataclass


@dataclass
class SubscriptionPlan:
    """Subscription plan definition."""

    id: str
    name: str
    description: Optional[str] = None
    price_cents: int = 0
    billing_period: str = "month"
    stripe_price_id: Optional[str] = None
    ai_analyses_per_month: Optional[int] = None
    ai_plans_limit: Optional[int] = None
    ai_chat_messages_per_day: Optional[int] = None
    ai_workouts_per_month: Optional[int] = None
    history_days: Optional[int] = None
    is_active: bool = True
    created_at: Optional[datetime] = None


@dataclass
class UserSubscription:
    """User's subscription status."""

    id: str
    user_id: str
    plan_id: str
    status: str = "active"
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False
    trial_end: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class UserUsage:
    """User's feature usage for a billing period."""

    id: str
    user_id: str
    period_start: date
    period_end: date
    ai_analyses_used: int = 0
    ai_chat_messages_used: int = 0
    ai_workouts_generated: int = 0
    ai_tokens_used: int = 0
    ai_cost_cents: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SubscriptionRepository:
    """
    SQLite-backed repository for subscription and usage management.

    Provides operations for managing subscription plans, user subscriptions,
    feature usage tracking, and access control for the multi-user platform.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the subscription repository.

        Args:
            db_path: Path to SQLite database file. If None, uses the default
                    training.db in the training-analyzer directory.
        """
        if db_path:
            self.db_path = Path(db_path)
        else:
            import os
            env_path = os.environ.get("TRAINING_DB_PATH")
            if env_path:
                self.db_path = Path(env_path)
            else:
                self.db_path = Path(__file__).parent.parent.parent.parent.parent / "training.db"

        self._ensure_tables_exist()

    @contextmanager
    def _get_connection(self):
        """Get database connection with context manager."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _ensure_tables_exist(self):
        """Ensure subscription-related tables exist."""
        with self._get_connection() as conn:
            # Subscription plans table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS subscription_plans (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    price_cents INTEGER DEFAULT 0,
                    billing_period TEXT DEFAULT 'month',
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

            # User subscriptions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_subscriptions (
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
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (plan_id) REFERENCES subscription_plans(id)
                )
            """)

            # User usage table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_usage (
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
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, period_start)
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_subscriptions_user
                ON user_subscriptions(user_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_usage_period
                ON user_usage(user_id, period_start DESC)
            """)

            # Insert default plans if they don't exist
            conn.execute("""
                INSERT OR IGNORE INTO subscription_plans
                (id, name, price_cents, ai_analyses_per_month, ai_plans_limit,
                 ai_chat_messages_per_day, ai_workouts_per_month, history_days)
                VALUES ('free', 'Free', 0, 5, 1, 10, 3, 180)
            """)
            conn.execute("""
                INSERT OR IGNORE INTO subscription_plans
                (id, name, price_cents, ai_analyses_per_month, ai_plans_limit,
                 ai_chat_messages_per_day, ai_workouts_per_month, history_days)
                VALUES ('pro', 'Pro', 999, NULL, NULL, NULL, NULL, NULL)
            """)

    def _row_to_plan(self, row: sqlite3.Row) -> SubscriptionPlan:
        """Convert a database row to a SubscriptionPlan entity."""
        created_at = row["created_at"]
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        return SubscriptionPlan(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            price_cents=row["price_cents"] or 0,
            billing_period=row["billing_period"] or "month",
            stripe_price_id=row["stripe_price_id"],
            ai_analyses_per_month=row["ai_analyses_per_month"],
            ai_plans_limit=row["ai_plans_limit"],
            ai_chat_messages_per_day=row["ai_chat_messages_per_day"],
            ai_workouts_per_month=row["ai_workouts_per_month"],
            history_days=row["history_days"],
            is_active=bool(row["is_active"]),
            created_at=created_at,
        )

    def _row_to_subscription(self, row: sqlite3.Row) -> UserSubscription:
        """Convert a database row to a UserSubscription entity."""
        def parse_datetime(val):
            if isinstance(val, str) and val:
                return datetime.fromisoformat(val)
            return val

        return UserSubscription(
            id=row["id"],
            user_id=row["user_id"],
            plan_id=row["plan_id"],
            status=row["status"] or "active",
            stripe_customer_id=row["stripe_customer_id"],
            stripe_subscription_id=row["stripe_subscription_id"],
            current_period_start=parse_datetime(row["current_period_start"]),
            current_period_end=parse_datetime(row["current_period_end"]),
            cancel_at_period_end=bool(row["cancel_at_period_end"]),
            trial_end=parse_datetime(row["trial_end"]),
            created_at=parse_datetime(row["created_at"]),
            updated_at=parse_datetime(row["updated_at"]),
        )

    def _row_to_usage(self, row: sqlite3.Row) -> UserUsage:
        """Convert a database row to a UserUsage entity."""
        def parse_datetime(val):
            if isinstance(val, str) and val:
                return datetime.fromisoformat(val)
            return val

        def parse_date(val):
            if isinstance(val, str) and val:
                return date.fromisoformat(val)
            return val

        return UserUsage(
            id=row["id"],
            user_id=row["user_id"],
            period_start=parse_date(row["period_start"]),
            period_end=parse_date(row["period_end"]),
            ai_analyses_used=row["ai_analyses_used"] or 0,
            ai_chat_messages_used=row["ai_chat_messages_used"] or 0,
            ai_workouts_generated=row["ai_workouts_generated"] or 0,
            ai_tokens_used=row["ai_tokens_used"] or 0,
            ai_cost_cents=row["ai_cost_cents"] or 0,
            created_at=parse_datetime(row["created_at"]),
            updated_at=parse_datetime(row["updated_at"]),
        )

    # ==================== Plan Methods ====================

    def get_plan(self, plan_id: str) -> Optional[SubscriptionPlan]:
        """
        Retrieve a subscription plan by ID.

        Args:
            plan_id: The plan identifier (e.g., 'free', 'pro')

        Returns:
            The SubscriptionPlan if found, None otherwise
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM subscription_plans WHERE id = ?",
                (plan_id,)
            ).fetchone()

            if row:
                return self._row_to_plan(row)
            return None

    def get_all_plans(self, active_only: bool = True) -> List[SubscriptionPlan]:
        """
        Retrieve all subscription plans.

        Args:
            active_only: If True, only return active plans

        Returns:
            List of SubscriptionPlan entities, ordered by price
        """
        query = "SELECT * FROM subscription_plans"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY price_cents ASC"

        with self._get_connection() as conn:
            rows = conn.execute(query).fetchall()
            return [self._row_to_plan(row) for row in rows]

    # ==================== Subscription Methods ====================

    def get_user_subscription(self, user_id: str) -> Optional[UserSubscription]:
        """
        Retrieve a user's current subscription.

        Args:
            user_id: The user's unique identifier

        Returns:
            The UserSubscription if found, None otherwise
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM user_subscriptions WHERE user_id = ?",
                (user_id,)
            ).fetchone()

            if row:
                return self._row_to_subscription(row)
            return None

    def create_subscription(
        self,
        subscription_id: str,
        user_id: str,
        plan_id: str = "free",
        status: str = "active",
        stripe_customer_id: Optional[str] = None,
        stripe_subscription_id: Optional[str] = None,
        current_period_start: Optional[datetime] = None,
        current_period_end: Optional[datetime] = None,
        trial_end: Optional[datetime] = None,
    ) -> UserSubscription:
        """
        Create a new subscription for a user.

        Args:
            subscription_id: Unique identifier for the subscription
            user_id: The user's unique identifier
            plan_id: The subscription plan ID (default: 'free')
            status: Subscription status (default: 'active')
            stripe_customer_id: Stripe customer ID (optional)
            stripe_subscription_id: Stripe subscription ID (optional)
            current_period_start: Start of current billing period
            current_period_end: End of current billing period
            trial_end: End of trial period (if applicable)

        Returns:
            The created UserSubscription entity
        """
        now = datetime.now().isoformat()

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO user_subscriptions
                (id, user_id, plan_id, status, stripe_customer_id, stripe_subscription_id,
                 current_period_start, current_period_end, trial_end, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                subscription_id,
                user_id,
                plan_id,
                status,
                stripe_customer_id,
                stripe_subscription_id,
                current_period_start.isoformat() if current_period_start else None,
                current_period_end.isoformat() if current_period_end else None,
                trial_end.isoformat() if trial_end else None,
                now,
                now,
            ))

        return UserSubscription(
            id=subscription_id,
            user_id=user_id,
            plan_id=plan_id,
            status=status,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
            current_period_start=current_period_start,
            current_period_end=current_period_end,
            trial_end=trial_end,
            created_at=datetime.fromisoformat(now),
            updated_at=datetime.fromisoformat(now),
        )

    def update_subscription(
        self,
        user_id: str,
        plan_id: Optional[str] = None,
        status: Optional[str] = None,
        stripe_customer_id: Optional[str] = None,
        stripe_subscription_id: Optional[str] = None,
        current_period_start: Optional[datetime] = None,
        current_period_end: Optional[datetime] = None,
        cancel_at_period_end: Optional[bool] = None,
        trial_end: Optional[datetime] = None,
    ) -> Optional[UserSubscription]:
        """
        Update an existing user subscription.

        Args:
            user_id: The user's unique identifier
            plan_id: New plan ID
            status: New status
            stripe_customer_id: Stripe customer ID
            stripe_subscription_id: Stripe subscription ID
            current_period_start: Start of current billing period
            current_period_end: End of current billing period
            cancel_at_period_end: Whether to cancel at period end
            trial_end: End of trial period

        Returns:
            The updated UserSubscription if found, None otherwise
        """
        updates = []
        params = []

        if plan_id is not None:
            updates.append("plan_id = ?")
            params.append(plan_id)
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if stripe_customer_id is not None:
            updates.append("stripe_customer_id = ?")
            params.append(stripe_customer_id)
        if stripe_subscription_id is not None:
            updates.append("stripe_subscription_id = ?")
            params.append(stripe_subscription_id)
        if current_period_start is not None:
            updates.append("current_period_start = ?")
            params.append(current_period_start.isoformat())
        if current_period_end is not None:
            updates.append("current_period_end = ?")
            params.append(current_period_end.isoformat())
        if cancel_at_period_end is not None:
            updates.append("cancel_at_period_end = ?")
            params.append(1 if cancel_at_period_end else 0)
        if trial_end is not None:
            updates.append("trial_end = ?")
            params.append(trial_end.isoformat())

        if not updates:
            return self.get_user_subscription(user_id)

        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(user_id)

        query = f"UPDATE user_subscriptions SET {', '.join(updates)} WHERE user_id = ?"

        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            if cursor.rowcount == 0:
                return None

        return self.get_user_subscription(user_id)

    # ==================== Usage Methods ====================

    def get_user_usage(
        self,
        user_id: str,
        period_start: Optional[date] = None,
    ) -> Optional[UserUsage]:
        """
        Retrieve a user's usage for a specific billing period.

        Args:
            user_id: The user's unique identifier
            period_start: Start of the billing period (default: current month)

        Returns:
            The UserUsage if found, None otherwise
        """
        if period_start is None:
            period_start = date.today().replace(day=1)

        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM user_usage WHERE user_id = ? AND period_start = ?",
                (user_id, period_start.isoformat())
            ).fetchone()

            if row:
                return self._row_to_usage(row)
            return None

    def _get_or_create_usage(
        self,
        conn: sqlite3.Connection,
        user_id: str,
        period_start: date,
    ) -> str:
        """
        Get or create a usage record for the user and period.

        Returns the usage record ID.
        """
        import uuid
        period_end = date(
            period_start.year + (1 if period_start.month == 12 else 0),
            1 if period_start.month == 12 else period_start.month + 1,
            1
        )

        # Check if record exists
        row = conn.execute(
            "SELECT id FROM user_usage WHERE user_id = ? AND period_start = ?",
            (user_id, period_start.isoformat())
        ).fetchone()

        if row:
            return row["id"]

        # Create new record
        usage_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        conn.execute("""
            INSERT INTO user_usage
            (id, user_id, period_start, period_end, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            usage_id,
            user_id,
            period_start.isoformat(),
            period_end.isoformat(),
            now,
            now,
        ))

        return usage_id

    def increment_usage(
        self,
        user_id: str,
        feature: str,
        amount: int = 1,
        tokens: int = 0,
        cost_cents: int = 0,
    ) -> UserUsage:
        """
        Increment usage counter for a specific feature.

        Args:
            user_id: The user's unique identifier
            feature: Feature name ('ai_analyses', 'ai_chat_messages', 'ai_workouts')
            amount: Amount to increment (default: 1)
            tokens: Number of tokens used (for AI features)
            cost_cents: Cost in cents (for AI features)

        Returns:
            The updated UserUsage entity
        """
        period_start = date.today().replace(day=1)

        # Map feature to column name
        column_map = {
            "ai_analyses": "ai_analyses_used",
            "ai_chat_messages": "ai_chat_messages_used",
            "ai_workouts": "ai_workouts_generated",
        }

        column = column_map.get(feature)
        if not column:
            raise ValueError(f"Unknown feature: {feature}")

        with self._get_connection() as conn:
            # Ensure usage record exists
            self._get_or_create_usage(conn, user_id, period_start)

            # Increment the counter
            conn.execute(f"""
                UPDATE user_usage
                SET {column} = {column} + ?,
                    ai_tokens_used = ai_tokens_used + ?,
                    ai_cost_cents = ai_cost_cents + ?,
                    updated_at = ?
                WHERE user_id = ? AND period_start = ?
            """, (
                amount,
                tokens,
                cost_cents,
                datetime.now().isoformat(),
                user_id,
                period_start.isoformat(),
            ))

        return self.get_user_usage(user_id, period_start)

    def reset_usage(
        self,
        user_id: str,
        period_start: Optional[date] = None,
    ) -> bool:
        """
        Reset all usage counters for a user's billing period.

        Args:
            user_id: The user's unique identifier
            period_start: Start of the billing period (default: current month)

        Returns:
            True if reset was successful, False if no record found
        """
        if period_start is None:
            period_start = date.today().replace(day=1)

        with self._get_connection() as conn:
            cursor = conn.execute("""
                UPDATE user_usage
                SET ai_analyses_used = 0,
                    ai_chat_messages_used = 0,
                    ai_workouts_generated = 0,
                    ai_tokens_used = 0,
                    ai_cost_cents = 0,
                    updated_at = ?
                WHERE user_id = ? AND period_start = ?
            """, (
                datetime.now().isoformat(),
                user_id,
                period_start.isoformat(),
            ))
            return cursor.rowcount > 0

    def can_use_feature(self, user_id: str, feature: str) -> bool:
        """
        Check if a user can use a specific feature based on their subscription limits.

        Args:
            user_id: The user's unique identifier
            feature: Feature name ('ai_analyses', 'ai_chat_messages', 'ai_workouts')

        Returns:
            True if the user can use the feature, False if limit reached
        """
        # Get user's subscription
        subscription = self.get_user_subscription(user_id)
        plan_id = subscription.plan_id if subscription else "free"

        # Get plan limits
        plan = self.get_plan(plan_id)
        if not plan:
            plan = self.get_plan("free")

        # Map feature to limit column
        limit_map = {
            "ai_analyses": plan.ai_analyses_per_month,
            "ai_chat_messages": plan.ai_chat_messages_per_day,
            "ai_workouts": plan.ai_workouts_per_month,
        }

        limit = limit_map.get(feature)

        # None means unlimited
        if limit is None:
            return True

        # Get current usage
        period_start = date.today().replace(day=1)
        usage = self.get_user_usage(user_id, period_start)

        if not usage:
            return True  # No usage yet

        # Map feature to usage column
        usage_map = {
            "ai_analyses": usage.ai_analyses_used,
            "ai_chat_messages": usage.ai_chat_messages_used,
            "ai_workouts": usage.ai_workouts_generated,
        }

        used = usage_map.get(feature, 0)

        return used < limit


# Singleton instance for dependency injection
_subscription_repository: Optional[SubscriptionRepository] = None


def get_subscription_repository() -> SubscriptionRepository:
    """Get or create the singleton SubscriptionRepository instance."""
    global _subscription_repository
    if _subscription_repository is None:
        _subscription_repository = SubscriptionRepository()
    return _subscription_repository
