"""Workout design and export API routes."""

from datetime import date
from typing import Optional, List, Tuple

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..deps import get_coach_service, get_training_db


router = APIRouter()


class WorkoutInterval(BaseModel):
    """A single interval in a structured workout."""
    type: str  # warmup, work, recovery, cooldown
    duration_sec: Optional[int] = None
    distance_m: Optional[int] = None
    target_pace_min: Optional[int] = None  # min sec/km
    target_pace_max: Optional[int] = None  # max sec/km
    target_hr_min: Optional[int] = None
    target_hr_max: Optional[int] = None
    repetitions: int = 1
    notes: Optional[str] = None


class StructuredWorkout(BaseModel):
    """A complete structured workout."""
    workout_id: str
    name: str
    description: str
    sport: str = "running"
    intervals: List[WorkoutInterval]
    estimated_duration_min: int
    estimated_distance_km: Optional[float] = None
    estimated_load: Optional[float] = None


class DesignWorkoutRequest(BaseModel):
    """Request to design a workout."""
    workout_type: str  # tempo, intervals, threshold, long, easy, fartlek
    duration_min: Optional[int] = None
    target_load: Optional[float] = None
    focus: Optional[str] = None  # speed, endurance, threshold, recovery


@router.post("/design")
async def design_workout(
    request: DesignWorkoutRequest,
    coach_service = Depends(get_coach_service),
    training_db = Depends(get_training_db),
):
    """
    AI-powered workout design.

    Creates structured workouts based on:
    - Workout type requested
    - Current fitness level
    - Training paces from goals
    - Athlete's HR zones

    Returns a structured workout with intervals that can be exported to Garmin.
    """
    try:
        import uuid

        # Get athlete context
        briefing = coach_service.get_daily_briefing(date.today())
        profile = training_db.get_user_profile()
        goals = training_db.get_race_goals()

        # Get training paces if available
        training_paces = {}
        if goals:
            import sys
            from pathlib import Path
            training_analyzer_path = Path(__file__).parent.parent.parent.parent.parent.parent.parent / "training-analyzer" / "src"
            if str(training_analyzer_path) not in sys.path:
                sys.path.insert(0, str(training_analyzer_path))
            from training_analyzer.analysis.goals import calculate_training_paces, RaceGoal, RaceDistance
            from datetime import datetime

            first_goal = goals[0]
            distance = RaceDistance.from_string(str(first_goal.get("distance", "10k"))) or RaceDistance.TEN_K
            target_time = first_goal.get("target_time_sec", 3000)
            race_date_str = first_goal.get("race_date", date.today().isoformat())

            if isinstance(race_date_str, str):
                race_date = datetime.strptime(race_date_str, "%Y-%m-%d").date()
            else:
                race_date = race_date_str

            goal = RaceGoal(
                race_date=race_date,
                distance=distance,
                target_time_sec=target_time,
            )
            training_paces = calculate_training_paces(goal)

        # HR zones
        max_hr = profile.max_hr if profile else 185
        rest_hr = profile.rest_hr if profile else 55
        hr_reserve = max_hr - rest_hr

        def hr_zone(low_pct: float, high_pct: float) -> Tuple[int, int]:
            return (
                int(rest_hr + hr_reserve * low_pct),
                int(rest_hr + hr_reserve * high_pct),
            )

        # Design based on workout type
        intervals = []
        workout_name = ""
        description = ""
        duration = request.duration_min or 45

        if request.workout_type == "easy":
            workout_name = "Easy Run"
            description = "Recovery/base building run at conversational pace"
            pace = training_paces.get("easy", {}).get("pace_sec", 360)
            hr_min, hr_max = hr_zone(0.5, 0.65)

            intervals = [
                WorkoutInterval(
                    type="warmup",
                    duration_sec=300,  # 5 min
                    notes="Walk or very easy jog",
                ),
                WorkoutInterval(
                    type="work",
                    duration_sec=(duration - 10) * 60,
                    target_pace_min=int(pace - 15),
                    target_pace_max=int(pace + 30),
                    target_hr_min=hr_min,
                    target_hr_max=hr_max,
                    notes="Easy conversational pace",
                ),
                WorkoutInterval(
                    type="cooldown",
                    duration_sec=300,  # 5 min
                    notes="Easy jog to walk",
                ),
            ]

        elif request.workout_type == "tempo":
            workout_name = "Tempo Run"
            description = "Sustained effort at lactate threshold pace"
            tempo_pace = training_paces.get("tempo", {}).get("pace_sec", 300)
            easy_pace = training_paces.get("easy", {}).get("pace_sec", 360)
            hr_min, hr_max = hr_zone(0.75, 0.85)
            easy_hr_min, easy_hr_max = hr_zone(0.5, 0.65)

            tempo_duration = min(30, duration - 20)  # At least 10 min warmup/cooldown

            intervals = [
                WorkoutInterval(
                    type="warmup",
                    duration_sec=600,  # 10 min
                    target_pace_min=int(easy_pace - 15),
                    target_pace_max=int(easy_pace + 30),
                    target_hr_min=easy_hr_min,
                    target_hr_max=easy_hr_max,
                    notes="Easy jog building to tempo",
                ),
                WorkoutInterval(
                    type="work",
                    duration_sec=tempo_duration * 60,
                    target_pace_min=int(tempo_pace - 10),
                    target_pace_max=int(tempo_pace + 10),
                    target_hr_min=hr_min,
                    target_hr_max=hr_max,
                    notes="Comfortably hard - can say short phrases",
                ),
                WorkoutInterval(
                    type="cooldown",
                    duration_sec=600,  # 10 min
                    target_pace_min=int(easy_pace),
                    target_pace_max=int(easy_pace + 60),
                    target_hr_min=easy_hr_min,
                    target_hr_max=easy_hr_max,
                    notes="Easy jog to recover",
                ),
            ]

        elif request.workout_type == "intervals":
            workout_name = "Interval Session"
            description = "High-intensity intervals with recovery"
            interval_pace = training_paces.get("interval", {}).get("pace_sec", 270)
            easy_pace = training_paces.get("easy", {}).get("pace_sec", 360)
            hr_min, hr_max = hr_zone(0.85, 0.95)
            recovery_hr_min, recovery_hr_max = hr_zone(0.5, 0.7)

            # Calculate number of intervals based on duration
            available_time = duration - 20  # Warmup + cooldown
            interval_time = 3 + 2  # 3 min work + 2 min recovery
            num_intervals = max(4, min(8, available_time // interval_time))

            intervals = [
                WorkoutInterval(
                    type="warmup",
                    duration_sec=600,  # 10 min
                    target_pace_min=int(easy_pace - 15),
                    target_pace_max=int(easy_pace + 30),
                    notes="Easy jog with strides",
                ),
            ]

            for i in range(num_intervals):
                intervals.append(WorkoutInterval(
                    type="work",
                    duration_sec=180,  # 3 min / ~800m
                    target_pace_min=int(interval_pace - 10),
                    target_pace_max=int(interval_pace + 10),
                    target_hr_min=hr_min,
                    target_hr_max=hr_max,
                    notes=f"Interval {i+1}/{num_intervals} - hard but controlled",
                ))
                if i < num_intervals - 1:  # No recovery after last interval
                    intervals.append(WorkoutInterval(
                        type="recovery",
                        duration_sec=120,  # 2 min
                        target_hr_min=recovery_hr_min,
                        target_hr_max=recovery_hr_max,
                        notes="Easy jog recovery",
                    ))

            intervals.append(WorkoutInterval(
                type="cooldown",
                duration_sec=600,  # 10 min
                target_pace_min=int(easy_pace),
                target_pace_max=int(easy_pace + 60),
                notes="Easy jog to recover",
            ))

        elif request.workout_type == "threshold":
            workout_name = "Threshold Workout"
            description = "Cruise intervals at threshold pace"
            threshold_pace = training_paces.get("threshold", {}).get("pace_sec", 285)
            easy_pace = training_paces.get("easy", {}).get("pace_sec", 360)
            hr_min, hr_max = hr_zone(0.80, 0.90)

            intervals = [
                WorkoutInterval(
                    type="warmup",
                    duration_sec=600,
                    notes="Easy jog with strides",
                ),
                WorkoutInterval(
                    type="work",
                    duration_sec=480,  # 8 min
                    target_pace_min=int(threshold_pace - 10),
                    target_pace_max=int(threshold_pace + 10),
                    target_hr_min=hr_min,
                    target_hr_max=hr_max,
                    notes="Threshold pace - hard but sustainable",
                    repetitions=3,
                ),
                WorkoutInterval(
                    type="recovery",
                    duration_sec=120,
                    notes="Easy jog between intervals",
                ),
                WorkoutInterval(
                    type="cooldown",
                    duration_sec=600,
                    notes="Easy jog to recover",
                ),
            ]

        elif request.workout_type == "long":
            workout_name = "Long Run"
            description = "Extended endurance run"
            long_pace = training_paces.get("long", {}).get("pace_sec", 340)
            hr_min, hr_max = hr_zone(0.60, 0.75)
            duration = request.duration_min or 90

            intervals = [
                WorkoutInterval(
                    type="warmup",
                    duration_sec=300,
                    notes="Very easy start",
                ),
                WorkoutInterval(
                    type="work",
                    duration_sec=(duration - 10) * 60,
                    target_pace_min=int(long_pace - 15),
                    target_pace_max=int(long_pace + 30),
                    target_hr_min=hr_min,
                    target_hr_max=hr_max,
                    notes="Steady aerobic pace, stay relaxed",
                ),
                WorkoutInterval(
                    type="cooldown",
                    duration_sec=300,
                    notes="Easy finish",
                ),
            ]

        else:
            raise HTTPException(status_code=400, detail=f"Unknown workout type: {request.workout_type}")

        # Calculate totals
        total_duration = sum(i.duration_sec or 0 for i in intervals) // 60

        workout = StructuredWorkout(
            workout_id=f"workout_{uuid.uuid4().hex[:8]}",
            name=workout_name,
            description=description,
            intervals=intervals,
            estimated_duration_min=total_duration,
        )

        return workout

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to design workout: {str(e)}")


@router.get("/{workout_id}")
async def get_workout(workout_id: str):
    """Get a specific designed workout."""
    # TODO: Implement workout storage
    raise HTTPException(status_code=404, detail=f"Workout {workout_id} not found")


@router.get("/{workout_id}/fit")
async def download_fit(workout_id: str):
    """
    Download workout as Garmin FIT file.

    The FIT file can be:
    1. Transferred to Garmin device via USB (/Garmin/NewFiles/)
    2. Imported to Garmin Connect
    """
    # TODO: Implement FIT file generation
    raise HTTPException(status_code=501, detail="FIT export not yet implemented")


@router.post("/{workout_id}/export-garmin")
async def export_to_garmin(workout_id: str):
    """
    Push workout directly to Garmin Connect.

    Requires Garmin Connect authentication.
    """
    # TODO: Implement Garmin Connect export
    raise HTTPException(status_code=501, detail="Garmin export not yet implemented")
