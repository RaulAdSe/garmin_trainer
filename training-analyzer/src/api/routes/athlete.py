"""Athlete context API routes."""

from datetime import date, datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..deps import get_coach_service, get_training_db


router = APIRouter()


class FitnessMetrics(BaseModel):
    """Current fitness metrics."""
    ctl: float
    atl: float
    tsb: float
    acwr: float
    risk_zone: str
    daily_load: float


class Physiology(BaseModel):
    """Athlete physiological profile."""
    max_hr: int
    rest_hr: int
    lthr: int  # Lactate threshold HR
    age: Optional[int] = None
    gender: Optional[str] = None
    weight_kg: Optional[float] = None
    vdot: Optional[float] = None


class HRZone(BaseModel):
    """Heart rate zone."""
    zone: int
    name: str
    min_hr: int
    max_hr: int
    description: str


class TrainingPace(BaseModel):
    """Training pace for a specific workout type."""
    name: str
    pace_sec_per_km: float
    pace_formatted: str
    hr_zone: str
    description: str


class RaceGoalResponse(BaseModel):
    """Race goal information."""
    distance: str
    distance_km: float
    target_time_formatted: str
    target_pace_formatted: str
    race_date: str
    weeks_remaining: int


class ReadinessResponse(BaseModel):
    """Readiness score and zone."""
    score: float
    zone: str
    recommendation: str


class AthleteContext(BaseModel):
    """Full athlete context for LLM injection."""
    fitness: FitnessMetrics
    physiology: Physiology
    hr_zones: list[HRZone]
    training_paces: list[TrainingPace]
    race_goals: list[RaceGoalResponse]
    readiness: ReadinessResponse


@router.get("/context", response_model=AthleteContext)
async def get_athlete_context(
    target_date: Optional[str] = None,
    coach_service = Depends(get_coach_service),
    training_db = Depends(get_training_db),
):
    """
    Get full athlete context for LLM injection.

    This endpoint aggregates all relevant athlete data:
    - Current fitness metrics (CTL/ATL/TSB/ACWR)
    - Physiological profile (HR zones, max HR, etc.)
    - Training paces based on goals
    - Active race goals
    - Current readiness score

    This context is injected into every LLM call to provide
    personalized, contextually-aware coaching.
    """
    try:
        # Parse date
        if target_date:
            from datetime import datetime
            parsed_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        else:
            parsed_date = date.today()

        # Get daily briefing (contains readiness, fitness metrics)
        briefing = coach_service.get_daily_briefing(parsed_date)

        # Get user profile
        profile = training_db.get_user_profile()

        # Build fitness metrics
        training_status = briefing.get("training_status") or {}
        fitness = FitnessMetrics(
            ctl=training_status.get("ctl", 0) or 0,
            atl=training_status.get("atl", 0) or 0,
            tsb=training_status.get("tsb", 0) or 0,
            acwr=training_status.get("acwr", 1.0) or 1.0,
            risk_zone=training_status.get("risk_zone", "unknown") or "unknown",
            daily_load=training_status.get("daily_load", 0) or 0,
        )

        # Calculate VDOT from goals if available
        vdot = None
        goals = training_db.get_race_goals()
        if goals:
            from ...analysis.goals import calculate_vdot, RaceDistance, calculate_training_paces, RaceGoal

            # Use first goal to estimate VDOT
            first_goal = goals[0]
            distance = RaceDistance.from_string(str(first_goal.get("distance", "10k"))) or RaceDistance.TEN_K
            target_time = first_goal.get("target_time_sec", 3000)
            vdot = calculate_vdot(target_time, distance)

        # Build physiology
        physiology = Physiology(
            max_hr=profile.max_hr if profile else 185,
            rest_hr=profile.rest_hr if profile else 55,
            lthr=profile.threshold_hr if profile else 165,
            age=profile.age if profile else None,
            gender=profile.gender if profile else None,
            weight_kg=profile.weight_kg if profile else None,
            vdot=round(vdot, 1) if vdot else None,
        )

        # Build HR zones (using Karvonen method)
        max_hr = physiology.max_hr
        rest_hr = physiology.rest_hr
        hr_reserve = max_hr - rest_hr

        zone_definitions = [
            (1, "Recovery", 0.50, 0.60, "Active recovery, easy breathing"),
            (2, "Aerobic", 0.60, 0.70, "Base building, conversational pace"),
            (3, "Tempo", 0.70, 0.80, "Comfortably hard, lactate threshold"),
            (4, "Threshold", 0.80, 0.90, "Hard, sustainable for 20-30 min"),
            (5, "VO2max", 0.90, 1.00, "Very hard, 3-8 min efforts"),
        ]

        hr_zones = []
        for zone_num, name, low_pct, high_pct, desc in zone_definitions:
            min_hr = int(rest_hr + hr_reserve * low_pct)
            max_hr_zone = int(rest_hr + hr_reserve * high_pct)
            hr_zones.append(HRZone(
                zone=zone_num,
                name=name,
                min_hr=min_hr,
                max_hr=max_hr_zone,
                description=desc,
            ))

        # Build training paces from goals
        training_paces = []
        race_goals_response = []

        if goals:
            from ...analysis.goals import calculate_training_paces, RaceGoal, RaceDistance

            for goal_data in goals:
                distance = RaceDistance.from_string(str(goal_data.get("distance", "10k"))) or RaceDistance.TEN_K
                target_time = goal_data.get("target_time_sec", 3000)
                race_date_str = goal_data.get("race_date", date.today().isoformat())

                # Parse race date
                from datetime import datetime
                if isinstance(race_date_str, str):
                    race_date_parsed = datetime.strptime(race_date_str, "%Y-%m-%d").date()
                else:
                    race_date_parsed = race_date_str

                goal = RaceGoal(
                    race_date=race_date_parsed,
                    distance=distance,
                    target_time_sec=target_time,
                )

                # Calculate paces for this goal
                paces = calculate_training_paces(goal)

                # Convert to response format (only add once)
                if not training_paces:  # Only from first goal
                    for pace_type, pace_data in paces.items():
                        training_paces.append(TrainingPace(
                            name=pace_data["name"],
                            pace_sec_per_km=pace_data["pace_sec"],
                            pace_formatted=pace_data["pace_formatted"],
                            hr_zone=pace_data["hr_zone"],
                            description=pace_data["description"],
                        ))

                # Add goal to response
                race_goals_response.append(RaceGoalResponse(
                    distance=distance.display_name,
                    distance_km=distance.value,
                    target_time_formatted=goal.target_time_formatted,
                    target_pace_formatted=goal.target_pace_formatted,
                    race_date=race_date_parsed.isoformat(),
                    weeks_remaining=goal.weeks_until_race,
                ))

        # Build readiness
        readiness_data = briefing.get("readiness", {})
        readiness = ReadinessResponse(
            score=readiness_data.get("score", 50),
            zone=readiness_data.get("zone", "yellow"),
            recommendation=readiness_data.get("recommendation", "Moderate training today"),
        )

        return AthleteContext(
            fitness=fitness,
            physiology=physiology,
            hr_zones=hr_zones,
            training_paces=training_paces,
            race_goals=race_goals_response,
            readiness=readiness,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get athlete context: {str(e)}")


@router.get("/readiness")
async def get_readiness(
    target_date: Optional[str] = None,
    coach_service = Depends(get_coach_service),
):
    """Get today's readiness score and recommendation."""
    try:
        if target_date:
            from datetime import datetime
            parsed_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        else:
            parsed_date = date.today()

        briefing = coach_service.get_daily_briefing(parsed_date)

        return {
            "date": parsed_date.isoformat(),
            "readiness": briefing.get("readiness"),
            "recommendation": briefing.get("recommendation"),
            "narrative": briefing.get("narrative"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get readiness: {str(e)}")


@router.get("/fitness-metrics")
async def get_fitness_metrics(
    days: int = 30,
    coach_service = Depends(get_coach_service),
    training_db = Depends(get_training_db),
):
    """Get fitness metrics history (CTL/ATL/TSB)."""
    try:
        from datetime import timedelta

        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # Get fitness metrics for date range
        metrics = []
        current = start_date
        while current <= end_date:
            fm = training_db.get_fitness_metrics(current.isoformat())
            if fm:
                metrics.append({
                    "date": current.isoformat(),
                    "ctl": fm.ctl,
                    "atl": fm.atl,
                    "tsb": fm.tsb,
                    "acwr": fm.acwr,
                    "daily_load": fm.daily_load,
                    "risk_zone": fm.risk_zone,
                })
            current += timedelta(days=1)

        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "metrics": metrics,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get fitness metrics: {str(e)}")


# ============================================================================
# VO2max Trend Tracking Response Models
# ============================================================================

class VO2maxDataPoint(BaseModel):
    """A single VO2max data point."""
    date: str
    vo2max_running: Optional[float] = None
    vo2max_cycling: Optional[float] = None
    training_status: Optional[str] = None


class VO2maxTrendResponse(BaseModel):
    """Response for VO2max trend data."""
    data_points: List[VO2maxDataPoint]
    trend: str  # "improving" | "stable" | "declining"
    change_percent: float
    current_vo2max_running: Optional[float] = None
    current_vo2max_cycling: Optional[float] = None
    peak_vo2max_running: Optional[float] = None
    peak_vo2max_cycling: Optional[float] = None
    current_vs_peak_running: Optional[float] = None  # Percentage
    current_vs_peak_cycling: Optional[float] = None  # Percentage
    start_date: str
    end_date: str


class RacePredictionsResponse(BaseModel):
    """Current race predictions."""
    race_time_5k: Optional[int] = None
    race_time_5k_formatted: Optional[str] = None
    race_time_10k: Optional[int] = None
    race_time_10k_formatted: Optional[str] = None
    race_time_half: Optional[int] = None
    race_time_half_formatted: Optional[str] = None
    race_time_marathon: Optional[int] = None
    race_time_marathon_formatted: Optional[str] = None


class TrainingPacesFromVO2maxResponse(BaseModel):
    """Training paces calculated from VO2max."""
    vo2max: float
    easy_pace: int
    easy_pace_formatted: str
    marathon_pace: int
    marathon_pace_formatted: str
    threshold_pace: int
    threshold_pace_formatted: str
    interval_pace: int
    interval_pace_formatted: str
    repetition_pace: int
    repetition_pace_formatted: str


@router.get("/vo2max-trend", response_model=VO2maxTrendResponse)
async def get_vo2max_trend(
    days: int = 90,
    training_db = Depends(get_training_db),
):
    """
    Get VO2max trend over time.

    Analyzes VO2max data from Garmin fitness syncs to show:
    - Historical data points with VO2max values
    - Trend direction (improving/stable/declining)
    - Percentage change over the period
    - Current vs peak comparison

    Args:
        days: Number of days to analyze (default 90)

    Returns:
        VO2maxTrendResponse with trend analysis
    """
    try:
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # Get Garmin fitness data for the date range
        fitness_data = training_db.get_garmin_fitness_range(
            start_date.isoformat(),
            end_date.isoformat(),
        )

        if not fitness_data:
            return VO2maxTrendResponse(
                data_points=[],
                trend="unknown",
                change_percent=0.0,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )

        # Convert to data points (sorted by date ascending)
        data_points = []
        running_values = []
        cycling_values = []

        for fd in sorted(fitness_data, key=lambda x: x.date):
            data_points.append(VO2maxDataPoint(
                date=fd.date,
                vo2max_running=fd.vo2max_running,
                vo2max_cycling=fd.vo2max_cycling,
                training_status=fd.training_status,
            ))
            if fd.vo2max_running is not None:
                running_values.append((fd.date, fd.vo2max_running))
            if fd.vo2max_cycling is not None:
                cycling_values.append((fd.date, fd.vo2max_cycling))

        # Calculate trend and stats
        current_running = running_values[-1][1] if running_values else None
        current_cycling = cycling_values[-1][1] if cycling_values else None
        peak_running = max((v[1] for v in running_values), default=None) if running_values else None
        peak_cycling = max((v[1] for v in cycling_values), default=None) if cycling_values else None

        # Calculate current vs peak percentages
        current_vs_peak_running = None
        current_vs_peak_cycling = None
        if current_running and peak_running:
            current_vs_peak_running = round((current_running / peak_running) * 100, 1)
        if current_cycling and peak_cycling:
            current_vs_peak_cycling = round((current_cycling / peak_cycling) * 100, 1)

        # Determine trend direction using running VO2max (primary metric)
        trend = "unknown"
        change_percent = 0.0

        if len(running_values) >= 2:
            # Compare first and last values
            first_value = running_values[0][1]
            last_value = running_values[-1][1]
            change_percent = ((last_value - first_value) / first_value) * 100 if first_value > 0 else 0
            change_percent = round(change_percent, 1)

            # Use a threshold of 2% to determine trend
            if change_percent > 2:
                trend = "improving"
            elif change_percent < -2:
                trend = "declining"
            else:
                trend = "stable"
        elif len(cycling_values) >= 2:
            # Fall back to cycling VO2max if running not available
            first_value = cycling_values[0][1]
            last_value = cycling_values[-1][1]
            change_percent = ((last_value - first_value) / first_value) * 100 if first_value > 0 else 0
            change_percent = round(change_percent, 1)

            if change_percent > 2:
                trend = "improving"
            elif change_percent < -2:
                trend = "declining"
            else:
                trend = "stable"

        return VO2maxTrendResponse(
            data_points=data_points,
            trend=trend,
            change_percent=change_percent,
            current_vo2max_running=current_running,
            current_vo2max_cycling=current_cycling,
            peak_vo2max_running=peak_running,
            peak_vo2max_cycling=peak_cycling,
            current_vs_peak_running=current_vs_peak_running,
            current_vs_peak_cycling=current_vs_peak_cycling,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get VO2max trend: {str(e)}")


@router.get("/race-predictions", response_model=RacePredictionsResponse)
async def get_race_predictions(
    training_db = Depends(get_training_db),
):
    """
    Get current Garmin race predictions.

    Returns predicted race times for 5K, 10K, Half Marathon, and Marathon
    based on current VO2max and training data.
    """
    try:
        # Get latest Garmin fitness data
        latest = training_db.get_latest_garmin_fitness_data()

        if not latest:
            return RacePredictionsResponse()

        def format_race_time(seconds: Optional[int]) -> Optional[str]:
            if seconds is None:
                return None
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            if hours > 0:
                return f"{hours}:{minutes:02d}:{secs:02d}"
            return f"{minutes}:{secs:02d}"

        return RacePredictionsResponse(
            race_time_5k=latest.race_time_5k,
            race_time_5k_formatted=format_race_time(latest.race_time_5k),
            race_time_10k=latest.race_time_10k,
            race_time_10k_formatted=format_race_time(latest.race_time_10k),
            race_time_half=latest.race_time_half,
            race_time_half_formatted=format_race_time(latest.race_time_half),
            race_time_marathon=latest.race_time_marathon,
            race_time_marathon_formatted=format_race_time(latest.race_time_marathon),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get race predictions: {str(e)}")


@router.get("/training-paces", response_model=TrainingPacesFromVO2maxResponse)
async def get_training_paces_from_vo2max(
    training_db = Depends(get_training_db),
):
    """
    Get training paces calculated from current VO2max.

    Uses Jack Daniels' VDOT tables to calculate optimal training paces
    for easy runs, marathon pace, threshold, interval, and repetition work.
    """
    try:
        from ...analysis.goals import calculate_training_paces_from_vo2max, format_pace_from_seconds

        # Get latest Garmin fitness data
        latest = training_db.get_latest_garmin_fitness_data()

        if not latest or not latest.vo2max_running:
            raise HTTPException(
                status_code=404,
                detail="No VO2max data available. Sync your Garmin device to get training paces."
            )

        vo2max = latest.vo2max_running
        paces = calculate_training_paces_from_vo2max(vo2max)

        return TrainingPacesFromVO2maxResponse(
            vo2max=vo2max,
            easy_pace=paces["easy_pace"],
            easy_pace_formatted=format_pace_from_seconds(paces["easy_pace"]),
            marathon_pace=paces["marathon_pace"],
            marathon_pace_formatted=format_pace_from_seconds(paces["marathon_pace"]),
            threshold_pace=paces["threshold_pace"],
            threshold_pace_formatted=format_pace_from_seconds(paces["threshold_pace"]),
            interval_pace=paces["interval_pace"],
            interval_pace_formatted=format_pace_from_seconds(paces["interval_pace"]),
            repetition_pace=paces["repetition_pace"],
            repetition_pace_formatted=format_pace_from_seconds(paces["repetition_pace"]),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get training paces: {str(e)}")


@router.get("/goal-feasibility")
async def get_goal_feasibility(
    training_db = Depends(get_training_db),
):
    """
    Assess feasibility of current race goals based on VO2max predictions.

    Compares Garmin's race predictions to your set goals to determine
    how realistic each goal is given your current fitness level.
    """
    try:
        from ...analysis.goals import get_goal_feasibility_summary

        # Get latest Garmin fitness data
        latest = training_db.get_latest_garmin_fitness_data()

        if not latest:
            return {
                "assessments": [],
                "message": "No VO2max data available. Sync your Garmin device for goal assessment."
            }

        # Get race goals
        goals = training_db.get_race_goals(upcoming_only=True)

        if not goals:
            return {
                "assessments": [],
                "message": "No race goals set. Create a goal to see feasibility assessment."
            }

        # Build race predictions dict
        race_predictions = {
            "race_time_5k": latest.race_time_5k,
            "race_time_10k": latest.race_time_10k,
            "race_time_half": latest.race_time_half,
            "race_time_marathon": latest.race_time_marathon,
        }

        # Assess each goal
        assessments = get_goal_feasibility_summary(race_predictions, goals)

        return {
            "assessments": assessments,
            "current_vo2max": latest.vo2max_running,
            "training_status": latest.training_status,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to assess goal feasibility: {str(e)}")
