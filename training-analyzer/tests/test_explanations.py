"""
Tests for the explainability module.

Tests the explanation generation for readiness and workout recommendations,
ensuring transparency in the reasoning behind recommendations.
"""

import pytest
from datetime import date

from src.models.explanations import (
    ImpactType,
    DataSourceType,
    DataSource,
    ExplanationFactor,
    ExplainedRecommendation,
    ExplainedReadiness,
    ExplainedWorkoutRecommendation,
)
from src.recommendations.readiness import calculate_explained_readiness
from src.recommendations.workout import recommend_explained_workout


class TestExplanationModels:
    """Test the explanation dataclass models."""

    def test_explanation_factor_creation(self):
        """Test creating an ExplanationFactor."""
        factor = ExplanationFactor(
            name="HRV Score",
            value=85.5,
            display_value="15% above baseline",
            impact=ImpactType.POSITIVE,
            weight=0.25,
            contribution_points=21.4,
            explanation="Excellent HRV indicating good autonomic recovery.",
            threshold="Target: > 75",
            baseline=74.0,
            data_sources=[
                DataSource(
                    source_type=DataSourceType.GARMIN_HRV,
                    source_name="Garmin HRV",
                    confidence=0.95,
                )
            ],
        )

        assert factor.name == "HRV Score"
        assert factor.value == 85.5
        assert factor.impact == ImpactType.POSITIVE
        assert len(factor.data_sources) == 1

    def test_explanation_factor_to_dict(self):
        """Test ExplanationFactor serialization."""
        factor = ExplanationFactor(
            name="Test Factor",
            value=50.0,
            display_value="50/100",
            impact=ImpactType.NEUTRAL,
            weight=0.2,
            contribution_points=10.0,
            explanation="Test explanation",
            data_sources=[
                DataSource(
                    source_type=DataSourceType.CALCULATED_TSB,
                    source_name="TSB",
                    confidence=0.9,
                )
            ],
        )

        result = factor.to_dict()

        assert result["name"] == "Test Factor"
        assert result["impact"] == "neutral"
        assert result["weight"] == 0.2
        assert len(result["data_sources"]) == 1
        assert result["data_sources"][0]["source_type"] == "calculated_tsb"

    def test_explained_recommendation_creation(self):
        """Test creating an ExplainedRecommendation."""
        factors = [
            ExplanationFactor(
                name="HRV",
                value=80,
                display_value="80/100",
                impact=ImpactType.POSITIVE,
                weight=0.25,
                contribution_points=20,
                explanation="Good HRV",
                data_sources=[],
            )
        ]

        rec = ExplainedRecommendation(
            recommendation="Ready for quality training",
            confidence=0.85,
            confidence_explanation="High confidence based on available data",
            factors=factors,
            data_points={"hrv": 80},
            calculation_summary="HRV: 80 x 0.25 = 20",
            alternatives_considered=["Easy run", "Rest"],
            key_driver="HRV",
        )

        assert rec.confidence == 0.85
        assert rec.key_driver == "HRV"
        assert len(rec.factors) == 1

    def test_explained_recommendation_get_factors(self):
        """Test getting positive and negative factors."""
        factors = [
            ExplanationFactor(
                name="Good Factor",
                value=90,
                display_value="90",
                impact=ImpactType.POSITIVE,
                weight=0.3,
                contribution_points=27,
                explanation="Positive impact",
                data_sources=[],
            ),
            ExplanationFactor(
                name="Bad Factor",
                value=30,
                display_value="30",
                impact=ImpactType.NEGATIVE,
                weight=0.3,
                contribution_points=-15,
                explanation="Negative impact",
                data_sources=[],
            ),
            ExplanationFactor(
                name="Neutral Factor",
                value=50,
                display_value="50",
                impact=ImpactType.NEUTRAL,
                weight=0.2,
                contribution_points=10,
                explanation="Neutral",
                data_sources=[],
            ),
        ]

        rec = ExplainedRecommendation(
            recommendation="Test",
            confidence=0.8,
            confidence_explanation="Test",
            factors=factors,
            data_points={},
            calculation_summary="",
        )

        positive = rec.get_positive_factors()
        negative = rec.get_negative_factors()
        limiting = rec.get_limiting_factor()

        assert len(positive) == 1
        assert positive[0].name == "Good Factor"
        assert len(negative) == 1
        assert negative[0].name == "Bad Factor"
        assert limiting.name == "Bad Factor"


class TestExplainedReadiness:
    """Test the explained readiness calculation."""

    def test_explained_readiness_with_full_data(self):
        """Test explained readiness with complete wellness data."""
        wellness_data = {
            "hrv": {
                "hrv_last_night_avg": 55,
                "hrv_weekly_avg": 50,
                "hrv_status": "BALANCED",
            },
            "sleep": {
                "total_sleep_hours": 7.5,
                "deep_sleep_pct": 22,
            },
            "body_battery": {
                "current": 75,
            },
            "stress": {
                "avg_stress_level": 35,
            },
        }

        fitness_metrics = {
            "tsb": 5.0,
            "acwr": 1.1,
            "ctl": 60,
            "atl": 55,
        }

        recent_activities = [
            {"date": date.today().isoformat(), "hrss": 50},
        ]

        result = calculate_explained_readiness(
            wellness_data=wellness_data,
            fitness_metrics=fitness_metrics,
            recent_activities=recent_activities,
            target_date=date.today(),
        )

        assert isinstance(result, ExplainedReadiness)
        assert 0 <= result.overall_score <= 100
        assert result.zone in ["green", "yellow", "red"]
        assert len(result.factor_breakdown) > 0
        assert result.recommendation is not None
        assert result.recommendation.confidence > 0

    def test_explained_readiness_with_minimal_data(self):
        """Test explained readiness with minimal data available."""
        result = calculate_explained_readiness(
            wellness_data=None,
            fitness_metrics=None,
            recent_activities=[],
            target_date=date.today(),
        )

        assert isinstance(result, ExplainedReadiness)
        # Should still produce a result with low confidence
        assert result.recommendation.confidence < 0.7

    def test_factor_breakdown_contains_data_sources(self):
        """Test that each factor includes data source information."""
        wellness_data = {
            "hrv": {
                "hrv_last_night_avg": 55,
                "hrv_weekly_avg": 50,
            },
        }

        result = calculate_explained_readiness(
            wellness_data=wellness_data,
            fitness_metrics={"tsb": 10, "acwr": 1.0},
            recent_activities=[],
        )

        # Find HRV factor
        hrv_factor = next(
            (f for f in result.factor_breakdown if "HRV" in f.name),
            None
        )

        assert hrv_factor is not None
        assert len(hrv_factor.data_sources) > 0
        assert hrv_factor.data_sources[0].source_type == DataSourceType.GARMIN_HRV

    def test_score_calculation_summary_format(self):
        """Test that score calculation summary is properly formatted."""
        result = calculate_explained_readiness(
            wellness_data={
                "hrv": {"hrv_last_night_avg": 50, "hrv_weekly_avg": 50},
                "sleep": {"total_sleep_hours": 7},
            },
            fitness_metrics={"tsb": 5, "acwr": 1.0},
            recent_activities=[],
        )

        # Should contain calculation steps
        assert "=" in result.score_calculation
        assert "x" in result.score_calculation  # Weight multiplication


class TestExplainedWorkoutRecommendation:
    """Test the explained workout recommendation."""

    def test_explained_workout_with_good_readiness(self):
        """Test workout recommendation with high readiness."""
        result = recommend_explained_workout(
            readiness_score=85,
            acwr=1.0,
            tsb=10,
            days_since_hard=2,
            days_since_long=5,
            weekly_load_so_far=200,
            target_weekly_load=300,
        )

        assert isinstance(result, ExplainedWorkoutRecommendation)
        assert result.workout_type is not None
        assert result.duration_min > 0
        assert len(result.decision_tree) > 0
        assert result.recommendation.confidence > 0

    def test_explained_workout_with_low_readiness(self):
        """Test workout recommendation with low readiness."""
        result = recommend_explained_workout(
            readiness_score=30,
            acwr=1.5,
            tsb=-20,
            days_since_hard=0,
            days_since_long=3,
            weekly_load_so_far=350,
            target_weekly_load=300,
        )

        # Should recommend rest or easy workout
        assert result.workout_type in ["rest", "recovery", "easy"]
        assert result.readiness_influence > 0  # Readiness was a key factor

    def test_decision_tree_shows_logic(self):
        """Test that decision tree shows the logic path."""
        result = recommend_explained_workout(
            readiness_score=75,
            acwr=1.2,
            tsb=0,
            days_since_hard=1,
            days_since_long=4,
            weekly_load_so_far=150,
            target_weekly_load=300,
        )

        # Decision tree should contain rule evaluations
        decision_text = "\n".join(result.decision_tree)
        assert "RULE" in decision_text or "Input" in decision_text

    def test_workout_factors_include_all_inputs(self):
        """Test that recommendation factors cover all input metrics."""
        result = recommend_explained_workout(
            readiness_score=80,
            acwr=1.0,
            tsb=5,
            days_since_hard=2,
            days_since_long=6,
            weekly_load_so_far=200,
            target_weekly_load=300,
        )

        factor_names = [f.name for f in result.recommendation.factors]

        # Should include key factors
        assert any("TSB" in name or "Form" in name for name in factor_names)
        assert any("Recovery" in name or "Pattern" in name for name in factor_names)

    def test_influence_scores_sum_appropriately(self):
        """Test that influence scores are reasonable."""
        result = recommend_explained_workout(
            readiness_score=50,
            acwr=1.4,  # High ACWR should influence
            tsb=-5,
            days_since_hard=1,
            days_since_long=5,
            weekly_load_so_far=250,
            target_weekly_load=300,
        )

        # At least one influence should be significant
        total_influence = (
            result.readiness_influence
            + result.load_influence
            + result.pattern_influence
        )
        assert total_influence >= 0


class TestExplanationImpactTypes:
    """Test impact type determination."""

    def test_positive_impact_for_good_values(self):
        """Test that good metric values result in positive impact."""
        wellness_data = {
            "hrv": {"hrv_last_night_avg": 70, "hrv_weekly_avg": 50},
            "sleep": {"total_sleep_hours": 9, "deep_sleep_pct": 25},
        }

        result = calculate_explained_readiness(
            wellness_data=wellness_data,
            fitness_metrics={"tsb": 15, "acwr": 1.0},
            recent_activities=[],
        )

        # Good values should be positive
        positive_factors = result.recommendation.get_positive_factors()
        assert len(positive_factors) > 0

    def test_negative_impact_for_poor_values(self):
        """Test that poor metric values result in negative impact."""
        wellness_data = {
            "hrv": {"hrv_last_night_avg": 30, "hrv_weekly_avg": 50},
            "sleep": {"total_sleep_hours": 4},
        }

        result = calculate_explained_readiness(
            wellness_data=wellness_data,
            fitness_metrics={"tsb": -30, "acwr": 1.8},
            recent_activities=[],
        )

        # Poor values should be negative
        negative_factors = result.recommendation.get_negative_factors()
        assert len(negative_factors) > 0


class TestConfidenceCalculation:
    """Test confidence score calculation."""

    def test_high_confidence_with_complete_data(self):
        """Test that complete data results in high confidence."""
        wellness_data = {
            "hrv": {"hrv_last_night_avg": 55, "hrv_weekly_avg": 50},
            "sleep": {"total_sleep_hours": 7},
            "body_battery": {"current": 70},
            "stress": {"avg_stress_level": 40},
        }

        result = calculate_explained_readiness(
            wellness_data=wellness_data,
            fitness_metrics={"tsb": 5, "acwr": 1.0},
            recent_activities=[{"date": date.today().isoformat(), "hrss": 50}],
        )

        assert result.recommendation.confidence >= 0.8

    def test_low_confidence_with_sparse_data(self):
        """Test that sparse data results in lower confidence."""
        result = calculate_explained_readiness(
            wellness_data={},
            fitness_metrics=None,
            recent_activities=[],
        )

        assert result.recommendation.confidence < 0.7


class TestDataPointTracking:
    """Test that raw data points are properly tracked."""

    def test_data_points_include_input_values(self):
        """Test that data_points dictionary includes input values."""
        wellness_data = {
            "hrv": {"hrv_last_night_avg": 55, "hrv_weekly_avg": 50},
            "sleep": {"total_sleep_hours": 7.5},
        }

        result = calculate_explained_readiness(
            wellness_data=wellness_data,
            fitness_metrics={"tsb": 10, "acwr": 1.1},
            recent_activities=[],
        )

        data_points = result.recommendation.data_points

        assert "hrv" in data_points or "HRV" in str(data_points)
        assert "sleep" in data_points or "Sleep" in str(data_points)

    def test_workout_data_points_complete(self):
        """Test that workout recommendation includes all input data."""
        result = recommend_explained_workout(
            readiness_score=75,
            acwr=1.1,
            tsb=5,
            days_since_hard=2,
            days_since_long=6,
            weekly_load_so_far=200,
            target_weekly_load=300,
        )

        data_points = result.recommendation.data_points

        assert data_points["readiness_score"] == 75
        assert data_points["acwr"] == 1.1
        assert data_points["tsb"] == 5
        assert data_points["days_since_hard"] == 2
