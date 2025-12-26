"""Build athlete context for LLM prompt injection."""

from typing import Optional, List, Dict, Any


def build_athlete_context_prompt(
    fitness_metrics: Optional[Dict[str, Any]] = None,
    profile: Optional[Any] = None,
    goals: Optional[List[Dict[str, Any]]] = None,
    readiness: Optional[Dict[str, Any]] = None,
    recent_activities: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    Build a formatted athlete context string for LLM prompt injection.

    This context is prepended to every LLM call to provide personalized,
    contextually-aware responses.

    Args:
        fitness_metrics: CTL, ATL, TSB, ACWR, risk zone
        profile: User profile with HR settings
        goals: List of race goals
        readiness: Current readiness score and factors
        recent_activities: Recent workout history

    Returns:
        Formatted context string
    """
    parts = []

    # Fitness metrics section
    if fitness_metrics:
        parts.append("FITNESS METRICS:")
        parts.append(f"  CTL (Chronic Training Load): {fitness_metrics.get('ctl', 0):.1f}")
        parts.append(f"  ATL (Acute Training Load): {fitness_metrics.get('atl', 0):.1f}")
        parts.append(f"  TSB (Training Stress Balance): {fitness_metrics.get('tsb', 0):.1f}")
        parts.append(f"  ACWR (Acute:Chronic Ratio): {fitness_metrics.get('acwr', 1.0):.2f}")
        parts.append(f"  Risk Zone: {fitness_metrics.get('risk_zone', 'unknown')}")
        parts.append("")

    # Physiology section
    if profile:
        parts.append("PHYSIOLOGY:")
        parts.append(f"  Max HR: {getattr(profile, 'max_hr', 185)} bpm")
        parts.append(f"  Resting HR: {getattr(profile, 'rest_hr', 55)} bpm")
        parts.append(f"  Lactate Threshold HR: {getattr(profile, 'threshold_hr', 165)} bpm")
        if hasattr(profile, 'age') and profile.age:
            parts.append(f"  Age: {profile.age}")
        if hasattr(profile, 'gender') and profile.gender:
            parts.append(f"  Gender: {profile.gender}")
        parts.append("")

        # HR Zones (Karvonen method)
        max_hr = getattr(profile, 'max_hr', 185)
        rest_hr = getattr(profile, 'rest_hr', 55)
        hr_reserve = max_hr - rest_hr

        parts.append("HR ZONES:")
        zone_defs = [
            ("Zone 1 (Recovery)", 0.50, 0.60),
            ("Zone 2 (Aerobic)", 0.60, 0.70),
            ("Zone 3 (Tempo)", 0.70, 0.80),
            ("Zone 4 (Threshold)", 0.80, 0.90),
            ("Zone 5 (VO2max)", 0.90, 1.00),
        ]
        for name, low, high in zone_defs:
            low_hr = int(rest_hr + hr_reserve * low)
            high_hr = int(rest_hr + hr_reserve * high)
            parts.append(f"  {name}: {low_hr}-{high_hr} bpm")
        parts.append("")

    # Goals section
    if goals:
        parts.append("RACE GOALS:")
        for goal in goals[:3]:  # Max 3 goals
            distance = goal.get("distance", "Unknown")
            target_time = goal.get("target_time_formatted", goal.get("target_time_sec", "Unknown"))
            race_date = goal.get("race_date", "Unknown")
            weeks = goal.get("weeks_until_race", "?")
            parts.append(f"  - {distance}: {target_time} on {race_date} ({weeks} weeks away)")
        parts.append("")

        # Training paces from first goal
        if goals:
            first_goal = goals[0]
            target_pace = first_goal.get("target_pace_formatted")
            if target_pace:
                parts.append("TRAINING PACES (based on goal):")
                # Estimate paces from race pace
                import re
                match = re.match(r"(\d+):(\d+)", str(target_pace))
                if match:
                    race_pace_sec = int(match.group(1)) * 60 + int(match.group(2))

                    pace_multipliers = [
                        ("Easy", 1.25),
                        ("Long Run", 1.20),
                        ("Tempo", 1.02),
                        ("Threshold", 0.98),
                        ("Interval", 0.92),
                    ]

                    for pace_name, mult in pace_multipliers:
                        pace_sec = int(race_pace_sec * mult)
                        pace_min = pace_sec // 60
                        pace_s = pace_sec % 60
                        parts.append(f"  {pace_name}: {pace_min}:{pace_s:02d}/km")
                    parts.append("")

    # Readiness section
    if readiness:
        parts.append("CURRENT READINESS:")
        parts.append(f"  Score: {readiness.get('score', 50)}/100")
        parts.append(f"  Zone: {readiness.get('zone', 'yellow').upper()}")
        if readiness.get('recommendation'):
            parts.append(f"  Recommendation: {readiness.get('recommendation')}")
        parts.append("")

    # Recent activity summary
    if recent_activities:
        parts.append("RECENT TRAINING (last 7 days):")
        total_distance = sum(a.get('distance_km', 0) or 0 for a in recent_activities)
        total_duration = sum(a.get('duration_min', 0) or 0 for a in recent_activities)
        workout_count = len(recent_activities)

        parts.append(f"  Workouts: {workout_count}")
        parts.append(f"  Total distance: {total_distance:.1f} km")
        parts.append(f"  Total duration: {total_duration:.0f} min")

        # Last 3 workouts summary
        if recent_activities[:3]:
            parts.append("  Recent workouts:")
            for activity in recent_activities[:3]:
                a_type = activity.get('activity_type', 'run')
                a_dist = activity.get('distance_km', 0) or 0
                a_dur = activity.get('duration_min', 0) or 0
                a_date = activity.get('date', 'unknown')
                parts.append(f"    - {a_date}: {a_type} {a_dist:.1f}km in {a_dur:.0f}min")
        parts.append("")

    return "\n".join(parts)


def format_workout_for_prompt(workout: Dict[str, Any]) -> str:
    """
    Format a workout dictionary for inclusion in a prompt.

    Args:
        workout: Workout data dictionary

    Returns:
        Formatted string for prompt
    """
    parts = []

    parts.append(f"Activity: {workout.get('activity_type', 'Unknown')}")
    parts.append(f"Date: {workout.get('date', 'Unknown')}")
    parts.append(f"Duration: {workout.get('duration_min', 0):.0f} minutes")
    parts.append(f"Distance: {workout.get('distance_km', 0):.2f} km")

    if workout.get('avg_hr'):
        parts.append(f"Avg HR: {workout.get('avg_hr')} bpm")
    if workout.get('max_hr'):
        parts.append(f"Max HR: {workout.get('max_hr')} bpm")
    if workout.get('pace_sec_per_km'):
        pace = workout.get('pace_sec_per_km')
        pace_min = int(pace // 60)
        pace_sec = int(pace % 60)
        parts.append(f"Avg Pace: {pace_min}:{pace_sec:02d}/km")

    if workout.get('hrss'):
        parts.append(f"Training Load (HRSS): {workout.get('hrss'):.1f}")
    if workout.get('trimp'):
        parts.append(f"TRIMP: {workout.get('trimp'):.1f}")

    # Zone distribution if available
    zones = []
    for i in range(1, 6):
        zone_key = f"zone{i}_pct"
        if workout.get(zone_key):
            zones.append(f"Z{i}: {workout.get(zone_key):.0f}%")
    if zones:
        parts.append(f"HR Zones: {', '.join(zones)}")

    return "\n".join(parts)
