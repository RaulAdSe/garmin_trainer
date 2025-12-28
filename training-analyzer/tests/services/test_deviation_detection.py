"""Tests for the Deviation Detection Service."""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock

from training_analyzer.services.deviation_detection import (
    DeviationDetectionService,
    WorkoutData,
    get_deviation_service,
    reset_deviation_service,
)
from training_analyzer.models.deviation import (
    DeviationType,
    DeviationMetrics,
    PlanDeviation,
)
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


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_goal():
    """Create a sample race goal."""
    return RaceGoal(
        race_date=date.today() + timedelta(weeks=8),
        distance=RaceDistance.HALF_MARATHON,
        target_time_seconds=6000,  # 1:40:00
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
        long_run_day=6,  # Sunday
        rest_days=[4],  # Friday
        max_weekly_hours=8.0,
    )


@pytest.fixture
def sample_plan(sample_goal, sample_athlete_context, sample_constraints):
    """Create a sample training plan."""
    weeks = []
    for week_num in range(1, 9):
        sessions = [
            PlannedSession(
                day_of_week=0,  # Monday
                workout_type=WorkoutType.EASY,
                description="Easy run",
                target_duration_min=45,
                target_load=40.0,
                target_hr_zone="Zone 2",
            ),
            PlannedSession(
                day_of_week=2,  # Wednesday
                workout_type=WorkoutType.TEMPO,
                description="Tempo run",
                target_duration_min=50,
                target_load=70.0,
                target_hr_zone="Zone 4",
            ),
            PlannedSession(
                day_of_week=4,  # Friday
                workout_type=WorkoutType.REST,
                description="Rest day",
                target_duration_min=0,
                target_load=0.0,
            ),
            PlannedSession(
                day_of_week=6,  # Sunday
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
def service():
    """Create a deviation detection service."""
    reset_deviation_service()
    return DeviationDetectionService()


# ============================================================================
# Test WorkoutData
# ============================================================================

class TestWorkoutData:
    """Tests for WorkoutData dataclass."""

    def test_from_activity_dict_basic(self):
        """Test creating WorkoutData from activity dictionary."""
        activity = {
            "activity_id": "act_123",
            "date": "2025-12-25",
            "activity_type": "running",
            "duration_min": 45.0,
            "hrss": 65.0,
            "distance_km": 8.5,
            "avg_hr": 145,
            "max_hr": 165,
        }

        workout = WorkoutData.from_activity_dict(activity)

        assert workout.workout_id == "act_123"
        assert workout.date == date(2025, 12, 25)
        assert workout.activity_type == "running"
        assert workout.duration_min == 45.0
        assert workout.load == 65.0
        assert workout.distance_km == 8.5

    def test_from_activity_dict_with_trimp(self):
        """Test WorkoutData uses TRIMP when HRSS not available."""
        activity = {
            "activity_id": "act_123",
            "date": "2025-12-25",
            "activity_type": "running",
            "duration_min": 45.0,
            "trimp": 75.0,
        }

        workout = WorkoutData.from_activity_dict(activity)
        assert workout.load == 75.0

    def test_from_activity_dict_with_date_object(self):
        """Test WorkoutData handles date objects."""
        activity = {
            "activity_id": "act_123",
            "date": date(2025, 12, 25),
            "activity_type": "running",
            "duration_min": 45.0,
            "hrss": 65.0,
        }

        workout = WorkoutData.from_activity_dict(activity)
        assert workout.date == date(2025, 12, 25)


# ============================================================================
# Test DeviationMetrics
# ============================================================================

class TestDeviationMetrics:
    """Tests for DeviationMetrics calculations."""

    def test_duration_deviation_pct(self):
        """Test duration deviation calculation."""
        metrics = DeviationMetrics(
            planned_duration_min=60,
            actual_duration_min=75,
            planned_load=50,
            actual_load=50,
        )

        assert metrics.duration_deviation_pct == 25.0  # 25% longer

    def test_load_deviation_pct(self):
        """Test load deviation calculation."""
        metrics = DeviationMetrics(
            planned_duration_min=60,
            actual_duration_min=60,
            planned_load=50,
            actual_load=65,
        )

        assert metrics.load_deviation_pct == 30.0  # 30% higher load

    def test_load_deviation_negative(self):
        """Test negative load deviation."""
        metrics = DeviationMetrics(
            planned_duration_min=60,
            actual_duration_min=60,
            planned_load=100,
            actual_load=70,
        )

        assert metrics.load_deviation_pct == -30.0  # 30% lower load

    def test_zero_planned_duration(self):
        """Test handling zero planned duration."""
        metrics = DeviationMetrics(
            planned_duration_min=0,
            actual_duration_min=30,
            planned_load=0,
            actual_load=25,
        )

        assert metrics.duration_deviation_pct == 0.0
        assert metrics.load_deviation_pct == 0.0

    def test_distance_deviation_pct(self):
        """Test distance deviation calculation."""
        metrics = DeviationMetrics(
            planned_duration_min=60,
            actual_duration_min=60,
            planned_load=50,
            actual_load=50,
            planned_distance_km=10.0,
            actual_distance_km=12.0,
        )

        assert metrics.distance_deviation_pct == 20.0

    def test_to_dict(self):
        """Test DeviationMetrics to_dict method."""
        metrics = DeviationMetrics(
            planned_duration_min=60,
            actual_duration_min=75,
            planned_load=50,
            actual_load=65,
        )

        data = metrics.to_dict()

        assert data["planned_duration_min"] == 60
        assert data["actual_duration_min"] == 75
        assert data["duration_deviation_pct"] == 25.0
        assert data["load_deviation_pct"] == 30.0


# ============================================================================
# Test Deviation Detection
# ============================================================================

class TestDeviationDetection:
    """Tests for deviation detection logic."""

    def test_detect_as_planned(self, service, sample_plan):
        """Test detection of workout matching plan."""
        # Get the plan start date
        race_date = sample_plan.goal.race_date
        plan_start = race_date - timedelta(weeks=sample_plan.total_weeks)

        # Create a workout for week 1, Monday (easy run)
        workout_date = plan_start  # Week 1, Day 0 (Monday)

        workout = WorkoutData(
            workout_id="act_123",
            date=workout_date,
            activity_type="running",
            duration_min=45,  # Matches plan
            load=42.0,  # Within 15% of 40.0
        )

        deviation = service.detect_deviation(sample_plan, workout)

        assert deviation is not None
        assert deviation.deviation_type == DeviationType.AS_PLANNED
        assert deviation.severity == "none"

    def test_detect_harder(self, service, sample_plan):
        """Test detection of harder workout."""
        race_date = sample_plan.goal.race_date
        plan_start = race_date - timedelta(weeks=sample_plan.total_weeks)
        workout_date = plan_start

        workout = WorkoutData(
            workout_id="act_123",
            date=workout_date,
            activity_type="running",
            duration_min=60,  # 33% longer
            load=65.0,  # 62% higher load
        )

        deviation = service.detect_deviation(sample_plan, workout)

        assert deviation is not None
        assert deviation.deviation_type == DeviationType.HARDER
        assert deviation.severity in ("moderate", "significant")

    def test_detect_easier(self, service, sample_plan):
        """Test detection of easier workout."""
        race_date = sample_plan.goal.race_date
        plan_start = race_date - timedelta(weeks=sample_plan.total_weeks)
        workout_date = plan_start

        workout = WorkoutData(
            workout_id="act_123",
            date=workout_date,
            activity_type="running",
            duration_min=30,  # 33% shorter
            load=25.0,  # 37.5% lower load
        )

        deviation = service.detect_deviation(sample_plan, workout)

        assert deviation is not None
        assert deviation.deviation_type == DeviationType.EASIER
        assert deviation.severity in ("minor", "moderate", "significant")

    def test_detect_extra_workout(self, service, sample_plan):
        """Test detection of extra workout not in plan."""
        race_date = sample_plan.goal.race_date
        plan_start = race_date - timedelta(weeks=sample_plan.total_weeks)

        # Workout on Tuesday (day 1) which has no planned session
        workout_date = plan_start + timedelta(days=1)

        workout = WorkoutData(
            workout_id="act_123",
            date=workout_date,
            activity_type="running",
            duration_min=40,
            load=35.0,
        )

        deviation = service.detect_deviation(sample_plan, workout)

        assert deviation is not None
        assert deviation.deviation_type == DeviationType.EXTRA
        assert deviation.severity == "minor"

    def test_detect_workout_on_rest_day(self, service, sample_plan):
        """Test detection of workout on planned rest day."""
        race_date = sample_plan.goal.race_date
        plan_start = race_date - timedelta(weeks=sample_plan.total_weeks)

        # Workout on Friday (day 4) which is a rest day
        workout_date = plan_start + timedelta(days=4)

        workout = WorkoutData(
            workout_id="act_123",
            date=workout_date,
            activity_type="running",
            duration_min=30,
            load=25.0,
        )

        deviation = service.detect_deviation(sample_plan, workout)

        # On rest day, should be treated as extra
        assert deviation is not None
        assert deviation.deviation_type == DeviationType.EXTRA


# ============================================================================
# Test Skipped Session Detection
# ============================================================================

class TestSkippedSessionDetection:
    """Tests for skipped session detection."""

    def test_detect_skipped_sessions(self, service, sample_plan):
        """Test detection of skipped sessions."""
        race_date = sample_plan.goal.race_date
        plan_start = race_date - timedelta(weeks=sample_plan.total_weeks)

        # Only complete one workout in week 1
        workouts = [
            WorkoutData(
                workout_id="act_123",
                date=plan_start,  # Monday
                activity_type="running",
                duration_min=45,
                load=40.0,
            ),
        ]

        # Check for skipped sessions at end of week 1
        check_date = plan_start + timedelta(days=6)

        skipped = service.detect_skipped_sessions(
            plan=sample_plan,
            workouts=workouts,
            check_date=check_date,
        )

        # Should have skipped Tempo (Wed) and Long (Sun)
        assert len(skipped) >= 2
        assert all(d.deviation_type == DeviationType.SKIPPED for d in skipped)

    def test_no_skipped_sessions(self, service, sample_plan):
        """Test when all sessions completed."""
        race_date = sample_plan.goal.race_date
        plan_start = race_date - timedelta(weeks=sample_plan.total_weeks)

        # Complete all planned workouts
        workouts = [
            WorkoutData(
                workout_id="act_1",
                date=plan_start,  # Monday easy
                activity_type="running",
                duration_min=45,
                load=40.0,
            ),
            WorkoutData(
                workout_id="act_2",
                date=plan_start + timedelta(days=2),  # Wednesday tempo
                activity_type="running",
                duration_min=50,
                load=70.0,
            ),
            WorkoutData(
                workout_id="act_3",
                date=plan_start + timedelta(days=6),  # Sunday long
                activity_type="running",
                duration_min=90,
                load=80.0,
            ),
        ]

        check_date = plan_start + timedelta(days=6)

        skipped = service.detect_skipped_sessions(
            plan=sample_plan,
            workouts=workouts,
            check_date=check_date,
        )

        assert len(skipped) == 0


# ============================================================================
# Test Deviation Summary
# ============================================================================

class TestDeviationSummary:
    """Tests for deviation summary generation."""

    def test_empty_deviations(self, service):
        """Test summary for no deviations."""
        summary = service.get_deviation_summary([])

        assert summary["total"] == 0
        assert summary["has_significant"] is False
        assert "No deviations" in summary["summary_text"]

    def test_summary_with_skipped(self, service, sample_plan):
        """Test summary includes skipped count."""
        race_date = sample_plan.goal.race_date
        plan_start = race_date - timedelta(weeks=sample_plan.total_weeks)

        deviations = [
            PlanDeviation(
                plan_id="plan_123",
                week_number=1,
                day_of_week=2,
                planned_date=plan_start + timedelta(days=2),
                deviation_type=DeviationType.SKIPPED,
                planned_workout_type="tempo",
                severity="significant",
            ),
        ]

        summary = service.get_deviation_summary(deviations)

        assert summary["total"] == 1
        assert summary["by_type"]["skipped"] == 1
        assert summary["has_significant"] is True
        assert "skipped" in summary["summary_text"].lower()

    def test_summary_multiple_types(self, service, sample_plan):
        """Test summary with multiple deviation types."""
        race_date = sample_plan.goal.race_date
        plan_start = race_date - timedelta(weeks=sample_plan.total_weeks)

        deviations = [
            PlanDeviation(
                plan_id="plan_123",
                week_number=1,
                day_of_week=0,
                planned_date=plan_start,
                deviation_type=DeviationType.HARDER,
                severity="moderate",
            ),
            PlanDeviation(
                plan_id="plan_123",
                week_number=1,
                day_of_week=2,
                planned_date=plan_start + timedelta(days=2),
                deviation_type=DeviationType.EASIER,
                severity="minor",
            ),
        ]

        summary = service.get_deviation_summary(deviations)

        assert summary["total"] == 2
        assert summary["by_type"]["harder"] == 1
        assert summary["by_type"]["easier"] == 1


# ============================================================================
# Test All Deviations
# ============================================================================

class TestDetectAllDeviations:
    """Tests for detect_all_deviations method."""

    def test_detect_all_with_mixed_deviations(self, service, sample_plan):
        """Test detecting all types of deviations."""
        race_date = sample_plan.goal.race_date
        plan_start = race_date - timedelta(weeks=sample_plan.total_weeks)

        workouts = [
            # Harder than planned Monday workout
            WorkoutData(
                workout_id="act_1",
                date=plan_start,
                activity_type="running",
                duration_min=65,  # Longer
                load=70.0,  # Higher load
            ),
            # Extra workout on Tuesday
            WorkoutData(
                workout_id="act_2",
                date=plan_start + timedelta(days=1),
                activity_type="running",
                duration_min=30,
                load=25.0,
            ),
        ]

        deviations = service.detect_all_deviations(
            plan=sample_plan,
            workouts=workouts,
            days_back=7,
        )

        # Should have harder deviation, extra workout, and skipped sessions
        deviation_types = [d.deviation_type for d in deviations]
        assert DeviationType.HARDER in deviation_types or DeviationType.AS_PLANNED in deviation_types
        assert DeviationType.EXTRA in deviation_types


# ============================================================================
# Test Classification Logic
# ============================================================================

class TestClassificationLogic:
    """Tests for deviation classification logic."""

    def test_classify_within_tolerance(self, service):
        """Test classification within tolerance."""
        metrics = DeviationMetrics(
            planned_duration_min=60,
            actual_duration_min=63,  # 5% longer
            planned_load=50,
            actual_load=52,  # 4% higher
        )

        deviation_type, severity = service._classify_deviation(metrics)

        assert deviation_type == DeviationType.AS_PLANNED
        assert severity == "none"

    def test_classify_harder_moderate(self, service):
        """Test classification of moderately harder workout."""
        metrics = DeviationMetrics(
            planned_duration_min=60,
            actual_duration_min=72,  # 20% longer
            planned_load=50,
            actual_load=65,  # 30% higher
        )

        deviation_type, severity = service._classify_deviation(metrics)

        assert deviation_type == DeviationType.HARDER
        assert severity in ("minor", "moderate", "significant")

    def test_classify_easier_significant(self, service):
        """Test classification of significantly easier workout."""
        metrics = DeviationMetrics(
            planned_duration_min=60,
            actual_duration_min=30,  # 50% shorter
            planned_load=50,
            actual_load=20,  # 60% lower
        )

        deviation_type, severity = service._classify_deviation(metrics)

        assert deviation_type == DeviationType.EASIER
        assert severity in ("moderate", "significant")


# ============================================================================
# Test Singleton Factory
# ============================================================================

class TestSingletonFactory:
    """Tests for service singleton factory."""

    def test_get_deviation_service_returns_singleton(self):
        """Test that get_deviation_service returns the same instance."""
        reset_deviation_service()

        service1 = get_deviation_service()
        service2 = get_deviation_service()

        assert service1 is service2

    def test_reset_deviation_service(self):
        """Test that reset creates new instance."""
        service1 = get_deviation_service()
        reset_deviation_service()
        service2 = get_deviation_service()

        assert service1 is not service2
