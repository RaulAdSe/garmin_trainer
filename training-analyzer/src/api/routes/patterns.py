"""API routes for pattern recognition analysis."""

import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..deps import get_current_user, get_training_db, CurrentUser
from ...models.patterns import (
    CorrelationAnalysis,
    FitnessPrediction,
    PerformanceCorrelations,
    TimingAnalysis,
    TSBOptimalRange,
)
from ...services.pattern_recognition_service import PatternRecognitionService


router = APIRouter()
logger = logging.getLogger(__name__)


def get_pattern_service(training_db=Depends(get_training_db)) -> PatternRecognitionService:
    """Dependency to get pattern recognition service."""
    return PatternRecognitionService(training_db)


@router.get("/timing", response_model=TimingAnalysis)
async def get_timing_analysis(
    days: int = Query(default=90, ge=30, le=365, description="Number of days to analyze"),
    current_user: CurrentUser = Depends(get_current_user),
    pattern_service: PatternRecognitionService = Depends(get_pattern_service),
):
    """
    Analyze workout timing patterns.

    Returns performance analysis by:
    - Time of day (early morning, morning, afternoon, evening, etc.)
    - Day of week

    Identifies optimal training windows based on historical performance.

    Args:
        days: Number of days to analyze (30-365, default 90)

    Returns:
        TimingAnalysis with:
        - Performance by time slot
        - Performance by day of week
        - Optimal training windows
        - Best/worst times to train
    """
    user_id = current_user.id

    try:
        analysis = pattern_service.analyze_timing_patterns(
            user_id=user_id,
            days=days,
        )
        return analysis

    except Exception as e:
        logger.error(f"Failed to analyze timing patterns for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to analyze timing patterns. Please try again later."
        )


@router.get("/tsb-optimal", response_model=TSBOptimalRange)
async def get_optimal_tsb_range(
    days: int = Query(default=180, ge=60, le=365, description="Number of days to analyze"),
    current_user: CurrentUser = Depends(get_current_user),
    pattern_service: PatternRecognitionService = Depends(get_pattern_service),
):
    """
    Find optimal TSB range for peak performance.

    Analyzes historical workouts to identify the Training Stress Balance (TSB)
    range where the athlete performs best.

    TSB = CTL - ATL (Fitness - Fatigue = Form)

    Args:
        days: Number of days to analyze (60-365, default 180)

    Returns:
        TSBOptimalRange with:
        - Optimal TSB range (min, max)
        - Performance by TSB zone
        - TSB vs performance data points (for scatter plot)
        - Correlation strength
        - Race timing recommendations
    """
    user_id = current_user.id

    try:
        analysis = pattern_service.find_optimal_tsb_range(
            user_id=user_id,
            days=days,
        )
        return analysis

    except Exception as e:
        logger.error(f"Failed to find optimal TSB range for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to analyze TSB patterns. Please try again later."
        )


@router.get("/peak-prediction", response_model=FitnessPrediction)
async def get_peak_fitness_prediction(
    target_date: Optional[str] = Query(
        default=None,
        description="Target date for peak fitness (YYYY-MM-DD format)"
    ),
    horizon_days: int = Query(
        default=90,
        ge=14,
        le=180,
        description="Prediction horizon in days"
    ),
    current_user: CurrentUser = Depends(get_current_user),
    pattern_service: PatternRecognitionService = Depends(get_pattern_service),
):
    """
    Predict peak fitness timing and CTL trajectory.

    Based on current training load trajectory, predicts:
    - When CTL will naturally peak
    - CTL projection over time
    - Recommendations for reaching target dates

    Args:
        target_date: Optional target date (race/goal) in YYYY-MM-DD format
        horizon_days: How far to project (14-180 days, default 90)

    Returns:
        FitnessPrediction with:
        - Current fitness state (CTL, ATL, TSB)
        - Natural peak date prediction
        - CTL trajectory projection
        - Recommendations for target date (if provided)
        - Taper timing
    """
    user_id = current_user.id

    # Parse target date if provided
    parsed_target_date: Optional[date] = None
    if target_date:
        try:
            parsed_target_date = date.fromisoformat(target_date)
            if parsed_target_date <= date.today():
                raise HTTPException(
                    status_code=400,
                    detail="Target date must be in the future"
                )
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid date format. Use YYYY-MM-DD"
            )

    try:
        prediction = pattern_service.predict_peak_fitness(
            user_id=user_id,
            target_date=parsed_target_date,
            horizon_days=horizon_days,
        )
        return prediction

    except Exception as e:
        logger.error(f"Failed to predict peak fitness for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to predict peak fitness. Please try again later."
        )


@router.get("/correlations", response_model=PerformanceCorrelations)
async def get_performance_correlations(
    days: int = Query(default=180, ge=60, le=365, description="Number of days to analyze"),
    current_user: CurrentUser = Depends(get_current_user),
    pattern_service: PatternRecognitionService = Depends(get_pattern_service),
):
    """
    Analyze factors that correlate with performance.

    Examines relationships between performance and:
    - TSB (form/freshness)
    - Sleep quality
    - Rest days before workout
    - Weekly training load
    - Fitness level (CTL)

    Args:
        days: Number of days to analyze (60-365, default 180)

    Returns:
        PerformanceCorrelations with:
        - Correlation coefficients for each factor
        - Statistical significance
        - Top positive and negative factors
        - Key insights
    """
    user_id = current_user.id

    try:
        correlations = pattern_service.get_performance_correlations(
            user_id=user_id,
            days=days,
        )
        return correlations

    except Exception as e:
        logger.error(f"Failed to analyze correlations for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to analyze performance correlations. Please try again later."
        )


@router.get("/summary", response_model=CorrelationAnalysis)
async def get_pattern_summary(
    days: int = Query(default=90, ge=30, le=365, description="Number of days to analyze"),
    current_user: CurrentUser = Depends(get_current_user),
    pattern_service: PatternRecognitionService = Depends(get_pattern_service),
):
    """
    Get combined pattern analysis summary.

    Returns all pattern analyses in a single response for dashboard display.

    Args:
        days: Number of days to analyze (30-365, default 90)

    Returns:
        CorrelationAnalysis with:
        - Timing analysis
        - TSB optimal range
        - Performance correlations
    """
    user_id = current_user.id

    try:
        # Fetch all analyses
        timing = pattern_service.analyze_timing_patterns(user_id=user_id, days=days)
        tsb = pattern_service.find_optimal_tsb_range(user_id=user_id, days=days)
        correlations = pattern_service.get_performance_correlations(user_id=user_id, days=days)

        return CorrelationAnalysis(
            timing_correlations=timing,
            tsb_correlations=tsb,
            performance_correlations=correlations,
        )

    except Exception as e:
        logger.error(f"Failed to get pattern summary for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to analyze patterns. Please try again later."
        )
