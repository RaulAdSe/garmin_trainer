"""Tests for the recommendations module."""

import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from training_analyzer.recommendations.readiness import (
    ReadinessFactors,
    ReadinessResult,
    calculate_readiness,
    calculate_hrv_score,
    calculate_sleep_score,
    calculate_stress_score,
    calculate_training_load_score,
    calculate_recovery_days_score,
    DEFAULT_WEIGHTS,
)
from training_analyzer.recommendations.workout import (
    WorkoutType,
    WorkoutRecommendation,
    recommend_workout,
    get_workout_description,
    WORKOUT_TEMPLATES,
)
from training_analyzer.recommendations.explain import (
    explain_readiness,
    explain_workout,
    generate_daily_narrative,
    format_training_status,
    format_readiness_factors,
)


class TestHRVScore:
    """Test HRV score calculation."""

    def test_hrv_at_baseline(self):
        """HRV at baseline (ratio=1.0) should give ~75 points."""
        score = calculate_hrv_score(50, 50, None)
        assert score is not None
        assert 70 <= score <= 80

    def test_hrv_above_baseline(self):
        """HRV above baseline should give higher score."""
        score = calculate_hrv_score(60, 50, None)
        assert score is not None
        assert score > 80

    def test_hrv_significantly_above(self):
        """HRV 20%+ above baseline should max out."""
        score = calculate_hrv_score(62, 50, None)  # 24% above
        assert score is not None
        assert score >= 95

    def test_hrv_below_baseline(self):
        """HRV below baseline should give lower score."""
        score = calculate_hrv_score(40, 50, None)  # 20% below
        assert score is not None
        assert score < 70

    def test_hrv_significantly_below(self):
        """Very low HRV should give very low score."""
        score = calculate_hrv_score(25, 50, None)  # 50% below
        assert score is not None
        assert score <= 30

    def test_hrv_status_high_bonus(self):
        """HIGH status should add bonus."""
        score_without = calculate_hrv_score(50, 50, None)
        score_with = calculate_hrv_score(50, 50, "HIGH")
        assert score_with > score_without

    def test_hrv_status_low_penalty(self):
        """LOW status should add penalty."""
        score_without = calculate_hrv_score(50, 50, None)
        score_with = calculate_hrv_score(50, 50, "LOW")
        assert score_with < score_without

    def test_hrv_missing_data(self):
        """Missing data should return None."""
        assert calculate_hrv_score(None, 50, None) is None
        assert calculate_hrv_score(50, None, None) is None
        assert calculate_hrv_score(50, 0, None) is None


class TestSleepScore:
    """Test sleep score calculation."""

    def test_perfect_sleep(self):
        """8 hours with 20% deep sleep should give high score."""
        score = calculate_sleep_score(8.0, 20.0)
        assert score is not None
        assert score >= 95

    def test_good_sleep(self):
        """7 hours with good deep sleep should give good score."""
        score = calculate_sleep_score(7.0, 18.0)
        assert score is not None
        assert 75 <= score <= 95

    def test_short_sleep(self):
        """Less than 6 hours should give lower score."""
        score = calculate_sleep_score(5.5, 18.0)
        assert score is not None
        assert score < 75

    def test_very_short_sleep(self):
        """Very short sleep should give low score."""
        score = calculate_sleep_score(4.0, 15.0)
        assert score is not None
        assert score < 60

    def test_use_garmin_sleep_score(self):
        """Should use Garmin sleep score if provided."""
        score = calculate_sleep_score(5.0, 10.0, sleep_score=85)
        assert score == 85.0

    def test_no_deep_sleep_data(self):
        """Should still work without deep sleep data."""
        score = calculate_sleep_score(7.5)
        assert score is not None
        assert score > 50

    def test_efficiency_bonus(self):
        """High efficiency should add bonus."""
        score_without = calculate_sleep_score(7.0, 18.0, sleep_efficiency=None)
        score_with = calculate_sleep_score(7.0, 18.0, sleep_efficiency=95)
        assert score_with > score_without

    def test_efficiency_penalty(self):
        """Low efficiency should add penalty."""
        score_without = calculate_sleep_score(7.0, 18.0, sleep_efficiency=None)
        score_with = calculate_sleep_score(7.0, 18.0, sleep_efficiency=60)
        assert score_with < score_without

    def test_missing_data(self):
        """Missing data should return None."""
        assert calculate_sleep_score(None) is None


class TestStressScore:
    """Test stress score calculation."""

    def test_low_stress(self):
        """Low stress should give high score."""
        score = calculate_stress_score(20)
        assert score is not None
        assert score >= 75

    def test_high_stress(self):
        """High stress should give low score."""
        score = calculate_stress_score(80)
        assert score is not None
        assert score <= 30

    def test_medium_stress(self):
        """Medium stress should give medium score."""
        score = calculate_stress_score(50)
        assert score is not None
        assert 40 <= score <= 60

    def test_prolonged_high_stress_penalty(self):
        """Prolonged high stress should reduce score."""
        # High stress ratio
        score = calculate_stress_score(
            50,
            rest_stress_duration=1000,
            high_stress_duration=3000,
        )
        # Regular stress
        score_regular = calculate_stress_score(50)
        assert score < score_regular

    def test_missing_data(self):
        """Missing data should return None."""
        assert calculate_stress_score(None) is None


class TestTrainingLoadScore:
    """Test training load score calculation."""

    def test_optimal_zone(self):
        """Optimal TSB and ACWR should give high score."""
        score = calculate_training_load_score(tsb=10, acwr=1.0)
        assert score is not None
        assert score >= 75

    def test_fresh_positive_tsb(self):
        """Very positive TSB should give high score."""
        score = calculate_training_load_score(tsb=25, acwr=1.0)
        assert score is not None
        assert score >= 85

    def test_fatigued_negative_tsb(self):
        """Negative TSB should give lower score."""
        score = calculate_training_load_score(tsb=-20, acwr=1.1)
        assert score is not None
        assert score < 70

    def test_danger_zone_acwr(self):
        """High ACWR (danger) should give low score."""
        score = calculate_training_load_score(tsb=0, acwr=1.6)
        assert score is not None
        assert score < 50

    def test_undertrained_acwr(self):
        """Low ACWR (undertrained) should give moderate score."""
        score = calculate_training_load_score(tsb=0, acwr=0.7)
        assert score is not None
        assert 50 <= score <= 80

    def test_caution_zone_acwr(self):
        """Caution ACWR should give lower score."""
        score_optimal = calculate_training_load_score(tsb=0, acwr=1.0)
        score_caution = calculate_training_load_score(tsb=0, acwr=1.4)
        assert score_caution < score_optimal

    def test_missing_data(self):
        """Should return None if no data."""
        assert calculate_training_load_score(None, None) is None

    def test_partial_data(self):
        """Should work with partial data."""
        # Only TSB
        score_tsb = calculate_training_load_score(tsb=10, acwr=None)
        assert score_tsb is not None

        # Only ACWR
        score_acwr = calculate_training_load_score(tsb=None, acwr=1.0)
        assert score_acwr is not None


class TestRecoveryDaysScore:
    """Test recovery days score calculation."""

    def test_just_trained(self):
        """0 days since hard workout should give low score."""
        score = calculate_recovery_days_score(0)
        assert score <= 40

    def test_one_day_recovery(self):
        """1 day recovery should give moderate score."""
        score = calculate_recovery_days_score(1)
        assert 50 <= score <= 70

    def test_two_days_recovery(self):
        """2 days recovery should give good score."""
        score = calculate_recovery_days_score(2)
        assert score >= 80

    def test_three_plus_days_recovery(self):
        """3+ days should give high score."""
        score = calculate_recovery_days_score(3)
        assert score >= 90


class TestReadinessCalculation:
    """Test overall readiness calculation."""

    def test_calculate_with_all_data(self):
        """Calculate readiness with complete data."""
        wellness_data = {
            "hrv": {"hrv_last_night_avg": 55, "hrv_weekly_avg": 50, "hrv_status": "BALANCED"},
            "sleep": {"total_sleep_hours": 7.5, "deep_sleep_pct": 18},
            "stress": {"avg_stress_level": 30, "body_battery_charged": 75},
        }
        fitness_metrics = {"tsb": 10, "acwr": 1.05}
        recent_activities = [
            {"date": (date.today() - timedelta(days=2)).isoformat(), "hrss": 80}
        ]

        result = calculate_readiness(
            wellness_data=wellness_data,
            fitness_metrics=fitness_metrics,
            recent_activities=recent_activities,
        )

        assert isinstance(result, ReadinessResult)
        assert 0 <= result.overall_score <= 100
        assert result.zone in ["green", "yellow", "red"]
        assert result.recommendation
        assert result.explanation

    def test_calculate_with_no_data(self):
        """Calculate readiness with no data should still return a result."""
        result = calculate_readiness(
            wellness_data=None,
            fitness_metrics=None,
            recent_activities=[],
        )

        assert isinstance(result, ReadinessResult)
        # With no data, defaults to conservative estimate
        # recovery_days=0 (default) means just trained, giving low recovery score
        assert 0 <= result.overall_score <= 100
        assert result.zone in ["green", "yellow", "red"]

    def test_green_zone_high_score(self):
        """High readiness should be green zone."""
        wellness_data = {
            "hrv": {"hrv_last_night_avg": 60, "hrv_weekly_avg": 50},
            "sleep": {"total_sleep_hours": 8, "deep_sleep_pct": 20},
            "stress": {"body_battery_charged": 90},
        }
        fitness_metrics = {"tsb": 20, "acwr": 1.0}

        result = calculate_readiness(
            wellness_data=wellness_data,
            fitness_metrics=fitness_metrics,
            recent_activities=[],
        )

        assert result.zone == "green"
        assert result.overall_score >= 67

    def test_red_zone_low_score(self):
        """Low readiness should be red zone."""
        wellness_data = {
            "hrv": {"hrv_last_night_avg": 25, "hrv_weekly_avg": 50},
            "sleep": {"total_sleep_hours": 4, "deep_sleep_pct": 10},
            "stress": {"avg_stress_level": 80, "body_battery_charged": 20},
        }
        fitness_metrics = {"tsb": -30, "acwr": 1.6}

        result = calculate_readiness(
            wellness_data=wellness_data,
            fitness_metrics=fitness_metrics,
            recent_activities=[],
        )

        assert result.zone == "red"
        assert result.overall_score < 34


class TestWorkoutRecommendation:
    """Test workout recommendation logic."""

    def test_low_readiness_rest(self):
        """Very low readiness should recommend rest."""
        rec = recommend_workout(
            readiness_score=20,
            acwr=1.0,
            tsb=0,
            days_since_hard=1,
            days_since_long=3,
            weekly_load_so_far=100,
            target_weekly_load=300,
        )

        assert rec.workout_type == WorkoutType.REST
        assert len(rec.warnings) > 0

    def test_low_readiness_recovery(self):
        """Low readiness (25-40) should recommend recovery."""
        rec = recommend_workout(
            readiness_score=35,
            acwr=1.0,
            tsb=0,
            days_since_hard=1,
            days_since_long=3,
            weekly_load_so_far=100,
            target_weekly_load=300,
        )

        assert rec.workout_type == WorkoutType.RECOVERY

    def test_high_acwr_danger(self):
        """High ACWR (danger zone) should recommend rest."""
        rec = recommend_workout(
            readiness_score=80,
            acwr=1.6,
            tsb=10,
            days_since_hard=2,
            days_since_long=3,
            weekly_load_so_far=100,
            target_weekly_load=300,
        )

        assert rec.workout_type == WorkoutType.REST
        assert "injury" in rec.reason.lower() or "danger" in rec.reason.lower()

    def test_high_acwr_caution(self):
        """Elevated ACWR should recommend easy day."""
        rec = recommend_workout(
            readiness_score=80,
            acwr=1.4,
            tsb=10,
            days_since_hard=2,
            days_since_long=3,
            weekly_load_so_far=100,
            target_weekly_load=300,
        )

        assert rec.workout_type == WorkoutType.EASY
        assert "acwr" in rec.reason.lower() or "load" in rec.reason.lower()

    def test_hard_easy_pattern(self):
        """Day after hard workout should be easy."""
        rec = recommend_workout(
            readiness_score=80,
            acwr=1.0,
            tsb=10,
            days_since_hard=0,  # Yesterday was hard
            days_since_long=3,
            weekly_load_so_far=100,
            target_weekly_load=300,
        )

        assert rec.workout_type in [WorkoutType.EASY, WorkoutType.RECOVERY]
        assert "hard" in rec.reason.lower() or "pattern" in rec.reason.lower()

    def test_undertrained_can_push(self):
        """Undertrained with high readiness should recommend intensity."""
        rec = recommend_workout(
            readiness_score=85,
            acwr=0.7,  # Undertrained
            tsb=15,
            days_since_hard=3,
            days_since_long=5,
            weekly_load_so_far=50,
            target_weekly_load=300,
        )

        assert rec.workout_type.intensity_level >= 3  # Tempo or harder
        assert "undertrained" in rec.reason.lower()

    def test_high_readiness_quality_work(self):
        """High readiness with good recovery should allow quality work."""
        rec = recommend_workout(
            readiness_score=85,
            acwr=1.0,
            tsb=15,
            days_since_hard=2,
            days_since_long=5,
            weekly_load_so_far=100,
            target_weekly_load=300,
        )

        assert rec.workout_type.intensity_level >= 3

    def test_long_run_due(self):
        """When due for long run and well recovered, should recommend long."""
        rec = recommend_workout(
            readiness_score=85,
            acwr=1.0,
            tsb=15,
            days_since_hard=2,
            days_since_long=7,  # Week since long run
            weekly_load_so_far=100,
            target_weekly_load=300,
        )

        assert rec.workout_type == WorkoutType.LONG

    def test_recommendation_has_duration(self):
        """Recommendations should have valid duration."""
        rec = recommend_workout(
            readiness_score=70,
            acwr=1.0,
            tsb=0,
            days_since_hard=1,
            days_since_long=3,
            weekly_load_so_far=100,
            target_weekly_load=300,
        )

        if rec.workout_type != WorkoutType.REST:
            assert rec.duration_min > 0


class TestWorkoutDescriptions:
    """Test workout type descriptions."""

    def test_all_types_have_descriptions(self):
        """All workout types should have descriptions."""
        for workout_type in WorkoutType:
            desc = get_workout_description(workout_type)
            assert "name" in desc
            assert "summary" in desc
            assert "purpose" in desc

    def test_all_types_have_templates(self):
        """All workout types should have templates."""
        for workout_type in WorkoutType:
            assert workout_type in WORKOUT_TEMPLATES


class TestExplanations:
    """Test explanation generation."""

    def test_explain_readiness(self):
        """Should generate readiness explanation."""
        factors = ReadinessFactors(
            hrv_score=85,
            sleep_score=75,
            body_battery=70,
            training_load_score=80,
            recovery_days=2,
        )

        explanation = explain_readiness(factors, 78)

        assert len(explanation) > 0
        assert isinstance(explanation, str)

    def test_explain_readiness_with_issues(self):
        """Should highlight issues in explanation."""
        factors = ReadinessFactors(
            hrv_score=45,  # Low
            sleep_score=40,  # Low
            body_battery=30,  # Low
            training_load_score=35,  # Low
            recovery_days=0,
        )

        explanation = explain_readiness(factors, 35)

        # Should mention limiting factors
        assert "sleep" in explanation.lower() or "hrv" in explanation.lower()

    def test_explain_workout(self):
        """Should generate workout explanation."""
        rec = WorkoutRecommendation(
            workout_type=WorkoutType.TEMPO,
            duration_min=45,
            intensity_description="Comfortably hard pace",
            hr_zone_target="Zone 3-4",
            reason="Good recovery, time for quality",
            alternatives=["Long run", "Easy run"],
            warnings=[],
        )

        explanation = explain_workout(rec)

        assert "tempo" in explanation.lower()
        assert "45" in explanation
        assert "zone 3-4" in explanation.lower()

    def test_generate_daily_narrative(self):
        """Should generate cohesive daily narrative."""
        readiness = ReadinessResult(
            date=date.today(),
            overall_score=78,
            factors=ReadinessFactors(
                hrv_score=80,
                sleep_score=75,
                training_load_score=80,
            ),
            zone="green",
            recommendation="Good day for moderate training",
            explanation="Well recovered",
        )

        rec = WorkoutRecommendation(
            workout_type=WorkoutType.TEMPO,
            duration_min=45,
            intensity_description="Comfortably hard",
            hr_zone_target="Zone 3-4",
            reason="Ready for quality work",
            alternatives=[],
            warnings=[],
        )

        narrative = generate_daily_narrative(readiness, rec)

        assert len(narrative) > 0
        assert "78" in narrative or "readiness" in narrative.lower()

    def test_format_training_status(self):
        """Should format training status correctly."""
        formatted = format_training_status(
            ctl=45.2,
            atl=52.1,
            tsb=-6.9,
            acwr=1.15,
            risk_zone="optimal",
        )

        assert "45.2" in formatted
        assert "52.1" in formatted
        assert "-6.9" in formatted
        assert "1.15" in formatted

    def test_format_readiness_factors(self):
        """Should format readiness factors correctly."""
        factors = ReadinessFactors(
            hrv_score=80,
            sleep_score=75,
            body_battery=70,
            recovery_days=2,
        )

        formatted = format_readiness_factors(factors)

        assert "80" in formatted
        assert "75" in formatted
        assert "70" in formatted
        assert "2" in formatted


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_readiness_score_bounds(self):
        """Readiness scores should be 0-100."""
        # Very good data
        result = calculate_readiness(
            wellness_data={
                "hrv": {"hrv_last_night_avg": 100, "hrv_weekly_avg": 50},
                "sleep": {"total_sleep_hours": 10, "deep_sleep_pct": 30},
                "stress": {"body_battery_charged": 100, "avg_stress_level": 0},
            },
            fitness_metrics={"tsb": 50, "acwr": 1.0},
            recent_activities=[],
        )
        assert 0 <= result.overall_score <= 100

        # Very bad data
        result = calculate_readiness(
            wellness_data={
                "hrv": {"hrv_last_night_avg": 10, "hrv_weekly_avg": 50},
                "sleep": {"total_sleep_hours": 2, "deep_sleep_pct": 5},
                "stress": {"body_battery_charged": 5, "avg_stress_level": 100},
            },
            fitness_metrics={"tsb": -50, "acwr": 2.0},
            recent_activities=[],
        )
        assert 0 <= result.overall_score <= 100

    def test_workout_with_extreme_inputs(self):
        """Workout recommendation should handle extreme inputs."""
        # All zeros
        rec = recommend_workout(
            readiness_score=0,
            acwr=0,
            tsb=0,
            days_since_hard=0,
            days_since_long=0,
            weekly_load_so_far=0,
            target_weekly_load=0,
        )
        assert isinstance(rec, WorkoutRecommendation)

        # Very high values
        rec = recommend_workout(
            readiness_score=100,
            acwr=3.0,
            tsb=50,
            days_since_hard=30,
            days_since_long=30,
            weekly_load_so_far=1000,
            target_weekly_load=500,
        )
        assert isinstance(rec, WorkoutRecommendation)

    def test_readiness_factors_serialization(self):
        """ReadinessFactors should serialize correctly."""
        factors = ReadinessFactors(
            hrv_score=80,
            sleep_score=None,
            body_battery=70,
        )

        d = factors.to_dict()

        assert d["hrv_score"] == 80
        assert d["sleep_score"] is None
        assert d["body_battery"] == 70

    def test_readiness_result_serialization(self):
        """ReadinessResult should serialize correctly."""
        result = ReadinessResult(
            date=date.today(),
            overall_score=75.5,
            factors=ReadinessFactors(),
            zone="green",
            recommendation="Test",
            explanation="Test explanation",
        )

        d = result.to_dict()

        assert d["overall_score"] == 75.5
        assert d["zone"] == "green"
        assert "date" in d

    def test_workout_recommendation_serialization(self):
        """WorkoutRecommendation should serialize correctly."""
        rec = WorkoutRecommendation(
            workout_type=WorkoutType.EASY,
            duration_min=45,
            intensity_description="Easy",
            hr_zone_target="Zone 2",
            reason="Recovery",
            alternatives=["Rest"],
            warnings=["Watch fatigue"],
        )

        d = rec.to_dict()

        assert d["workout_type"] == "easy"
        assert d["duration_min"] == 45
        assert len(d["alternatives"]) == 1
        assert len(d["warnings"]) == 1
