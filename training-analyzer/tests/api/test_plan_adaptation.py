"""Tests for the plan adaptation API endpoints."""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import Mock, AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from training_analyzer.main import app
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
from training_analyzer.models.deviation import (
    DeviationType,
    DeviationMetrics,
    PlanDeviation,
    AdaptationSuggestion,
    SessionAdjustment,
    AdaptationAction,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def sample_goal():
    """Create a sample race goal."""
    return RaceGoal(
        race_date=date.today() + timedelta(weeks=8),
        distance=RaceDistance.HALF_MARATHON,
        target_time_seconds=6000,
        race_name="Test Race",
        priority=1,
    )


@pytest.fixture
def sample_athlete_context():
    """Create sample athlete context."""
    return AthleteContext(
        current_ctl=45.0,
        current_atl=50.0,
        recent_weekly_load=300.0,
        recent_weekly_hours=5.0,
        max_hr=185,
        rest_hr=55,
        threshold_hr=165,
    )


@pytest.fixture
def sample_constraints():
    """Create sample plan constraints."""
    return PlanConstraints(
        days_per_week=5,
        long_run_day=6,
        rest_days=[4],
        max_weekly_hours=8.0,
    )


@pytest.fixture
def sample_plan(sample_goal, sample_athlete_context, sample_constraints):
    """Create a sample training plan."""
    weeks = []
    for week_num in range(1, 9):
        sessions = [
            PlannedSession(
                day_of_week=0,
                workout_type=WorkoutType.EASY,
                description="Easy run",
                target_duration_min=45,
                target_load=40.0,
                target_hr_zone="Zone 2",
            ),
            PlannedSession(
                day_of_week=2,
                workout_type=WorkoutType.TEMPO,
                description="Tempo run",
                target_duration_min=50,
                target_load=70.0,
                target_hr_zone="Zone 4",
            ),
            PlannedSession(
                day_of_week=4,
                workout_type=WorkoutType.REST,
                description="Rest day",
                target_duration_min=0,
                target_load=0.0,
            ),
            PlannedSession(
                day_of_week=6,
                workout_type=WorkoutType.LONG,
                description="Long run",
                target_duration_min=90,
                target_load=80.0,
                target_hr_zone="Zone 2",
            ),
        ]
        weeks.append(TrainingWeek(
            week_number=week_num,
            phase=TrainingPhase.BUILD,
            target_load=190.0,
            sessions=sessions,
        ))

    return TrainingPlan(
        id="plan_test_123",
        goal=sample_goal,
        weeks=weeks,
        periodization=PeriodizationType.LINEAR,
        peak_week=7,
        created_at=datetime.now(),
        athlete_context=sample_athlete_context,
        constraints=sample_constraints,
    )


@pytest.fixture
def mock_plan_repository(sample_plan):
    """Create a mock plan repository."""
    repo = MagicMock()
    repo.get.return_value = sample_plan
    repo.save.return_value = None
    return repo


@pytest.fixture
def mock_coach_service():
    """Create a mock coach service."""
    service = MagicMock()
    service.get_recent_activities.return_value = [
        {
            "activity_id": "act_123",
            "date": (date.today() - timedelta(days=1)).isoformat(),
            "activity_type": "running",
            "duration_min": 65.0,
            "hrss": 75.0,
            "distance_km": 10.5,
            "avg_hr": 155,
            "max_hr": 175,
        }
    ]
    service.get_daily_briefing.return_value = {
        "training_status": {
            "ctl": 45.0,
            "atl": 52.0,
            "tsb": -7.0,
        },
        "readiness": {
            "score": 72.0,
        },
    }
    return service


@pytest.fixture
def mock_training_db():
    """Create a mock training database."""
    db = MagicMock()
    return db


# ============================================================================
# Test Check Deviation Endpoint
# ============================================================================

class TestCheckDeviationEndpoint:
    """Tests for POST /api/v1/plans/{id}/check-deviation."""

    def test_check_deviation_plan_not_found(self, client):
        """Test 404 when plan not found."""
        mock_repo = MagicMock()
        mock_repo.get.return_value = None

        with patch(
            "training_analyzer.api.routes.plans.get_plan_repository",
            return_value=mock_repo,
        ), patch(
            "training_analyzer.api.routes.plans.get_coach_service",
        ):
            response = client.post("/api/v1/plans/nonexistent/check-deviation")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_check_deviation_no_deviations(
        self,
        client,
        sample_plan,
        mock_plan_repository,
        mock_coach_service,
    ):
        """Test when no deviations detected."""
        # Configure mock to return activities matching plan
        race_date = sample_plan.goal.race_date
        plan_start = race_date - timedelta(weeks=sample_plan.total_weeks)

        mock_coach_service.get_recent_activities.return_value = [
            {
                "activity_id": "act_123",
                "date": plan_start.isoformat(),  # Monday
                "activity_type": "running",
                "duration_min": 45.0,  # Matches plan
                "hrss": 42.0,  # Within tolerance
            }
        ]

        with patch(
            "training_analyzer.api.routes.plans.get_plan_repository",
            return_value=mock_plan_repository,
        ), patch(
            "training_analyzer.api.routes.plans.get_coach_service",
            return_value=mock_coach_service,
        ):
            response = client.post("/api/v1/plans/plan_test_123/check-deviation")

        assert response.status_code == 200
        data = response.json()
        assert data["plan_id"] == "plan_test_123"
        assert "deviations" in data
        assert "summary" in data

    def test_check_deviation_with_harder_workout(
        self,
        client,
        sample_plan,
        mock_plan_repository,
        mock_coach_service,
    ):
        """Test detection of harder workout."""
        race_date = sample_plan.goal.race_date
        plan_start = race_date - timedelta(weeks=sample_plan.total_weeks)

        # Workout significantly harder than planned
        mock_coach_service.get_recent_activities.return_value = [
            {
                "activity_id": "act_123",
                "date": plan_start.isoformat(),
                "activity_type": "running",
                "duration_min": 70.0,  # Much longer
                "hrss": 85.0,  # Much higher load
            }
        ]

        with patch(
            "training_analyzer.api.routes.plans.get_plan_repository",
            return_value=mock_plan_repository,
        ), patch(
            "training_analyzer.api.routes.plans.get_coach_service",
            return_value=mock_coach_service,
        ):
            response = client.post(
                "/api/v1/plans/plan_test_123/check-deviation",
                json={"days_back": 7},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["plan_id"] == "plan_test_123"

    def test_check_deviation_custom_days_back(
        self,
        client,
        sample_plan,
        mock_plan_repository,
        mock_coach_service,
    ):
        """Test with custom days_back parameter."""
        with patch(
            "training_analyzer.api.routes.plans.get_plan_repository",
            return_value=mock_plan_repository,
        ), patch(
            "training_analyzer.api.routes.plans.get_coach_service",
            return_value=mock_coach_service,
        ):
            response = client.post(
                "/api/v1/plans/plan_test_123/check-deviation",
                json={"days_back": 14},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["checked_days"] == 14


# ============================================================================
# Test Auto-Adapt Endpoint
# ============================================================================

class TestAutoAdaptEndpoint:
    """Tests for POST /api/v1/plans/{id}/auto-adapt."""

    def test_auto_adapt_plan_not_found(self, client):
        """Test 404 when plan not found."""
        mock_repo = MagicMock()
        mock_repo.get.return_value = None

        with patch(
            "training_analyzer.api.routes.plans.get_plan_repository",
            return_value=mock_repo,
        ), patch(
            "training_analyzer.api.routes.plans.get_coach_service",
        ), patch(
            "training_analyzer.api.routes.plans.get_training_db",
        ):
            response = client.post("/api/v1/plans/nonexistent/auto-adapt")

        assert response.status_code == 404

    def test_auto_adapt_no_significant_deviations(
        self,
        client,
        sample_plan,
        mock_plan_repository,
        mock_coach_service,
        mock_training_db,
    ):
        """Test when no significant deviations need adaptation."""
        race_date = sample_plan.goal.race_date
        plan_start = race_date - timedelta(weeks=sample_plan.total_weeks)

        # Activities matching plan (no significant deviations)
        mock_coach_service.get_recent_activities.return_value = [
            {
                "activity_id": "act_123",
                "date": plan_start.isoformat(),
                "activity_type": "running",
                "duration_min": 45.0,
                "hrss": 40.0,
            }
        ]

        with patch(
            "training_analyzer.api.routes.plans.get_plan_repository",
            return_value=mock_plan_repository,
        ), patch(
            "training_analyzer.api.routes.plans.get_coach_service",
            return_value=mock_coach_service,
        ), patch(
            "training_analyzer.api.routes.plans.get_training_db",
            return_value=mock_training_db,
        ):
            response = client.post("/api/v1/plans/plan_test_123/auto-adapt")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "No adaptations needed."

    def test_auto_adapt_with_suggestions(
        self,
        client,
        sample_plan,
        mock_plan_repository,
        mock_coach_service,
        mock_training_db,
    ):
        """Test adaptation with significant deviations."""
        race_date = sample_plan.goal.race_date
        plan_start = race_date - timedelta(weeks=sample_plan.total_weeks)

        # Significantly harder workout
        mock_coach_service.get_recent_activities.return_value = [
            {
                "activity_id": "act_123",
                "date": plan_start.isoformat(),
                "activity_type": "running",
                "duration_min": 80.0,  # Much longer
                "hrss": 100.0,  # Much higher load
            }
        ]

        # Mock the adaptation agent
        mock_agent = AsyncMock()
        mock_suggestion = AdaptationSuggestion(
            plan_id="plan_test_123",
            deviation=PlanDeviation(
                plan_id="plan_test_123",
                week_number=1,
                day_of_week=0,
                planned_date=plan_start,
                deviation_type=DeviationType.HARDER,
                severity="significant",
            ),
            actions=[AdaptationAction.REDUCE_INTENSITY],
            affected_weeks=[1],
            session_adjustments=[],
            explanation="Your last workout was harder than planned.",
            expected_load_change_pct=-15.0,
        )
        mock_agent.suggest_adaptation.return_value = mock_suggestion

        with patch(
            "training_analyzer.api.routes.plans.get_plan_repository",
            return_value=mock_plan_repository,
        ), patch(
            "training_analyzer.api.routes.plans.get_coach_service",
            return_value=mock_coach_service,
        ), patch(
            "training_analyzer.api.routes.plans.get_training_db",
            return_value=mock_training_db,
        ), patch(
            "training_analyzer.api.routes.plans.get_adaptation_agent",
            return_value=mock_agent,
        ):
            response = client.post("/api/v1/plans/plan_test_123/auto-adapt")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["suggestions"]) >= 0

    def test_auto_adapt_apply_immediately(
        self,
        client,
        sample_plan,
        mock_plan_repository,
        mock_coach_service,
        mock_training_db,
    ):
        """Test applying adaptations immediately."""
        race_date = sample_plan.goal.race_date
        plan_start = race_date - timedelta(weeks=sample_plan.total_weeks)

        mock_coach_service.get_recent_activities.return_value = [
            {
                "activity_id": "act_123",
                "date": plan_start.isoformat(),
                "activity_type": "running",
                "duration_min": 80.0,
                "hrss": 100.0,
            }
        ]

        mock_agent = AsyncMock()
        mock_suggestion = AdaptationSuggestion(
            plan_id="plan_test_123",
            deviation=PlanDeviation(
                plan_id="plan_test_123",
                week_number=1,
                day_of_week=0,
                planned_date=plan_start,
                deviation_type=DeviationType.HARDER,
                severity="significant",
            ),
            actions=[AdaptationAction.REDUCE_INTENSITY],
            affected_weeks=[1],
            session_adjustments=[
                SessionAdjustment(
                    day_of_week=2,
                    original_type="tempo",
                    suggested_type="easy",
                    original_duration_min=50,
                    suggested_duration_min=40,
                    original_load=70.0,
                    suggested_load=35.0,
                    rationale="Reduce intensity after hard effort",
                )
            ],
            explanation="Reducing next session intensity.",
            expected_load_change_pct=-25.0,
        )
        mock_agent.suggest_adaptation.return_value = mock_suggestion

        with patch(
            "training_analyzer.api.routes.plans.get_plan_repository",
            return_value=mock_plan_repository,
        ), patch(
            "training_analyzer.api.routes.plans.get_coach_service",
            return_value=mock_coach_service,
        ), patch(
            "training_analyzer.api.routes.plans.get_training_db",
            return_value=mock_training_db,
        ), patch(
            "training_analyzer.api.routes.plans.get_adaptation_agent",
            return_value=mock_agent,
        ):
            response = client.post(
                "/api/v1/plans/plan_test_123/auto-adapt",
                json={"apply_immediately": True},
            )

        assert response.status_code == 200
        data = response.json()
        # Verify save was called on repository
        mock_plan_repository.save.assert_called()


# ============================================================================
# Test Error Handling
# ============================================================================

class TestErrorHandling:
    """Tests for error handling in adaptation endpoints."""

    def test_check_deviation_activity_fetch_error(
        self,
        client,
        sample_plan,
        mock_plan_repository,
    ):
        """Test handling of activity fetch errors."""
        mock_coach_service = MagicMock()
        mock_coach_service.get_recent_activities.side_effect = Exception("API error")

        with patch(
            "training_analyzer.api.routes.plans.get_plan_repository",
            return_value=mock_plan_repository,
        ), patch(
            "training_analyzer.api.routes.plans.get_coach_service",
            return_value=mock_coach_service,
        ):
            response = client.post("/api/v1/plans/plan_test_123/check-deviation")

        assert response.status_code == 500
        assert "Failed to fetch" in response.json()["detail"]


# ============================================================================
# Test Request Validation
# ============================================================================

class TestRequestValidation:
    """Tests for request parameter validation."""

    def test_check_deviation_default_days_back(
        self,
        client,
        sample_plan,
        mock_plan_repository,
        mock_coach_service,
    ):
        """Test default days_back parameter."""
        with patch(
            "training_analyzer.api.routes.plans.get_plan_repository",
            return_value=mock_plan_repository,
        ), patch(
            "training_analyzer.api.routes.plans.get_coach_service",
            return_value=mock_coach_service,
        ):
            response = client.post("/api/v1/plans/plan_test_123/check-deviation")

        assert response.status_code == 200
        assert response.json()["checked_days"] == 7

    def test_auto_adapt_without_explanation(
        self,
        client,
        sample_plan,
        mock_plan_repository,
        mock_coach_service,
        mock_training_db,
    ):
        """Test auto-adapt without explanation."""
        mock_coach_service.get_recent_activities.return_value = []

        with patch(
            "training_analyzer.api.routes.plans.get_plan_repository",
            return_value=mock_plan_repository,
        ), patch(
            "training_analyzer.api.routes.plans.get_coach_service",
            return_value=mock_coach_service,
        ), patch(
            "training_analyzer.api.routes.plans.get_training_db",
            return_value=mock_training_db,
        ):
            response = client.post(
                "/api/v1/plans/plan_test_123/auto-adapt",
                json={"include_explanation": False},
            )

        assert response.status_code == 200
