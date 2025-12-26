"""Training plan generation and management API routes."""

from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any
import json

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from ..deps import get_coach_service, get_training_db
from ...models.plans import (
    TrainingPlan,
    TrainingWeek,
    PlannedSession,
    RaceGoal,
    PlanConstraints,
    AthleteContext,
    PeriodizationType,
    TrainingPhase,
    WorkoutType,
    RaceDistance,
    GeneratePlanRequestSchema,
    GoalInputSchema,
    ConstraintsInputSchema,
    AdaptPlanRequestSchema,
    parse_goal_input,
    parse_constraints_input,
    parse_time_string,
    day_name_to_number,
)
from ...agents.plan_agent import PlanAgent, PlanGenerationError


router = APIRouter()


# In-memory storage for plans (would be replaced with database in production)
_plans_storage: Dict[str, Dict[str, Any]] = {}


# ============================================================================
# Pydantic Models for API
# ============================================================================

class PlanConstraintsInput(BaseModel):
    """Constraints for training plan generation."""
    days_per_week: int = Field(5, ge=3, le=7, description="Training days per week")
    long_run_day: str = Field("sunday", description="Day of week for long run")
    rest_days: List[str] = Field(default_factory=list, description="Days to skip training")
    max_weekly_hours: float = Field(8.0, ge=2.0, le=20.0, description="Maximum weekly training hours")
    max_session_duration_min: int = Field(150, ge=30, le=240, description="Maximum session duration")
    include_cross_training: bool = Field(False, description="Include cross-training sessions")
    back_to_back_hard_ok: bool = Field(False, description="Allow consecutive hard days")


class GoalInput(BaseModel):
    """Race goal for plan generation."""
    race_date: str = Field(..., description="Race date in YYYY-MM-DD format")
    distance: str = Field(..., description="Race distance: 5k, 10k, half, marathon, ultra")
    target_time: str = Field(..., description="Target time in H:MM:SS or MM:SS format")
    race_name: Optional[str] = Field(None, description="Name of the race")
    priority: int = Field(1, ge=1, le=3, description="Race priority (1=A race, 2=B, 3=C)")


class GeneratePlanRequest(BaseModel):
    """Request to generate a training plan."""
    goal: GoalInput
    constraints: PlanConstraintsInput = Field(default_factory=PlanConstraintsInput)
    periodization_type: Optional[str] = Field(
        None,
        description="Periodization type: linear, reverse, block. If not specified, AI decides."
    )


class UpdatePlanRequest(BaseModel):
    """Request to update a training plan."""
    name: Optional[str] = None
    is_active: Optional[bool] = None
    weeks: Optional[List[Dict[str, Any]]] = None


class AdaptPlanRequest(BaseModel):
    """Request to adapt a training plan based on performance."""
    reason: Optional[str] = Field(None, description="Reason for adaptation")
    force_recalculate: bool = Field(False, description="Force full recalculation")
    weeks_to_adapt: Optional[List[int]] = Field(
        None,
        description="Specific weeks to adapt. If not specified, adapts all remaining weeks."
    )


class PlanSessionOutput(BaseModel):
    """Output schema for a planned session."""
    day_of_week: int
    day_name: str
    workout_type: str
    description: str
    target_duration_min: int
    target_load: float
    target_pace: Optional[str] = None
    target_hr_zone: Optional[str] = None
    intervals: Optional[List[Dict[str, Any]]] = None
    notes: Optional[str] = None


class PlanWeekOutput(BaseModel):
    """Output schema for a training week."""
    week_number: int
    phase: str
    target_load: float
    planned_duration_min: int
    workout_count: int
    quality_session_count: int
    sessions: List[PlanSessionOutput]
    focus: Optional[str] = None
    notes: Optional[str] = None
    is_cutback: bool = False


class PlanOutput(BaseModel):
    """Output schema for a complete training plan."""
    id: str
    name: Optional[str]
    description: Optional[str]
    goal: Dict[str, Any]
    periodization: str
    total_weeks: int
    peak_week: int
    phases_summary: Dict[str, int]
    total_planned_load: float
    weeks: List[PlanWeekOutput]
    is_active: bool
    created_at: str
    updated_at: Optional[str] = None


class PlanSummaryOutput(BaseModel):
    """Summary output for plan listing."""
    id: str
    name: Optional[str]
    goal: Dict[str, Any]
    periodization: str
    total_weeks: int
    phases_summary: Dict[str, int]
    is_active: bool
    created_at: str


# ============================================================================
# Helper Functions
# ============================================================================

def _get_athlete_context(coach_service, training_db) -> AthleteContext:
    """Build athlete context from available data."""
    try:
        # Get current fitness metrics
        briefing = coach_service.get_daily_briefing(date.today())
        training_status = briefing.get("training_status", {})

        current_ctl = training_status.get("ctl", 30.0)
        current_atl = training_status.get("atl", 30.0)

        # Get recent weekly load (average over last 4 weeks)
        weekly_loads = []
        for weeks_back in range(4):
            try:
                summary = coach_service.get_weekly_summary(weeks_back)
                weekly_loads.append(summary.get("total_load", 0))
            except Exception:
                pass

        recent_weekly_load = sum(weekly_loads) / len(weekly_loads) if weekly_loads else current_ctl * 7

        # Estimate weekly hours (rough: 1 load point ~= 1 minute)
        recent_weekly_hours = recent_weekly_load / 60

        return AthleteContext(
            current_ctl=current_ctl,
            current_atl=current_atl,
            recent_weekly_load=recent_weekly_load,
            recent_weekly_hours=recent_weekly_hours,
            max_hr=185,  # Could get from profile
            rest_hr=55,
            threshold_hr=165,
        )
    except Exception as e:
        # Return defaults if we can't get actual data
        return AthleteContext(
            current_ctl=30.0,
            current_atl=30.0,
            recent_weekly_load=200.0,
            recent_weekly_hours=4.0,
        )


def _plan_to_storage(plan: TrainingPlan) -> Dict[str, Any]:
    """Convert TrainingPlan to storage format."""
    return plan.to_dict()


def _storage_to_plan(data: Dict[str, Any]) -> TrainingPlan:
    """Convert storage format back to TrainingPlan."""
    # Parse goal
    goal_data = data["goal"]
    goal = RaceGoal(
        race_date=datetime.strptime(goal_data["race_date"], "%Y-%m-%d").date(),
        distance=RaceDistance(goal_data["distance"]),
        target_time_seconds=goal_data["target_time_seconds"],
        race_name=goal_data.get("race_name"),
        priority=goal_data.get("priority", 1),
    )

    # Parse weeks
    weeks = []
    for week_data in data["weeks"]:
        sessions = []
        for session_data in week_data["sessions"]:
            sessions.append(PlannedSession(
                day_of_week=session_data["day_of_week"],
                workout_type=WorkoutType(session_data["workout_type"]),
                description=session_data["description"],
                target_duration_min=session_data["target_duration_min"],
                target_load=session_data["target_load"],
                target_pace=session_data.get("target_pace"),
                target_hr_zone=session_data.get("target_hr_zone"),
                intervals=session_data.get("intervals"),
                notes=session_data.get("notes"),
            ))

        weeks.append(TrainingWeek(
            week_number=week_data["week_number"],
            phase=TrainingPhase(week_data["phase"]),
            target_load=week_data["target_load"],
            sessions=sessions,
            focus=week_data.get("focus"),
            notes=week_data.get("notes"),
            is_cutback=week_data.get("is_cutback", False),
        ))

    # Parse athlete context if available
    athlete_context = None
    if data.get("athlete_context"):
        ac_data = data["athlete_context"]
        athlete_context = AthleteContext(
            current_ctl=ac_data["current_ctl"],
            current_atl=ac_data["current_atl"],
            recent_weekly_load=ac_data["recent_weekly_load"],
            recent_weekly_hours=ac_data["recent_weekly_hours"],
            max_hr=ac_data.get("max_hr", 185),
            rest_hr=ac_data.get("rest_hr", 55),
            threshold_hr=ac_data.get("threshold_hr", 165),
            vdot=ac_data.get("vdot"),
        )

    # Parse constraints if available
    constraints = None
    if data.get("constraints"):
        c_data = data["constraints"]
        constraints = PlanConstraints(
            days_per_week=c_data["days_per_week"],
            long_run_day=c_data["long_run_day"],
            rest_days=c_data.get("rest_days", []),
            max_weekly_hours=c_data["max_weekly_hours"],
            max_session_duration_min=c_data.get("max_session_duration_min", 150),
            include_cross_training=c_data.get("include_cross_training", False),
            back_to_back_hard_ok=c_data.get("back_to_back_hard_ok", False),
        )

    return TrainingPlan(
        id=data["id"],
        goal=goal,
        weeks=weeks,
        periodization=PeriodizationType(data["periodization"]),
        peak_week=data["peak_week"],
        created_at=datetime.fromisoformat(data["created_at"]),
        athlete_context=athlete_context,
        constraints=constraints,
        name=data.get("name"),
        description=data.get("description"),
        is_active=data.get("is_active", False),
        updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
        adaptation_history=data.get("adaptation_history", []),
    )


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/generate", response_model=PlanOutput)
async def generate_plan(
    request: GeneratePlanRequest,
    coach_service=Depends(get_coach_service),
    training_db=Depends(get_training_db),
):
    """
    Generate a periodized training plan using AI.

    The plan is based on:
    - Race goal (distance, target time, date)
    - Current fitness level (CTL)
    - Athlete constraints (days/week, max hours, etc.)

    Uses LangGraph-based PlanAgent with GPT for intelligent plan structure
    and session generation.
    """
    try:
        # Parse goal
        race_date = datetime.strptime(request.goal.race_date, "%Y-%m-%d").date()
        weeks_until_race = (race_date - date.today()).days // 7

        if weeks_until_race < 1:
            raise HTTPException(
                status_code=400,
                detail="Race date must be at least 1 week away"
            )

        if weeks_until_race > 52:
            raise HTTPException(
                status_code=400,
                detail="Race date too far in future (max 52 weeks)"
            )

        # Parse distance
        distance_map = {
            "5k": RaceDistance.FIVE_K,
            "10k": RaceDistance.TEN_K,
            "half": RaceDistance.HALF_MARATHON,
            "half_marathon": RaceDistance.HALF_MARATHON,
            "marathon": RaceDistance.MARATHON,
            "ultra": RaceDistance.ULTRA,
        }
        distance = distance_map.get(request.goal.distance.lower(), RaceDistance.CUSTOM)

        # Parse target time
        target_seconds = parse_time_string(request.goal.target_time)

        # Create goal object
        goal = RaceGoal(
            race_date=race_date,
            distance=distance,
            target_time_seconds=target_seconds,
            race_name=request.goal.race_name,
            priority=request.goal.priority,
        )

        # Create constraints
        constraints = PlanConstraints(
            days_per_week=request.constraints.days_per_week,
            long_run_day=day_name_to_number(request.constraints.long_run_day),
            rest_days=[day_name_to_number(d) for d in request.constraints.rest_days],
            max_weekly_hours=request.constraints.max_weekly_hours,
            max_session_duration_min=request.constraints.max_session_duration_min,
            include_cross_training=request.constraints.include_cross_training,
            back_to_back_hard_ok=request.constraints.back_to_back_hard_ok,
        )

        # Get athlete context
        athlete_context = _get_athlete_context(coach_service, training_db)

        # Generate plan using PlanAgent
        agent = PlanAgent()
        plan = await agent.generate_plan(
            goal=goal,
            athlete_context=athlete_context,
            constraints=constraints,
        )

        # Store the plan
        _plans_storage[plan.id] = _plan_to_storage(plan)

        return plan.to_dict()

    except PlanGenerationError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate plan: {str(e)}"
        )


@router.get("", response_model=Dict[str, Any])
async def list_plans(
    active_only: bool = False,
    limit: int = 50,
    offset: int = 0,
):
    """
    List all training plans.

    Args:
        active_only: Only return active plans
        limit: Maximum number of plans to return
        offset: Number of plans to skip
    """
    plans = list(_plans_storage.values())

    # Filter by active status if requested
    if active_only:
        plans = [p for p in plans if p.get("is_active", False)]

    # Sort by created_at descending (newest first)
    plans.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    # Apply pagination
    total = len(plans)
    plans = plans[offset:offset + limit]

    # Return summary format
    summaries = []
    for plan in plans:
        summaries.append({
            "id": plan["id"],
            "name": plan.get("name"),
            "goal": {
                "race_date": plan["goal"]["race_date"],
                "distance": plan["goal"]["distance"],
                "target_time": plan["goal"]["target_time_formatted"],
            },
            "periodization": plan["periodization"],
            "total_weeks": plan["total_weeks"],
            "phases_summary": plan["phases_summary"],
            "is_active": plan.get("is_active", False),
            "created_at": plan["created_at"],
        })

    return {
        "plans": summaries,
        "count": len(summaries),
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.get("/active", response_model=Dict[str, Any])
async def get_active_plan():
    """
    Get the currently active training plan.

    Returns the active plan with current week information.
    """
    active_plans = [p for p in _plans_storage.values() if p.get("is_active", False)]

    if not active_plans:
        return {
            "active_plan": None,
            "message": "No active plan. Generate a new plan or activate an existing one.",
        }

    # Get the most recently created active plan
    active_plan = max(active_plans, key=lambda x: x.get("created_at", ""))
    plan = _storage_to_plan(active_plan)

    # Get current week
    current_week = plan.get_current_week()
    current_week_data = current_week.to_dict() if current_week else None

    # Calculate progress
    weeks_completed = 0
    if current_week:
        weeks_completed = current_week.week_number - 1

    return {
        "active_plan": plan.to_summary_dict(),
        "current_week": current_week_data,
        "weeks_completed": weeks_completed,
        "weeks_remaining": plan.total_weeks - weeks_completed,
        "days_until_race": plan.goal.weeks_until_race() * 7,
    }


@router.get("/{plan_id}", response_model=PlanOutput)
async def get_plan(plan_id: str):
    """
    Get a specific training plan by ID.

    Returns the complete plan with all weeks and sessions.
    """
    if plan_id not in _plans_storage:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")

    return _plans_storage[plan_id]


@router.get("/{plan_id}/week/{week_number}", response_model=PlanWeekOutput)
async def get_plan_week(plan_id: str, week_number: int):
    """
    Get a specific week from a training plan.
    """
    if plan_id not in _plans_storage:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")

    plan_data = _plans_storage[plan_id]
    weeks = plan_data.get("weeks", [])

    for week in weeks:
        if week["week_number"] == week_number:
            return week

    raise HTTPException(
        status_code=404,
        detail=f"Week {week_number} not found in plan {plan_id}"
    )


@router.put("/{plan_id}", response_model=PlanOutput)
async def update_plan(plan_id: str, request: UpdatePlanRequest):
    """
    Update a training plan.

    Can update:
    - name: Plan name
    - is_active: Whether this is the active plan
    - weeks: Replace week data
    """
    if plan_id not in _plans_storage:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")

    plan_data = _plans_storage[plan_id]

    # Update fields if provided
    if request.name is not None:
        plan_data["name"] = request.name

    if request.is_active is not None:
        # If activating this plan, deactivate others
        if request.is_active:
            for pid, pdata in _plans_storage.items():
                if pid != plan_id:
                    pdata["is_active"] = False
        plan_data["is_active"] = request.is_active

    if request.weeks is not None:
        plan_data["weeks"] = request.weeks

    # Update timestamp
    plan_data["updated_at"] = datetime.now().isoformat()

    _plans_storage[plan_id] = plan_data

    return plan_data


@router.delete("/{plan_id}")
async def delete_plan(plan_id: str):
    """
    Delete a training plan.
    """
    if plan_id not in _plans_storage:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")

    del _plans_storage[plan_id]

    return {"message": f"Plan {plan_id} deleted successfully"}


@router.post("/{plan_id}/activate")
async def activate_plan(plan_id: str):
    """
    Set a plan as the active training plan.

    Only one plan can be active at a time.
    """
    if plan_id not in _plans_storage:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")

    # Deactivate all other plans
    for pid, pdata in _plans_storage.items():
        pdata["is_active"] = pid == plan_id

    return {
        "message": f"Plan {plan_id} is now active",
        "plan_id": plan_id,
    }


@router.post("/{plan_id}/adapt", response_model=PlanOutput)
async def adapt_plan(
    plan_id: str,
    request: AdaptPlanRequest,
    coach_service=Depends(get_coach_service),
    training_db=Depends(get_training_db),
):
    """
    AI-assisted plan adaptation based on recent performance.

    Analyzes recent training data and adapts the remaining weeks of the plan:
    - Adjusts target loads based on actual vs planned
    - Modifies intensity distribution based on recovery
    - Considers performance trends and fatigue indicators

    Args:
        plan_id: The plan to adapt
        request: Adaptation parameters
    """
    if plan_id not in _plans_storage:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")

    try:
        plan = _storage_to_plan(_plans_storage[plan_id])

        # Get performance data
        performance_data = _gather_performance_data(coach_service, training_db)

        # Use PlanAgent for adaptation
        agent = PlanAgent()
        adapted_plan = await agent.adapt_plan(
            plan=plan,
            performance_data=performance_data,
            weeks_to_adapt=request.weeks_to_adapt,
        )

        # Store the adapted plan
        _plans_storage[plan_id] = _plan_to_storage(adapted_plan)

        return adapted_plan.to_dict()

    except PlanGenerationError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to adapt plan: {str(e)}"
        )


@router.post("/{plan_id}/duplicate", response_model=PlanOutput)
async def duplicate_plan(plan_id: str, new_race_date: Optional[str] = None):
    """
    Duplicate an existing plan, optionally adjusting for a new race date.

    Args:
        plan_id: The plan to duplicate
        new_race_date: New race date (YYYY-MM-DD). If provided, plan dates are adjusted.
    """
    if plan_id not in _plans_storage:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")

    original_data = _plans_storage[plan_id].copy()

    # Generate new ID
    new_id = TrainingPlan.generate_id()
    original_data["id"] = new_id
    original_data["name"] = f"{original_data.get('name', 'Plan')} (Copy)"
    original_data["is_active"] = False
    original_data["created_at"] = datetime.now().isoformat()
    original_data["updated_at"] = None
    original_data["adaptation_history"] = []

    # Adjust race date if provided
    if new_race_date:
        try:
            new_date = datetime.strptime(new_race_date, "%Y-%m-%d").date()
            original_data["goal"]["race_date"] = new_race_date
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid date format. Use YYYY-MM-DD."
            )

    _plans_storage[new_id] = original_data

    return original_data


@router.get("/{plan_id}/export")
async def export_plan(plan_id: str, format: str = "json"):
    """
    Export a plan in various formats.

    Args:
        plan_id: The plan to export
        format: Export format (json, ical, csv)
    """
    if plan_id not in _plans_storage:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")

    plan_data = _plans_storage[plan_id]

    if format == "json":
        return plan_data
    elif format == "ical":
        # Generate iCal format
        ical_content = _generate_ical(plan_data)
        return {
            "format": "ical",
            "content": ical_content,
            "filename": f"training_plan_{plan_id}.ics",
        }
    elif format == "csv":
        # Generate CSV format
        csv_content = _generate_csv(plan_data)
        return {
            "format": "csv",
            "content": csv_content,
            "filename": f"training_plan_{plan_id}.csv",
        }
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {format}. Use json, ical, or csv."
        )


# ============================================================================
# Helper Functions for Endpoints
# ============================================================================

def _gather_performance_data(coach_service, training_db) -> Dict[str, Any]:
    """Gather recent performance data for plan adaptation."""
    try:
        # Get last 2 weeks of data
        today = date.today()
        two_weeks_ago = today - timedelta(days=14)

        activities = coach_service.get_recent_activities(days=14)

        # Get fitness metrics
        briefing = coach_service.get_daily_briefing(today)
        training_status = briefing.get("training_status", {})

        # Calculate actual vs planned (simplified)
        total_load = sum(a.get("hrss", 0) or a.get("trimp", 0) for a in activities)

        # Get weekly summaries
        week_summaries = []
        for weeks_back in range(2):
            try:
                summary = coach_service.get_weekly_summary(weeks_back)
                week_summaries.append({
                    "week": weeks_back,
                    "total_load": summary.get("total_load", 0),
                    "workout_count": summary.get("workout_count", 0),
                    "ctl_change": summary.get("ctl_change", 0),
                })
            except Exception:
                pass

        return {
            "current_ctl": training_status.get("ctl", 30),
            "current_atl": training_status.get("atl", 30),
            "current_tsb": training_status.get("tsb", 0),
            "acwr": training_status.get("acwr", 1.0),
            "risk_zone": training_status.get("risk_zone", "optimal"),
            "readiness": briefing.get("readiness", {}).get("score", 70),
            "total_load_2_weeks": total_load,
            "activity_count_2_weeks": len(activities),
            "weekly_summaries": week_summaries,
        }
    except Exception as e:
        # Return minimal data if we can't get actual data
        return {
            "current_ctl": 30,
            "current_atl": 30,
            "error": str(e),
        }


def _generate_ical(plan_data: Dict[str, Any]) -> str:
    """Generate iCal format for the training plan."""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Reactive Training App//Training Plan//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    race_date = datetime.strptime(plan_data["goal"]["race_date"], "%Y-%m-%d").date()
    total_weeks = plan_data["total_weeks"]

    for week in plan_data["weeks"]:
        week_number = week["week_number"]
        weeks_before_race = total_weeks - week_number + 1
        week_start = race_date - timedelta(weeks=weeks_before_race)

        for session in week["sessions"]:
            if session["workout_type"] == "rest":
                continue

            day_offset = session["day_of_week"]
            session_date = week_start + timedelta(days=day_offset)

            # Create event
            lines.append("BEGIN:VEVENT")
            lines.append(f"DTSTART;VALUE=DATE:{session_date.strftime('%Y%m%d')}")
            lines.append(f"DTEND;VALUE=DATE:{session_date.strftime('%Y%m%d')}")
            lines.append(f"SUMMARY:{session['workout_type'].upper()}: {session['description'][:50]}")
            lines.append(f"DESCRIPTION:Duration: {session['target_duration_min']} min\\nZone: {session.get('target_hr_zone', 'N/A')}")
            lines.append(f"CATEGORIES:Training,{week['phase'].upper()}")
            lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")

    return "\n".join(lines)


def _generate_csv(plan_data: Dict[str, Any]) -> str:
    """Generate CSV format for the training plan."""
    lines = ["Week,Day,Date,Phase,Type,Duration (min),Description,HR Zone,Notes"]

    race_date = datetime.strptime(plan_data["goal"]["race_date"], "%Y-%m-%d").date()
    total_weeks = plan_data["total_weeks"]

    for week in plan_data["weeks"]:
        week_number = week["week_number"]
        weeks_before_race = total_weeks - week_number + 1
        week_start = race_date - timedelta(weeks=weeks_before_race)

        for session in week["sessions"]:
            day_offset = session["day_of_week"]
            session_date = week_start + timedelta(days=day_offset)

            line = [
                str(week_number),
                session["day_name"],
                session_date.strftime("%Y-%m-%d"),
                week["phase"],
                session["workout_type"],
                str(session["target_duration_min"]),
                f'"{session["description"]}"',
                session.get("target_hr_zone") or "",
                f'"{session.get("notes", "")}"' if session.get("notes") else "",
            ]
            lines.append(",".join(line))

    return "\n".join(lines)
