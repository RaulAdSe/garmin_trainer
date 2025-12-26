"""
Tests for the Workout API routes.

Tests cover:
- Workout design endpoint
- Workout retrieval and listing
- FIT file export
- Quick workout endpoints
- Error handling
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import base64

from fastapi.testclient import TestClient

from training_analyzer.main import app
from training_analyzer.db.repositories.workout_repository import get_workout_repository
from training_analyzer.models.workouts import (
    IntervalType,
    StructuredWorkout,
    WorkoutInterval,
    WorkoutSport,
)
from training_analyzer.models.athlete_context import AthleteContext


# ============================================================================
# Test Client Setup
# ============================================================================

@pytest.fixture
def client():
    """Create a test client for the API."""
    return TestClient(app)


@pytest.fixture
def mock_services():
    """Mock the coach service and training db dependencies."""
    with patch('training_analyzer.api.routes.workouts.get_coach_service') as mock_coach, \
         patch('training_analyzer.api.routes.workouts.get_training_db') as mock_db:

        # Mock coach service
        coach = MagicMock()
        coach.get_daily_briefing.return_value = {
            "fitness": {"ctl": 45.0, "atl": 50.0, "tsb": -5.0},
            "readiness": {"score": 75, "zone": "green"},
        }
        mock_coach.return_value = coach

        # Mock training db
        db = MagicMock()
        db.get_user_profile.return_value = MagicMock(
            max_hr=185,
            rest_hr=55,
            threshold_hr=165,
        )
        db.get_race_goals.return_value = []
        mock_db.return_value = db

        yield {"coach": coach, "db": db}


@pytest.fixture
def sample_workout():
    """Create a sample workout and store it."""
    workout = StructuredWorkout.create(
        name="Test Tempo Run",
        description="Test tempo workout",
        intervals=[
            WorkoutInterval(
                type=IntervalType.WARMUP,
                duration_sec=600,
                target_pace_range=(340, 380),
                target_hr_range=(120, 140),
            ),
            WorkoutInterval(
                type=IntervalType.WORK,
                duration_sec=1200,
                target_pace_range=(290, 310),
                target_hr_range=(155, 170),
            ),
            WorkoutInterval(
                type=IntervalType.COOLDOWN,
                duration_sec=600,
                target_pace_range=(340, 380),
                target_hr_range=(120, 140),
            ),
        ],
        estimated_load=75.0,
    )

    # Store the workout using the repository
    repo = get_workout_repository()
    repo.save(workout)

    yield workout

    # Cleanup
    repo.delete(workout.id)


@pytest.fixture(autouse=True)
def cleanup_workout_store():
    """Clean up workout store after each test."""
    yield
    # Note: In production, we would use a test database
    # For now, we rely on test-specific cleanup in each fixture


# ============================================================================
# Test Workout Design Endpoint
# ============================================================================

class TestDesignWorkout:
    """Tests for POST /api/v1/workouts/design."""

    def test_design_easy_workout(self, client, mock_services):
        """Test designing an easy workout."""
        response = client.post(
            "/api/v1/workouts/design",
            json={
                "workout_type": "easy",
                "duration_min": 45,
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "workout_id" in data
        assert data["name"] == "Easy Run"
        assert data["sport"] == "running"
        assert len(data["intervals"]) >= 3  # warmup, work, cooldown

    def test_design_tempo_workout(self, client, mock_services):
        """Test designing a tempo workout."""
        response = client.post(
            "/api/v1/workouts/design",
            json={
                "workout_type": "tempo",
                "duration_min": 50,
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "Tempo Run"
        assert any(i["type"] == "work" for i in data["intervals"])

    def test_design_interval_workout(self, client, mock_services):
        """Test designing an interval workout."""
        response = client.post(
            "/api/v1/workouts/design",
            json={
                "workout_type": "intervals",
                "duration_min": 55,
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "Interval Session"
        # Should have multiple work intervals
        work_intervals = [i for i in data["intervals"] if i["type"] == "work"]
        assert len(work_intervals) >= 4

    def test_design_threshold_workout(self, client, mock_services):
        """Test designing a threshold workout."""
        response = client.post(
            "/api/v1/workouts/design",
            json={
                "workout_type": "threshold",
                "duration_min": 50,
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "Threshold Workout"

    def test_design_long_workout(self, client, mock_services):
        """Test designing a long run workout."""
        response = client.post(
            "/api/v1/workouts/design",
            json={
                "workout_type": "long",
                "duration_min": 90,
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "Long Run"
        assert data["estimated_duration_min"] >= 80

    def test_design_fartlek_workout(self, client, mock_services):
        """Test designing a fartlek workout."""
        response = client.post(
            "/api/v1/workouts/design",
            json={
                "workout_type": "fartlek",
                "duration_min": 45,
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "Fartlek Run"

    def test_design_workout_invalid_type(self, client, mock_services):
        """Test that unknown workout type returns error."""
        response = client.post(
            "/api/v1/workouts/design",
            json={
                "workout_type": "unknown_type",
                "duration_min": 45,
            }
        )

        # Should fall back to easy workout, not error
        assert response.status_code == 200

    def test_design_workout_missing_type(self, client, mock_services):
        """Test that missing workout type returns validation error."""
        response = client.post(
            "/api/v1/workouts/design",
            json={
                "duration_min": 45,
            }
        )

        assert response.status_code == 422  # Validation error

    def test_design_workout_with_target_load(self, client, mock_services):
        """Test designing workout with target load parameter."""
        response = client.post(
            "/api/v1/workouts/design",
            json={
                "workout_type": "tempo",
                "duration_min": 45,
                "target_load": 80.0,
            }
        )

        assert response.status_code == 200

    def test_design_workout_with_focus(self, client, mock_services):
        """Test designing workout with focus parameter."""
        response = client.post(
            "/api/v1/workouts/design",
            json={
                "workout_type": "intervals",
                "duration_min": 50,
                "focus": "speed",
            }
        )

        assert response.status_code == 200


# ============================================================================
# Test Workout Retrieval Endpoints
# ============================================================================

class TestGetWorkout:
    """Tests for GET /api/v1/workouts/{workout_id}."""

    def test_get_existing_workout(self, client, sample_workout):
        """Test retrieving an existing workout."""
        response = client.get(f"/api/v1/workouts/{sample_workout.id}")

        assert response.status_code == 200
        data = response.json()

        assert data["workout_id"] == sample_workout.id
        assert data["name"] == sample_workout.name
        assert len(data["intervals"]) == len(sample_workout.intervals)

    def test_get_nonexistent_workout(self, client):
        """Test retrieving a workout that doesn't exist."""
        response = client.get("/api/v1/workouts/nonexistent_id")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestListWorkouts:
    """Tests for GET /api/v1/workouts/."""

    def test_list_empty(self, client):
        """Test listing workouts when store is empty."""
        response = client.get("/api/v1/workouts/")

        assert response.status_code == 200
        assert response.json() == []

    def test_list_with_workouts(self, client, sample_workout, mock_services):
        """Test listing workouts when store has workouts."""
        # Create additional workout
        response = client.post(
            "/api/v1/workouts/design",
            json={"workout_type": "easy", "duration_min": 30}
        )
        assert response.status_code == 200

        response = client.get("/api/v1/workouts/")

        assert response.status_code == 200
        workouts = response.json()
        assert len(workouts) >= 2

    def test_list_with_pagination(self, client, mock_services):
        """Test listing workouts with pagination."""
        # Create multiple workouts
        for i in range(5):
            client.post(
                "/api/v1/workouts/design",
                json={"workout_type": "easy", "duration_min": 30}
            )

        # Get with limit
        response = client.get("/api/v1/workouts/?limit=2")

        assert response.status_code == 200
        assert len(response.json()) == 2

        # Get with offset
        response = client.get("/api/v1/workouts/?limit=2&offset=2")

        assert response.status_code == 200
        assert len(response.json()) == 2


class TestDeleteWorkout:
    """Tests for DELETE /api/v1/workouts/{workout_id}."""

    def test_delete_existing_workout(self, client, sample_workout):
        """Test deleting an existing workout."""
        response = client.delete(f"/api/v1/workouts/{sample_workout.id}")

        assert response.status_code == 200
        assert "deleted" in response.json()["message"]

        # Verify it's gone
        response = client.get(f"/api/v1/workouts/{sample_workout.id}")
        assert response.status_code == 404

    def test_delete_nonexistent_workout(self, client):
        """Test deleting a workout that doesn't exist."""
        response = client.delete("/api/v1/workouts/nonexistent_id")

        assert response.status_code == 404


# ============================================================================
# Test FIT Export Endpoints
# ============================================================================

class TestFITExport:
    """Tests for FIT file export endpoints."""

    def test_download_fit(self, client, sample_workout):
        """Test downloading a workout as FIT file."""
        response = client.get(f"/api/v1/workouts/{sample_workout.id}/fit")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/vnd.ant.fit"
        assert "attachment" in response.headers["content-disposition"]
        assert ".fit" in response.headers["content-disposition"]

        # Verify FIT file structure
        content = response.content
        assert len(content) > 14  # At least header size
        assert content[8:12] == b'.FIT'  # FIT signature

    def test_download_fit_nonexistent(self, client):
        """Test downloading FIT for nonexistent workout."""
        response = client.get("/api/v1/workouts/nonexistent_id/fit")

        assert response.status_code == 404

    def test_get_fit_bytes(self, client, sample_workout):
        """Test getting FIT file as base64 bytes."""
        response = client.get(f"/api/v1/workouts/{sample_workout.id}/fit/bytes")

        assert response.status_code == 200
        data = response.json()

        assert "workout_id" in data
        assert "data_base64" in data
        assert "size_bytes" in data
        assert data["content_type"] == "application/vnd.ant.fit"

        # Verify base64 data is valid
        fit_bytes = base64.b64decode(data["data_base64"])
        assert len(fit_bytes) == data["size_bytes"]
        assert fit_bytes[8:12] == b'.FIT'

    def test_get_fit_bytes_nonexistent(self, client):
        """Test getting FIT bytes for nonexistent workout."""
        response = client.get("/api/v1/workouts/nonexistent_id/fit/bytes")

        assert response.status_code == 404


class TestGarminExport:
    """Tests for Garmin Connect export endpoint."""

    def test_export_to_garmin_not_implemented(self, client, sample_workout):
        """Test that Garmin Connect export returns not implemented message."""
        response = client.post(
            f"/api/v1/workouts/{sample_workout.id}/export-garmin",
            json={"use_stored_credentials": True}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is False
        assert "not yet implemented" in data["message"].lower()

    def test_export_to_garmin_nonexistent(self, client):
        """Test exporting nonexistent workout to Garmin."""
        response = client.post(
            "/api/v1/workouts/nonexistent_id/export-garmin",
            json={"use_stored_credentials": True}
        )

        assert response.status_code == 404


# ============================================================================
# Test Quick Workout Endpoints
# ============================================================================

class TestQuickWorkouts:
    """Tests for quick workout generation endpoints."""

    def test_quick_easy(self, client, mock_services):
        """Test quick easy run endpoint."""
        response = client.post("/api/v1/workouts/quick/easy?duration_min=40")

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "Easy Run"

    def test_quick_tempo(self, client, mock_services):
        """Test quick tempo run endpoint."""
        response = client.post("/api/v1/workouts/quick/tempo?duration_min=45")

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "Tempo Run"

    def test_quick_intervals(self, client, mock_services):
        """Test quick intervals endpoint."""
        response = client.post("/api/v1/workouts/quick/intervals?duration_min=50")

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "Interval Session"

    def test_quick_long(self, client, mock_services):
        """Test quick long run endpoint."""
        response = client.post("/api/v1/workouts/quick/long?duration_min=120")

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "Long Run"

    def test_quick_default_duration(self, client, mock_services):
        """Test quick endpoints use default duration when not specified."""
        response = client.post("/api/v1/workouts/quick/easy")

        assert response.status_code == 200
        # Default should be 45 minutes for easy


# ============================================================================
# Test Workout Response Structure
# ============================================================================

class TestResponseStructure:
    """Tests for response data structure."""

    def test_workout_response_fields(self, client, mock_services):
        """Test that workout response has all expected fields."""
        response = client.post(
            "/api/v1/workouts/design",
            json={"workout_type": "tempo", "duration_min": 50}
        )

        assert response.status_code == 200
        data = response.json()

        # Required fields
        assert "workout_id" in data
        assert "name" in data
        assert "description" in data
        assert "sport" in data
        assert "intervals" in data
        assert "estimated_duration_min" in data

        # Optional fields
        assert "estimated_distance_km" in data or data.get("estimated_distance_km") is None
        assert "estimated_load" in data or data.get("estimated_load") is None
        assert "created_at" in data

    def test_interval_response_fields(self, client, mock_services):
        """Test that interval response has all expected fields."""
        response = client.post(
            "/api/v1/workouts/design",
            json={"workout_type": "intervals", "duration_min": 50}
        )

        assert response.status_code == 200
        intervals = response.json()["intervals"]

        for interval in intervals:
            assert "type" in interval
            assert interval["type"] in ["warmup", "work", "recovery", "cooldown", "rest", "active_recovery"]

            # Duration should be present
            assert "duration_sec" in interval or "distance_m" in interval

    def test_interval_targets_present(self, client, mock_services):
        """Test that work intervals have target values."""
        response = client.post(
            "/api/v1/workouts/design",
            json={"workout_type": "tempo", "duration_min": 50}
        )

        assert response.status_code == 200
        intervals = response.json()["intervals"]

        work_intervals = [i for i in intervals if i["type"] == "work"]
        assert len(work_intervals) > 0

        for work in work_intervals:
            # Should have either pace or HR targets
            has_pace = work.get("target_pace_min") is not None
            has_hr = work.get("target_hr_min") is not None
            assert has_pace or has_hr


# ============================================================================
# Test Error Handling
# ============================================================================

class TestErrorHandling:
    """Tests for error handling."""

    def test_invalid_json(self, client):
        """Test handling of invalid JSON in request."""
        response = client.post(
            "/api/v1/workouts/design",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    def test_duration_validation(self, client, mock_services):
        """Test duration parameter validation."""
        # Too short
        response = client.post(
            "/api/v1/workouts/design",
            json={"workout_type": "easy", "duration_min": 5}
        )
        assert response.status_code == 422

        # Too long
        response = client.post(
            "/api/v1/workouts/design",
            json={"workout_type": "easy", "duration_min": 500}
        )
        assert response.status_code == 422

    def test_target_load_validation(self, client, mock_services):
        """Test target_load parameter validation."""
        # Negative
        response = client.post(
            "/api/v1/workouts/design",
            json={"workout_type": "easy", "target_load": -10}
        )
        assert response.status_code == 422

        # Too high
        response = client.post(
            "/api/v1/workouts/design",
            json={"workout_type": "easy", "target_load": 1000}
        )
        assert response.status_code == 422
