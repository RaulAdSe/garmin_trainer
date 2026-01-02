"""Recovery module API routes for sleep debt, HRV trends, and recovery time."""

import logging
from datetime import date, datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query

from ..deps import get_current_user, CurrentUser, get_training_db, get_coach_service
from ...db.database import TrainingDatabase
from ...models.recovery import (
    SleepRecord,
    SleepDebtAnalysis,
    SleepDebtResponse,
    HRVRecord,
    HRVTrendAnalysis,
    HRVTrendResponse,
    RecoveryTimeEstimate,
    RecoveryTimeResponse,
    RecoveryModuleData,
    RecoveryModuleResponse,
    RecoveryModuleRequest,
)
from ...services.recovery_module_service import get_recovery_service


router = APIRouter()
logger = logging.getLogger(__name__)


# =============================================================================
# Helper Functions
# =============================================================================

def _get_sleep_records_from_db(
    db: TrainingDatabase,
    days: int = 30,
) -> List[SleepRecord]:
    """
    Fetch sleep records from the database.

    This retrieves sleep data from Garmin wellness data.
    """
    try:
        # Get wellness data which includes sleep
        wellness_data = db.get_wellness_data(days=days)

        sleep_records = []
        for record in wellness_data:
            if record.get("sleep_seconds") is not None:
                sleep_hours = record.get("sleep_seconds", 0) / 3600
                record_date = record.get("date")

                if isinstance(record_date, str):
                    record_date = date.fromisoformat(record_date)

                sleep_record = SleepRecord(
                    date=record_date,
                    duration_hours=sleep_hours,
                    quality_score=record.get("sleep_quality_score"),
                    deep_sleep_hours=(record.get("deep_sleep_seconds") or 0) / 3600,
                    rem_sleep_hours=(record.get("rem_sleep_seconds") or 0) / 3600,
                    light_sleep_hours=(record.get("light_sleep_seconds") or 0) / 3600,
                    awake_time_hours=(record.get("awake_seconds") or 0) / 3600,
                )
                sleep_records.append(sleep_record)

        return sorted(sleep_records, key=lambda r: r.date)
    except Exception as e:
        logger.warning(f"Failed to get sleep records: {e}")
        return []


def _get_hrv_records_from_db(
    db: TrainingDatabase,
    days: int = 30,
) -> List[HRVRecord]:
    """
    Fetch HRV records from the database.

    This retrieves HRV data from Garmin wellness data.
    """
    try:
        wellness_data = db.get_wellness_data(days=days)

        hrv_records = []
        for record in wellness_data:
            if record.get("hrv_rmssd") is not None or record.get("resting_hr") is not None:
                record_date = record.get("date")

                if isinstance(record_date, str):
                    record_date = date.fromisoformat(record_date)

                # Only create record if we have HRV data
                rmssd = record.get("hrv_rmssd")
                if rmssd is not None and rmssd > 0:
                    hrv_record = HRVRecord(
                        date=record_date,
                        rmssd=rmssd,
                        sdnn=record.get("hrv_sdnn"),
                        lf_power=record.get("hrv_lf"),
                        hf_power=record.get("hrv_hf"),
                        lf_hf_ratio=record.get("hrv_lf_hf_ratio"),
                    )
                    hrv_records.append(hrv_record)

        return sorted(hrv_records, key=lambda r: r.date)
    except Exception as e:
        logger.warning(f"Failed to get HRV records: {e}")
        return []


def _get_last_workout_info(db: TrainingDatabase) -> Optional[dict]:
    """Get information about the last workout for recovery estimation."""
    try:
        # Get most recent activity
        activities = db.get_activity_metrics_range(days=7)
        if not activities:
            return None

        last_activity = activities[0]  # Most recent
        activity_dict = last_activity.to_dict()

        # Calculate intensity based on HR zones
        zone3_pct = activity_dict.get("zone3_pct") or 0
        zone4_pct = activity_dict.get("zone4_pct") or 0
        zone5_pct = activity_dict.get("zone5_pct") or 0

        # Simple intensity score based on zone distribution
        intensity = min(100, (zone3_pct * 0.5) + (zone4_pct * 0.8) + (zone5_pct * 1.0) + 20)

        return {
            "activity_id": activity_dict.get("activity_id"),
            "date": activity_dict.get("date"),
            "intensity": intensity,
            "duration_min": activity_dict.get("duration_min") or 30,
            "hrss": activity_dict.get("hrss"),
        }
    except Exception as e:
        logger.warning(f"Failed to get last workout info: {e}")
        return None


def _get_current_fitness_state(coach_service) -> dict:
    """Get current TSB and VO2max from coach service."""
    try:
        context = coach_service.get_athlete_context()
        fitness = context.get("fitness_metrics", {})
        physiology = context.get("physiology", {})

        return {
            "tsb": fitness.get("tsb"),
            "vo2max": physiology.get("vo2max_running") or physiology.get("vo2max"),
        }
    except Exception as e:
        logger.warning(f"Failed to get fitness state: {e}")
        return {"tsb": None, "vo2max": None}


# =============================================================================
# API Endpoints
# =============================================================================

@router.get("/", response_model=RecoveryModuleResponse)
async def get_recovery_data(
    target_date: Optional[date] = Query(None, description="Target date for analysis"),
    include_sleep_debt: bool = Query(True, description="Include sleep debt analysis"),
    include_hrv_trend: bool = Query(True, description="Include HRV trend analysis"),
    include_recovery_time: bool = Query(True, description="Include recovery time"),
    sleep_target_hours: float = Query(8.0, ge=4.0, le=12.0, description="Target sleep hours"),
    current_user: CurrentUser = Depends(get_current_user),
    training_db: TrainingDatabase = Depends(get_training_db),
    coach_service=Depends(get_coach_service),
):
    """
    Get complete recovery module data.

    Combines:
    - 7-day rolling sleep debt analysis
    - HRV trend with coefficient of variation
    - Post-workout recovery time estimation

    Returns an overall recovery score and recommendations.
    """
    try:
        recovery_service = get_recovery_service()

        # Fetch data from database
        sleep_records = _get_sleep_records_from_db(training_db, days=30) if include_sleep_debt else None
        hrv_records = _get_hrv_records_from_db(training_db, days=30) if include_hrv_trend else None
        last_workout = _get_last_workout_info(training_db) if include_recovery_time else None
        fitness_state = _get_current_fitness_state(coach_service)

        # Calculate recovery data
        recovery_data = recovery_service.get_full_recovery_data(
            sleep_records=sleep_records,
            hrv_records=hrv_records,
            last_workout=last_workout,
            current_tsb=fitness_state.get("tsb"),
            vo2max=fitness_state.get("vo2max"),
            target_sleep_hours=sleep_target_hours,
        )

        return RecoveryModuleResponse(
            success=True,
            data=recovery_data,
        )

    except Exception as e:
        logger.error(f"Failed to get recovery data: {e}")
        return RecoveryModuleResponse(
            success=False,
            error=f"Failed to calculate recovery data: {str(e)}",
        )


@router.get("/sleep-debt", response_model=SleepDebtResponse)
async def get_sleep_debt(
    target_hours: float = Query(8.0, ge=4.0, le=12.0, description="Target sleep hours"),
    window_days: int = Query(7, ge=3, le=14, description="Analysis window in days"),
    current_user: CurrentUser = Depends(get_current_user),
    training_db: TrainingDatabase = Depends(get_training_db),
):
    """
    Get 7-day rolling sleep debt analysis.

    Calculates cumulative sleep debt based on target vs actual sleep.
    Includes impact level and recovery recommendations.
    """
    try:
        recovery_service = get_recovery_service()

        # Fetch sleep records
        sleep_records = _get_sleep_records_from_db(training_db, days=window_days + 7)

        if not sleep_records:
            return SleepDebtResponse(
                success=True,
                data=None,
                error="No sleep data available. Connect your wearable to track sleep.",
            )

        # Calculate sleep debt
        sleep_debt = recovery_service.get_sleep_debt(
            sleep_records=sleep_records,
            target_hours=target_hours,
            window_days=window_days,
        )

        return SleepDebtResponse(
            success=True,
            data=sleep_debt,
        )

    except Exception as e:
        logger.error(f"Failed to calculate sleep debt: {e}")
        return SleepDebtResponse(
            success=False,
            error=f"Failed to calculate sleep debt: {str(e)}",
        )


@router.get("/hrv-trend", response_model=HRVTrendResponse)
async def get_hrv_trend(
    current_user: CurrentUser = Depends(get_current_user),
    training_db: TrainingDatabase = Depends(get_training_db),
):
    """
    Get HRV trend analysis with rolling averages and coefficient of variation.

    Includes:
    - 7-day and 30-day rolling averages
    - Coefficient of variation (more stable than raw HRV)
    - Trend direction and percentage change
    - Baseline comparison
    """
    try:
        recovery_service = get_recovery_service()

        # Fetch HRV records (need 30+ days for good baseline)
        hrv_records = _get_hrv_records_from_db(training_db, days=45)

        if not hrv_records:
            return HRVTrendResponse(
                success=True,
                data=None,
                error="No HRV data available. Connect your wearable to track HRV.",
            )

        # Calculate HRV trend
        hrv_trend = recovery_service.get_hrv_trend(hrv_records=hrv_records)

        return HRVTrendResponse(
            success=True,
            data=hrv_trend,
        )

    except Exception as e:
        logger.error(f"Failed to calculate HRV trend: {e}")
        return HRVTrendResponse(
            success=False,
            error=f"Failed to calculate HRV trend: {str(e)}",
        )


@router.get("/recovery-time", response_model=RecoveryTimeResponse)
async def get_recovery_time_estimate(
    workout_id: Optional[str] = Query(None, description="Specific workout to estimate for"),
    current_user: CurrentUser = Depends(get_current_user),
    training_db: TrainingDatabase = Depends(get_training_db),
    coach_service=Depends(get_coach_service),
):
    """
    Get post-workout recovery time estimation.

    Estimates recovery time based on:
    - Workout intensity and duration
    - Current fatigue state (TSB)
    - Sleep debt
    - HRV status
    - Fitness level (VO2max)

    Returns hours until recovered and hours until fresh for hard training.
    """
    try:
        recovery_service = get_recovery_service()

        # Get workout info
        if workout_id:
            activity = training_db.get_activity_metrics(workout_id)
            if not activity:
                return RecoveryTimeResponse(
                    success=False,
                    error=f"Workout {workout_id} not found",
                )
            activity_dict = activity.to_dict()

            # Calculate intensity
            zone3_pct = activity_dict.get("zone3_pct") or 0
            zone4_pct = activity_dict.get("zone4_pct") or 0
            zone5_pct = activity_dict.get("zone5_pct") or 0
            intensity = min(100, (zone3_pct * 0.5) + (zone4_pct * 0.8) + (zone5_pct * 1.0) + 20)

            workout_info = {
                "activity_id": workout_id,
                "intensity": intensity,
                "duration_min": activity_dict.get("duration_min") or 30,
                "hrss": activity_dict.get("hrss"),
            }
        else:
            # Use last workout
            workout_info = _get_last_workout_info(training_db)
            if not workout_info:
                return RecoveryTimeResponse(
                    success=False,
                    error="No recent workout found for recovery estimation",
                )

        # Get supporting data
        sleep_records = _get_sleep_records_from_db(training_db, days=7)
        hrv_records = _get_hrv_records_from_db(training_db, days=30)
        fitness_state = _get_current_fitness_state(coach_service)

        # Calculate sleep debt
        sleep_debt_hours = None
        if sleep_records:
            sleep_debt = recovery_service.get_sleep_debt(sleep_records)
            sleep_debt_hours = sleep_debt.total_debt_hours

        # Get HRV relative to baseline
        hrv_relative = None
        if hrv_records:
            hrv_trend = recovery_service.get_hrv_trend(hrv_records)
            hrv_relative = hrv_trend.relative_to_baseline

        # Estimate recovery time
        recovery_time = recovery_service.get_recovery_time(
            workout_intensity=workout_info.get("intensity", 50),
            workout_duration_min=workout_info.get("duration_min", 30),
            workout_hrss=workout_info.get("hrss"),
            current_tsb=fitness_state.get("tsb"),
            sleep_debt_hours=sleep_debt_hours,
            hrv_relative_to_baseline=hrv_relative,
            vo2max=fitness_state.get("vo2max"),
        )

        return RecoveryTimeResponse(
            success=True,
            data=recovery_time,
            workout_id=workout_info.get("activity_id"),
        )

    except Exception as e:
        logger.error(f"Failed to estimate recovery time: {e}")
        return RecoveryTimeResponse(
            success=False,
            error=f"Failed to estimate recovery time: {str(e)}",
        )


@router.get("/score")
async def get_recovery_score(
    current_user: CurrentUser = Depends(get_current_user),
    training_db: TrainingDatabase = Depends(get_training_db),
    coach_service=Depends(get_coach_service),
):
    """
    Get just the recovery score (0-100) and status.

    Quick endpoint for dashboard widgets that just need the score.
    """
    try:
        recovery_service = get_recovery_service()

        # Fetch data
        sleep_records = _get_sleep_records_from_db(training_db, days=7)
        hrv_records = _get_hrv_records_from_db(training_db, days=30)
        fitness_state = _get_current_fitness_state(coach_service)

        # Calculate recovery data
        recovery_data = recovery_service.get_full_recovery_data(
            sleep_records=sleep_records,
            hrv_records=hrv_records,
            current_tsb=fitness_state.get("tsb"),
            vo2max=fitness_state.get("vo2max"),
        )

        return {
            "success": True,
            "recoveryScore": recovery_data.recovery_score,
            "recoveryStatus": recovery_data.overall_recovery_status.value,
            "summaryMessage": recovery_data.summary_message,
            "hasData": bool(sleep_records or hrv_records),
        }

    except Exception as e:
        logger.error(f"Failed to get recovery score: {e}")
        return {
            "success": False,
            "error": str(e),
        }
