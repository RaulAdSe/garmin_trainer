"""Tests for training plan generation API routes."""

import pytest
import tempfile
import os
from datetime import date, datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
import json

# Import the app and router
from training_analyzer.main import app
from training_analyzer.api.routes import plans
from training_analyzer.api import deps
from training_analyzer.db.repositories.plan_repository import PlanRepository
from training_analyzer.models.plans import (
    TrainingPlan,
    TrainingWeek,
    PlannedSession,
    RaceGoal,
    PlanConstraints,
    AthleteContext,
    PeriodizationType,
    TrainingPhase,
    WorkoutType,
    RaceDistance,
)


# Test client
client = TestClient(app)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def clear_plans_storage(tmp_path):
    """Clear the plans storage before each test by using a temporary database."""
    # Create a temporary database for testing
    test_db = tmp_path / "test_training.db"
    test_repo = PlanRepository(str(test_db))

    # Override the dependency
    def get_test_plan_repo():
        return test_repo

    app.dependency_overrides[deps.get_plan_repository] = get_test_plan_repo

    yield test_repo

    # Cleanup
    app.dependency_overrides.pop(deps.get_plan_repository, None)


@pytest.fixture
def mock_coach_service():
    """Create a mock coach service."""
    mock = Mock()
    mock.get_daily_briefing.return_value = {
        "training_status": {
            "ctl": 45.0,
            "atl": 50.0,
            "tsb": -5.0,
            "acwr": 1.1,
            "risk_zone": "optimal",
        },
        "readiness": {
            "score": 75,
            "zone": "green",
        },
    }
    mock.get_weekly_summary.return_value = {
        "total_load": 300,
        "workout_count": 5,
        "ctl_change": 2.0,
    }
    mock.get_recent_activities.return_value = [
        {"date": "2025-12-25", "hrss": 50, "trimp": 60},
        {"date": "2025-12-24", "hrss": 70, "trimp": 85},
    ]
    return mock


@pytest.fixture
def mock_training_db():
    """Create a mock training database."""
    return Mock()


@pytest.fixture
def sample_plan_request():
    """Sample plan generation request."""
    future_date = (date.today() + timedelta(weeks=16)).isoformat()
    return {
        "goal": {
            "race_date": future_date,
            "distance": "marathon",
            "target_time": "3:30:00",
            "race_name": "Test Marathon",
            "priority": 1,
        },
        "constraints": {
            "days_per_week": 5,
            "long_run_day": "sunday",
            "rest_days": ["friday"],
            "max_weekly_hours": 8.0,
            "max_session_duration_min": 150,
            "include_cross_training": False,
            "back_to_back_hard_ok": False,
        },
    }


@pytest.fixture
def sample_plan():
    """Create a sample training plan for testing."""
    future_date = date.today() + timedelta(weeks=16)

    goal = RaceGoal(
        race_date=future_date,
        distance=RaceDistance.MARATHON,
        target_time_seconds=12600,  # 3:30:00
        race_name="Test Marathon",
        priority=1,
    )

    # Create sample weeks
    weeks = []
    for week_num in range(1, 17):
        sessions = []
        for day in range(7):
            if day == 6:  # Sunday - Long run
                sessions.append(PlannedSession(
                    day_of_week=day,
                    workout_type=WorkoutType.LONG,
                    description="Long run",
                    target_duration_min=90 + week_num * 3,
                    target_load=100.0,
                    target_hr_zone="Zone 2",
                ))
            elif day == 1:  # Tuesday - Quality
                sessions.append(PlannedSession(
                    day_of_week=day,
                    workout_type=WorkoutType.TEMPO,
                    description="Tempo run",
                    target_duration_min=45,
                    target_load=70.0,
                    target_hr_zone="Zone 3-4",
                ))
            elif day == 4:  # Friday - Rest
                sessions.append(PlannedSession(
                    day_of_week=day,
                    workout_type=WorkoutType.REST,
                    description="Rest day",
                    target_duration_min=0,
                    target_load=0.0,
                ))
            else:  # Other days - Easy
                sessions.append(PlannedSession(
                    day_of_week=day,
                    workout_type=WorkoutType.EASY,
                    description="Easy run",
                    target_duration_min=40,
                    target_load=40.0,
                    target_hr_zone="Zone 1-2",
                ))

        phase = TrainingPhase.BASE if week_num <= 4 else (
            TrainingPhase.BUILD if week_num <= 12 else (
                TrainingPhase.PEAK if week_num <= 15 else TrainingPhase.TAPER
            )
        )

        weeks.append(TrainingWeek(
            week_number=week_num,
            phase=phase,
            target_load=300.0 + week_num * 10,
            sessions=sessions,
            focus="Build endurance",
            notes="Stay consistent",
        ))

    plan = TrainingPlan(
        id="plan_test123",
        goal=goal,
        weeks=weeks,
        periodization=PeriodizationType.LINEAR,
        peak_week=15,
        created_at=datetime.now(),
        is_active=False,
    )

    return plan


# ============================================================================
# Test Plan Generation
# ============================================================================

class TestGeneratePlan:
    """Tests for the /generate endpoint."""

    @patch('training_analyzer.api.routes.plans.PlanAgent')
    @patch('training_analyzer.api.routes.plans.get_coach_service')
    @patch('training_analyzer.api.routes.plans.get_training_db')
    def test_generate_plan_success(
        self, mock_get_db, mock_get_coach, mock_agent_class,
        sample_plan_request, sample_plan
    ):
        """Test successful plan generation."""
        # Setup mocks
        mock_coach = Mock()
        mock_coach.get_daily_briefing.return_value = {
            "training_status": {"ctl": 45.0, "atl": 50.0},
        }
        mock_coach.get_weekly_summary.return_value = {"total_load": 300}
        mock_get_coach.return_value = mock_coach
        mock_get_db.return_value = Mock()

        # Mock the agent
        mock_agent = AsyncMock()
        mock_agent.generate_plan.return_value = sample_plan
        mock_agent_class.return_value = mock_agent

        response = client.post("/api/v1/plans/generate", json=sample_plan_request)

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["periodization"] == "linear"
        assert data["total_weeks"] == 16

    def test_generate_plan_race_too_soon(self, sample_plan_request):
        """Test error when race date is too soon."""
        sample_plan_request["goal"]["race_date"] = (
            date.today() + timedelta(days=3)
        ).isoformat()

        response = client.post("/api/v1/plans/generate", json=sample_plan_request)

        assert response.status_code == 400
        assert "at least 1 week" in response.json()["detail"]

    def test_generate_plan_race_too_far(self, sample_plan_request):
        """Test error when race date is too far in the future."""
        sample_plan_request["goal"]["race_date"] = (
            date.today() + timedelta(weeks=60)
        ).isoformat()

        response = client.post("/api/v1/plans/generate", json=sample_plan_request)

        assert response.status_code == 400
        assert "too far" in response.json()["detail"]

    def test_generate_plan_invalid_time_format(self, sample_plan_request):
        """Test error with invalid time format."""
        sample_plan_request["goal"]["target_time"] = "invalid"

        response = client.post("/api/v1/plans/generate", json=sample_plan_request)

        # Should fail validation or parsing
        assert response.status_code in [400, 422, 500]


# ============================================================================
# Test List Plans
# ============================================================================

class TestListPlans:
    """Tests for the GET /plans endpoint."""

    def test_list_plans_empty(self):
        """Test listing plans when none exist."""
        response = client.get("/api/v1/plans")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["plans"] == []

    def test_list_plans_with_data(self, sample_plan, clear_plans_storage):
        """Test listing plans with existing plans."""
        # Add a plan to storage via repository
        clear_plans_storage.save(sample_plan)

        response = client.get("/api/v1/plans")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert len(data["plans"]) == 1
        assert data["plans"][0]["id"] == sample_plan.id

    def test_list_plans_active_only(self, sample_plan, clear_plans_storage):
        """Test filtering by active status."""
        # Add inactive plan
        clear_plans_storage.save(sample_plan)

        # Add active plan
        import copy
        active_plan = copy.deepcopy(sample_plan)
        active_plan.id = "plan_active"
        active_plan.is_active = True
        clear_plans_storage.save(active_plan)

        response = client.get("/api/v1/plans?active_only=true")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["plans"][0]["id"] == "plan_active"

    def test_list_plans_pagination(self, sample_plan, clear_plans_storage):
        """Test pagination of plans."""
        import copy
        # Add multiple plans
        for i in range(5):
            plan = copy.deepcopy(sample_plan)
            plan.id = f"plan_{i}"
            plan.created_at = datetime.now() - timedelta(hours=i)
            clear_plans_storage.save(plan)

        # Test limit
        response = client.get("/api/v1/plans?limit=2")
        assert response.json()["count"] == 2

        # Test offset
        response = client.get("/api/v1/plans?offset=2&limit=2")
        assert response.json()["count"] == 2
        assert response.json()["total"] == 5


# ============================================================================
# Test Get Plan
# ============================================================================

class TestGetPlan:
    """Tests for the GET /plans/{id} endpoint."""

    def test_get_plan_success(self, sample_plan, clear_plans_storage):
        """Test getting a specific plan."""
        clear_plans_storage.save(sample_plan)

        response = client.get(f"/api/v1/plans/{sample_plan.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_plan.id
        assert len(data["weeks"]) == 16

    def test_get_plan_not_found(self):
        """Test getting a non-existent plan."""
        response = client.get("/api/v1/plans/nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


# ============================================================================
# Test Get Plan Week
# ============================================================================

class TestGetPlanWeek:
    """Tests for the GET /plans/{id}/week/{week_number} endpoint."""

    def test_get_plan_week_success(self, sample_plan, clear_plans_storage):
        """Test getting a specific week from a plan."""
        clear_plans_storage.save(sample_plan)

        response = client.get(f"/api/v1/plans/{sample_plan.id}/week/1")

        assert response.status_code == 200
        data = response.json()
        assert data["week_number"] == 1
        assert "sessions" in data

    def test_get_plan_week_not_found(self, sample_plan, clear_plans_storage):
        """Test getting a non-existent week."""
        clear_plans_storage.save(sample_plan)

        response = client.get(f"/api/v1/plans/{sample_plan.id}/week/99")

        assert response.status_code == 404


# ============================================================================
# Test Update Plan
# ============================================================================

class TestUpdatePlan:
    """Tests for the PUT /plans/{id} endpoint."""

    def test_update_plan_name(self, sample_plan, clear_plans_storage):
        """Test updating plan name."""
        clear_plans_storage.save(sample_plan)

        response = client.put(
            f"/api/v1/plans/{sample_plan.id}",
            json={"name": "My Updated Plan"}
        )

        assert response.status_code == 200
        assert response.json()["name"] == "My Updated Plan"
        updated_plan = clear_plans_storage.get_as_dict(sample_plan.id)
        assert updated_plan["name"] == "My Updated Plan"

    def test_update_plan_activate(self, sample_plan, clear_plans_storage):
        """Test activating a plan."""
        clear_plans_storage.save(sample_plan)

        response = client.put(
            f"/api/v1/plans/{sample_plan.id}",
            json={"is_active": True}
        )

        assert response.status_code == 200
        assert response.json()["is_active"] is True

    def test_update_plan_deactivates_others(self, sample_plan, clear_plans_storage):
        """Test that activating one plan deactivates others."""
        import copy
        # Add two plans
        plan1 = copy.deepcopy(sample_plan)
        plan1.id = "plan_1"
        plan1.is_active = True
        clear_plans_storage.save(plan1)

        plan2 = copy.deepcopy(sample_plan)
        plan2.id = "plan_2"
        plan2.is_active = False
        clear_plans_storage.save(plan2)

        # Activate plan 2
        response = client.put("/api/v1/plans/plan_2", json={"is_active": True})

        assert response.status_code == 200
        plan1_data = clear_plans_storage.get_as_dict("plan_1")
        plan2_data = clear_plans_storage.get_as_dict("plan_2")
        assert plan1_data["is_active"] is False
        assert plan2_data["is_active"] is True

    def test_update_plan_not_found(self):
        """Test updating non-existent plan."""
        response = client.put(
            "/api/v1/plans/nonexistent",
            json={"name": "Test"}
        )

        assert response.status_code == 404


# ============================================================================
# Test Delete Plan
# ============================================================================

class TestDeletePlan:
    """Tests for the DELETE /plans/{id} endpoint."""

    def test_delete_plan_success(self, sample_plan, clear_plans_storage):
        """Test deleting a plan."""
        clear_plans_storage.save(sample_plan)

        response = client.delete(f"/api/v1/plans/{sample_plan.id}")

        assert response.status_code == 200
        assert not clear_plans_storage.exists(sample_plan.id)

    def test_delete_plan_not_found(self):
        """Test deleting non-existent plan."""
        response = client.delete("/api/v1/plans/nonexistent")

        assert response.status_code == 404


# ============================================================================
# Test Activate Plan
# ============================================================================

class TestActivatePlan:
    """Tests for the POST /plans/{id}/activate endpoint."""

    def test_activate_plan_success(self, sample_plan, clear_plans_storage):
        """Test activating a plan."""
        clear_plans_storage.save(sample_plan)

        response = client.post(f"/api/v1/plans/{sample_plan.id}/activate")

        assert response.status_code == 200
        plan_data = clear_plans_storage.get_as_dict(sample_plan.id)
        assert plan_data["is_active"] is True

    def test_activate_plan_not_found(self):
        """Test activating non-existent plan."""
        response = client.post("/api/v1/plans/nonexistent/activate")

        assert response.status_code == 404


# ============================================================================
# Test Adapt Plan
# ============================================================================

class TestAdaptPlan:
    """Tests for the POST /plans/{id}/adapt endpoint."""

    @patch('training_analyzer.api.routes.plans.PlanAgent')
    @patch('training_analyzer.api.routes.plans.get_coach_service')
    @patch('training_analyzer.api.routes.plans.get_training_db')
    def test_adapt_plan_success(
        self, mock_get_db, mock_get_coach, mock_agent_class, sample_plan, clear_plans_storage
    ):
        """Test adapting a plan."""
        # Setup mocks
        mock_coach = Mock()
        mock_coach.get_daily_briefing.return_value = {
            "training_status": {"ctl": 45.0, "atl": 50.0, "tsb": -5.0, "acwr": 1.1, "risk_zone": "optimal"},
            "readiness": {"score": 75},
        }
        mock_coach.get_recent_activities.return_value = []
        mock_coach.get_weekly_summary.return_value = {"total_load": 300, "workout_count": 5, "ctl_change": 2.0}
        mock_get_coach.return_value = mock_coach
        mock_get_db.return_value = Mock()

        # Store the plan
        clear_plans_storage.save(sample_plan)

        # Mock the agent
        import copy
        adapted_plan = copy.deepcopy(sample_plan)
        adapted_plan.adaptation_history.append({
            "timestamp": datetime.now().isoformat(),
            "reason": "Performance adjustment",
            "changes": {},
            "weeks_affected": [1, 2],
            "triggered_by": "performance",
        })

        mock_agent = AsyncMock()
        mock_agent.adapt_plan.return_value = adapted_plan
        mock_agent_class.return_value = mock_agent

        response = client.post(
            f"/api/v1/plans/{sample_plan.id}/adapt",
            json={"reason": "Test adaptation"}
        )

        assert response.status_code == 200

    def test_adapt_plan_not_found(self):
        """Test adapting non-existent plan."""
        response = client.post(
            "/api/v1/plans/nonexistent/adapt",
            json={}
        )

        assert response.status_code == 404


# ============================================================================
# Test Duplicate Plan
# ============================================================================

class TestDuplicatePlan:
    """Tests for the POST /plans/{id}/duplicate endpoint."""

    def test_duplicate_plan_success(self, sample_plan, clear_plans_storage):
        """Test duplicating a plan."""
        clear_plans_storage.save(sample_plan)

        response = client.post(f"/api/v1/plans/{sample_plan.id}/duplicate")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] != sample_plan.id
        assert "(Copy)" in (data.get("name") or "")
        assert data["is_active"] is False

    def test_duplicate_plan_with_new_date(self, sample_plan, clear_plans_storage):
        """Test duplicating with a new race date."""
        clear_plans_storage.save(sample_plan)
        new_date = (date.today() + timedelta(weeks=20)).isoformat()

        response = client.post(
            f"/api/v1/plans/{sample_plan.id}/duplicate?new_race_date={new_date}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["goal"]["race_date"] == new_date

    def test_duplicate_plan_not_found(self):
        """Test duplicating non-existent plan."""
        response = client.post("/api/v1/plans/nonexistent/duplicate")

        assert response.status_code == 404


# ============================================================================
# Test Export Plan
# ============================================================================

class TestExportPlan:
    """Tests for the GET /plans/{id}/export endpoint."""

    def test_export_plan_json(self, sample_plan, clear_plans_storage):
        """Test exporting plan as JSON."""
        clear_plans_storage.save(sample_plan)

        response = client.get(f"/api/v1/plans/{sample_plan.id}/export?format=json")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_plan.id

    def test_export_plan_ical(self, sample_plan, clear_plans_storage):
        """Test exporting plan as iCal."""
        clear_plans_storage.save(sample_plan)

        response = client.get(f"/api/v1/plans/{sample_plan.id}/export?format=ical")

        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "ical"
        assert "BEGIN:VCALENDAR" in data["content"]
        assert ".ics" in data["filename"]

    def test_export_plan_csv(self, sample_plan, clear_plans_storage):
        """Test exporting plan as CSV."""
        clear_plans_storage.save(sample_plan)

        response = client.get(f"/api/v1/plans/{sample_plan.id}/export?format=csv")

        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "csv"
        assert "Week,Day,Date" in data["content"]
        assert ".csv" in data["filename"]

    def test_export_plan_invalid_format(self, sample_plan, clear_plans_storage):
        """Test exporting with invalid format."""
        clear_plans_storage.save(sample_plan)

        response = client.get(f"/api/v1/plans/{sample_plan.id}/export?format=pdf")

        assert response.status_code == 400
        assert "Unsupported format" in response.json()["detail"]

    def test_export_plan_not_found(self):
        """Test exporting non-existent plan."""
        response = client.get("/api/v1/plans/nonexistent/export")

        assert response.status_code == 404


# ============================================================================
# Test Active Plan
# ============================================================================

class TestActivePlan:
    """Tests for the GET /plans/active endpoint."""

    def test_get_active_plan_none(self):
        """Test getting active plan when none is active."""
        response = client.get("/api/v1/plans/active")

        assert response.status_code == 200
        data = response.json()
        assert data["active_plan"] is None

    def test_get_active_plan_exists(self, sample_plan, clear_plans_storage):
        """Test getting active plan when one exists."""
        sample_plan.is_active = True
        clear_plans_storage.save(sample_plan)

        response = client.get("/api/v1/plans/active")

        assert response.status_code == 200
        data = response.json()
        assert data["active_plan"] is not None
        assert "current_week" in data
        assert "weeks_remaining" in data


# ============================================================================
# Test Model Parsing
# ============================================================================

class TestModelParsing:
    """Tests for model parsing utilities."""

    def test_parse_time_string_hours(self):
        """Test parsing time with hours."""
        from training_analyzer.models.plans import parse_time_string

        result = parse_time_string("3:30:00")
        assert result == 12600  # 3.5 hours in seconds

    def test_parse_time_string_minutes(self):
        """Test parsing time without hours."""
        from training_analyzer.models.plans import parse_time_string

        result = parse_time_string("25:30")
        assert result == 1530  # 25.5 minutes in seconds

    def test_day_name_to_number(self):
        """Test converting day names to numbers."""
        from training_analyzer.models.plans import day_name_to_number

        assert day_name_to_number("monday") == 0
        assert day_name_to_number("Sunday") == 6
        assert day_name_to_number("tue") == 1

    def test_race_goal_properties(self):
        """Test RaceGoal computed properties."""
        goal = RaceGoal(
            race_date=date.today() + timedelta(weeks=16),
            distance=RaceDistance.MARATHON,
            target_time_seconds=12600,
        )

        assert goal.distance_km == 42.195
        assert goal.target_time_formatted == "3:30:00"
        assert ":" in goal.target_pace_formatted
        assert goal.weeks_until_race() == 16

    def test_training_week_properties(self):
        """Test TrainingWeek computed properties."""
        sessions = [
            PlannedSession(
                day_of_week=0,
                workout_type=WorkoutType.EASY,
                description="Easy run",
                target_duration_min=40,
                target_load=40.0,
            ),
            PlannedSession(
                day_of_week=1,
                workout_type=WorkoutType.TEMPO,
                description="Tempo",
                target_duration_min=50,
                target_load=70.0,
            ),
            PlannedSession(
                day_of_week=2,
                workout_type=WorkoutType.REST,
                description="Rest",
                target_duration_min=0,
                target_load=0.0,
            ),
        ]

        week = TrainingWeek(
            week_number=1,
            phase=TrainingPhase.BUILD,
            target_load=300.0,
            sessions=sessions,
        )

        assert week.planned_duration_min == 90
        assert week.workout_count == 2  # Excludes rest
        assert len(week.quality_sessions) == 1  # Only tempo


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for the plans API."""

    @patch('training_analyzer.api.routes.plans.PlanAgent')
    @patch('training_analyzer.api.routes.plans.get_coach_service')
    @patch('training_analyzer.api.routes.plans.get_training_db')
    def test_full_plan_lifecycle(
        self, mock_get_db, mock_get_coach, mock_agent_class, sample_plan, sample_plan_request
    ):
        """Test creating, updating, and managing a plan."""
        # Setup mocks
        mock_coach = Mock()
        mock_coach.get_daily_briefing.return_value = {
            "training_status": {"ctl": 45.0, "atl": 50.0},
        }
        mock_coach.get_weekly_summary.return_value = {"total_load": 300}
        mock_get_coach.return_value = mock_coach
        mock_get_db.return_value = Mock()

        mock_agent = AsyncMock()
        mock_agent.generate_plan.return_value = sample_plan
        mock_agent_class.return_value = mock_agent

        # 1. Generate plan
        response = client.post("/api/v1/plans/generate", json=sample_plan_request)
        assert response.status_code == 200
        plan_id = response.json()["id"]

        # 2. List plans
        response = client.get("/api/v1/plans")
        assert response.status_code == 200
        assert response.json()["count"] == 1

        # 3. Update plan name
        response = client.put(
            f"/api/v1/plans/{plan_id}",
            json={"name": "My Marathon Plan"}
        )
        assert response.status_code == 200

        # 4. Activate plan
        response = client.post(f"/api/v1/plans/{plan_id}/activate")
        assert response.status_code == 200

        # 5. Get active plan
        response = client.get("/api/v1/plans/active")
        assert response.status_code == 200
        assert response.json()["active_plan"]["id"] == plan_id

        # 6. Get specific week
        response = client.get(f"/api/v1/plans/{plan_id}/week/1")
        assert response.status_code == 200

        # 7. Export plan
        response = client.get(f"/api/v1/plans/{plan_id}/export?format=csv")
        assert response.status_code == 200

        # 8. Duplicate plan
        response = client.post(f"/api/v1/plans/{plan_id}/duplicate")
        assert response.status_code == 200
        new_plan_id = response.json()["id"]
        assert new_plan_id != plan_id

        # 9. Delete duplicate
        response = client.delete(f"/api/v1/plans/{new_plan_id}")
        assert response.status_code == 200

        # 10. List plans should show 1 again
        response = client.get("/api/v1/plans")
        assert response.json()["count"] == 1
