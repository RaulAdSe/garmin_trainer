"""Supabase/PostgreSQL database adapter implementation.

This adapter provides PostgreSQL-compatible database access via Supabase,
implementing the DatabaseAdapter interface for seamless backend switching.

PostgreSQL/Supabase-Specific Considerations:

Syntax Differences from SQLite:
    +--------------------------+----------------------------+
    | SQLite                   | PostgreSQL                 |
    +--------------------------+----------------------------+
    | INTEGER PRIMARY KEY      | SERIAL PRIMARY KEY         |
    | AUTOINCREMENT            | SERIAL or BIGSERIAL        |
    | TEXT                     | TEXT or VARCHAR(n)         |
    | REAL                     | DOUBLE PRECISION           |
    | INTEGER (boolean)        | BOOLEAN                    |
    | CURRENT_TIMESTAMP        | NOW() or CURRENT_TIMESTAMP |
    | INSERT OR REPLACE        | INSERT ... ON CONFLICT     |
    | datetime('now')          | NOW()                      |
    | date('now')              | CURRENT_DATE               |
    | strftime('%Y-%m-%d', ..) | TO_CHAR(date, 'YYYY-MM-DD')|
    +--------------------------+----------------------------+

Supabase Features:
    - Row-Level Security (RLS) for multi-tenant isolation
    - Built-in Auth with JWT tokens
    - Realtime subscriptions
    - Edge Functions for serverless compute
    - Auto-generated REST APIs
    - Connection pooling via PgBouncer

Environment Variables Required:
    SUPABASE_URL          - Project URL (https://xxx.supabase.co)
    SUPABASE_ANON_KEY     - Anonymous/public key for client
    SUPABASE_SERVICE_KEY  - Service role key for backend (bypasses RLS)

See DATABASE_SCALING_PLAN.md for the full migration strategy.
"""

import os
import time
from contextlib import contextmanager
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from . import (
    DatabaseAdapter,
    ActivityMetricsData,
    FitnessMetricsData,
    UserProfileData,
)


# Supabase client will be imported conditionally
# to avoid import errors when supabase package is not installed
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = None


class SupabaseAdapter(DatabaseAdapter):
    """Supabase/PostgreSQL implementation of the DatabaseAdapter interface.

    This adapter provides:
    - Full PostgreSQL compatibility via Supabase client
    - Row-Level Security (RLS) for multi-tenant data isolation
    - Connection pooling handled by Supabase
    - JWT-based authentication support

    Usage:
        # Initialize with environment variables
        adapter = SupabaseAdapter()

        # Or with explicit credentials
        adapter = SupabaseAdapter(
            url="https://xxx.supabase.co",
            key="your-service-key"
        )

        # Multi-tenant query (RLS automatically filters by user)
        activities = adapter.get_activities_range(
            "2024-01-01", "2024-01-31",
            user_id="auth-user-uuid"
        )

    Note:
        This is currently a placeholder implementation. The actual Supabase
        integration will be completed during the production migration phase.
        See DATABASE_SCALING_PLAN.md for details.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        key: Optional[str] = None,
        use_service_key: bool = True
    ):
        """Initialize Supabase adapter.

        Args:
            url: Supabase project URL. If not provided, uses SUPABASE_URL env var.
            key: Supabase API key. If not provided, uses SUPABASE_SERVICE_KEY
                 or SUPABASE_ANON_KEY based on use_service_key.
            use_service_key: If True (default), use service key which bypasses RLS.
                            Set to False for client-side usage with RLS.

        Raises:
            ImportError: If supabase package is not installed.
            ValueError: If required environment variables are missing.
        """
        if not SUPABASE_AVAILABLE:
            raise ImportError(
                "supabase package is not installed. "
                "Install with: pip install supabase"
            )

        self.url = url or os.environ.get("SUPABASE_URL")
        if not self.url:
            raise ValueError(
                "Supabase URL not provided. Set SUPABASE_URL environment variable "
                "or pass url parameter."
            )

        if key:
            self.key = key
        elif use_service_key:
            self.key = os.environ.get("SUPABASE_SERVICE_KEY")
        else:
            self.key = os.environ.get("SUPABASE_ANON_KEY")

        if not self.key:
            raise ValueError(
                "Supabase API key not provided. Set SUPABASE_SERVICE_KEY or "
                "SUPABASE_ANON_KEY environment variable, or pass key parameter."
            )

        self._client: Optional[Client] = None
        self._in_transaction = False

    @property
    def client(self) -> Client:
        """Lazy-initialize Supabase client."""
        if self._client is None:
            self._client = create_client(self.url, self.key)
        return self._client

    def initialize(self) -> None:
        """Initialize the database connection.

        For Supabase, schema creation is handled via migrations or the
        Supabase Dashboard. This method verifies the connection works.

        Note: Unlike SQLite, we don't create tables here. Schema should be
        managed via Supabase migrations or the MCP tools.
        """
        # Verify connection by making a simple query
        try:
            self.client.table("users").select("id").limit(1).execute()
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Supabase: {e}")

    def close(self) -> None:
        """Close the Supabase client.

        Note: Supabase client handles connection pooling internally,
        but we should still cleanup for proper resource management.
        """
        self._client = None

    @contextmanager
    def transaction(self):
        """Context manager for database transactions.

        Note: Supabase REST API doesn't support explicit transactions.
        For transactional operations, use Supabase Edge Functions with
        direct PostgreSQL connection, or use the rpc() method to call
        PostgreSQL stored procedures.

        This is a placeholder that provides interface compatibility.
        For actual transaction support, implement a PostgreSQL stored
        procedure and call it via rpc().
        """
        # TODO: Implement actual transaction support via stored procedures
        # Example:
        #   self.client.rpc('begin_transaction').execute()
        #   try:
        #       yield self
        #       self.client.rpc('commit_transaction').execute()
        #   except:
        #       self.client.rpc('rollback_transaction').execute()
        #       raise

        self._in_transaction = True
        try:
            yield self
        finally:
            self._in_transaction = False

    # =========================================================================
    # Activity Metrics
    # =========================================================================

    def save_activity(
        self,
        activity: ActivityMetricsData,
        user_id: str = "default"
    ) -> ActivityMetricsData:
        """Save or update activity metrics.

        PostgreSQL Syntax:
            INSERT INTO activity_metrics (...)
            VALUES (...)
            ON CONFLICT (activity_id) DO UPDATE SET
                date = EXCLUDED.date,
                ...
                updated_at = NOW();

        Note: With RLS enabled, user_id filtering happens automatically
        based on the authenticated user's JWT token.
        """
        data = {
            "activity_id": activity.activity_id,
            "date": activity.date,  # PostgreSQL: Can use DATE type directly
            "start_time": activity.start_time,  # PostgreSQL: TIMESTAMPTZ
            "activity_type": activity.activity_type,
            "activity_name": activity.activity_name,
            "hrss": activity.hrss,  # PostgreSQL: DOUBLE PRECISION
            "trimp": activity.trimp,
            "avg_hr": activity.avg_hr,
            "max_hr": activity.max_hr,
            "duration_min": activity.duration_min,
            "distance_km": activity.distance_km,
            "pace_sec_per_km": activity.pace_sec_per_km,
            "zone1_pct": activity.zone1_pct,
            "zone2_pct": activity.zone2_pct,
            "zone3_pct": activity.zone3_pct,
            "zone4_pct": activity.zone4_pct,
            "zone5_pct": activity.zone5_pct,
            "sport_type": activity.sport_type,
            "avg_power": activity.avg_power,
            "max_power": activity.max_power,
            "normalized_power": activity.normalized_power,
            "tss": activity.tss,
            "intensity_factor": activity.intensity_factor,
            "variability_index": activity.variability_index,
            "avg_speed_kmh": activity.avg_speed_kmh,
            "elevation_gain_m": activity.elevation_gain_m,
            "cadence": activity.cadence,
            "user_id": user_id,  # Multi-tenant: Store user_id
            # PostgreSQL: updated_at handled by trigger or NOW()
        }

        # Supabase upsert (PostgreSQL ON CONFLICT)
        result = self.client.table("activity_metrics").upsert(
            data,
            on_conflict="activity_id"  # Primary key for conflict detection
        ).execute()

        activity.updated_at = datetime.utcnow().isoformat()
        activity.user_id = user_id
        return activity

    def get_activity(
        self,
        activity_id: str,
        user_id: str = "default"
    ) -> Optional[ActivityMetricsData]:
        """Get a single activity by ID.

        Note: With RLS enabled, the query automatically filters by
        the authenticated user. The user_id parameter is used for
        explicit filtering when using service key (bypasses RLS).
        """
        query = self.client.table("activity_metrics").select("*").eq(
            "activity_id", activity_id
        )

        # If using service key, add explicit user filter
        # (RLS would handle this automatically with anon key)
        query = query.eq("user_id", user_id)

        result = query.single().execute()

        if result.data:
            return self._dict_to_activity(result.data)
        return None

    def get_activities_range(
        self,
        start_date: str,
        end_date: str,
        user_id: str = "default",
        activity_type: Optional[str] = None,
        sport_type: Optional[str] = None
    ) -> List[ActivityMetricsData]:
        """Get activities within a date range.

        PostgreSQL date comparison works directly with DATE type:
            WHERE date >= '2024-01-01' AND date <= '2024-01-31'
        """
        query = self.client.table("activity_metrics").select("*").gte(
            "date", start_date
        ).lte("date", end_date).eq("user_id", user_id)

        if activity_type:
            query = query.eq("activity_type", activity_type)

        if sport_type:
            query = query.eq("sport_type", sport_type)

        # PostgreSQL: ORDER BY date DESC, activity_id
        query = query.order("date", desc=True).order("activity_id")

        result = query.execute()
        return [self._dict_to_activity(row) for row in result.data]

    def get_activities_paginated(
        self,
        user_id: str = "default",
        page: int = 1,
        page_size: int = 20,
        activity_type: Optional[str] = None,
        sport_type: Optional[str] = None
    ) -> Tuple[List[ActivityMetricsData], int]:
        """Get paginated activities with total count.

        PostgreSQL pagination:
            SELECT * FROM activity_metrics
            ORDER BY date DESC
            LIMIT 20 OFFSET 0;

        Supabase provides range() for LIMIT/OFFSET:
            .range(0, 19)  # First 20 items (0-indexed, inclusive)
        """
        # Calculate range for Supabase (0-indexed, inclusive)
        start = (page - 1) * page_size
        end = start + page_size - 1

        # Build query
        query = self.client.table("activity_metrics").select(
            "*",
            count="exact"  # Get total count with response
        ).eq("user_id", user_id)

        if activity_type:
            query = query.eq("activity_type", activity_type)

        if sport_type:
            query = query.eq("sport_type", sport_type)

        # Order and paginate
        query = query.order("date", desc=True).order("activity_id").range(start, end)

        result = query.execute()

        activities = [self._dict_to_activity(row) for row in result.data]
        total = result.count or 0

        return activities, total

    def delete_activity(
        self,
        activity_id: str,
        user_id: str = "default"
    ) -> bool:
        """Delete an activity by ID."""
        result = self.client.table("activity_metrics").delete().eq(
            "activity_id", activity_id
        ).eq("user_id", user_id).execute()

        return len(result.data) > 0

    def _dict_to_activity(self, data: Dict[str, Any]) -> ActivityMetricsData:
        """Convert a Supabase response dict to ActivityMetricsData."""
        return ActivityMetricsData(
            activity_id=data.get("activity_id", ""),
            date=data.get("date", ""),
            start_time=data.get("start_time"),
            activity_type=data.get("activity_type"),
            activity_name=data.get("activity_name"),
            hrss=data.get("hrss"),
            trimp=data.get("trimp"),
            avg_hr=data.get("avg_hr"),
            max_hr=data.get("max_hr"),
            duration_min=data.get("duration_min"),
            distance_km=data.get("distance_km"),
            pace_sec_per_km=data.get("pace_sec_per_km"),
            zone1_pct=data.get("zone1_pct"),
            zone2_pct=data.get("zone2_pct"),
            zone3_pct=data.get("zone3_pct"),
            zone4_pct=data.get("zone4_pct"),
            zone5_pct=data.get("zone5_pct"),
            sport_type=data.get("sport_type"),
            avg_power=data.get("avg_power"),
            max_power=data.get("max_power"),
            normalized_power=data.get("normalized_power"),
            tss=data.get("tss"),
            intensity_factor=data.get("intensity_factor"),
            variability_index=data.get("variability_index"),
            avg_speed_kmh=data.get("avg_speed_kmh"),
            elevation_gain_m=data.get("elevation_gain_m"),
            cadence=data.get("cadence"),
            user_id=data.get("user_id"),
            updated_at=data.get("updated_at"),
        )

    # =========================================================================
    # Fitness Metrics
    # =========================================================================

    def save_fitness_metrics(
        self,
        metrics: FitnessMetricsData,
        user_id: str = "default"
    ) -> FitnessMetricsData:
        """Save or update daily fitness metrics.

        PostgreSQL Syntax:
            INSERT INTO fitness_metrics (date, daily_load, ...)
            VALUES ('2024-01-15', 85.5, ...)
            ON CONFLICT (date, user_id) DO UPDATE SET
                daily_load = EXCLUDED.daily_load,
                updated_at = NOW();
        """
        data = {
            "date": metrics.date,
            "daily_load": metrics.daily_load,
            "ctl": metrics.ctl,
            "atl": metrics.atl,
            "tsb": metrics.tsb,
            "acwr": metrics.acwr,
            "risk_zone": metrics.risk_zone,
            "user_id": user_id,
        }

        self.client.table("fitness_metrics").upsert(
            data,
            on_conflict="date,user_id"  # Composite key for multi-tenant
        ).execute()

        metrics.updated_at = datetime.utcnow().isoformat()
        metrics.user_id = user_id
        return metrics

    def get_fitness_metrics(
        self,
        date_str: str,
        user_id: str = "default"
    ) -> Optional[FitnessMetricsData]:
        """Get fitness metrics for a specific date."""
        result = self.client.table("fitness_metrics").select("*").eq(
            "date", date_str
        ).eq("user_id", user_id).single().execute()

        if result.data:
            return self._dict_to_fitness(result.data)
        return None

    def get_fitness_range(
        self,
        start_date: str,
        end_date: str,
        user_id: str = "default"
    ) -> List[FitnessMetricsData]:
        """Get fitness metrics for a date range."""
        result = self.client.table("fitness_metrics").select("*").gte(
            "date", start_date
        ).lte("date", end_date).eq("user_id", user_id).order(
            "date", desc=True
        ).execute()

        return [self._dict_to_fitness(row) for row in result.data]

    def get_latest_fitness_metrics(
        self,
        user_id: str = "default"
    ) -> Optional[FitnessMetricsData]:
        """Get the most recent fitness metrics."""
        result = self.client.table("fitness_metrics").select("*").eq(
            "user_id", user_id
        ).order("date", desc=True).limit(1).execute()

        if result.data:
            return self._dict_to_fitness(result.data[0])
        return None

    def _dict_to_fitness(self, data: Dict[str, Any]) -> FitnessMetricsData:
        """Convert a Supabase response dict to FitnessMetricsData."""
        return FitnessMetricsData(
            date=data.get("date", ""),
            daily_load=data.get("daily_load", 0.0),
            ctl=data.get("ctl", 0.0),
            atl=data.get("atl", 0.0),
            tsb=data.get("tsb", 0.0),
            acwr=data.get("acwr", 0.0),
            risk_zone=data.get("risk_zone", ""),
            user_id=data.get("user_id"),
            updated_at=data.get("updated_at"),
        )

    # =========================================================================
    # User Profile
    # =========================================================================

    def get_user_profile(
        self,
        user_id: str = "default"
    ) -> UserProfileData:
        """Get user profile with HR zones and settings.

        Note: In production, this would query user_profiles table
        which extends Supabase auth.users.
        """
        try:
            result = self.client.table("user_profiles").select("*").eq(
                "id", user_id
            ).single().execute()

            if result.data:
                return UserProfileData(
                    id=result.data.get("id", user_id),
                    max_hr=result.data.get("max_hr"),
                    rest_hr=result.data.get("rest_hr"),
                    threshold_hr=result.data.get("threshold_hr"),
                    gender=result.data.get("gender", "male"),
                    age=result.data.get("age"),
                    weight_kg=result.data.get("weight_kg"),
                    timezone=result.data.get("timezone", "UTC"),
                    updated_at=result.data.get("updated_at"),
                )
        except Exception:
            pass

        # Return defaults if no profile exists
        return UserProfileData(
            id=user_id,
            max_hr=185,
            rest_hr=55,
            threshold_hr=165,
            gender="male",
            age=30,
            weight_kg=None,
        )

    def save_user_profile(
        self,
        profile: UserProfileData
    ) -> UserProfileData:
        """Save or update user profile.

        PostgreSQL Syntax:
            INSERT INTO user_profiles (id, max_hr, ...)
            VALUES ('user-uuid', 185, ...)
            ON CONFLICT (id) DO UPDATE SET
                max_hr = EXCLUDED.max_hr,
                updated_at = NOW();
        """
        data = {
            "id": profile.id,
            "max_hr": profile.max_hr,
            "rest_hr": profile.rest_hr,
            "threshold_hr": profile.threshold_hr,
            "gender": profile.gender,
            "age": profile.age,
            "weight_kg": profile.weight_kg,
            "timezone": profile.timezone,
        }

        self.client.table("user_profiles").upsert(
            data,
            on_conflict="id"
        ).execute()

        profile.updated_at = datetime.utcnow().isoformat()
        return profile

    # =========================================================================
    # Statistics and Aggregations
    # =========================================================================

    def get_daily_load_totals(
        self,
        start_date: str,
        end_date: str,
        user_id: str = "default"
    ) -> List[Dict[str, Any]]:
        """Get aggregated daily load totals.

        For complex aggregations, use a PostgreSQL stored procedure
        or Supabase Edge Function:

            CREATE OR REPLACE FUNCTION get_daily_load_totals(
                p_user_id UUID,
                p_start_date DATE,
                p_end_date DATE
            ) RETURNS TABLE (
                date DATE,
                total_hrss DOUBLE PRECISION,
                total_trimp DOUBLE PRECISION,
                activity_count BIGINT
            ) AS $$
            BEGIN
                RETURN QUERY
                SELECT
                    am.date,
                    SUM(am.hrss) as total_hrss,
                    SUM(am.trimp) as total_trimp,
                    COUNT(*) as activity_count
                FROM activity_metrics am
                WHERE am.user_id = p_user_id
                    AND am.date >= p_start_date
                    AND am.date <= p_end_date
                GROUP BY am.date
                ORDER BY am.date;
            END;
            $$ LANGUAGE plpgsql;

        Call via: self.client.rpc('get_daily_load_totals', {...}).execute()
        """
        # For now, use client-side aggregation (not ideal for performance)
        # TODO: Implement as PostgreSQL stored procedure
        result = self.client.table("activity_metrics").select(
            "date, hrss, trimp"
        ).gte("date", start_date).lte("date", end_date).eq(
            "user_id", user_id
        ).order("date").execute()

        # Client-side aggregation (temporary solution)
        daily_totals: Dict[str, Dict[str, Any]] = {}
        for row in result.data:
            date = row["date"]
            if date not in daily_totals:
                daily_totals[date] = {
                    "date": date,
                    "total_hrss": 0.0,
                    "total_trimp": 0.0,
                    "activity_count": 0,
                }
            daily_totals[date]["total_hrss"] += row.get("hrss") or 0
            daily_totals[date]["total_trimp"] += row.get("trimp") or 0
            daily_totals[date]["activity_count"] += 1

        return list(daily_totals.values())

    def get_stats(
        self,
        user_id: str = "default"
    ) -> Dict[str, Any]:
        """Get database statistics for a user.

        PostgreSQL aggregation:
            SELECT
                COUNT(*) as activity_count,
                MIN(date) as min_date,
                MAX(date) as max_date
            FROM activity_metrics
            WHERE user_id = 'xxx';
        """
        # Activity stats
        activity_result = self.client.table("activity_metrics").select(
            "date",
            count="exact"
        ).eq("user_id", user_id).order("date").execute()

        activity_count = activity_result.count or 0
        activity_dates = [r["date"] for r in activity_result.data] if activity_result.data else []

        # Fitness stats
        fitness_result = self.client.table("fitness_metrics").select(
            "date",
            count="exact"
        ).eq("user_id", user_id).order("date").execute()

        fitness_count = fitness_result.count or 0
        fitness_dates = [r["date"] for r in fitness_result.data] if fitness_result.data else []

        return {
            "backend": "supabase",
            "url": self.url,
            "total_activities": activity_count,
            "total_fitness_days": fitness_count,
            "activity_date_range": {
                "earliest": activity_dates[0] if activity_dates else None,
                "latest": activity_dates[-1] if activity_dates else None,
            },
            "fitness_date_range": {
                "earliest": fitness_dates[0] if fitness_dates else None,
                "latest": fitness_dates[-1] if fitness_dates else None,
            },
        }

    # =========================================================================
    # Health Check
    # =========================================================================

    def health_check(self) -> Dict[str, Any]:
        """Check database health and connectivity.

        Executes a simple query to verify Supabase connection.
        """
        start_time = time.time()
        try:
            # Simple health check query
            # PostgreSQL: SELECT version()
            result = self.client.rpc("pg_version").execute()
            version = result.data if result.data else "unknown"

            latency_ms = (time.time() - start_time) * 1000

            return {
                "healthy": True,
                "backend": "supabase",
                "version": version,
                "latency_ms": round(latency_ms, 2),
                "details": {
                    "url": self.url,
                    "connection_pooling": True,
                    "rls_enabled": True,
                },
            }

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return {
                "healthy": False,
                "backend": "supabase",
                "version": None,
                "latency_ms": round(latency_ms, 2),
                "details": {
                    "error": str(e),
                    "url": self.url,
                },
            }


# =============================================================================
# PostgreSQL Schema Migration Notes
# =============================================================================
"""
When migrating from SQLite to PostgreSQL, the following schema changes are needed:

1. Primary Key Types:
   SQLite:   activity_id TEXT PRIMARY KEY
   Postgres: activity_id TEXT PRIMARY KEY  (or UUID PRIMARY KEY DEFAULT gen_random_uuid())

2. Auto-increment:
   SQLite:   id INTEGER PRIMARY KEY AUTOINCREMENT
   Postgres: id SERIAL PRIMARY KEY  (or BIGSERIAL for large tables)

3. Boolean Types:
   SQLite:   is_active INTEGER DEFAULT 1
   Postgres: is_active BOOLEAN DEFAULT TRUE

4. Timestamp Handling:
   SQLite:   created_at TEXT DEFAULT CURRENT_TIMESTAMP
   Postgres: created_at TIMESTAMPTZ DEFAULT NOW()

5. Date Types:
   SQLite:   date TEXT
   Postgres: date DATE

6. Multi-tenant Indexes:
   Add user_id to all tables and create composite indexes:
   CREATE INDEX idx_activity_user_date ON activity_metrics(user_id, date DESC);

7. Row-Level Security (RLS):
   ALTER TABLE activity_metrics ENABLE ROW LEVEL SECURITY;

   CREATE POLICY "Users can view own activities"
       ON activity_metrics FOR SELECT
       USING (auth.uid() = user_id);

   CREATE POLICY "Users can insert own activities"
       ON activity_metrics FOR INSERT
       WITH CHECK (auth.uid() = user_id);

8. Upsert Syntax:
   SQLite:   INSERT OR REPLACE INTO ...
   Postgres: INSERT INTO ... ON CONFLICT (key) DO UPDATE SET ...

See training-analyzer/scripts/migrate_to_supabase.py for the migration script.
"""
