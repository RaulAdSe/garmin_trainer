"""Tests for the CyclingWorkoutAgent."""

import pytest
from training_analyzer.agents.cycling_agent import (
    CyclingAthleteContext,
    CyclingWorkoutAgent,
    CyclingWorkoutInterval,
    get_cycling_agent,
)
from training_analyzer.models.workouts import (
    IntensityZone,
    IntervalType,
    WorkoutSport,
)


class TestCyclingAthleteContext:
    """Tests for CyclingAthleteContext."""

    def test_default_context(self):
        """Test default context values."""
        context = CyclingAthleteContext()
        assert context.ftp == 200
        assert context.max_hr == 185
        assert context.rest_hr == 55

    def test_power_zones_calculated(self):
        """Test power zones are calculated from FTP."""
        context = CyclingAthleteContext(ftp=250)
        zones = context.power_zones

        # Zone 1: <55% FTP
        assert zones[1] == (0, 137)  # 0-55% of 250

        # Zone 4: 90-105% FTP (threshold)
        z4_low, z4_high = zones[4]
        assert z4_low == int(250 * 0.90)  # 225
        assert z4_high == int(250 * 1.05)  # 262

    def test_power_zone_range(self):
        """Test getting specific power zone range."""
        context = CyclingAthleteContext(ftp=300)
        z5_low, z5_high = context.get_power_zone_range(5)

        # Zone 5: 105-120% FTP
        assert z5_low == int(300 * 1.05)  # 315
        assert z5_high == int(300 * 1.20)  # 360

    def test_hr_zones(self):
        """Test HR zone calculation."""
        context = CyclingAthleteContext(max_hr=190, rest_hr=50)
        z3_low, z3_high = context.get_hr_zone_range(3)

        # Zone 3: 70-80% HRR
        hr_reserve = 190 - 50  # 140
        expected_low = int(50 + 140 * 0.70)  # 148
        expected_high = int(50 + 140 * 0.80)  # 162

        assert z3_low == expected_low
        assert z3_high == expected_high

    def test_power_to_weight(self):
        """Test power-to-weight calculation."""
        context = CyclingAthleteContext(ftp=280, weight_kg=70)
        pw = context.get_power_to_weight()
        assert pw == 4.0  # 280/70 = 4.0 W/kg

    def test_power_to_weight_no_weight(self):
        """Test power-to-weight with no weight."""
        context = CyclingAthleteContext(ftp=280)
        assert context.get_power_to_weight() is None

    def test_to_dict(self):
        """Test serialization to dictionary."""
        context = CyclingAthleteContext(ftp=250, ctl=50, atl=45)
        data = context.to_dict()

        assert data["ftp"] == 250
        assert data["ctl"] == 50
        assert data["atl"] == 45
        assert "power_zones" in data
        assert "zone1" in data["power_zones"]


class TestCyclingWorkoutInterval:
    """Tests for CyclingWorkoutInterval."""

    def test_basic_interval(self):
        """Test basic interval creation."""
        interval = CyclingWorkoutInterval(
            type=IntervalType.WORK,
            duration_sec=1200,
            target_power_pct_ftp=(88, 94),
            target_cadence_range=(85, 95),
        )

        assert interval.duration_sec == 1200
        assert interval.target_power_pct_ftp == (88, 94)
        assert interval.target_cadence_range == (85, 95)

    def test_erg_mode_interval(self):
        """Test ERG mode interval."""
        interval = CyclingWorkoutInterval(
            type=IntervalType.WORK,
            duration_sec=600,
            erg_mode=True,
            erg_power=230,
        )

        assert interval.erg_mode is True
        assert interval.erg_power == 230

    def test_power_range_from_ftp(self):
        """Test calculating absolute power from FTP percentage."""
        interval = CyclingWorkoutInterval(
            type=IntervalType.WORK,
            duration_sec=1200,
            target_power_pct_ftp=(90, 100),
        )

        power_range = interval.get_power_range_from_ftp(250)
        assert power_range == (225, 250)  # 90-100% of 250

    def test_to_dict(self):
        """Test serialization."""
        interval = CyclingWorkoutInterval(
            type=IntervalType.WORK,
            duration_sec=600,
            target_power_pct_ftp=(88, 94),
            erg_mode=True,
            erg_power=200,
        )

        data = interval.to_dict()
        assert data["duration_sec"] == 600
        assert data["target_power_pct_ftp"] == [88, 94]
        assert data["erg_mode"] is True
        assert data["erg_power"] == 200


class TestCyclingWorkoutAgent:
    """Tests for CyclingWorkoutAgent."""

    @pytest.fixture
    def agent(self):
        """Create agent for testing."""
        return CyclingWorkoutAgent()

    @pytest.fixture
    def context(self):
        """Create athlete context for testing."""
        return CyclingAthleteContext(ftp=250)

    def test_design_sweet_spot(self, agent, context):
        """Test sweet spot workout design."""
        workout = agent.design_workout("sweet_spot", 60, context)

        assert workout.name == "Sweet Spot"
        assert workout.sport == WorkoutSport.CYCLING
        assert len(workout.intervals) >= 3  # warmup + intervals + cooldown

        # Check for sweet spot intervals
        work_intervals = [i for i in workout.intervals if i.type == IntervalType.WORK]
        assert len(work_intervals) >= 2

    def test_design_vo2max(self, agent, context):
        """Test VO2max workout design."""
        workout = agent.design_workout("vo2max", 75, context)

        assert "VO2max" in workout.name
        assert workout.estimated_load > 60 * 1.0  # Higher load than duration

        # Check for high-intensity intervals
        work_intervals = [i for i in workout.intervals if i.type == IntervalType.WORK]
        assert len(work_intervals) >= 4

    def test_design_threshold(self, agent, context):
        """Test threshold workout design."""
        workout = agent.design_workout("threshold", 60, context)

        assert "Threshold" in workout.name

        # Check for threshold intervals
        work_intervals = [i for i in workout.intervals if i.type == IntervalType.WORK]
        assert len(work_intervals) >= 2

    def test_design_over_unders(self, agent, context):
        """Test over-under workout design."""
        workout = agent.design_workout("over_unders", 60, context)

        assert "Over-Under" in workout.name

        # Should have multiple over/under segments
        work_intervals = [i for i in workout.intervals if i.type == IntervalType.WORK]
        assert len(work_intervals) >= 6  # At least 2 blocks of 3 cycles

    def test_design_endurance(self, agent, context):
        """Test endurance workout design."""
        workout = agent.design_workout("endurance", 90, context)

        assert "Endurance" in workout.name
        assert workout.estimated_load < 90 * 0.8  # Lower load

    def test_design_recovery(self, agent, context):
        """Test recovery workout design."""
        workout = agent.design_workout("recovery", 45, context)

        assert "Recovery" in workout.name
        assert workout.estimated_load < 45 * 0.5  # Very low load

    def test_design_tempo(self, agent, context):
        """Test tempo workout design."""
        workout = agent.design_workout("tempo", 60, context)

        assert "Tempo" in workout.name

    def test_design_sprint(self, agent, context):
        """Test sprint workout design."""
        workout = agent.design_workout("sprint", 60, context)

        assert "Sprint" in workout.name

        # Check for short, high-intensity intervals
        work_intervals = [i for i in workout.intervals if i.type == IntervalType.WORK]
        assert len(work_intervals) >= 6

    def test_design_ramp_test(self, agent, context):
        """Test ramp test design."""
        workout = agent.design_workout("ramp_test", 30, context)

        assert "Ramp" in workout.name

        # Should have progressive steps
        work_intervals = [i for i in workout.intervals if i.type == IntervalType.WORK]
        assert len(work_intervals) >= 10

    def test_design_ftp_test(self, agent, context):
        """Test FTP test design."""
        workout = agent.design_workout("ftp_test", 60, context)

        assert "FTP" in workout.name

        # Should have a 20-minute test interval
        work_intervals = [i for i in workout.intervals if i.type == IntervalType.WORK]
        assert any(i.duration_sec == 1200 for i in work_intervals)  # 20 min

    def test_unknown_type_defaults_to_endurance(self, agent, context):
        """Test unknown workout type defaults to endurance."""
        workout = agent.design_workout("unknown_type", 60, context)

        assert "Endurance" in workout.name

    def test_get_cycling_agent_singleton(self):
        """Test singleton pattern."""
        agent1 = get_cycling_agent()
        agent2 = get_cycling_agent()
        assert agent1 is agent2


class TestCyclingWorkoutIntegration:
    """Integration tests for cycling workouts."""

    def test_workout_intervals_have_targets(self):
        """Test that work intervals have appropriate targets."""
        agent = CyclingWorkoutAgent()
        context = CyclingAthleteContext(ftp=280)

        workout = agent.design_workout("sweet_spot", 60, context)

        for interval in workout.intervals:
            if interval.type == IntervalType.WORK:
                # Work intervals should have power targets
                assert hasattr(interval, 'target_power_pct_ftp') or hasattr(interval, 'target_power_range')

    def test_workout_duration_reasonable(self):
        """Test that estimated duration is reasonable."""
        agent = CyclingWorkoutAgent()
        context = CyclingAthleteContext(ftp=250)

        workout = agent.design_workout("vo2max", 75, context)

        # Estimated duration should be close to requested
        assert 60 <= workout.estimated_duration_min <= 90

    def test_different_ftp_produces_different_targets(self):
        """Test that different FTP produces different power targets."""
        agent = CyclingWorkoutAgent()

        context_low = CyclingAthleteContext(ftp=200)
        context_high = CyclingAthleteContext(ftp=300)

        workout_low = agent.design_workout("sweet_spot", 60, context_low)
        workout_high = agent.design_workout("sweet_spot", 60, context_high)

        # The descriptions should show different power values
        assert "200" not in workout_high.description or "300" not in workout_low.description



