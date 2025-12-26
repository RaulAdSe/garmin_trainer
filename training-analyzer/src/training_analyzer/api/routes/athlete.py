"""Athlete context API routes."""

from datetime import date
from typing import Optional

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
            from training_analyzer.analysis.goals import calculate_training_paces, RaceGoal, RaceDistance

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
