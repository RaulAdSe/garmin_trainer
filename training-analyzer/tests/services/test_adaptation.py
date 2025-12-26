"""Tests for the WorkoutAdaptationEngine."""

import pytest
from datetime import date, timedelta
from training_analyzer.services.adaptation import (
    AdaptationRecommendation,
    AdaptationTrigger,
    AdaptationType,
    PerformanceTrend,
    WorkoutAdaptationEngine,
    WorkoutCompletion,
    WorkoutPrediction,
    get_adaptation_engine,
)


class TestWorkoutCompletion:
    """Tests for WorkoutCompletion dataclass."""

    def test_completed_workout(self):
        """Test a completed workout."""
        completion = WorkoutCompletion(
            workout_id="test_1",
            planned_date=date.today(),
            completed_date=date.today(),
            planned_duration_min=60,
            planned_load=80.0,
            planned_type="tempo",
            actual_duration_min=55,
            actual_load=75.0,
        )

        assert completion.was_completed is True
        assert completion.compliance_pct is not None
        assert completion.compliance_pct == pytest.approx(93.75, rel=0.01)

    def test_uncompleted_workout(self):
        """Test an uncompleted workout."""
        completion = WorkoutCompletion(
            workout_id="test_2",
            planned_date=date.today(),
            completed_date=None,
            planned_duration_min=60,
            planned_load=80.0,
            planned_type="tempo",
        )

        assert completion.was_completed is False
        assert completion.compliance_pct is None

    def test_duration_compliance(self):
        """Test duration compliance calculation."""
        completion = WorkoutCompletion(
            workout_id="test_3",
            planned_date=date.today(),
            completed_date=date.today(),
            planned_duration_min=60,
            planned_load=80.0,
            planned_type="easy",
            actual_duration_min=45,
            actual_load=60.0,
        )

        assert completion.duration_compliance_pct == 75.0

    def test_to_dict(self):
        """Test serialization."""
        completion = WorkoutCompletion(
            workout_id="test_4",
            planned_date=date.today(),
            completed_date=date.today(),
            planned_duration_min=60,
            planned_load=80.0,
            planned_type="intervals",
            actual_duration_min=60,
            actual_load=85.0,
            rpe=7,
            feeling="good",
        )

        data = completion.to_dict()

        assert data["workout_id"] == "test_4"
        assert data["was_completed"] is True
        assert data["rpe"] == 7
        assert data["feeling"] == "good"


class TestPerformanceTrend:
    """Tests for PerformanceTrend."""

    def test_improving_trend(self):
        """Test detection of improving trend."""
        trend = PerformanceTrend(
            metric_name="load",
            period_days=14,
            values=[50.0, 55.0, 60.0, 65.0, 70.0, 75.0, 80.0],
            dates=[date.today() - timedelta(days=i) for i in range(7, 0, -1)],
        )

        assert trend.trend_direction == "improving"
        assert trend.change_pct is not None
        assert trend.change_pct > 0

    def test_declining_trend(self):
        """Test detection of declining trend."""
        trend = PerformanceTrend(
            metric_name="load",
            period_days=14,
            values=[80.0, 75.0, 70.0, 65.0, 60.0, 55.0, 50.0],
            dates=[date.today() - timedelta(days=i) for i in range(7, 0, -1)],
        )

        assert trend.trend_direction == "declining"
        assert trend.change_pct is not None
        assert trend.change_pct < 0

    def test_stable_trend(self):
        """Test detection of stable trend."""
        trend = PerformanceTrend(
            metric_name="load",
            period_days=14,
            values=[60.0, 61.0, 59.0, 60.5, 60.0, 59.5, 60.0],
            dates=[date.today() - timedelta(days=i) for i in range(7, 0, -1)],
        )

        assert trend.trend_direction == "stable"

    def test_insufficient_data(self):
        """Test handling of insufficient data."""
        trend = PerformanceTrend(
            metric_name="load",
            period_days=14,
            values=[60.0, 65.0],
            dates=[date.today(), date.today() - timedelta(days=1)],
        )

        assert trend.trend_direction == "insufficient_data"

    def test_current_and_average(self):
        """Test current and average value properties."""
        trend = PerformanceTrend(
            metric_name="rpe",
            period_days=7,
            values=[5.0, 6.0, 7.0, 6.0, 5.0],
            dates=[date.today() - timedelta(days=i) for i in range(5, 0, -1)],
        )

        assert trend.current_value == 5.0
        assert trend.average_value == 5.8


class TestWorkoutAdaptationEngine:
    """Tests for WorkoutAdaptationEngine."""

    @pytest.fixture
    def engine(self):
        """Create a fresh engine for each test."""
        return WorkoutAdaptationEngine()

    @pytest.fixture
    def sample_completions(self):
        """Create sample workout completions."""
        completions = []
        for i in range(14):
            completed = i % 5 != 0  # Skip every 5th workout
            completions.append(WorkoutCompletion(
                workout_id=f"workout_{i}",
                planned_date=date.today() - timedelta(days=13 - i),
                completed_date=date.today() - timedelta(days=13 - i) if completed else None,
                planned_duration_min=60,
                planned_load=70.0,
                planned_type="easy" if i % 2 == 0 else "tempo",
                actual_duration_min=55 if completed else None,
                actual_load=65.0 if completed else None,
                rpe=5 if completed else None,
            ))
        return completions

    def test_compliance_rate_empty(self, engine):
        """Test compliance rate with no data."""
        rate = engine.get_compliance_rate(14)
        assert rate == 100.0  # Default when no data

    def test_compliance_rate_with_data(self, engine, sample_completions):
        """Test compliance rate with data."""
        for c in sample_completions:
            engine.record_completion(c)

        rate = engine.get_compliance_rate(14)
        # 3 out of 14 not completed = ~78% completion
        assert 70 <= rate <= 90

    def test_load_compliance(self, engine, sample_completions):
        """Test load compliance calculation."""
        for c in sample_completions:
            engine.record_completion(c)

        load_compliance = engine.get_load_compliance(14)
        # Actual load 65 vs planned 70 = ~93%
        assert 85 <= load_compliance <= 100

    def test_analyze_trends(self, engine, sample_completions):
        """Test trend analysis."""
        for c in sample_completions:
            engine.record_completion(c)

        trend = engine.analyze_trends("load", 14)

        assert trend.metric_name == "load"
        assert len(trend.values) > 0

    def test_predict_workout_outcome_fresh(self, engine):
        """Test prediction for fresh athlete."""
        prediction = engine.predict_workout_outcome(
            workout_id="test_workout",
            planned_date=date.today() + timedelta(days=1),
            planned_type="tempo",
            planned_load=75.0,
            current_ctl=50.0,
            current_atl=45.0,
            current_tsb=5.0,  # Fresh
        )

        assert prediction.predicted_completion_probability > 0.8
        assert prediction.predicted_quality in ["excellent", "good"]
        assert prediction.injury_risk == "low"

    def test_predict_workout_outcome_fatigued(self, engine):
        """Test prediction for fatigued athlete."""
        prediction = engine.predict_workout_outcome(
            workout_id="test_workout",
            planned_date=date.today() + timedelta(days=1),
            planned_type="intervals",
            planned_load=90.0,
            current_ctl=40.0,
            current_atl=65.0,  # High fatigue
            current_tsb=-25.0,  # Very negative
        )

        # High ACWR should trigger warnings
        assert prediction.injury_risk in ["moderate", "high"]
        assert prediction.predicted_quality in ["moderate", "poor"]

    def test_generate_adaptations_optimal(self, engine):
        """Test adaptation generation for optimal state."""
        recommendations = engine.generate_adaptations(
            current_ctl=50.0,
            current_atl=50.0,
            current_tsb=0.0,  # Balanced
        )

        # No major adaptations needed for balanced state
        high_priority = [r for r in recommendations if r.confidence > 0.8]
        assert len(high_priority) == 0

    def test_generate_adaptations_overreaching(self, engine):
        """Test adaptation generation for overreaching."""
        recommendations = engine.generate_adaptations(
            current_ctl=40.0,
            current_atl=65.0,  # ACWR = 1.625 > 1.5
            current_tsb=-25.0,
        )

        # Should recommend reducing load
        overreach_recs = [
            r for r in recommendations
            if r.trigger == AdaptationTrigger.OVERREACHING
        ]
        assert len(overreach_recs) >= 1
        assert any(r.volume_multiplier < 1.0 for r in overreach_recs)

    def test_generate_adaptations_race_taper(self, engine):
        """Test adaptation generation for race taper."""
        race_date = date.today() + timedelta(days=5)

        recommendations = engine.generate_adaptations(
            current_ctl=55.0,
            current_atl=50.0,
            current_tsb=5.0,
            upcoming_race_date=race_date,
        )

        # Should recommend taper
        taper_recs = [
            r for r in recommendations
            if r.trigger == AdaptationTrigger.RACE_TAPER
        ]
        assert len(taper_recs) >= 1
        assert any(r.volume_multiplier < 0.6 for r in taper_recs)

    def test_apply_adaptation(self, engine):
        """Test applying an adaptation to a workout."""
        recommendation = AdaptationRecommendation(
            trigger=AdaptationTrigger.OVERREACHING,
            adaptation_type=AdaptationType.REDUCE_VOLUME,
            target_workout_id=None,
            target_date=date.today(),
            volume_multiplier=0.7,
            intensity_multiplier=0.9,
            reason="Test adaptation",
        )

        original_load = 100.0
        original_duration = 60

        adjusted_load, adjusted_duration = engine.apply_adaptation(
            recommendation, original_load, original_duration
        )

        assert adjusted_load == 100.0 * 0.7 * 0.9  # 63.0
        assert adjusted_duration == 42  # 60 * 0.7
        assert recommendation.applied is True

    def test_get_adaptation_summary(self, engine, sample_completions):
        """Test getting adaptation summary."""
        for c in sample_completions:
            engine.record_completion(c)

        summary = engine.get_adaptation_summary()

        assert "total_completions" in summary
        assert summary["total_completions"] == 14
        assert "compliance_rate_14d" in summary
        assert "trends" in summary

    def test_singleton(self):
        """Test singleton pattern."""
        engine1 = get_adaptation_engine()
        engine2 = get_adaptation_engine()
        assert engine1 is engine2


class TestAdaptationRecommendation:
    """Tests for AdaptationRecommendation."""

    def test_recommendation_to_dict(self):
        """Test recommendation serialization."""
        rec = AdaptationRecommendation(
            trigger=AdaptationTrigger.RECOVERY_NEEDED,
            adaptation_type=AdaptationType.ADD_RECOVERY,
            target_workout_id="workout_123",
            target_date=date.today(),
            volume_multiplier=0.5,
            intensity_multiplier=0.6,
            reason="High fatigue detected",
            confidence=0.85,
        )

        data = rec.to_dict()

        assert data["trigger"] == "recovery_needed"
        assert data["adaptation_type"] == "add_recovery"
        assert data["volume_multiplier"] == 0.5
        assert data["confidence"] == 0.85

