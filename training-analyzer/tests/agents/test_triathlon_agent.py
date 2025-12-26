"""Tests for the TriathlonAgent."""

import pytest
from datetime import date, timedelta
from training_analyzer.agents.triathlon_agent import (
    BrickWorkout,
    FatigueCarryoverModel,
    MultiSportDay,
    RaceDistance,
    RaceDistanceSpecs,
    TriathlonAgent,
    TriathlonAthleteContext,
    get_triathlon_agent,
)
from training_analyzer.agents.cycling_agent import CyclingAthleteContext
from training_analyzer.models.workouts import (
    AthleteContext,
    PoolLength,
    SwimAthleteContext,
    WorkoutSport,
)


class TestRaceDistanceSpecs:
    """Tests for RaceDistanceSpecs."""

    def test_sprint_distance(self):
        """Test sprint triathlon distances."""
        specs = RaceDistanceSpecs.from_distance(RaceDistance.SPRINT)
        assert specs.swim_m == 750
        assert specs.bike_km == 20.0
        assert specs.run_km == 5.0

    def test_olympic_distance(self):
        """Test Olympic triathlon distances."""
        specs = RaceDistanceSpecs.from_distance(RaceDistance.OLYMPIC)
        assert specs.swim_m == 1500
        assert specs.bike_km == 40.0
        assert specs.run_km == 10.0

    def test_half_ironman_distance(self):
        """Test 70.3 triathlon distances."""
        specs = RaceDistanceSpecs.from_distance(RaceDistance.HALF_IRONMAN)
        assert specs.swim_m == 1900
        assert specs.bike_km == 90.0
        assert specs.run_km == 21.1

    def test_ironman_distance(self):
        """Test full Ironman distances."""
        specs = RaceDistanceSpecs.from_distance(RaceDistance.IRONMAN)
        assert specs.swim_m == 3800
        assert specs.bike_km == 180.0
        assert specs.run_km == 42.2


class TestTriathlonAthleteContext:
    """Tests for TriathlonAthleteContext."""

    @pytest.fixture
    def context(self):
        """Create a triathlon context."""
        return TriathlonAthleteContext(
            run_context=AthleteContext(),
            bike_context=CyclingAthleteContext(ftp=250),
            swim_context=SwimAthleteContext(css_pace=100),
            target_race=RaceDistance.OLYMPIC,
            race_date=date.today() + timedelta(weeks=12),
            combined_ctl=45.0,
            combined_atl=40.0,
        )

    def test_combined_tsb(self, context):
        """Test combined TSB calculation."""
        tsb = context.get_combined_tsb()
        assert tsb == 5.0  # 45 - 40

    def test_weeks_to_race(self, context):
        """Test weeks to race calculation."""
        weeks = context.get_weeks_to_race()
        assert weeks == 12

    def test_weeks_to_race_no_race(self):
        """Test weeks to race with no race date."""
        context = TriathlonAthleteContext(
            run_context=AthleteContext(),
            bike_context=CyclingAthleteContext(),
            swim_context=SwimAthleteContext(),
        )
        assert context.get_weeks_to_race() is None

    def test_to_dict(self, context):
        """Test serialization."""
        data = context.to_dict()

        assert "run_context" in data
        assert "bike_context" in data
        assert "swim_context" in data
        assert data["target_race"] == "olympic"
        assert data["combined_tsb"] == 5.0
        assert data["weeks_to_race"] == 12


class TestFatigueCarryoverModel:
    """Tests for FatigueCarryoverModel."""

    def test_bike_to_run_carryover(self):
        """Test bike-to-run has highest carryover."""
        factor = FatigueCarryoverModel.get_carryover_factor("bike", "run")
        assert factor == 1.25  # Significant brick effect

    def test_swim_to_bike_carryover(self):
        """Test swim-to-bike has minimal carryover."""
        factor = FatigueCarryoverModel.get_carryover_factor("swim", "bike")
        assert factor == 1.05  # Minimal effect

    def test_recovery_hours_bike_run(self):
        """Test bike-to-run needs no recovery (brick)."""
        hours = FatigueCarryoverModel.get_recovery_hours("bike", "run")
        assert hours == 0  # Brick workout

    def test_recovery_hours_run_swim(self):
        """Test run-to-swim needs recovery."""
        hours = FatigueCarryoverModel.get_recovery_hours("run", "swim")
        assert hours >= 3

    def test_adjust_second_workout_intensity(self):
        """Test second workout adjustment."""
        # High first workout load should reduce second workout target
        adjusted = FatigueCarryoverModel.adjust_second_workout_intensity(
            "bike", 100.0, 50.0
        )
        assert adjusted < 50.0  # Should be reduced


class TestBrickWorkout:
    """Tests for BrickWorkout."""

    def test_brick_workout_creation(self):
        """Test creating a brick workout."""
        from training_analyzer.models.workouts import (
            StructuredWorkout,
            WorkoutInterval,
            IntervalType,
        )

        # Create mock workouts
        bike = StructuredWorkout.create(
            name="Bike",
            description="Bike workout",
            intervals=[
                WorkoutInterval(type=IntervalType.WORK, duration_sec=3600)
            ],
            sport=WorkoutSport.CYCLING,
            estimated_load=60.0,
        )
        run = StructuredWorkout.create(
            name="Run",
            description="Run workout",
            intervals=[
                WorkoutInterval(type=IntervalType.WORK, duration_sec=1800)
            ],
            sport=WorkoutSport.RUNNING,
            estimated_load=30.0,
        )

        brick = BrickWorkout(
            id="brick_123",
            name="Test Brick",
            description="Test",
            first_workout=bike,
            second_workout=run,
        )

        # Total duration includes transition
        assert brick.total_duration_min == 60 + 30 + 5  # 5 min default transition

        # Load includes 15% brick effect
        expected_load = (60 + 30) * 1.15
        assert brick.total_estimated_load == expected_load

    def test_brick_to_dict(self):
        """Test brick workout serialization."""
        from training_analyzer.models.workouts import (
            StructuredWorkout,
            WorkoutInterval,
            IntervalType,
        )

        bike = StructuredWorkout.create(
            name="Bike",
            description="Bike",
            intervals=[WorkoutInterval(type=IntervalType.WORK, duration_sec=1800)],
            sport=WorkoutSport.CYCLING,
            estimated_load=40.0,
        )
        run = StructuredWorkout.create(
            name="Run",
            description="Run",
            intervals=[WorkoutInterval(type=IntervalType.WORK, duration_sec=1200)],
            sport=WorkoutSport.RUNNING,
            estimated_load=25.0,
        )

        brick = BrickWorkout(
            id="brick_456",
            name="Brick Test",
            description="Test brick",
            first_workout=bike,
            second_workout=run,
        )

        data = brick.to_dict()

        assert data["id"] == "brick_456"
        assert data["name"] == "Brick Test"
        assert "first_workout" in data
        assert "second_workout" in data


class TestTriathlonAgent:
    """Tests for TriathlonAgent."""

    @pytest.fixture
    def agent(self):
        """Create triathlon agent."""
        return TriathlonAgent()

    @pytest.fixture
    def context(self):
        """Create triathlon context."""
        return TriathlonAthleteContext(
            run_context=AthleteContext(),
            bike_context=CyclingAthleteContext(ftp=250),
            swim_context=SwimAthleteContext(css_pace=100),
        )

    def test_create_bike_run_brick(self, agent, context):
        """Test creating a bike-to-run brick workout."""
        brick = agent.create_brick_workout(
            "bike_run", 90, context, "moderate"
        )

        assert "Bike-to-Run" in brick.name
        assert brick.first_workout.sport == WorkoutSport.CYCLING
        assert brick.second_workout.sport == WorkoutSport.RUNNING

    def test_create_swim_bike_brick(self, agent, context):
        """Test creating a swim-to-bike brick workout."""
        brick = agent.create_brick_workout(
            "swim_bike", 90, context, "moderate"
        )

        assert "Swim-to-Bike" in brick.name
        assert brick.first_workout.sport == WorkoutSport.SWIMMING
        assert brick.second_workout.sport == WorkoutSport.CYCLING

    def test_plan_multi_sport_day_with_brick(self, agent, context):
        """Test planning a multi-sport day with brick workout."""
        day = agent.plan_multi_sport_day(
            target_date=date.today(),
            available_hours=3.0,
            context=context,
            include_brick=True,
        )

        assert len(day.brick_workouts) == 1
        assert len(day.workouts) >= 1  # Should have swim session too
        assert day.total_duration_min > 0
        assert day.total_load > 0

    def test_plan_multi_sport_day_without_brick(self, agent, context):
        """Test planning a multi-sport day without brick."""
        day = agent.plan_multi_sport_day(
            target_date=date.today(),
            available_hours=2.0,
            context=context,
            include_brick=False,
        )

        assert len(day.brick_workouts) == 0
        assert len(day.workouts) >= 2  # Should have multiple sessions

    def test_create_taper_week_race_week(self, agent, context):
        """Test creating race week taper plan."""
        race_date = date.today() + timedelta(days=7)

        days = agent.create_taper_week(
            race_date=race_date,
            weeks_out=1,
            context=context,
        )

        # Should have training days leading up to race
        assert len(days) >= 4

        # Each day should have reduced volume
        for day in days:
            assert day.total_duration_min < 120  # Short sessions

    def test_create_taper_week_2_weeks_out(self, agent, context):
        """Test creating 2-weeks-out taper plan."""
        race_date = date.today() + timedelta(days=14)

        days = agent.create_taper_week(
            race_date=race_date,
            weeks_out=2,
            context=context,
        )

        assert len(days) >= 5

    def test_estimate_race_performance_olympic(self, agent, context):
        """Test race performance estimation for Olympic distance."""
        prediction = agent.estimate_race_performance(
            RaceDistance.OLYMPIC, context
        )

        assert "predicted_times" in prediction
        assert "swim" in prediction["predicted_times"]
        assert "bike" in prediction["predicted_times"]
        assert "run" in prediction["predicted_times"]
        assert "total" in prediction["predicted_times"]

        assert "pacing" in prediction
        assert "swim_pace_100m" in prediction["pacing"]
        assert "bike_power_w" in prediction["pacing"]
        assert "run_pace_km" in prediction["pacing"]

    def test_estimate_race_performance_ironman(self, agent, context):
        """Test race performance estimation for Ironman."""
        prediction = agent.estimate_race_performance(
            RaceDistance.IRONMAN, context
        )

        # Ironman should have longer times
        total_time = prediction["predicted_times"]["total"]
        # Should be many hours (contains ":")
        assert ":" in total_time

    def test_get_triathlon_agent_singleton(self):
        """Test singleton pattern."""
        agent1 = get_triathlon_agent()
        agent2 = get_triathlon_agent()
        assert agent1 is agent2


class TestMultiSportDay:
    """Tests for MultiSportDay."""

    def test_multi_sport_day_totals(self):
        """Test that totals are calculated correctly."""
        from training_analyzer.models.workouts import (
            StructuredWorkout,
            WorkoutInterval,
            IntervalType,
        )

        swim = StructuredWorkout.create(
            name="Swim",
            description="Swim",
            intervals=[WorkoutInterval(type=IntervalType.WORK, duration_sec=2700)],
            sport=WorkoutSport.SWIMMING,
            estimated_load=40.0,
        )

        day = MultiSportDay(
            date=date.today(),
            workouts=[swim],
            brick_workouts=[],
        )

        assert day.total_duration_min == 45
        assert day.total_load == 40.0

    def test_multi_sport_day_to_dict(self):
        """Test serialization."""
        day = MultiSportDay(
            date=date.today(),
            workouts=[],
            brick_workouts=[],
            notes="Test day",
        )

        data = day.to_dict()

        assert "date" in data
        assert "workouts" in data
        assert "brick_workouts" in data
        assert data["notes"] == "Test day"

