"""SQLite-backed repository for AI/LLM usage tracking.

Provides logging and reporting of AI API calls including token counts,
costs, and per-user analytics for the multi-user platform.
"""

import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path


@dataclass
class AIUsageLog:
    """Represents a single AI usage log entry."""
    id: Optional[int] = None
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = "default"
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None

    # Model info
    provider: str = "openai"
    model_id: str = ""
    model_type: Optional[str] = None  # 'fast' or 'smart'

    # Token usage
    input_tokens: int = 0
    output_tokens: int = 0

    # Cost (in cents)
    input_cost_cents: float = 0.0
    output_cost_cents: float = 0.0
    total_cost_cents: float = 0.0

    # Context
    analysis_type: str = ""  # 'workout_analysis', 'chat', etc.
    entity_type: Optional[str] = None  # 'workout', 'plan'
    entity_id: Optional[str] = None  # workout_id, plan_id

    # Status
    status: str = "completed"  # 'pending', 'completed', 'failed'
    error_message: Optional[str] = None
    is_cached: bool = False

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class UsageSummary:
    """Summary of usage for a time period."""
    user_id: str = ""
    period_start: date = None
    period_end: date = None
    total_requests: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_cost_cents: float = 0.0
    by_analysis_type: Dict[str, int] = field(default_factory=dict)
    by_model: Dict[str, int] = field(default_factory=dict)
    requests_by_type: Dict[str, int] = field(default_factory=dict)
    cost_by_type: Dict[str, float] = field(default_factory=dict)


@dataclass
class UsageLimits:
    """Usage limits for a user."""
    user_id: str
    daily_request_limit: int = 100
    daily_token_limit: int = 500000
    daily_cost_limit_cents: int = 500
    monthly_cost_limit_cents: int = 5000
    current_daily_requests: int = 0
    current_daily_cost_cents: float = 0.0
    current_monthly_cost_cents: float = 0.0
    is_rate_limited: bool = False


class AIUsageRepository:
    """
    SQLite-backed repository for AI/LLM usage logging and reporting.

    Provides methods for logging AI API calls, tracking token usage and costs,
    and generating usage reports for billing and analytics.
    """

    # SQL for creating the ai_usage_logs table
    CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS ai_usage_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id TEXT UNIQUE NOT NULL,
        user_id TEXT DEFAULT 'default',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        completed_at TEXT,
        duration_ms INTEGER,

        provider TEXT DEFAULT 'openai',
        model_id TEXT NOT NULL,
        model_type TEXT,

        input_tokens INTEGER DEFAULT 0,
        output_tokens INTEGER DEFAULT 0,

        input_cost_cents REAL DEFAULT 0,
        output_cost_cents REAL DEFAULT 0,
        total_cost_cents REAL DEFAULT 0,

        analysis_type TEXT NOT NULL,
        entity_type TEXT,
        entity_id TEXT,

        status TEXT DEFAULT 'completed',
        error_message TEXT,
        is_cached INTEGER DEFAULT 0
    );

    CREATE INDEX IF NOT EXISTS idx_ai_usage_user ON ai_usage_logs(user_id);
    CREATE INDEX IF NOT EXISTS idx_ai_usage_created ON ai_usage_logs(created_at);
    CREATE INDEX IF NOT EXISTS idx_ai_usage_type ON ai_usage_logs(analysis_type);
    CREATE INDEX IF NOT EXISTS idx_ai_usage_user_created ON ai_usage_logs(user_id, created_at);
    """

    # Model pricing table SQL
    CREATE_PRICING_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS ai_model_pricing (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        provider TEXT NOT NULL,
        model_id TEXT NOT NULL,
        input_price_per_million_cents INTEGER NOT NULL,
        output_price_per_million_cents INTEGER NOT NULL,
        effective_from TEXT DEFAULT CURRENT_TIMESTAMP,
        effective_until TEXT,
        UNIQUE(provider, model_id, effective_from)
    );
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the AI usage repository.

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

        self._ensure_table_exists()

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

    def _ensure_table_exists(self) -> None:
        """Create the tables if they don't exist."""
        with self._get_connection() as conn:
            conn.executescript(self.CREATE_TABLE_SQL)
            conn.executescript(self.CREATE_PRICING_TABLE_SQL)

            # Insert default model pricing if not exists
            conn.execute("""
                INSERT OR IGNORE INTO ai_model_pricing
                (provider, model_id, input_price_per_million_cents, output_price_per_million_cents)
                VALUES
                    ('openai', 'gpt-4o-mini', 15, 60),
                    ('openai', 'gpt-4o', 250, 1000),
                    ('openai', 'gpt-4-turbo', 1000, 3000),
                    ('anthropic', 'claude-3-5-sonnet-20241022', 300, 1500),
                    ('anthropic', 'claude-3-haiku-20240307', 25, 125)
            """)

    def _calculate_cost(
        self,
        conn: sqlite3.Connection,
        provider: str,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
    ) -> Tuple[float, float]:
        """
        Calculate cost in cents for token usage.

        Returns:
            Tuple of (input_cost_cents, output_cost_cents)
        """
        row = conn.execute("""
            SELECT input_price_per_million_cents, output_price_per_million_cents
            FROM ai_model_pricing
            WHERE provider = ? AND model_id = ?
            AND (effective_until IS NULL OR effective_until > datetime('now'))
            ORDER BY effective_from DESC
            LIMIT 1
        """, (provider, model_id)).fetchone()

        if not row:
            return (0.0, 0.0)

        input_cost = (input_tokens / 1_000_000) * row["input_price_per_million_cents"]
        output_cost = (output_tokens / 1_000_000) * row["output_price_per_million_cents"]

        return (input_cost, output_cost)

    def log_request(
        self,
        request_id: str,
        user_id: str,
        model_id: str,
        analysis_type: str,
        provider: str = "openai",
        model_type: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
    ) -> AIUsageLog:
        """
        Log the start of an AI API request.

        Args:
            request_id: Unique identifier for this request
            user_id: The user's unique identifier
            model_id: The AI model being used
            analysis_type: Type of analysis ('workout_analysis', 'chat', 'plan', etc.)
            provider: AI provider ('openai', 'anthropic')
            model_type: Model tier ('fast', 'smart')
            entity_type: Type of entity being analyzed ('workout', 'plan')
            entity_id: ID of the entity being analyzed

        Returns:
            The created AIUsageLog entity
        """
        now = datetime.utcnow()

        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO ai_usage_logs
                (request_id, user_id, created_at, provider, model_id, model_type,
                 analysis_type, entity_type, entity_id, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
            """, (
                request_id,
                user_id,
                now.isoformat(),
                provider,
                model_id,
                model_type,
                analysis_type,
                entity_type,
                entity_id,
            ))

        return AIUsageLog(
            id=cursor.lastrowid,
            request_id=request_id,
            user_id=user_id,
            created_at=now,
            provider=provider,
            model_id=model_id,
            model_type=model_type,
            analysis_type=analysis_type,
            entity_type=entity_type,
            entity_id=entity_id,
            status="pending",
        )

    def update_request(
        self,
        request_id: str,
        status: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        error_message: Optional[str] = None,
        is_cached: bool = False,
    ) -> Optional[AIUsageLog]:
        """
        Update an AI request with completion details.

        Args:
            request_id: The request's unique identifier
            status: Final status ('completed', 'failed', 'cached')
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens used
            error_message: Error message if request failed
            is_cached: Whether result was served from cache

        Returns:
            The updated AIUsageLog if found, None otherwise
        """
        now = datetime.utcnow()

        with self._get_connection() as conn:
            # Get the request to calculate duration and cost
            row = conn.execute(
                "SELECT created_at, provider, model_id FROM ai_usage_logs WHERE request_id = ?",
                (request_id,)
            ).fetchone()

            if not row:
                return None

            created_at = datetime.fromisoformat(row["created_at"])
            duration_ms = int((now - created_at).total_seconds() * 1000)

            # Calculate costs
            input_cost_cents, output_cost_cents = self._calculate_cost(
                conn,
                row["provider"],
                row["model_id"],
                input_tokens,
                output_tokens,
            )

            total_cost_cents = input_cost_cents + output_cost_cents

            conn.execute("""
                UPDATE ai_usage_logs
                SET completed_at = ?,
                    duration_ms = ?,
                    input_tokens = ?,
                    output_tokens = ?,
                    input_cost_cents = ?,
                    output_cost_cents = ?,
                    total_cost_cents = ?,
                    status = ?,
                    error_message = ?,
                    is_cached = ?
                WHERE request_id = ?
            """, (
                now.isoformat(),
                duration_ms,
                input_tokens,
                output_tokens,
                input_cost_cents,
                output_cost_cents,
                total_cost_cents,
                status,
                error_message,
                1 if is_cached else 0,
                request_id,
            ))

        # Return updated record
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM ai_usage_logs WHERE request_id = ?",
                (request_id,)
            ).fetchone()
            if row:
                return self._row_to_log(row)
            return None

    def _row_to_log(self, row: sqlite3.Row) -> AIUsageLog:
        """Convert a database row to an AIUsageLog entity."""
        return AIUsageLog(
            id=row["id"],
            request_id=row["request_id"],
            user_id=row["user_id"],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            duration_ms=row["duration_ms"],
            provider=row["provider"],
            model_id=row["model_id"],
            model_type=row["model_type"],
            input_tokens=row["input_tokens"] or 0,
            output_tokens=row["output_tokens"] or 0,
            input_cost_cents=row["input_cost_cents"] or 0.0,
            output_cost_cents=row["output_cost_cents"] or 0.0,
            total_cost_cents=row["total_cost_cents"] or 0.0,
            analysis_type=row["analysis_type"],
            entity_type=row["entity_type"],
            entity_id=row["entity_id"],
            status=row["status"] or "pending",
            error_message=row["error_message"],
            is_cached=bool(row["is_cached"]),
        )

    def log_usage(
        self,
        request_id: str,
        user_id: Optional[str],
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        total_cost_cents: float,
        analysis_type: str,
        duration_ms: Optional[int] = None,
        model_type: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        is_cached: bool = False,
        status: str = "completed",
        error_message: Optional[str] = None,
    ) -> AIUsageLog:
        """
        Log a new AI usage entry (complete in one call).

        This is a convenience method that logs both the request start and completion
        in a single call. Use log_request() and update_request() for async patterns.

        Args:
            request_id: Unique identifier for this request
            user_id: User who made the request (None for anonymous)
            model_id: Model used (e.g., 'gpt-4o-mini')
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            total_cost_cents: Total cost in cents
            analysis_type: Type of analysis performed
            duration_ms: Request duration in milliseconds
            model_type: 'fast' or 'smart'
            entity_type: Type of entity analyzed (e.g., 'workout')
            entity_id: ID of entity analyzed
            is_cached: Whether response was from cache
            status: Status of the request
            error_message: Error message if failed

        Returns:
            The created AIUsageLog
        """
        now = datetime.utcnow()

        with self._get_connection() as conn:
            # Calculate costs from pricing table
            input_cost_cents, output_cost_cents = self._calculate_cost(
                conn, "openai", model_id, input_tokens, output_tokens
            )
            calculated_total = input_cost_cents + output_cost_cents

            log = AIUsageLog(
                request_id=request_id,
                user_id=user_id or "default",
                created_at=now,
                completed_at=now,
                duration_ms=duration_ms,
                provider="openai",
                model_id=model_id,
                model_type=model_type,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                input_cost_cents=input_cost_cents,
                output_cost_cents=output_cost_cents,
                total_cost_cents=total_cost_cents if total_cost_cents > 0 else calculated_total,
                analysis_type=analysis_type,
                entity_type=entity_type,
                entity_id=entity_id,
                status=status,
                error_message=error_message,
                is_cached=is_cached,
            )

            cursor = conn.execute(
                """
                INSERT INTO ai_usage_logs (
                    request_id, user_id, created_at, completed_at, duration_ms,
                    provider, model_id, model_type,
                    input_tokens, output_tokens,
                    input_cost_cents, output_cost_cents, total_cost_cents,
                    analysis_type, entity_type, entity_id,
                    status, error_message, is_cached
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    log.request_id,
                    log.user_id,
                    log.created_at.isoformat(),
                    log.completed_at.isoformat() if log.completed_at else None,
                    log.duration_ms,
                    log.provider,
                    log.model_id,
                    log.model_type,
                    log.input_tokens,
                    log.output_tokens,
                    log.input_cost_cents,
                    log.output_cost_cents,
                    log.total_cost_cents,
                    log.analysis_type,
                    log.entity_type,
                    log.entity_id,
                    log.status,
                    log.error_message,
                    1 if log.is_cached else 0,
                )
            )
            log.id = cursor.lastrowid

        return log

    def get_usage_count(
        self,
        user_id: str,
        analysis_type: str,
        period_start: date,
        period_end: Optional[date] = None,
    ) -> int:
        """
        Count completed requests for a user and analysis type within a time period.

        Used for quota enforcement to check usage before allowing AI calls.

        Args:
            user_id: User to count usage for.
            analysis_type: Type of analysis ('workout_analysis', 'chat', 'plan').
            period_start: Start date (inclusive).
            period_end: End date (inclusive), defaults to today.

        Returns:
            Number of completed requests in the period.
        """
        if period_end is None:
            period_end = date.today()

        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) as count
                FROM ai_usage_logs
                WHERE user_id = ?
                  AND analysis_type = ?
                  AND date(created_at) >= ?
                  AND date(created_at) <= ?
                  AND status = 'completed'
                """,
                (user_id, analysis_type, period_start.isoformat(), period_end.isoformat())
            ).fetchone()

        return row["count"] or 0

    def get_usage_summary(
        self,
        user_id: str,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
    ) -> UsageSummary:
        """
        Get usage summary for a user within a time period.

        Args:
            user_id: User to get summary for
            period_start: Start of period (defaults to start of current month)
            period_end: End of period (defaults to today)

        Returns:
            UsageSummary with aggregated data
        """
        if period_start is None:
            period_start = date.today().replace(day=1)
        if period_end is None:
            period_end = date.today()

        with self._get_connection() as conn:
            # Get totals
            row = conn.execute(
                """
                SELECT
                    COUNT(*) as total_requests,
                    COALESCE(SUM(input_tokens), 0) as total_input_tokens,
                    COALESCE(SUM(output_tokens), 0) as total_output_tokens,
                    COALESCE(SUM(total_cost_cents), 0) as total_cost_cents
                FROM ai_usage_logs
                WHERE user_id = ?
                  AND date(created_at) >= ?
                  AND date(created_at) <= ?
                  AND status = 'completed'
                """,
                (user_id, period_start.isoformat(), period_end.isoformat())
            ).fetchone()

            total_input = row["total_input_tokens"] or 0
            total_output = row["total_output_tokens"] or 0

            summary = UsageSummary(
                user_id=user_id,
                period_start=period_start,
                period_end=period_end,
                total_requests=row["total_requests"] or 0,
                total_input_tokens=total_input,
                total_output_tokens=total_output,
                total_tokens=total_input + total_output,
                total_cost_cents=row["total_cost_cents"] or 0.0,
            )

            # Get breakdown by analysis type (requests)
            rows = conn.execute(
                """
                SELECT analysis_type, COUNT(*) as count
                FROM ai_usage_logs
                WHERE user_id = ?
                  AND date(created_at) >= ?
                  AND date(created_at) <= ?
                  AND status = 'completed'
                GROUP BY analysis_type
                """,
                (user_id, period_start.isoformat(), period_end.isoformat())
            ).fetchall()
            summary.by_analysis_type = {row["analysis_type"]: row["count"] for row in rows}
            summary.requests_by_type = summary.by_analysis_type.copy()

            # Get breakdown by analysis type (cost)
            rows = conn.execute(
                """
                SELECT analysis_type, COALESCE(SUM(total_cost_cents), 0) as cost_cents
                FROM ai_usage_logs
                WHERE user_id = ?
                  AND date(created_at) >= ?
                  AND date(created_at) <= ?
                  AND status = 'completed'
                GROUP BY analysis_type
                """,
                (user_id, period_start.isoformat(), period_end.isoformat())
            ).fetchall()
            summary.cost_by_type = {row["analysis_type"]: row["cost_cents"] for row in rows}

            # Get breakdown by model
            rows = conn.execute(
                """
                SELECT model_id, COUNT(*) as count
                FROM ai_usage_logs
                WHERE user_id = ?
                  AND date(created_at) >= ?
                  AND date(created_at) <= ?
                  AND status = 'completed'
                GROUP BY model_id
                """,
                (user_id, period_start.isoformat(), period_end.isoformat())
            ).fetchall()
            summary.by_model = {row["model_id"]: row["count"] for row in rows}

        return summary

    def get_user_usage_summary(
        self,
        user_id: str,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
    ) -> UsageSummary:
        """
        Get a summary of AI usage for a user over a period.

        This is an alias for get_usage_summary() for API consistency.

        Args:
            user_id: The user's unique identifier
            period_start: Start date (default: first of current month)
            period_end: End date (default: today)

        Returns:
            UsageSummary with aggregated usage data
        """
        return self.get_usage_summary(user_id, period_start, period_end)

    def get_usage_by_date_range(
        self,
        user_id: str,
        start_date: date,
        end_date: date,
    ) -> List[Dict[str, Any]]:
        """
        Get daily usage breakdown for a date range.

        Args:
            user_id: The user's unique identifier
            start_date: Start date
            end_date: End date

        Returns:
            List of dicts with date, requests, tokens, and cost_usd
        """
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT
                    date(created_at) as date,
                    COUNT(*) as requests,
                    COALESCE(SUM(input_tokens + output_tokens), 0) as tokens,
                    ROUND(COALESCE(SUM(total_cost_cents), 0) / 100.0, 4) as cost_usd
                FROM ai_usage_logs
                WHERE user_id = ?
                AND date(created_at) >= ?
                AND date(created_at) <= ?
                AND status = 'completed'
                GROUP BY date(created_at)
                ORDER BY date DESC
            """, (user_id, start_date.isoformat(), end_date.isoformat())).fetchall()

            return [
                {
                    "date": row["date"],
                    "requests": row["requests"],
                    "tokens": row["tokens"],
                    "cost_usd": row["cost_usd"],
                }
                for row in rows
            ]

    def get_usage_by_analysis_type(
        self,
        user_id: str,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Get usage breakdown by analysis type for the last N days.

        Args:
            user_id: The user's unique identifier
            days: Number of days to look back

        Returns:
            List of dicts with analysis_type, requests, and cost_usd
        """
        start_date = (date.today() - timedelta(days=days)).isoformat()

        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT
                    analysis_type,
                    COUNT(*) as requests,
                    ROUND(COALESCE(SUM(total_cost_cents), 0) / 100.0, 4) as cost_usd
                FROM ai_usage_logs
                WHERE user_id = ?
                AND date(created_at) >= ?
                AND status = 'completed'
                GROUP BY analysis_type
                ORDER BY requests DESC
            """, (user_id, start_date)).fetchall()

            return [
                {
                    "analysis_type": row["analysis_type"],
                    "requests": row["requests"],
                    "cost_usd": row["cost_usd"],
                }
                for row in rows
            ]

    def get_total_cost(
        self,
        user_id: str,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
    ) -> float:
        """
        Get total cost in USD for a user over a period.

        Args:
            user_id: The user's unique identifier
            period_start: Start date (default: first of current month)
            period_end: End date (default: today)

        Returns:
            Total cost in USD
        """
        if period_start is None:
            period_start = date.today().replace(day=1)
        if period_end is None:
            period_end = date.today()

        with self._get_connection() as conn:
            row = conn.execute("""
                SELECT COALESCE(SUM(total_cost_cents), 0) as total_cents
                FROM ai_usage_logs
                WHERE user_id = ?
                AND date(created_at) >= ?
                AND date(created_at) <= ?
                AND status = 'completed'
            """, (user_id, period_start.isoformat(), period_end.isoformat())).fetchone()

            return row["total_cents"] / 100.0

    def get_usage_history(
        self,
        user_id: str,
        days: int = 30,
        granularity: str = "day",
    ) -> List[Dict[str, Any]]:
        """
        Get usage history grouped by time period.

        Args:
            user_id: User to get history for
            days: Number of days of history
            granularity: 'day', 'week', or 'month'

        Returns:
            List of usage data by time period
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # Determine date grouping based on granularity
        if granularity == "week":
            date_format = "%Y-W%W"
            group_expr = "strftime('%Y-W%W', created_at)"
        elif granularity == "month":
            date_format = "%Y-%m"
            group_expr = "strftime('%Y-%m', created_at)"
        else:  # day
            date_format = "%Y-%m-%d"
            group_expr = "date(created_at)"

        with self._get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT
                    {group_expr} as period,
                    COUNT(*) as requests,
                    COALESCE(SUM(input_tokens), 0) as input_tokens,
                    COALESCE(SUM(output_tokens), 0) as output_tokens,
                    COALESCE(SUM(total_cost_cents), 0) as cost_cents
                FROM ai_usage_logs
                WHERE user_id = ?
                  AND date(created_at) >= ?
                  AND date(created_at) <= ?
                  AND status = 'completed'
                GROUP BY {group_expr}
                ORDER BY period DESC
                """,
                (user_id, start_date.isoformat(), end_date.isoformat())
            ).fetchall()

        return [
            {
                "period": row["period"],
                "requests": row["requests"],
                "input_tokens": row["input_tokens"],
                "output_tokens": row["output_tokens"],
                "total_tokens": row["input_tokens"] + row["output_tokens"],
                "cost_cents": row["cost_cents"],
            }
            for row in rows
        ]

    def get_usage_by_type(
        self,
        user_id: str,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Get usage breakdown by analysis type.

        Args:
            user_id: User to get breakdown for
            days: Number of days to include

        Returns:
            List of usage data by analysis type
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    analysis_type,
                    COUNT(*) as requests,
                    COALESCE(SUM(input_tokens), 0) as input_tokens,
                    COALESCE(SUM(output_tokens), 0) as output_tokens,
                    COALESCE(SUM(total_cost_cents), 0) as cost_cents,
                    COALESCE(AVG(duration_ms), 0) as avg_duration_ms
                FROM ai_usage_logs
                WHERE user_id = ?
                  AND date(created_at) >= ?
                  AND date(created_at) <= ?
                  AND status = 'completed'
                GROUP BY analysis_type
                ORDER BY cost_cents DESC
                """,
                (user_id, start_date.isoformat(), end_date.isoformat())
            ).fetchall()

        return [
            {
                "analysis_type": row["analysis_type"],
                "requests": row["requests"],
                "input_tokens": row["input_tokens"],
                "output_tokens": row["output_tokens"],
                "total_tokens": row["input_tokens"] + row["output_tokens"],
                "cost_cents": row["cost_cents"],
                "avg_duration_ms": row["avg_duration_ms"],
            }
            for row in rows
        ]

    def get_usage_limits(
        self,
        user_id: str,
        daily_request_limit: int = 100,
        daily_cost_limit_cents: int = 500,
        monthly_cost_limit_cents: int = 5000,
    ) -> UsageLimits:
        """
        Get current usage against limits.

        Args:
            user_id: User to check limits for
            daily_request_limit: Maximum daily requests
            daily_cost_limit_cents: Maximum daily cost in cents
            monthly_cost_limit_cents: Maximum monthly cost in cents

        Returns:
            UsageLimits with current usage and limit status
        """
        today = date.today()
        month_start = today.replace(day=1)

        with self._get_connection() as conn:
            # Daily usage
            daily = conn.execute(
                """
                SELECT
                    COUNT(*) as requests,
                    COALESCE(SUM(total_cost_cents), 0) as cost_cents
                FROM ai_usage_logs
                WHERE user_id = ?
                  AND date(created_at) = ?
                  AND status = 'completed'
                """,
                (user_id, today.isoformat())
            ).fetchone()

            # Monthly usage
            monthly = conn.execute(
                """
                SELECT COALESCE(SUM(total_cost_cents), 0) as cost_cents
                FROM ai_usage_logs
                WHERE user_id = ?
                  AND date(created_at) >= ?
                  AND status = 'completed'
                """,
                (user_id, month_start.isoformat())
            ).fetchone()

        is_rate_limited = (
            daily["requests"] >= daily_request_limit or
            daily["cost_cents"] >= daily_cost_limit_cents or
            monthly["cost_cents"] >= monthly_cost_limit_cents
        )

        return UsageLimits(
            user_id=user_id,
            daily_request_limit=daily_request_limit,
            daily_cost_limit_cents=daily_cost_limit_cents,
            monthly_cost_limit_cents=monthly_cost_limit_cents,
            current_daily_requests=daily["requests"],
            current_daily_cost_cents=daily["cost_cents"],
            current_monthly_cost_cents=monthly["cost_cents"],
            is_rate_limited=is_rate_limited,
        )

    def get_recent_logs(
        self,
        user_id: str,
        limit: int = 50,
    ) -> List[AIUsageLog]:
        """
        Get recent usage logs for a user.

        Args:
            user_id: User to get logs for
            limit: Maximum number of logs to return

        Returns:
            List of AIUsageLog entries
        """
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM ai_usage_logs
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit)
            ).fetchall()

        logs = []
        for row in rows:
            logs.append(AIUsageLog(
                id=row["id"],
                request_id=row["request_id"],
                user_id=row["user_id"],
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
                completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
                duration_ms=row["duration_ms"],
                provider=row["provider"],
                model_id=row["model_id"],
                model_type=row["model_type"],
                input_tokens=row["input_tokens"],
                output_tokens=row["output_tokens"],
                input_cost_cents=row["input_cost_cents"],
                output_cost_cents=row["output_cost_cents"],
                total_cost_cents=row["total_cost_cents"],
                analysis_type=row["analysis_type"],
                entity_type=row["entity_type"],
                entity_id=row["entity_id"],
                status=row["status"],
                error_message=row["error_message"],
                is_cached=bool(row["is_cached"]),
            ))

        return logs


# Singleton instance
_ai_usage_repository: Optional[AIUsageRepository] = None


def get_ai_usage_repository(db_path: Optional[str] = None) -> AIUsageRepository:
    """Get the AI usage repository singleton."""
    global _ai_usage_repository
    if _ai_usage_repository is None:
        _ai_usage_repository = AIUsageRepository(db_path)
    return _ai_usage_repository
