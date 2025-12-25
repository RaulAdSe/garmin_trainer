"""Tests for activity enrichment service."""

import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from training_analyzer.services.enrichment import (
    EnrichmentService,
    get_n8n_db_path,
)
from training_analyzer.db.database import TrainingDatabase, UserProfile


@pytest.fixture
def temp_training_db():
    """Create a temporary training database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    db = TrainingDatabase(db_path)
    yield db

    # Cleanup
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture
def mock_profile():
    """Create a mock user profile."""
    return UserProfile(
        id=1,
        max_hr=185,
        rest_hr=55,
        threshold_hr=165,
        gender="male",
        age=30,
        weight_kg=70.0,
        updated_at="2024-01-01T00:00:00",
    )


class TestEnrichmentServiceInit:
    """Tests for enrichment service initialization."""

    def test_creates_with_training_db(self, temp_training_db):
        """Should create service with provided training db."""
        service = EnrichmentService(training_db=temp_training_db)
        assert service.training_db == temp_training_db

    def test_creates_default_training_db(self):
        """Should create default training db if not provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["TRAINING_DB_PATH"] = os.path.join(tmpdir, "test.db")
            try:
                service = EnrichmentService()
                assert service.training_db is not None
            finally:
                del os.environ["TRAINING_DB_PATH"]


class TestN8NDbPath:
    """Tests for n8n database path detection."""

    def test_env_var_override(self, monkeypatch):
        """Should use N8N_DB_PATH env var if set and exists."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            monkeypatch.setenv("N8N_DB_PATH", temp_path)
            path = get_n8n_db_path()
            assert path == Path(temp_path)
        finally:
            os.unlink(temp_path)

    def test_env_var_nonexistent(self, monkeypatch):
        """Should return None if N8N_DB_PATH doesn't exist."""
        monkeypatch.setenv("N8N_DB_PATH", "/nonexistent/path.db")
        path = get_n8n_db_path()
        assert path is None


class TestEnrichActivity:
    """Tests for single activity enrichment."""

    def test_enrich_complete_activity(self, temp_training_db, mock_profile):
        """Should enrich activity with all HR data."""
        service = EnrichmentService(training_db=temp_training_db)

        raw_activity = {
            "activity_id": "12345",
            "start_time": "2024-01-15T08:30:00",
            "activity_type": "running",
            "activity_name": "Morning Run",
            "avg_hr": 150,
            "max_hr": 175,
            "duration_s": 2700,  # 45 minutes
            "distance_m": 8500,  # 8.5 km
        }

        result = service.enrich_activity(raw_activity, mock_profile)

        assert result is not None
        assert result.activity_id == "12345"
        assert result.date == "2024-01-15"
        assert result.activity_type == "running"
        assert result.hrss is not None
        assert result.hrss > 0
        assert result.trimp is not None
        assert result.trimp > 0
        assert result.duration_min == 45.0
        assert result.distance_km == 8.5
        assert result.pace_sec_per_km is not None

    def test_enrich_activity_no_hr(self, temp_training_db, mock_profile):
        """Should handle activity without HR data."""
        service = EnrichmentService(training_db=temp_training_db)

        raw_activity = {
            "activity_id": "12345",
            "start_time": "2024-01-15T08:30:00",
            "activity_type": "running",
            "duration_s": 2700,
            "distance_m": 8500,
        }

        result = service.enrich_activity(raw_activity, mock_profile)

        assert result is not None
        assert result.activity_id == "12345"
        assert result.hrss is None  # No HRSS without HR
        assert result.trimp is None  # No TRIMP without HR
        assert result.duration_min == 45.0

    def test_enrich_activity_no_id(self, temp_training_db, mock_profile):
        """Should return None for activity without ID."""
        service = EnrichmentService(training_db=temp_training_db)

        raw_activity = {
            "start_time": "2024-01-15T08:30:00",
            "activity_type": "running",
        }

        result = service.enrich_activity(raw_activity, mock_profile)
        assert result is None

    def test_enrich_activity_date_parsing(self, temp_training_db, mock_profile):
        """Should correctly parse various date formats."""
        service = EnrichmentService(training_db=temp_training_db)

        # ISO format with T
        activity1 = {
            "activity_id": "1",
            "start_time": "2024-01-15T08:30:00",
        }
        result1 = service.enrich_activity(activity1, mock_profile)
        assert result1.date == "2024-01-15"

        # Space-separated format
        activity2 = {
            "activity_id": "2",
            "start_time": "2024-01-16 10:00:00",
        }
        result2 = service.enrich_activity(activity2, mock_profile)
        assert result2.date == "2024-01-16"

    def test_enrich_activity_pace_calculation(self, temp_training_db, mock_profile):
        """Should correctly calculate pace."""
        service = EnrichmentService(training_db=temp_training_db)

        raw_activity = {
            "activity_id": "12345",
            "start_time": "2024-01-15T08:30:00",
            "duration_s": 3000,  # 50 minutes = 3000 seconds
            "distance_m": 10000,  # 10 km
        }

        result = service.enrich_activity(raw_activity, mock_profile)

        # Pace should be 300 seconds per km (5:00 min/km)
        assert result.pace_sec_per_km == 300


class TestEnrichActivities:
    """Tests for batch activity enrichment."""

    def test_enrich_activities_stores_results(self, temp_training_db):
        """Should store enriched activities in database."""
        service = EnrichmentService(training_db=temp_training_db)

        # Mock the raw activities fetch
        mock_activities = [
            {
                "activity_id": "1",
                "start_time": "2024-01-15T08:30:00",
                "activity_type": "running",
                "avg_hr": 150,
                "max_hr": 175,
                "duration_s": 2700,
                "distance_m": 8500,
            },
            {
                "activity_id": "2",
                "start_time": "2024-01-16T09:00:00",
                "activity_type": "cycling",
                "avg_hr": 140,
                "max_hr": 165,
                "duration_s": 3600,
                "distance_m": 25000,
            },
        ]

        with patch.object(service, "get_raw_activities", return_value=mock_activities):
            processed, success = service.enrich_activities(days=7)

        assert processed == 2
        assert success == 2

        # Verify stored in database
        activity1 = temp_training_db.get_activity_metrics("1")
        assert activity1 is not None
        assert activity1.activity_type == "running"


class TestFitnessCalculation:
    """Tests for fitness metrics calculation from activities."""

    def test_calculate_fitness_from_activities(self, temp_training_db):
        """Should calculate fitness metrics from enriched activities."""
        from datetime import datetime, timedelta

        service = EnrichmentService(training_db=temp_training_db)

        # Add some activities with known loads - use recent dates
        from training_analyzer.db.database import ActivityMetrics

        base_date = datetime.now().date()
        test_date = None

        for i in range(10):
            activity_date = (base_date - timedelta(days=20-i)).isoformat()
            if i == 5:
                test_date = activity_date  # Save a date to check later
            metrics = ActivityMetrics(
                activity_id=f"act_{i}",
                date=activity_date,
                activity_type="running",
                activity_name=f"Run {i}",
                hrss=50.0,  # Consistent load
                trimp=70.0,
                avg_hr=150,
                max_hr=175,
                duration_min=45.0,
                distance_km=8.5,
                pace_sec_per_km=318.0,
                zone1_pct=None,
                zone2_pct=None,
                zone3_pct=None,
                zone4_pct=None,
                zone5_pct=None,
            )
            temp_training_db.save_activity_metrics(metrics)

        days_calculated = service.calculate_fitness_from_activities(
            days=30, load_metric="hrss"
        )

        assert days_calculated > 0

        # Verify fitness metrics exist
        fitness = temp_training_db.get_fitness_metrics(test_date)
        assert fitness is not None
        assert fitness.daily_load == 50.0

    def test_calculate_fitness_with_trimp(self, temp_training_db):
        """Should use TRIMP when specified."""
        from datetime import datetime, timedelta

        service = EnrichmentService(training_db=temp_training_db)

        from training_analyzer.db.database import ActivityMetrics

        # Use a recent date
        test_date = (datetime.now().date() - timedelta(days=5)).isoformat()

        metrics = ActivityMetrics(
            activity_id="1",
            date=test_date,
            activity_type="running",
            activity_name="Run",
            hrss=50.0,
            trimp=100.0,  # Different from HRSS
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
        temp_training_db.save_activity_metrics(metrics)

        service.calculate_fitness_from_activities(days=30, load_metric="trimp")

        fitness = temp_training_db.get_fitness_metrics(test_date)
        assert fitness is not None
        assert fitness.daily_load == 100.0  # Should use TRIMP


class TestFullEnrichment:
    """Tests for full enrichment pipeline."""

    def test_run_full_enrichment(self, temp_training_db):
        """Should run complete enrichment pipeline."""
        service = EnrichmentService(training_db=temp_training_db)

        mock_activities = [
            {
                "activity_id": "1",
                "start_time": "2024-01-15T08:30:00",
                "activity_type": "running",
                "avg_hr": 150,
                "max_hr": 175,
                "duration_s": 2700,
                "distance_m": 8500,
            },
        ]

        with patch.object(service, "get_raw_activities", return_value=mock_activities):
            result = service.run_full_enrichment(days=30)

        assert "activities_processed" in result
        assert "activities_enriched" in result
        assert "fitness_days_calculated" in result
        assert result["activities_processed"] == 1
        assert result["activities_enriched"] == 1
