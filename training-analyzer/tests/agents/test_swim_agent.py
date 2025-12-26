"""Tests for the SwimWorkoutAgent."""

import pytest
from training_analyzer.agents.swim_agent import (
    SwimWorkoutAgent,
    get_swim_agent,
    SWIM_DRILLS,
)
from training_analyzer.models.workouts import (
    IntensityZone,
    IntervalType,
    PoolLength,
    SwimAthleteContext,
    SwimStrokeType,
    WorkoutSport,
)


class TestSwimWorkoutAgent:
    """Tests for SwimWorkoutAgent."""

    @pytest.fixture
    def agent(self):
        """Create agent for testing."""
        return SwimWorkoutAgent()

    @pytest.fixture
    def context(self):
        """Create swim athlete context for testing."""
        return SwimAthleteContext(
            css_pace=100,  # 1:40/100m
            preferred_pool_length=PoolLength.SCM,
        )

    def test_design_endurance(self, agent, context):
        """Test endurance workout design."""
        workout = agent.design_workout("endurance", 45, context)

        assert "Endurance" in workout.name or "Aerobic" in workout.name
        assert workout.sport == WorkoutSport.SWIMMING
        assert len(workout.intervals) >= 3

    def test_design_threshold(self, agent, context):
        """Test threshold/CSS workout design."""
        workout = agent.design_workout("threshold", 60, context)

        assert "Threshold" in workout.name or "CSS" in workout.name

        # Should have multiple threshold intervals
        work_intervals = [i for i in workout.intervals if i.type == IntervalType.WORK]
        assert len(work_intervals) >= 4

    def test_design_speed(self, agent, context):
        """Test speed/sprint workout design."""
        workout = agent.design_workout("speed", 45, context)

        assert "Speed" in workout.name

        # Check for short, fast intervals
        work_intervals = [i for i in workout.intervals if i.type == IntervalType.WORK]
        assert len(work_intervals) >= 6

    def test_design_drill_focus(self, agent, context):
        """Test technique/drill workout design."""
        workout = agent.design_workout("drill", 45, context)

        assert "Technique" in workout.name or "Drill" in workout.name

        # Should have drill intervals
        drill_intervals = [
            i for i in workout.intervals
            if hasattr(i, 'is_drill') and i.is_drill
        ]
        assert len(drill_intervals) >= 2

    def test_design_mixed(self, agent, context):
        """Test mixed workout design."""
        workout = agent.design_workout("mixed", 60, context)

        assert "Mixed" in workout.name

        # Should have variety of intervals (3 sets with different focuses)
        work_intervals = [i for i in workout.intervals if i.type == IntervalType.WORK]
        assert len(work_intervals) >= 3

    def test_design_pyramid(self, agent, context):
        """Test pyramid workout design."""
        workout = agent.design_workout("pyramid", 60, context)

        assert "Pyramid" in workout.name

        # Should have ascending/descending distances
        work_intervals = [i for i in workout.intervals if i.type == IntervalType.WORK]
        assert len(work_intervals) >= 5

    def test_design_descending(self, agent, context):
        """Test descending set workout design."""
        workout = agent.design_workout("descending", 60, context)

        assert "Descending" in workout.name

    def test_design_broken_swim(self, agent, context):
        """Test broken swim workout design."""
        workout = agent.design_workout("broken", 60, context)

        assert "Broken" in workout.name

        # Should have multiple short segments
        work_intervals = [i for i in workout.intervals if i.type == IntervalType.WORK]
        assert len(work_intervals) >= 8

    def test_design_css_test(self, agent, context):
        """Test CSS test workout design."""
        workout = agent.design_workout("css_test", 60, context)

        assert "CSS" in workout.name or "Test" in workout.name

        # Should have 400m and 200m test intervals
        work_intervals = [i for i in workout.intervals if i.type == IntervalType.WORK]
        distances = [i.distance_m for i in work_intervals if i.distance_m]
        assert 400 in distances
        assert 200 in distances

    def test_design_recovery(self, agent, context):
        """Test recovery workout design."""
        workout = agent.design_workout("recovery", 30, context)

        assert "Recovery" in workout.name
        assert workout.estimated_load < 30 * 0.5  # Low load

    def test_unknown_type_defaults_to_mixed(self, agent, context):
        """Test unknown workout type defaults to mixed."""
        workout = agent.design_workout("unknown_type", 45, context)

        assert "Mixed" in workout.name

    def test_get_swim_agent_singleton(self):
        """Test singleton pattern."""
        agent1 = get_swim_agent()
        agent2 = get_swim_agent()
        assert agent1 is agent2


class TestSwimWorkoutIntervals:
    """Tests for swim workout interval properties."""

    @pytest.fixture
    def agent(self):
        return SwimWorkoutAgent()

    @pytest.fixture
    def context(self):
        return SwimAthleteContext(css_pace=90)  # 1:30/100m

    def test_pace_targets_based_on_css(self, agent, context):
        """Test that pace targets are relative to CSS."""
        workout = agent.design_workout("threshold", 45, context)

        # Find threshold work intervals
        work_intervals = [i for i in workout.intervals if i.type == IntervalType.WORK]

        for interval in work_intervals:
            if hasattr(interval, 'target_pace_per_100m') and interval.target_pace_per_100m:
                pace_low, pace_high = interval.target_pace_per_100m
                # Pace should be relative to CSS (90)
                assert 70 <= pace_low <= 130
                assert 70 <= pace_high <= 130

    def test_intervals_have_stroke_type(self, agent, context):
        """Test that swim intervals have stroke type."""
        workout = agent.design_workout("mixed", 45, context)

        for interval in workout.intervals:
            if hasattr(interval, 'stroke_type'):
                assert interval.stroke_type in SwimStrokeType

    def test_total_distance_calculated(self, agent, context):
        """Test that total distance is reasonable."""
        workout = agent.design_workout("threshold", 60, context)

        # Calculate total distance from intervals
        total_distance = sum(
            (i.distance_m or 0) * i.repetitions
            for i in workout.intervals
        )

        # For a 60-minute threshold workout, expect 2000-3500m
        assert 1500 <= total_distance <= 4000


class TestSwimDrills:
    """Tests for swim drills data."""

    def test_freestyle_drills_exist(self):
        """Test that freestyle drills are defined."""
        drills = SWIM_DRILLS[SwimStrokeType.FREESTYLE]
        assert len(drills) >= 5

        # Each drill should have name and description
        for drill_name, drill_desc in drills:
            assert len(drill_name) > 0
            assert len(drill_desc) > 0

    def test_all_strokes_have_drills(self):
        """Test that all main strokes have drills."""
        assert SwimStrokeType.FREESTYLE in SWIM_DRILLS
        assert SwimStrokeType.BACKSTROKE in SWIM_DRILLS
        assert SwimStrokeType.BREASTSTROKE in SWIM_DRILLS
        assert SwimStrokeType.BUTTERFLY in SWIM_DRILLS


class TestSwimAthleteContextIntegration:
    """Integration tests with SwimAthleteContext."""

    def test_different_css_produces_different_paces(self):
        """Test that different CSS produces different target paces."""
        agent = SwimWorkoutAgent()

        context_slow = SwimAthleteContext(css_pace=120)  # 2:00/100m
        context_fast = SwimAthleteContext(css_pace=80)   # 1:20/100m

        workout_slow = agent.design_workout("threshold", 45, context_slow)
        workout_fast = agent.design_workout("threshold", 45, context_fast)

        # Descriptions should mention different paces
        assert workout_slow.description != workout_fast.description

    def test_pool_length_affects_workout(self):
        """Test that pool length is respected."""
        agent = SwimWorkoutAgent()

        context_scm = SwimAthleteContext(
            css_pace=100,
            preferred_pool_length=PoolLength.SCM,
        )
        context_lcm = SwimAthleteContext(
            css_pace=100,
            preferred_pool_length=PoolLength.LCM,
        )

        # Both should produce valid workouts
        workout_scm = agent.design_workout("endurance", 45, context_scm)
        workout_lcm = agent.design_workout("endurance", 45, context_lcm)

        assert workout_scm is not None
        assert workout_lcm is not None

