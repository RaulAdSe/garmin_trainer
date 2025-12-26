"""Training plan generation API routes."""

from datetime import date, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..deps import get_coach_service, get_training_db


router = APIRouter()


class PlanConstraints(BaseModel):
    """Constraints for training plan generation."""
    days_per_week: int = 5
    long_run_day: str = "sunday"  # Day of week for long run
    no_train_days: List[str] = []  # Days to skip
    max_weekly_hours: float = 8.0
    include_cross_training: bool = False


class GoalInput(BaseModel):
    """Race goal for plan generation."""
    race_date: str  # YYYY-MM-DD
    distance: str  # 5k, 10k, half, marathon
    target_time: str  # H:MM:SS or MM:SS


class GeneratePlanRequest(BaseModel):
    """Request to generate a training plan."""
    goal: GoalInput
    constraints: PlanConstraints = PlanConstraints()


class PlannedSession(BaseModel):
    """A planned training session."""
    day: str
    session_type: str  # easy, long, tempo, intervals, rest, etc.
    duration_min: Optional[int] = None
    description: str
    target_pace: Optional[str] = None
    target_hr_zone: Optional[str] = None


class TrainingWeek(BaseModel):
    """A week of training."""
    week_number: int
    phase: str  # base, build, peak, taper
    target_load: float
    sessions: List[PlannedSession]
    notes: Optional[str] = None


class TrainingPlan(BaseModel):
    """Complete training plan."""
    plan_id: str
    goal: GoalInput
    periodization: str  # linear, reverse, block
    total_weeks: int
    peak_week: int
    weeks: List[TrainingWeek]
    created_at: str


@router.post("/generate")
async def generate_plan(
    request: GeneratePlanRequest,
    coach_service = Depends(get_coach_service),
    training_db = Depends(get_training_db),
):
    """
    Generate a periodized training plan using AI.

    The plan is based on:
    - Race goal (distance, target time, date)
    - Current fitness level (CTL)
    - Athlete constraints (days/week, etc.)

    Uses GPT-5-mini for plan structure and GPT-5-nano for session details.
    """
    try:
        from datetime import datetime
        import uuid

        # Parse goal
        race_date = datetime.strptime(request.goal.race_date, "%Y-%m-%d").date()
        weeks_until_race = (race_date - date.today()).days // 7

        if weeks_until_race < 1:
            raise HTTPException(status_code=400, detail="Race date must be at least 1 week away")

        if weeks_until_race > 52:
            raise HTTPException(status_code=400, detail="Race date too far in future (max 52 weeks)")

        # Get current fitness
        briefing = coach_service.get_daily_briefing(date.today())
        current_ctl = briefing.get("training_status", {}).get("ctl", 30)

        # Determine periodization phases
        if weeks_until_race >= 16:
            phases = [
                ("base", 4),
                ("build", weeks_until_race - 8),
                ("peak", 3),
                ("taper", 1),
            ]
        elif weeks_until_race >= 8:
            phases = [
                ("base", 2),
                ("build", weeks_until_race - 5),
                ("peak", 2),
                ("taper", 1),
            ]
        else:
            phases = [
                ("build", weeks_until_race - 2),
                ("peak", 1),
                ("taper", 1),
            ]

        # Generate weeks
        weeks = []
        week_num = 1
        target_ctl_growth = (60 - current_ctl) / weeks_until_race  # Target CTL 60 by race

        for phase_name, phase_weeks in phases:
            for i in range(phase_weeks):
                # Calculate load for this week
                if phase_name == "taper":
                    target_load = current_ctl * 4  # Reduced load
                elif phase_name == "peak":
                    target_load = current_ctl * 6  # Moderate load
                elif phase_name == "build":
                    target_load = current_ctl * 7 * (1 + (i * 0.05))  # Progressive
                else:  # base
                    target_load = current_ctl * 6

                # Create sessions based on constraints
                sessions = _generate_week_sessions(
                    phase=phase_name,
                    days_per_week=request.constraints.days_per_week,
                    long_run_day=request.constraints.long_run_day,
                    no_train_days=request.constraints.no_train_days,
                    week_in_phase=i + 1,
                    total_phase_weeks=phase_weeks,
                )

                weeks.append(TrainingWeek(
                    week_number=week_num,
                    phase=phase_name,
                    target_load=round(target_load, 1),
                    sessions=sessions,
                    notes=_get_phase_notes(phase_name, i + 1, phase_weeks),
                ))

                week_num += 1
                current_ctl += target_ctl_growth

        plan = TrainingPlan(
            plan_id=f"plan_{uuid.uuid4().hex[:8]}",
            goal=request.goal,
            periodization="linear",
            total_weeks=weeks_until_race,
            peak_week=weeks_until_race - 1,
            weeks=weeks,
            created_at=datetime.now().isoformat(),
        )

        return plan

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate plan: {str(e)}")


def _generate_week_sessions(
    phase: str,
    days_per_week: int,
    long_run_day: str,
    no_train_days: List[str],
    week_in_phase: int,
    total_phase_weeks: int,
) -> List[PlannedSession]:
    """Generate sessions for a training week."""

    day_order = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    sessions = []

    # Determine which days to train
    available_days = [d for d in day_order if d not in no_train_days]
    train_days = available_days[:days_per_week]

    for day in day_order:
        if day in no_train_days:
            sessions.append(PlannedSession(
                day=day,
                session_type="rest",
                description="Rest day",
            ))
        elif day not in train_days:
            sessions.append(PlannedSession(
                day=day,
                session_type="rest",
                description="Rest day",
            ))
        elif day == long_run_day and day in train_days:
            # Long run
            duration = 60 + (week_in_phase * 10) if phase != "taper" else 45
            sessions.append(PlannedSession(
                day=day,
                session_type="long",
                duration_min=min(duration, 150),
                description="Long run - easy pace, build endurance",
                target_hr_zone="Zone 2",
            ))
        elif phase in ["build", "peak"] and day == "tuesday" and day in train_days:
            # Quality session 1
            if phase == "peak":
                sessions.append(PlannedSession(
                    day=day,
                    session_type="threshold",
                    duration_min=45,
                    description="Threshold intervals: 4x8min at threshold pace",
                    target_hr_zone="Zone 4",
                ))
            else:
                sessions.append(PlannedSession(
                    day=day,
                    session_type="tempo",
                    duration_min=50,
                    description="Tempo run: 20-30min at tempo pace",
                    target_hr_zone="Zone 3-4",
                ))
        elif phase in ["build", "peak"] and day == "thursday" and day in train_days:
            # Quality session 2
            sessions.append(PlannedSession(
                day=day,
                session_type="intervals",
                duration_min=45,
                description="Intervals: 6x800m at interval pace, 400m recovery",
                target_hr_zone="Zone 4-5",
            ))
        elif day in train_days:
            # Easy day
            sessions.append(PlannedSession(
                day=day,
                session_type="easy",
                duration_min=40,
                description="Easy run - recovery pace",
                target_hr_zone="Zone 1-2",
            ))
        else:
            sessions.append(PlannedSession(
                day=day,
                session_type="rest",
                description="Rest day",
            ))

    return sessions


def _get_phase_notes(phase: str, week_in_phase: int, total_weeks: int) -> str:
    """Get notes for the training phase."""
    notes = {
        "base": "Focus on building aerobic base. Keep runs easy and conversational.",
        "build": "Introduce quality sessions. Listen to your body and recover well.",
        "peak": "Race-specific training. Maintain fitness while staying fresh.",
        "taper": "Reduce volume, maintain intensity. Stay confident and rested.",
    }

    base_note = notes.get(phase, "")

    if week_in_phase == 1:
        return f"{base_note} First week of {phase} phase."
    elif week_in_phase == total_weeks:
        return f"{base_note} Last week of {phase} phase - transition coming."

    return base_note


@router.get("")
async def list_plans():
    """List all training plans."""
    # TODO: Implement plan storage
    return {"plans": [], "count": 0}


@router.get("/{plan_id}")
async def get_plan(plan_id: str):
    """Get a specific training plan."""
    # TODO: Implement plan storage/retrieval
    raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")


@router.get("/active")
async def get_active_plan():
    """Get the currently active training plan."""
    # TODO: Implement active plan tracking
    return {"active_plan": None, "message": "No active plan"}


@router.post("/{plan_id}/adapt")
async def adapt_plan(
    plan_id: str,
    coach_service = Depends(get_coach_service),
):
    """
    AI-assisted plan adaptation based on recent performance.

    Adjusts the plan based on:
    - Actual vs planned load
    - Fitness progression
    - Recovery indicators
    """
    # TODO: Implement plan adaptation
    raise HTTPException(status_code=501, detail="Plan adaptation not yet implemented")
