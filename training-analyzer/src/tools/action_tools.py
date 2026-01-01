"""
LangChain-compatible action tools for the agentic AI coach.

These tools allow the AI agent to take actions like:
- Creating personalized training plans
- Designing individual workouts
- Logging training notes
- Setting race goals

The tools integrate with existing agents and services where available,
with fallback to mock data when services are not yet implemented.
"""

import asyncio
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool

# Import existing agents and services
from ..agents import (
    PlanAgent,
    WorkoutDesignAgent,
    get_workout_agent,
)
from ..models.plans import (
    AthleteContext as PlanAthleteContext,
    PlanConstraints,
    RaceDistance,
    RaceGoal,
    TrainingPlan,
    parse_time_string,
)
from ..models.workouts import (
    AthleteContext as WorkoutAthleteContext,
    StructuredWorkout,
    WorkoutDesignRequest,
)


# ============================================================================
# Helper Functions
# ============================================================================

def _get_default_athlete_context() -> WorkoutAthleteContext:
    """
    Get default athlete context for workout design.

    In a full implementation, this would fetch from the database
    based on the current user's profile and training data.
    """
    # TODO: Integrate with coach service to get real athlete context
    return WorkoutAthleteContext(
        max_hr=185,
        rest_hr=55,
        lthr=165,
        ctl=45.0,
        atl=40.0,
        tsb=5.0,
        readiness_score=75,
        easy_pace=360,      # 6:00/km
        long_pace=345,      # 5:45/km
        tempo_pace=300,     # 5:00/km
        threshold_pace=285, # 4:45/km
        interval_pace=270,  # 4:30/km
        race_pace=290,      # 4:50/km
    )


def _get_default_plan_athlete_context() -> PlanAthleteContext:
    """
    Get default athlete context for plan generation.

    In a full implementation, this would fetch from the database
    based on the current user's profile and training data.
    """
    # TODO: Integrate with coach service to get real athlete context
    return PlanAthleteContext(
        current_ctl=45.0,
        current_atl=40.0,
        recent_weekly_load=350.0,
        recent_weekly_hours=6.0,
        max_hr=185,
        rest_hr=55,
        threshold_hr=165,
        vdot=45.0,
    )


def _parse_race_distance(distance_str: str) -> RaceDistance:
    """Parse a race distance string to RaceDistance enum."""
    distance_map = {
        "5k": RaceDistance.FIVE_K,
        "5K": RaceDistance.FIVE_K,
        "10k": RaceDistance.TEN_K,
        "10K": RaceDistance.TEN_K,
        "half_marathon": RaceDistance.HALF_MARATHON,
        "half": RaceDistance.HALF_MARATHON,
        "marathon": RaceDistance.MARATHON,
        "ultra": RaceDistance.ULTRA,
    }
    return distance_map.get(distance_str, RaceDistance.CUSTOM)


def _run_async(coro):
    """Run an async coroutine in a synchronous context."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None:
        # If we're already in an async context, create a new loop in a thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    else:
        return asyncio.run(coro)


# ============================================================================
# Action Tools
# ============================================================================

@tool
def create_training_plan(
    race_distance: str,
    race_date: str,
    target_time: Optional[str] = None,
    priority: str = "A"
) -> dict:
    """Generate a personalized training plan.

    Uses athlete profile and patterns automatically.
    Only requires: distance, date, and optionally target time.

    Args:
        race_distance: Target race distance ("5K", "10K", "half_marathon", "marathon")
        race_date: Race date in ISO format (YYYY-MM-DD)
        target_time: Optional target time (e.g., "3:45:00" for marathon, "25:00" for 5K)
        priority: Race priority ("A" = main goal, "B" = secondary, "C" = tune-up)

    Returns:
        TrainingPlan dict with weeks, workouts, and periodization
    """
    try:
        # Parse inputs
        distance = _parse_race_distance(race_distance)
        target_date = datetime.strptime(race_date, "%Y-%m-%d").date()

        # Calculate target time in seconds
        if target_time:
            target_seconds = parse_time_string(target_time)
        else:
            # Estimate based on distance and typical times
            default_times = {
                RaceDistance.FIVE_K: 25 * 60,           # 25:00
                RaceDistance.TEN_K: 52 * 60,            # 52:00
                RaceDistance.HALF_MARATHON: 115 * 60,   # 1:55:00
                RaceDistance.MARATHON: 4 * 3600,        # 4:00:00
            }
            target_seconds = default_times.get(distance, 60 * 60)

        # Map priority letter to number
        priority_map = {"A": 1, "B": 2, "C": 3}
        priority_num = priority_map.get(priority.upper(), 1)

        # Create goal
        goal = RaceGoal(
            race_date=target_date,
            distance=distance,
            target_time_seconds=target_seconds,
            race_name=f"{race_distance} Race",
            priority=priority_num,
        )

        # Get athlete context
        athlete_context = _get_default_plan_athlete_context()

        # Try to use the plan agent
        try:
            plan_agent = PlanAgent()
            plan = _run_async(plan_agent.generate_plan(
                goal=goal,
                athlete_context=athlete_context,
                constraints=PlanConstraints(),
            ))

            return {
                "success": True,
                "plan": plan.to_dict(),
                "message": f"Created {plan.total_weeks}-week training plan for {race_distance}",
            }

        except Exception as agent_error:
            # Fallback to mock plan
            weeks_until_race = (target_date - date.today()).days // 7
            weeks_until_race = max(4, min(weeks_until_race, 20))

            return {
                "success": True,
                "plan": {
                    "id": f"plan_{uuid.uuid4().hex[:12]}",
                    "name": f"{race_distance} Training Plan",
                    "description": f"Periodized plan targeting {goal.target_time_formatted}",
                    "goal": goal.to_dict(),
                    "total_weeks": weeks_until_race,
                    "periodization": "linear",
                    "peak_week": max(1, weeks_until_race - 3),
                    "phases_summary": {
                        "base": weeks_until_race // 4,
                        "build": weeks_until_race // 2,
                        "peak": max(1, weeks_until_race // 6),
                        "taper": 1,
                    },
                    "created_at": datetime.now().isoformat(),
                },
                "message": f"Created {weeks_until_race}-week training plan for {race_distance}",
                "note": "Plan generated with default structure (agent not available)",
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to create training plan: {str(e)}",
        }


@tool
def design_workout(
    workout_type: str,
    target_duration_min: Optional[int] = None,
    target_distance_km: Optional[float] = None,
    focus: Optional[str] = None
) -> dict:
    """Design a single workout for today/tomorrow.

    Automatically considers:
    - Current readiness and fatigue
    - Recent training load
    - Upcoming race goals

    Args:
        workout_type: Type ("easy", "tempo", "intervals", "long", "threshold", "fartlek")
        target_duration_min: Optional target duration in minutes
        target_distance_km: Optional target distance in km
        focus: Optional focus area ("endurance", "speed", "threshold", "recovery")

    Returns:
        DesignedWorkout dict with intervals, paces, and instructions
    """
    try:
        # Get the workout agent
        agent = get_workout_agent()

        # Get athlete context
        athlete_context = _get_default_athlete_context()

        # Create workout design request
        request = WorkoutDesignRequest(
            workout_type=workout_type.lower(),
            duration_min=target_duration_min or 45,
            focus=focus,
        )

        # Design the workout using the rule-based method (sync)
        workout = agent.design_workout(request, athlete_context)

        # Convert to dict with additional information
        workout_dict = workout.to_dict()

        # Add pace guidance
        pace_map = {
            "easy": athlete_context.format_pace(athlete_context.easy_pace),
            "long": athlete_context.format_pace(athlete_context.long_pace),
            "tempo": athlete_context.format_pace(athlete_context.tempo_pace),
            "threshold": athlete_context.format_pace(athlete_context.threshold_pace),
            "intervals": athlete_context.format_pace(athlete_context.interval_pace),
            "interval": athlete_context.format_pace(athlete_context.interval_pace),
            "fartlek": f"{athlete_context.format_pace(athlete_context.easy_pace)} - {athlete_context.format_pace(athlete_context.interval_pace)}",
        }

        return {
            "success": True,
            "workout": workout_dict,
            "guidance": {
                "suggested_pace": pace_map.get(workout_type.lower(), athlete_context.format_pace(athlete_context.easy_pace)),
                "hr_zones": athlete_context.to_dict()["hr_zones"],
                "current_readiness": athlete_context.readiness_score,
                "current_form": f"CTL: {athlete_context.ctl:.1f}, ATL: {athlete_context.atl:.1f}, TSB: {athlete_context.tsb:.1f}",
            },
            "message": f"Designed {workout.name} ({workout.estimated_duration_min} min)",
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to design workout: {str(e)}",
        }


@tool
def log_note(
    content: str,
    date: Optional[str] = None,
    workout_id: Optional[str] = None
) -> dict:
    """Log a training note or reflection.

    Notes can be attached to a specific workout or stand alone.
    Great for tracking how you felt, external factors, or insights.

    Args:
        content: Note content (the actual text of the note)
        date: Optional date in YYYY-MM-DD format (defaults to today)
        workout_id: Optional workout ID to attach note to

    Returns:
        Note dict with id, content, created_at
    """
    try:
        # Parse date
        if date:
            note_date = datetime.strptime(date, "%Y-%m-%d").date()
        else:
            note_date = datetime.now().date()

        # Generate note ID
        note_id = f"note_{uuid.uuid4().hex[:12]}"

        # Create note object
        note = {
            "id": note_id,
            "content": content,
            "date": note_date.isoformat(),
            "workout_id": workout_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        # TODO: In a full implementation, save to database
        # from ..db.repositories import get_note_repository
        # note_repo = get_note_repository()
        # note_repo.save(note)

        return {
            "success": True,
            "note": note,
            "message": f"Logged note for {note_date.isoformat()}" +
                      (f" (attached to workout {workout_id})" if workout_id else ""),
            "note_info": "Note saved (database integration pending)",
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to log note: {str(e)}",
        }


@tool
def set_goal(
    race_distance: str,
    race_date: str,
    target_time: Optional[str] = None,
    race_name: Optional[str] = None,
    priority: str = "A"
) -> dict:
    """Create or update a race goal.

    Setting clear goals helps the AI coach provide better recommendations
    and design appropriate training plans.

    Args:
        race_distance: Race distance ("5K", "10K", "half_marathon", "marathon")
        race_date: Race date in YYYY-MM-DD format
        target_time: Optional target time (e.g., "3:45:00" for marathon)
        race_name: Optional race name (e.g., "Berlin Marathon 2025")
        priority: Priority level ("A" = main goal, "B" = secondary, "C" = tune-up race)

    Returns:
        Goal dict with id, distance, date, target
    """
    try:
        # Parse inputs
        distance = _parse_race_distance(race_distance)
        target_date = datetime.strptime(race_date, "%Y-%m-%d").date()

        # Validate date is in the future
        if target_date <= date.today():
            return {
                "success": False,
                "error": "Race date must be in the future",
                "message": "Cannot set a goal for a past date",
            }

        # Calculate target time in seconds
        if target_time:
            target_seconds = parse_time_string(target_time)
        else:
            # Estimate based on distance and typical times for a recreational runner
            default_times = {
                RaceDistance.FIVE_K: 25 * 60,           # 25:00
                RaceDistance.TEN_K: 52 * 60,            # 52:00
                RaceDistance.HALF_MARATHON: 115 * 60,   # 1:55:00
                RaceDistance.MARATHON: 4 * 3600,        # 4:00:00
                RaceDistance.ULTRA: 10 * 3600,          # 10:00:00
            }
            target_seconds = default_times.get(distance, 60 * 60)

        # Map priority letter to number
        priority_map = {"A": 1, "B": 2, "C": 3}
        priority_num = priority_map.get(priority.upper(), 1)

        # Create goal object
        goal = RaceGoal(
            race_date=target_date,
            distance=distance,
            target_time_seconds=target_seconds,
            race_name=race_name or f"{race_distance} Race",
            priority=priority_num,
        )

        # Generate goal ID
        goal_id = f"goal_{uuid.uuid4().hex[:12]}"

        # Calculate weeks until race
        weeks_until = goal.weeks_until_race()

        # Create response
        goal_dict = {
            "id": goal_id,
            "race_name": goal.race_name,
            "distance": goal.distance.value,
            "distance_km": goal.distance_km,
            "race_date": goal.race_date.isoformat(),
            "target_time_seconds": goal.target_time_seconds,
            "target_time_formatted": goal.target_time_formatted,
            "target_pace_formatted": goal.target_pace_formatted,
            "priority": priority,
            "weeks_until_race": weeks_until,
            "created_at": datetime.now().isoformat(),
        }

        # TODO: In a full implementation, save to database
        # from ..db.repositories import get_goal_repository
        # goal_repo = get_goal_repository()
        # goal_repo.save(goal_dict)

        # Provide training recommendation based on time available
        if weeks_until < 4:
            recommendation = "Limited time - focus on maintaining fitness and race-specific workouts"
        elif weeks_until < 8:
            recommendation = "Short preparation - prioritize threshold work and race-pace sessions"
        elif weeks_until < 12:
            recommendation = "Good preparation window - include build phase with quality sessions"
        else:
            recommendation = "Excellent preparation time - full periodization with base, build, peak phases"

        return {
            "success": True,
            "goal": goal_dict,
            "message": f"Set goal: {goal.race_name} ({goal.distance.value}) on {goal.race_date.isoformat()} targeting {goal.target_time_formatted}",
            "weeks_until_race": weeks_until,
            "training_recommendation": recommendation,
            "note": "Goal saved (database integration pending)",
        }

    except ValueError as ve:
        return {
            "success": False,
            "error": str(ve),
            "message": f"Invalid input: {str(ve)}",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to set goal: {str(e)}",
        }


# ============================================================================
# Tool Registry
# ============================================================================

# List of all action tools for easy import
ACTION_TOOLS = [
    create_training_plan,
    design_workout,
    log_note,
    set_goal,
]


def get_action_tools() -> List:
    """Get all action tools for the AI agent."""
    return ACTION_TOOLS


__all__ = [
    # Tools
    "create_training_plan",
    "design_workout",
    "log_note",
    "set_goal",
    # Tool list
    "ACTION_TOOLS",
    "get_action_tools",
]
