"""Tests for the FatiguePredictionService."""

import pytest
from datetime import date, timedelta
from training_analyzer.services.fatigue_prediction import (
    ACWRAlert,
    DailyReadiness,
    FatigueLevel,
    FatiguePrediction,
    FatiguePredictionService,
    RecoveryEstimate,
    RecoveryState,
    RiskLevel,
    get_fatigue_service,
)


class TestDailyReadiness:
    """Tests for DailyReadiness dataclass."""

    def test_basic_readiness(self):
        """Test basic readiness data."""
        readiness = DailyReadiness(
            date=date.today(),
            ctl=50.0,
            atl=45.0,
            tsb=5.0,
            acwr=0.9,
        )

        assert readiness.ctl == 50.0
        assert readiness.tsb == 5.0

    def test_readiness_with_recovery_data(self):
        """Test readiness with full recovery data."""
        readiness = DailyReadiness(
            date=date.today(),
            ctl=50.0,
            atl=45.0,
            tsb=5.0,
            acwr=0.9,
            hrv_rmssd=45.0,
            resting_hr=52,
            sleep_hours=8.0,
            sleep_quality=85.0,
            perceived_fatigue=3,
            perceived_soreness=2,
            mood=8,
        )

        data = readiness.to_dict()

        assert data["hrv_rmssd"] == 45.0
        assert data["sleep_hours"] == 8.0
        assert data["perceived_fatigue"] == 3


class TestACWRAlert:
    """Tests for ACWRAlert."""

    def test_no_alert_sweet_spot(self):
        """Test no alert for ACWR in sweet spot."""
        alert = ACWRAlert.evaluate(1.0)
        assert alert is None

        alert = ACWRAlert.evaluate(1.2)
        assert alert is None

    def test_alert_undertraining(self):
        """Test alert for undertraining."""
        alert = ACWRAlert.evaluate(0.6)

        assert alert is not None
        assert alert.risk_level == RiskLevel.MODERATE
        assert "undertraining" in alert.message.lower()

    def test_alert_caution_zone(self):
        """Test alert for caution zone."""
        alert = ACWRAlert.evaluate(1.4)

        assert alert is not None
        assert alert.risk_level == RiskLevel.MODERATE
        assert "elevated" in alert.message.lower()

    def test_alert_danger_zone(self):
        """Test alert for danger zone."""
        alert = ACWRAlert.evaluate(1.7)

        assert alert is not None
        assert alert.risk_level == RiskLevel.HIGH
        assert "danger" in alert.message.lower()

    def test_alert_to_dict(self):
        """Test alert serialization."""
        alert = ACWRAlert.evaluate(1.6)

        data = alert.to_dict()

        assert "acwr" in data
        assert "risk_level" in data
        assert "recommended_action" in data


class TestFatiguePredictionService:
    """Tests for FatiguePredictionService."""

    @pytest.fixture
    def service(self):
        """Create a fresh service for each test."""
        return FatiguePredictionService()

    def test_predict_fatigue_fresh(self, service):
        """Test prediction for fresh athlete."""
        readiness = DailyReadiness(
            date=date.today(),
            ctl=50.0,
            atl=45.0,
            tsb=15.0,  # Fresh
            acwr=0.9,
            hrv_rmssd=50.0,
            sleep_hours=8.5,
            perceived_fatigue=2,
        )

        # Set baselines
        service.set_baselines(hrv_baseline=48.0, rhr_baseline=50)

        prediction = service.predict_fatigue(readiness)

        assert prediction.fatigue_level in [FatigueLevel.FRESH, FatigueLevel.RECOVERED]
        assert prediction.fatigue_score < 40
        assert prediction.recommended_intensity in ["hard", "moderate"]

    def test_predict_fatigue_exhausted(self, service):
        """Test prediction for exhausted athlete."""
        readiness = DailyReadiness(
            date=date.today(),
            ctl=40.0,
            atl=70.0,  # Very high fatigue
            tsb=-30.0,  # Very negative
            acwr=1.75,  # Danger zone
            hrv_rmssd=30.0,  # Suppressed
            sleep_hours=5.0,  # Poor sleep
            perceived_fatigue=9,
            perceived_soreness=8,
            mood=3,
        )

        # Set baselines
        service.set_baselines(hrv_baseline=48.0, rhr_baseline=50)

        prediction = service.predict_fatigue(readiness)

        assert prediction.fatigue_level in [FatigueLevel.FATIGUED, FatigueLevel.EXHAUSTED]
        assert prediction.fatigue_score > 60
        assert prediction.recommended_intensity in ["rest", "easy"]
        assert prediction.overtraining_risk in [RiskLevel.HIGH, RiskLevel.CRITICAL]

    def test_predict_fatigue_moderate(self, service):
        """Test prediction for moderately fatigued athlete."""
        readiness = DailyReadiness(
            date=date.today(),
            ctl=50.0,
            atl=55.0,
            tsb=-5.0,
            acwr=1.1,
            sleep_hours=7.0,
            perceived_fatigue=5,
        )

        prediction = service.predict_fatigue(readiness)

        assert prediction.fatigue_level in [FatigueLevel.MODERATE, FatigueLevel.RECOVERED]
        assert 30 <= prediction.fatigue_score <= 60
        assert prediction.recommended_intensity in ["easy", "moderate"]

    def test_contributing_factors(self, service):
        """Test that contributing factors are calculated."""
        readiness = DailyReadiness(
            date=date.today(),
            ctl=50.0,
            atl=50.0,
            tsb=0.0,
            acwr=1.0,
        )

        prediction = service.predict_fatigue(readiness)

        assert "tsb" in prediction.contributing_factors
        assert "acwr" in prediction.contributing_factors

    def test_record_readiness_updates_baselines(self, service):
        """Test that recording readiness updates baselines."""
        # Record multiple readiness entries
        for i in range(10):
            readiness = DailyReadiness(
                date=date.today() - timedelta(days=9 - i),
                ctl=50.0,
                atl=50.0,
                tsb=0.0,
                acwr=1.0,
                hrv_rmssd=45.0 + i,
                resting_hr=50 + (i % 3),
            )
            service.record_readiness(readiness)

        # Baselines should be set
        assert service._hrv_baseline is not None
        assert service._rhr_baseline is not None

    def test_estimate_recovery_high_fatigue(self, service):
        """Test recovery estimation for high fatigue."""
        estimate = service.estimate_recovery(
            current_fatigue_score=75.0,
            current_tsb=-20.0,
        )

        assert estimate.hours_until_recovered >= 36
        assert estimate.hours_until_fresh > estimate.hours_until_recovered
        assert "rest" in estimate.recovery_activities[0].lower() or "light" in estimate.recovery_activities[0].lower()
        assert estimate.sleep_recommendation >= 8.5

    def test_estimate_recovery_low_fatigue(self, service):
        """Test recovery estimation for low fatigue."""
        estimate = service.estimate_recovery(
            current_fatigue_score=25.0,
            current_tsb=5.0,
        )

        assert estimate.hours_until_recovered <= 24
        assert estimate.sleep_recommendation <= 8.0

    def test_check_acwr_alert_normal(self, service):
        """Test ACWR check for normal values."""
        alert = service.check_acwr_alert(ctl=50.0, atl=50.0)
        assert alert is None  # 1.0 is in sweet spot

    def test_check_acwr_alert_elevated(self, service):
        """Test ACWR check for elevated values."""
        alert = service.check_acwr_alert(ctl=40.0, atl=60.0)  # ACWR = 1.5

        assert alert is not None
        assert alert.risk_level in [RiskLevel.MODERATE, RiskLevel.HIGH]

    def test_get_fatigue_trend(self, service):
        """Test fatigue trend calculation."""
        # Record readiness history
        for i in range(14):
            readiness = DailyReadiness(
                date=date.today() - timedelta(days=13 - i),
                ctl=50.0,
                atl=50.0 + i,  # Increasing fatigue
                tsb=-i,  # Decreasing TSB
                acwr=1.0 + (i * 0.02),
            )
            service.record_readiness(readiness)

        trend = service.get_fatigue_trend(14)

        assert "trend" in trend
        assert trend["trend"] in ["recovering", "accumulating_fatigue", "stable"]
        assert trend["data_points"] == 14

    def test_get_fatigue_trend_insufficient_data(self, service):
        """Test fatigue trend with insufficient data."""
        trend = service.get_fatigue_trend(14)

        assert trend["status"] == "insufficient_data"

    def test_singleton(self):
        """Test singleton pattern."""
        service1 = get_fatigue_service()
        service2 = get_fatigue_service()
        assert service1 is service2


class TestRecoveryEstimate:
    """Tests for RecoveryEstimate."""

    def test_recovery_estimate_to_dict(self):
        """Test recovery estimate serialization."""
        estimate = RecoveryEstimate(
            hours_until_recovered=24.0,
            hours_until_fresh=36.0,
            optimal_next_hard_workout=date.today() + timedelta(days=2),
            optimal_next_easy_workout=date.today() + timedelta(days=1),
            recovery_activities=["Light stretching", "Walk"],
            sleep_recommendation=8.0,
        )

        data = estimate.to_dict()

        assert data["hours_until_recovered"] == 24.0
        assert data["sleep_recommendation"] == 8.0
        assert len(data["recovery_activities"]) == 2


class TestFatiguePrediction:
    """Tests for FatiguePrediction dataclass."""

    def test_fatigue_prediction_to_dict(self):
        """Test fatigue prediction serialization."""
        prediction = FatiguePrediction(
            date=date.today(),
            fatigue_level=FatigueLevel.MODERATE,
            fatigue_score=55.0,
            recovery_state=RecoveryState.MODERATE,
            overtraining_risk=RiskLevel.LOW,
            injury_risk=RiskLevel.LOW,
            burnout_risk=RiskLevel.LOW,
            recommended_intensity="easy",
            recovery_hours_needed=24.0,
            contributing_factors={"tsb": 45.0, "acwr": 25.0},
            confidence=0.75,
        )

        data = prediction.to_dict()

        assert data["fatigue_level"] == "moderate"
        assert data["fatigue_score"] == 55.0
        assert data["recommended_intensity"] == "easy"
        assert data["confidence"] == 0.75



