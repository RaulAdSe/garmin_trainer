"""Tests for training database."""

import os
import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from training_analyzer.db.database import (
    TrainingDatabase,
    UserProfile,
    ActivityMetrics,
    DailyFitnessMetrics,
    get_default_db_path,
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    db = TrainingDatabase(db_path)
    yield db

    # Cleanup
    try:
        os.unlink(db_path)
    except OSError:
        pass


class TestDatabaseInit:
    """Tests for database initialization."""

    def test_creates_database(self, temp_db):
        """Database should be created on init."""
        assert temp_db.db_path.exists()

    def test_creates_tables(self, temp_db):
        """Required tables should be created."""
        with temp_db._get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = {row["name"] for row in cursor.fetchall()}

        assert "user_profile" in tables
        assert "fitness_metrics" in tables
        assert "activity_metrics" in tables

    def test_default_profile_created(self, temp_db):
        """Default user profile should be created."""
        profile = temp_db.get_user_profile()
        assert profile.max_hr == 185
        assert profile.rest_hr == 55
        assert profile.threshold_hr == 165


class TestUserProfile:
    """Tests for user profile operations."""

    def test_get_default_profile(self, temp_db):
        """Should return default profile."""
        profile = temp_db.get_user_profile()

        assert isinstance(profile, UserProfile)
        assert profile.id == 1

    def test_update_profile_single_field(self, temp_db):
        """Should update single field while preserving others."""
        original = temp_db.get_user_profile()

        updated = temp_db.update_user_profile(max_hr=190)

        assert updated.max_hr == 190
        assert updated.rest_hr == original.rest_hr

    def test_update_profile_multiple_fields(self, temp_db):
        """Should update multiple fields."""
        updated = temp_db.update_user_profile(
            max_hr=190,
            rest_hr=50,
            age=35,
            gender="female",
        )

        assert updated.max_hr == 190
        assert updated.rest_hr == 50
        assert updated.age == 35
        assert updated.gender == "female"

    def test_profile_to_dict(self, temp_db):
        """Profile should serialize to dict."""
        profile = temp_db.get_user_profile()
        d = profile.to_dict()

        assert "max_hr" in d
        assert "rest_hr" in d
        assert "threshold_hr" in d


class TestActivityMetrics:
    """Tests for activity metrics operations."""

    def test_save_and_get_activity(self, temp_db):
        """Should save and retrieve activity metrics."""
        metrics = ActivityMetrics(
            activity_id="12345",
            date="2024-01-15",
            activity_type="running",
            activity_name="Morning Run",
            hrss=85.5,
            trimp=120.3,
            avg_hr=150,
            max_hr=175,
            duration_min=45.0,
            distance_km=8.5,
            pace_sec_per_km=318.0,
            zone1_pct=10.0,
            zone2_pct=50.0,
            zone3_pct=25.0,
            zone4_pct=10.0,
            zone5_pct=5.0,
        )

        temp_db.save_activity_metrics(metrics)
        retrieved = temp_db.get_activity_metrics("12345")

        assert retrieved is not None
        assert retrieved.activity_id == "12345"
        assert retrieved.hrss == 85.5
        assert retrieved.date == "2024-01-15"

    def test_get_nonexistent_activity(self, temp_db):
        """Should return None for nonexistent activity."""
        result = temp_db.get_activity_metrics("nonexistent")
        assert result is None

    def test_get_activities_for_date(self, temp_db):
        """Should get all activities for a date."""
        # Add multiple activities for same date
        for i in range(3):
            metrics = ActivityMetrics(
                activity_id=f"activity_{i}",
                date="2024-01-15",
                activity_type="running",
                activity_name=f"Run {i}",
                hrss=50.0 + i * 10,
                trimp=None,
                avg_hr=None,
                max_hr=None,
                duration_min=None,
                distance_km=None,
                pace_sec_per_km=None,
                zone1_pct=None,
                zone2_pct=None,
                zone3_pct=None,
                zone4_pct=None,
                zone5_pct=None,
            )
            temp_db.save_activity_metrics(metrics)

        activities = temp_db.get_activities_for_date("2024-01-15")
        assert len(activities) == 3

    def test_get_activities_range(self, temp_db):
        """Should get activities in date range."""
        dates = ["2024-01-10", "2024-01-15", "2024-01-20", "2024-01-25"]
        for i, d in enumerate(dates):
            metrics = ActivityMetrics(
                activity_id=f"activity_{i}",
                date=d,
                activity_type="running",
                activity_name=f"Run on {d}",
                hrss=50.0,
                trimp=None,
                avg_hr=None,
                max_hr=None,
                duration_min=None,
                distance_km=None,
                pace_sec_per_km=None,
                zone1_pct=None,
                zone2_pct=None,
                zone3_pct=None,
                zone4_pct=None,
                zone5_pct=None,
            )
            temp_db.save_activity_metrics(metrics)

        # Get range that includes middle two
        activities = temp_db.get_activities_range("2024-01-15", "2024-01-20")
        assert len(activities) == 2

    def test_activity_upsert(self, temp_db):
        """Should update existing activity."""
        metrics = ActivityMetrics(
            activity_id="12345",
            date="2024-01-15",
            activity_type="running",
            activity_name="Morning Run",
            hrss=85.5,
            trimp=None,
            avg_hr=150,
            max_hr=None,
            duration_min=None,
            distance_km=None,
            pace_sec_per_km=None,
            zone1_pct=None,
            zone2_pct=None,
            zone3_pct=None,
            zone4_pct=None,
            zone5_pct=None,
        )
        temp_db.save_activity_metrics(metrics)

        # Update with new values
        metrics.hrss = 90.0
        metrics.trimp = 130.0
        temp_db.save_activity_metrics(metrics)

        retrieved = temp_db.get_activity_metrics("12345")
        assert retrieved.hrss == 90.0
        assert retrieved.trimp == 130.0

    def test_activity_to_dict(self):
        """Activity should serialize to dict."""
        metrics = ActivityMetrics(
            activity_id="12345",
            date="2024-01-15",
            activity_type="running",
            activity_name="Test",
            hrss=50.0,
            trimp=None,
            avg_hr=None,
            max_hr=None,
            duration_min=None,
            distance_km=None,
            pace_sec_per_km=None,
            zone1_pct=None,
            zone2_pct=None,
            zone3_pct=None,
            zone4_pct=None,
            zone5_pct=None,
        )
        d = metrics.to_dict()

        assert d["activity_id"] == "12345"
        assert d["hrss"] == 50.0


class TestFitnessMetrics:
    """Tests for fitness metrics operations."""

    def test_save_and_get_fitness(self, temp_db):
        """Should save and retrieve fitness metrics."""
        metrics = DailyFitnessMetrics(
            date="2024-01-15",
            daily_load=85.0,
            ctl=50.0,
            atl=70.0,
            tsb=-20.0,
            acwr=1.4,
            risk_zone="caution",
        )

        temp_db.save_fitness_metrics(metrics)
        retrieved = temp_db.get_fitness_metrics("2024-01-15")

        assert retrieved is not None
        assert retrieved.date == "2024-01-15"
        assert retrieved.ctl == 50.0
        assert retrieved.risk_zone == "caution"

    def test_get_nonexistent_fitness(self, temp_db):
        """Should return None for nonexistent date."""
        result = temp_db.get_fitness_metrics("2024-01-01")
        assert result is None

    def test_get_fitness_range(self, temp_db):
        """Should get fitness metrics in date range."""
        for i in range(10, 20):
            metrics = DailyFitnessMetrics(
                date=f"2024-01-{i}",
                daily_load=50.0,
                ctl=40.0 + i,
                atl=60.0 + i,
                tsb=-20.0,
                acwr=1.2,
                risk_zone="optimal",
            )
            temp_db.save_fitness_metrics(metrics)

        # Get 5 days
        results = temp_db.get_fitness_range("2024-01-12", "2024-01-16")
        assert len(results) == 5

    def test_get_latest_fitness(self, temp_db):
        """Should get most recent fitness metrics."""
        dates = ["2024-01-10", "2024-01-15", "2024-01-20"]
        for d in dates:
            metrics = DailyFitnessMetrics(
                date=d,
                daily_load=50.0,
                ctl=50.0,
                atl=50.0,
                tsb=0.0,
                acwr=1.0,
                risk_zone="optimal",
            )
            temp_db.save_fitness_metrics(metrics)

        latest = temp_db.get_latest_fitness_metrics()
        assert latest.date == "2024-01-20"

    def test_get_latest_fitness_empty(self, temp_db):
        """Should return None when no fitness data."""
        latest = temp_db.get_latest_fitness_metrics()
        assert latest is None

    def test_fitness_to_dict(self):
        """Fitness metrics should serialize to dict."""
        metrics = DailyFitnessMetrics(
            date="2024-01-15",
            daily_load=85.0,
            ctl=50.0,
            atl=70.0,
            tsb=-20.0,
            acwr=1.4,
            risk_zone="caution",
        )
        d = metrics.to_dict()

        assert d["date"] == "2024-01-15"
        assert d["risk_zone"] == "caution"


class TestDailyLoadTotals:
    """Tests for daily load aggregation."""

    def test_get_daily_load_totals(self, temp_db):
        """Should aggregate daily loads from activities."""
        # Add multiple activities for same date
        for i in range(3):
            metrics = ActivityMetrics(
                activity_id=f"act_{i}",
                date="2024-01-15",
                activity_type="running",
                activity_name=f"Run {i}",
                hrss=30.0,  # Each 30, total 90
                trimp=40.0,  # Each 40, total 120
                avg_hr=None,
                max_hr=None,
                duration_min=None,
                distance_km=None,
                pace_sec_per_km=None,
                zone1_pct=None,
                zone2_pct=None,
                zone3_pct=None,
                zone4_pct=None,
                zone5_pct=None,
            )
            temp_db.save_activity_metrics(metrics)

        totals = temp_db.get_daily_load_totals("2024-01-01", "2024-01-31")

        assert len(totals) == 1
        assert totals[0]["date"] == "2024-01-15"
        assert totals[0]["total_hrss"] == 90.0
        assert totals[0]["total_trimp"] == 120.0
        assert totals[0]["activity_count"] == 3


class TestDatabaseStats:
    """Tests for database statistics."""

    def test_empty_stats(self, temp_db):
        """Should return stats for empty database."""
        stats = temp_db.get_stats()

        assert stats["total_activities"] == 0
        assert stats["total_fitness_days"] == 0
        assert stats["activity_date_range"]["earliest"] is None

    def test_stats_with_data(self, temp_db):
        """Should return correct stats with data."""
        # Add some activities
        for i in range(5):
            metrics = ActivityMetrics(
                activity_id=f"act_{i}",
                date=f"2024-01-{10+i}",
                activity_type="running",
                activity_name=f"Run {i}",
                hrss=50.0,
                trimp=None,
                avg_hr=None,
                max_hr=None,
                duration_min=None,
                distance_km=None,
                pace_sec_per_km=None,
                zone1_pct=None,
                zone2_pct=None,
                zone3_pct=None,
                zone4_pct=None,
                zone5_pct=None,
            )
            temp_db.save_activity_metrics(metrics)

        # Add some fitness metrics
        for i in range(3):
            metrics = DailyFitnessMetrics(
                date=f"2024-01-{10+i}",
                daily_load=50.0,
                ctl=50.0,
                atl=50.0,
                tsb=0.0,
                acwr=1.0,
                risk_zone="optimal",
            )
            temp_db.save_fitness_metrics(metrics)

        stats = temp_db.get_stats()

        assert stats["total_activities"] == 5
        assert stats["total_fitness_days"] == 3
        assert stats["activity_date_range"]["earliest"] == "2024-01-10"
        assert stats["activity_date_range"]["latest"] == "2024-01-14"


class TestDefaultDbPath:
    """Tests for default database path."""

    def test_env_var_override(self, monkeypatch):
        """Should use TRAINING_DB_PATH env var if set."""
        monkeypatch.setenv("TRAINING_DB_PATH", "/custom/path/training.db")
        path = get_default_db_path()
        assert path == Path("/custom/path/training.db")

    def test_default_path_format(self, monkeypatch):
        """Default path should be in training-analyzer directory."""
        monkeypatch.delenv("TRAINING_DB_PATH", raising=False)
        path = get_default_db_path()
        assert path.name == "training.db"
