"""Tests for analysis module."""

import pytest
from datetime import date, timedelta

from training_analyzer.analysis.trends import (
    FitnessTrend,
    PerformanceTrend,
    calculate_fitness_trend,
    calculate_pace_at_hr_trend,
    detect_overtraining_signals,
    generate_ascii_chart,
)
from training_analyzer.analysis.weekly import (
    WeeklyAnalysis,
    analyze_week,
    generate_weekly_insights,
    format_weekly_summary,
    generate_zone_bar_chart,
)
from training_analyzer.analysis.goals import (
    RaceDistance,
    RaceGoal,
    GoalProgress,
    predict_race_time,
    calculate_training_paces,
    assess_goal_progress,
    format_time,
    parse_time,
    calculate_vdot,
)


class TestFitnessTrend:
    """Tests for fitness trend calculation."""

    def test_calculate_fitness_trend_improving(self):
        """Test trend detection when fitness is improving."""
        # Create improving CTL trend
        history = []
        base_date = date.today() - timedelta(days=30)

        for i in range(28):
            history.append({
                "date": (base_date + timedelta(days=i)).isoformat(),
                "ctl": 30 + i * 0.5,  # Increasing CTL
                "daily_load": 50 + (i % 3) * 20,  # Variable load
            })

        trend = calculate_fitness_trend(history, period_days=28)

        assert trend is not None
        assert trend.trend_direction == "improving"
        assert trend.ctl_change > 0
        assert trend.ctl_change_pct > 0

    def test_calculate_fitness_trend_declining(self):
        """Test trend detection when fitness is declining."""
        history = []
        base_date = date.today() - timedelta(days=30)

        for i in range(28):
            history.append({
                "date": (base_date + timedelta(days=i)).isoformat(),
                "ctl": 50 - i * 0.5,  # Decreasing CTL
                "daily_load": 30,
            })

        trend = calculate_fitness_trend(history, period_days=28)

        assert trend is not None
        assert trend.trend_direction == "declining"
        assert trend.ctl_change < 0

    def test_calculate_fitness_trend_maintaining(self):
        """Test trend detection when fitness is stable."""
        history = []
        base_date = date.today() - timedelta(days=30)

        for i in range(28):
            history.append({
                "date": (base_date + timedelta(days=i)).isoformat(),
                "ctl": 45 + (i % 2),  # Stable CTL with minor variation
                "daily_load": 50,
            })

        trend = calculate_fitness_trend(history, period_days=28)

        assert trend is not None
        assert trend.trend_direction == "maintaining"

    def test_calculate_fitness_trend_empty_input(self):
        """Test with empty input."""
        trend = calculate_fitness_trend([])
        assert trend is None

    def test_calculate_fitness_trend_insufficient_data(self):
        """Test with insufficient data."""
        history = [{"date": date.today().isoformat(), "ctl": 50, "daily_load": 100}]
        trend = calculate_fitness_trend(history)
        assert trend is None

    def test_fitness_trend_weekly_load_avg(self):
        """Test weekly load average calculation."""
        history = []
        base_date = date.today() - timedelta(days=30)

        for i in range(28):
            history.append({
                "date": (base_date + timedelta(days=i)).isoformat(),
                "ctl": 45,
                "daily_load": 100,  # 100 per day = 700 per week
            })

        trend = calculate_fitness_trend(history, period_days=28)

        assert trend is not None
        # Weekly average should be around 700
        assert 650 < trend.weekly_load_avg < 750


class TestPaceAtHRTrend:
    """Tests for pace at HR trend analysis."""

    def test_calculate_pace_at_hr_trend_basic(self):
        """Test basic pace at HR calculation."""
        activities = []
        base_date = date.today() - timedelta(days=60)

        for i in range(10):
            activities.append({
                "date": (base_date + timedelta(days=i * 7)).isoformat(),
                "avg_hr": 145,
                "pace_sec_per_km": 330 - i * 3,  # Improving pace
                "distance_km": 8.0,
            })

        trends = calculate_pace_at_hr_trend(
            activities,
            target_hr_zone=(140, 150),
            period_days=90
        )

        assert len(trends) == 10
        # Efficiency should be improving (last better than first)
        assert trends[-1].efficiency_score > trends[0].efficiency_score

    def test_calculate_pace_at_hr_trend_filters_by_hr(self):
        """Test that only activities in HR range are included."""
        activities = [
            {
                "date": date.today().isoformat(),
                "avg_hr": 145,  # In range
                "pace_sec_per_km": 300,
                "distance_km": 5.0,
            },
            {
                "date": (date.today() - timedelta(days=1)).isoformat(),
                "avg_hr": 120,  # Out of range (too low)
                "pace_sec_per_km": 400,
                "distance_km": 5.0,
            },
            {
                "date": (date.today() - timedelta(days=2)).isoformat(),
                "avg_hr": 170,  # Out of range (too high)
                "pace_sec_per_km": 280,
                "distance_km": 5.0,
            },
        ]

        trends = calculate_pace_at_hr_trend(
            activities,
            target_hr_zone=(140, 150),
            period_days=90
        )

        assert len(trends) == 1
        assert trends[0].avg_hr == 145

    def test_calculate_pace_at_hr_trend_filters_by_distance(self):
        """Test that short activities are filtered out."""
        activities = [
            {
                "date": date.today().isoformat(),
                "avg_hr": 145,
                "pace_sec_per_km": 300,
                "distance_km": 5.0,  # Valid
            },
            {
                "date": (date.today() - timedelta(days=1)).isoformat(),
                "avg_hr": 145,
                "pace_sec_per_km": 300,
                "distance_km": 2.0,  # Too short
            },
        ]

        trends = calculate_pace_at_hr_trend(
            activities,
            target_hr_zone=(140, 150),
            period_days=90
        )

        assert len(trends) == 1

    def test_calculate_pace_at_hr_trend_empty(self):
        """Test with no matching activities."""
        trends = calculate_pace_at_hr_trend([], (140, 150))
        assert trends == []


class TestOvertrainingSignals:
    """Tests for overtraining signal detection."""

    def test_detect_high_acwr(self):
        """Test detection of high ACWR."""
        fitness_history = []
        for i in range(7):
            fitness_history.append({
                "date": (date.today() - timedelta(days=i)).isoformat(),
                "acwr": 1.4,  # Elevated
                "tsb": -10,
            })

        signals = detect_overtraining_signals(fitness_history, [])
        assert any("ACWR" in s for s in signals)

    def test_detect_negative_tsb(self):
        """Test detection of prolonged negative TSB."""
        fitness_history = []
        for i in range(7):
            fitness_history.append({
                "date": (date.today() - timedelta(days=i)).isoformat(),
                "acwr": 1.0,
                "tsb": -25,  # Very negative
            })

        signals = detect_overtraining_signals(fitness_history, [])
        assert any("TSB" in s for s in signals)

    def test_detect_declining_hrv(self):
        """Test detection of declining HRV."""
        # Need significant decline (>15%) to trigger
        # First half: high HRV, second half: significantly lower
        wellness_history = [
            {"hrv_last_night_avg": 60},  # First half - higher
            {"hrv_last_night_avg": 58},
            {"hrv_last_night_avg": 55},
            {"hrv_last_night_avg": 40},  # Second half - much lower
            {"hrv_last_night_avg": 38},
            {"hrv_last_night_avg": 35},
        ]

        signals = detect_overtraining_signals([], wellness_history)
        assert any("HRV" in s for s in signals)

    def test_no_signals_healthy(self):
        """Test no signals for healthy metrics."""
        fitness_history = []
        for i in range(7):
            fitness_history.append({
                "date": (date.today() - timedelta(days=i)).isoformat(),
                "acwr": 1.0,  # Optimal
                "tsb": 5,  # Positive
            })

        signals = detect_overtraining_signals(fitness_history, [])
        # Should not have high ACWR or negative TSB signals
        assert not any("ACWR has been elevated" in s for s in signals)
        assert not any("TSB has been very negative" in s for s in signals)


class TestASCIIChart:
    """Tests for ASCII chart generation."""

    def test_generate_ascii_chart_basic(self):
        """Test basic chart generation."""
        values = [10, 20, 30, 40, 50]
        labels = ["A", "B", "C", "D", "E"]

        chart = generate_ascii_chart(values, labels, title="Test Chart")

        assert "Test Chart" in chart
        assert "*" in chart  # Data points

    def test_generate_ascii_chart_empty(self):
        """Test with empty data."""
        chart = generate_ascii_chart([], [])
        assert "No data" in chart


class TestWeeklyAnalysis:
    """Tests for weekly training analysis."""

    def test_analyze_week_basic(self):
        """Test basic weekly analysis."""
        activities = [
            {
                "date": date.today().isoformat(),
                "hrss": 80,
                "duration_min": 60,
                "distance_km": 10,
                "zone1_pct": 20,
                "zone2_pct": 60,
                "zone3_pct": 15,
                "zone4_pct": 5,
                "zone5_pct": 0,
            },
            {
                "date": (date.today() - timedelta(days=1)).isoformat(),
                "hrss": 50,
                "duration_min": 45,
                "distance_km": 7,
                "zone1_pct": 30,
                "zone2_pct": 70,
                "zone3_pct": 0,
                "zone4_pct": 0,
                "zone5_pct": 0,
            },
        ]

        analysis = analyze_week(activities, [])

        assert analysis.activity_count == 2
        assert analysis.total_load == 130  # 80 + 50
        assert analysis.total_duration_min == 105  # 60 + 45
        assert analysis.total_distance_km == 17  # 10 + 7

    def test_analyze_week_empty(self):
        """Test with no activities."""
        analysis = analyze_week([], [])

        assert analysis.activity_count == 0
        assert analysis.total_load == 0
        assert "No activities" in analysis.insights[0]

    def test_analyze_week_zone_distribution(self):
        """Test zone distribution calculation."""
        activities = [
            {
                "date": date.today().isoformat(),
                "duration_min": 60,
                "zone1_pct": 0,
                "zone2_pct": 100,
                "zone3_pct": 0,
                "zone4_pct": 0,
                "zone5_pct": 0,
                "hrss": 50,
            },
        ]

        analysis = analyze_week(activities, [])

        assert analysis.zone2_pct == 100.0
        assert analysis.zone1_pct == 0.0

    def test_generate_weekly_insights(self):
        """Test insight generation."""
        analysis = WeeklyAnalysis(
            week_start=date.today() - timedelta(days=6),
            week_end=date.today(),
            total_distance_km=50,
            total_duration_min=300,
            total_load=350,
            activity_count=5,
            zone1_pct=25,
            zone2_pct=55,
            zone3_pct=10,
            zone4_pct=8,
            zone5_pct=2,
            week_over_week_change=25,
            is_recovery_week=False,
            load_vs_target=95,
            ctl_change=3,
            atl_change=5,
        )

        insights = generate_weekly_insights(analysis)

        assert len(insights) > 0
        # Should mention the large week-over-week increase
        assert any("increase" in i.lower() for i in insights)

    def test_format_weekly_summary(self):
        """Test summary formatting."""
        analysis = WeeklyAnalysis(
            week_start=date.today() - timedelta(days=6),
            week_end=date.today(),
            total_distance_km=50,
            total_duration_min=300,
            total_load=350,
            activity_count=5,
            zone1_pct=25,
            zone2_pct=55,
            zone3_pct=10,
            zone4_pct=8,
            zone5_pct=2,
            week_over_week_change=0,
            is_recovery_week=False,
            load_vs_target=95,
            ctl_change=3,
            atl_change=5,
            insights=["Test insight"],
        )

        summary = format_weekly_summary(analysis)

        assert "Volume:" in summary
        assert "Zone Distribution:" in summary
        assert "Insights:" in summary


class TestRaceDistance:
    """Tests for RaceDistance enum."""

    def test_race_distance_values(self):
        """Test race distance values."""
        assert RaceDistance.FIVE_K.value == 5.0
        assert RaceDistance.TEN_K.value == 10.0
        assert abs(RaceDistance.HALF_MARATHON.value - 21.0975) < 0.01
        assert abs(RaceDistance.MARATHON.value - 42.195) < 0.01

    def test_from_string(self):
        """Test parsing race distance from string."""
        assert RaceDistance.from_string("5k") == RaceDistance.FIVE_K
        assert RaceDistance.from_string("10K") == RaceDistance.TEN_K
        assert RaceDistance.from_string("half") == RaceDistance.HALF_MARATHON
        assert RaceDistance.from_string("marathon") == RaceDistance.MARATHON
        assert RaceDistance.from_string("invalid") is None

    def test_display_name(self):
        """Test display names."""
        assert RaceDistance.FIVE_K.display_name == "5K"
        assert RaceDistance.HALF_MARATHON.display_name == "Half Marathon"


class TestRaceGoal:
    """Tests for RaceGoal dataclass."""

    def test_race_goal_target_pace(self):
        """Test target pace calculation."""
        goal = RaceGoal(
            race_date=date.today() + timedelta(days=90),
            distance=RaceDistance.FIVE_K,
            target_time_sec=1200,  # 20 minutes
        )

        assert goal.target_pace == 240  # 4 min/km = 240 sec/km

    def test_race_goal_target_pace_formatted(self):
        """Test formatted pace."""
        goal = RaceGoal(
            race_date=date.today() + timedelta(days=90),
            distance=RaceDistance.FIVE_K,
            target_time_sec=1200,  # 20 minutes
        )

        assert goal.target_pace_formatted == "4:00/km"

    def test_race_goal_weeks_until_race(self):
        """Test weeks remaining calculation."""
        goal = RaceGoal(
            race_date=date.today() + timedelta(days=35),
            distance=RaceDistance.FIVE_K,
            target_time_sec=1200,
        )

        assert goal.weeks_until_race == 5

    def test_race_goal_to_dict(self):
        """Test serialization."""
        goal = RaceGoal(
            race_date=date.today() + timedelta(days=30),
            distance=RaceDistance.TEN_K,
            target_time_sec=2400,
        )

        d = goal.to_dict()

        assert "race_date" in d
        assert "distance" in d
        assert "target_pace_formatted" in d


class TestTimeFormatting:
    """Tests for time formatting functions."""

    def test_format_time_hours(self):
        """Test formatting with hours."""
        assert format_time(3661) == "1:01:01"
        assert format_time(7200) == "2:00:00"

    def test_format_time_minutes_only(self):
        """Test formatting minutes and seconds only."""
        assert format_time(1230) == "20:30"
        assert format_time(600) == "10:00"

    def test_parse_time_hours(self):
        """Test parsing with hours."""
        assert parse_time("1:45:00") == 6300
        assert parse_time("2:00:00") == 7200

    def test_parse_time_minutes(self):
        """Test parsing minutes only."""
        assert parse_time("25:00") == 1500
        assert parse_time("10:30") == 630

    def test_parse_time_invalid(self):
        """Test invalid time format."""
        with pytest.raises(ValueError):
            parse_time("invalid")


class TestRacePrediction:
    """Tests for race time prediction."""

    def test_predict_race_time_basic(self):
        """Test basic race prediction using Riegel formula."""
        # 20 min 5K should predict ~41 min 10K
        predicted = predict_race_time(
            recent_race_time_sec=1200,  # 20 min
            recent_race_distance=RaceDistance.FIVE_K,
            target_distance=RaceDistance.TEN_K,
        )

        # Riegel: T2 = T1 * (D2/D1)^1.06
        # T2 = 1200 * (10/5)^1.06 = 1200 * 2.085 = 2502
        assert 2400 < predicted < 2600

    def test_predict_race_time_marathon(self):
        """Test marathon prediction from half."""
        # 1:30 half should predict ~3:10+ marathon
        predicted = predict_race_time(
            recent_race_time_sec=5400,  # 1:30
            recent_race_distance=RaceDistance.HALF_MARATHON,
            target_distance=RaceDistance.MARATHON,
        )

        # Should be over 2x the half time due to fatigue factor
        assert predicted > 5400 * 2.0
        assert predicted < 5400 * 2.5


class TestTrainingPaces:
    """Tests for training pace calculation."""

    def test_calculate_training_paces_basic(self):
        """Test training pace calculation."""
        goal = RaceGoal(
            race_date=date.today() + timedelta(days=90),
            distance=RaceDistance.TEN_K,
            target_time_sec=2400,  # 40 min = 4:00/km pace
        )

        paces = calculate_training_paces(goal)

        assert "easy" in paces
        assert "tempo" in paces
        assert "interval" in paces

        # Easy should be slower than goal pace
        assert paces["easy"]["pace_sec"] > goal.target_pace
        # Interval should be faster than goal pace
        assert paces["interval"]["pace_sec"] < goal.target_pace

    def test_calculate_training_paces_has_formatted(self):
        """Test that paces include formatted strings."""
        goal = RaceGoal(
            race_date=date.today() + timedelta(days=90),
            distance=RaceDistance.FIVE_K,
            target_time_sec=1200,
        )

        paces = calculate_training_paces(goal)

        for pace_type in paces:
            assert "pace_formatted" in paces[pace_type]
            assert "/km" in paces[pace_type]["pace_formatted"]


class TestGoalProgress:
    """Tests for goal progress assessment."""

    def test_assess_goal_progress_on_track(self):
        """Test goal progress when on track."""
        goal = RaceGoal(
            race_date=date.today() + timedelta(days=120),
            distance=RaceDistance.TEN_K,
            target_time_sec=2400,  # 40 min
        )

        progress = assess_goal_progress(
            goal=goal,
            current_fitness={"ctl": 50},
            recent_activities=[
                {
                    "distance_km": 10,
                    "duration_min": 42,  # 42 min 10K = close to goal
                    "hrss": 80,
                }
            ],
        )

        assert progress.weeks_remaining > 0
        assert len(progress.recommendations) > 0

    def test_assess_goal_progress_no_data(self):
        """Test goal progress with no activity data."""
        goal = RaceGoal(
            race_date=date.today() + timedelta(days=60),
            distance=RaceDistance.FIVE_K,
            target_time_sec=1200,
        )

        progress = assess_goal_progress(
            goal=goal,
            current_fitness={"ctl": 30},
            recent_activities=[],
        )

        # Should still provide recommendations
        assert len(progress.recommendations) > 0


class TestVDOT:
    """Tests for VDOT calculation."""

    def test_calculate_vdot_5k(self):
        """Test VDOT calculation for 5K."""
        # 20 min 5K (4:00/km) should give VDOT around 45
        vdot = calculate_vdot(1200, RaceDistance.FIVE_K)
        assert 40 < vdot < 55

    def test_calculate_vdot_range(self):
        """Test VDOT stays in reasonable range."""
        # Very fast 5K
        vdot_fast = calculate_vdot(780, RaceDistance.FIVE_K)  # 13 min
        assert vdot_fast <= 85

        # Slow 5K
        vdot_slow = calculate_vdot(2400, RaceDistance.FIVE_K)  # 40 min
        assert vdot_slow >= 20


class TestWeeklyAnalysisDataclass:
    """Tests for WeeklyAnalysis dataclass."""

    def test_to_dict(self):
        """Test serialization."""
        analysis = WeeklyAnalysis(
            week_start=date(2024, 1, 1),
            week_end=date(2024, 1, 7),
            total_distance_km=50.5,
            total_duration_min=300,
            total_load=350,
            activity_count=5,
            zone1_pct=20.5,
            zone2_pct=55.0,
            zone3_pct=15.0,
            zone4_pct=8.0,
            zone5_pct=1.5,
            week_over_week_change=10.0,
            is_recovery_week=False,
            load_vs_target=95.0,
            ctl_change=2.5,
            atl_change=5.0,
        )

        d = analysis.to_dict()

        assert d["week_start"] == "2024-01-01"
        assert d["activity_count"] == 5
        assert "zone_distribution" in d

    def test_to_json(self):
        """Test JSON serialization."""
        analysis = WeeklyAnalysis(
            week_start=date(2024, 1, 1),
            week_end=date(2024, 1, 7),
            total_distance_km=50,
            total_duration_min=300,
            total_load=350,
            activity_count=5,
            zone1_pct=20,
            zone2_pct=55,
            zone3_pct=15,
            zone4_pct=8,
            zone5_pct=2,
            week_over_week_change=0,
            is_recovery_week=False,
            load_vs_target=95,
            ctl_change=2,
            atl_change=5,
        )

        json_str = analysis.to_json()
        assert isinstance(json_str, str)
        assert "2024-01-01" in json_str


class TestZoneBarChart:
    """Tests for zone bar chart generation."""

    def test_generate_zone_bar_chart(self):
        """Test zone bar chart generation."""
        analysis = WeeklyAnalysis(
            week_start=date(2024, 1, 1),
            week_end=date(2024, 1, 7),
            total_distance_km=50,
            total_duration_min=300,
            total_load=350,
            activity_count=5,
            zone1_pct=20,
            zone2_pct=55,
            zone3_pct=15,
            zone4_pct=8,
            zone5_pct=2,
            week_over_week_change=0,
            is_recovery_week=False,
            load_vs_target=95,
            ctl_change=2,
            atl_change=5,
        )

        chart = generate_zone_bar_chart(analysis)

        assert "Zone Distribution" in chart
        assert "Z1" in chart
        assert "Z5" in chart
        assert "#" in chart  # Bar characters
