"""Build athlete context for LLM prompt injection."""

from typing import Optional, List, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..metrics.power import PowerZones, CyclingAthleteContext
    from ..models.workouts import SwimZones, SwimAthleteContext


def _format_time(seconds: int) -> str:
    """Format seconds to HH:MM:SS or MM:SS format."""
    if not seconds:
        return "N/A"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def _classify_activity_level(steps: Optional[int]) -> str:
    """Classify activity level based on step count."""
    if steps is None:
        return "UNKNOWN"
    if steps < 5000:
        return "LOW - rest day"
    elif steps <= 12000:
        return "NORMAL"
    else:
        return "HIGH - very active"


def _format_swim_pace(pace_sec: int) -> str:
    """Format swim pace in seconds to mm:ss/100m format."""
    if not pace_sec:
        return "N/A"
    minutes = pace_sec // 60
    seconds = pace_sec % 60
    return f"{minutes}:{seconds:02d}/100m"


def build_athlete_context_prompt(
    fitness_metrics: Optional[Dict[str, Any]] = None,
    profile: Optional[Any] = None,
    goals: Optional[List[Dict[str, Any]]] = None,
    readiness: Optional[Dict[str, Any]] = None,
    recent_activities: Optional[List[Dict[str, Any]]] = None,
    vo2max: Optional[Dict[str, Any]] = None,
    race_predictions: Optional[Dict[str, Any]] = None,
    training_status: Optional[str] = None,
    daily_activity: Optional[Dict[str, Any]] = None,
    prev_day_activity: Optional[Dict[str, Any]] = None,
    cycling_context: Optional["CyclingAthleteContext"] = None,
    power_zones: Optional["PowerZones"] = None,
    swim_context: Optional["SwimAthleteContext"] = None,
    swim_zones: Optional["SwimZones"] = None,
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
        vo2max: VO2max values (running and/or cycling)
        race_predictions: Garmin race predictions (5K, 10K, HM, Marathon in seconds)
        training_status: Current training status (productive, unproductive, etc.)
        daily_activity: Daily activity averages (steps, active_minutes)
        prev_day_activity: Previous day activity data (steps, active_minutes, date)
        cycling_context: CyclingAthleteContext with FTP, power zones, and cycling metrics
        power_zones: PowerZones dataclass with 7-zone Coggan model
        swim_context: SwimAthleteContext with CSS, swim zones, and swim metrics
        swim_zones: SwimZones dataclass with 5-zone CSS-based model

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

    # Fitness level section (VO2max and training status)
    if vo2max or training_status:
        parts.append("FITNESS LEVEL:")
        if vo2max:
            if vo2max.get("running"):
                parts.append(f"  VO2max (Running): {vo2max.get('running'):.1f} ml/kg/min")
            if vo2max.get("cycling"):
                parts.append(f"  VO2max (Cycling): {vo2max.get('cycling'):.1f} ml/kg/min")
        if training_status:
            parts.append(f"  Training Status: {training_status}")
        parts.append("")

    # Race predictions section
    if race_predictions:
        parts.append("RACE PREDICTIONS (Garmin):")
        predictions = []
        if race_predictions.get("5k"):
            predictions.append(f"5K: {_format_time(race_predictions.get('5k'))}")
        if race_predictions.get("10k"):
            predictions.append(f"10K: {_format_time(race_predictions.get('10k'))}")
        if race_predictions.get("half_marathon"):
            predictions.append(f"HM: {_format_time(race_predictions.get('half_marathon'))}")
        if race_predictions.get("marathon"):
            predictions.append(f"Marathon: {_format_time(race_predictions.get('marathon'))}")
        if predictions:
            parts.append(f"  {' | '.join(predictions)}")
        parts.append("")

    # Daily activity section
    if prev_day_activity or daily_activity:
        parts.append("DAILY ACTIVITY:")

        # Previous day activity (most important for workout context)
        if prev_day_activity:
            prev_steps = prev_day_activity.get("steps")
            prev_active = prev_day_activity.get("active_minutes")
            prev_date = prev_day_activity.get("date", "")

            if prev_steps is not None:
                activity_level = _classify_activity_level(prev_steps)
                date_label = f"({prev_date})" if prev_date else ""
                active_str = f", {prev_active} active min" if prev_active else ""
                parts.append(f"  Previous day {date_label}: {prev_steps:,} steps{active_str} ({activity_level})")

        # 7-day average
        if daily_activity:
            avg_parts = []
            if daily_activity.get("steps"):
                avg_parts.append(f"{daily_activity.get('steps'):,} steps/day")
            if daily_activity.get("active_minutes"):
                avg_parts.append(f"{daily_activity.get('active_minutes')} active min/day")
            if avg_parts:
                parts.append(f"  7-day average: {', '.join(avg_parts)}")

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

    # Cycling-specific context (when FTP/power zones are available)
    if cycling_context is not None:
        parts.append("CYCLING METRICS:")
        parts.append(f"  FTP: {cycling_context.ftp}W")
        if cycling_context.power_to_weight:
            parts.append(f"  Power-to-Weight: {cycling_context.power_to_weight} W/kg")
        if cycling_context.power_zones:
            parts.append(f"  Cycling CTL: {cycling_context.cycling_ctl:.1f}")
            parts.append(f"  Cycling ATL: {cycling_context.cycling_atl:.1f}")
            parts.append(f"  Cycling TSB: {cycling_context.cycling_tsb:.1f}")
        if cycling_context.typical_efficiency_factor:
            parts.append(f"  Efficiency Factor: {cycling_context.typical_efficiency_factor:.2f}")
        parts.append("")
        parts.append("POWER ZONES (Coggan):")
        if cycling_context.power_zones:
            zone_names = ["Active Recovery", "Endurance", "Tempo", "Threshold", "VO2max", "Anaerobic", "Neuromuscular"]
            for i in range(1, 8):
                min_w, max_w = cycling_context.power_zones.get_zone(i)
                parts.append(f"  Z{i} ({zone_names[i-1]}): {min_w}-{max_w}W")
        parts.append("")

    elif power_zones is not None:
        # If only power_zones provided (without full cycling context)
        parts.append("POWER ZONES (Coggan):")
        parts.append(f"  FTP: {power_zones.ftp}W")
        zone_names = ["Active Recovery", "Endurance", "Tempo", "Threshold", "VO2max", "Anaerobic", "Neuromuscular"]
        for i in range(1, 8):
            min_w, max_w = power_zones.get_zone(i)
            parts.append(f"  Z{i} ({zone_names[i-1]}): {min_w}-{max_w}W")
        parts.append("")

    # Swimming-specific context (when CSS/swim zones are available)
    if swim_context is not None:
        parts.append("SWIM METRICS:")
        parts.append(f"  CSS (Critical Swim Speed): {_format_swim_pace(swim_context.css_pace)}")
        if swim_context.preferred_pool_length:
            parts.append(f"  Preferred Pool: {swim_context.preferred_pool_length}m")
        if swim_context.preferred_stroke:
            stroke = swim_context.preferred_stroke
            if hasattr(stroke, 'value'):
                stroke = stroke.value
            parts.append(f"  Preferred Stroke: {stroke.title()}")
        parts.append(f"  Swim CTL: {swim_context.swim_ctl:.1f}")
        parts.append(f"  Swim ATL: {swim_context.swim_atl:.1f}")

        # SWOLF by stroke if available
        swolf_data = []
        if swim_context.freestyle_swolf:
            swolf_data.append(f"Free: {swim_context.freestyle_swolf}")
        if swim_context.backstroke_swolf:
            swolf_data.append(f"Back: {swim_context.backstroke_swolf}")
        if swim_context.breaststroke_swolf:
            swolf_data.append(f"Breast: {swim_context.breaststroke_swolf}")
        if swim_context.butterfly_swolf:
            swolf_data.append(f"Fly: {swim_context.butterfly_swolf}")
        if swolf_data:
            parts.append(f"  SWOLF by Stroke: {', '.join(swolf_data)}")
        parts.append("")

        # Swim zones from context
        parts.append("SWIM ZONES (CSS-based):")
        zone_paces = swim_context.get_swim_zones()
        zone_names = [
            ("Zone 1 (Recovery)", "zone1_recovery"),
            ("Zone 2 (Aerobic)", "zone2_aerobic"),
            ("Zone 3 (Threshold)", "zone3_threshold"),
            ("Zone 4 (VO2max)", "zone4_vo2max"),
            ("Zone 5 (Sprint)", "zone5_sprint"),
        ]
        for name, key in zone_names:
            if key in zone_paces:
                fast, slow = zone_paces[key]
                parts.append(f"  {name}: {_format_swim_pace(fast)} - {_format_swim_pace(slow)}")
        parts.append("")

    elif swim_zones is not None:
        # If only swim_zones provided (without full swim context)
        parts.append("SWIM ZONES (CSS-based):")
        parts.append(f"  CSS: {_format_swim_pace(swim_zones.css_pace)}")
        parts.append(f"  Zone 1 (Recovery): {_format_swim_pace(swim_zones.zone1_recovery[0])} - {_format_swim_pace(swim_zones.zone1_recovery[1])}")
        parts.append(f"  Zone 2 (Aerobic): {_format_swim_pace(swim_zones.zone2_aerobic[0])} - {_format_swim_pace(swim_zones.zone2_aerobic[1])}")
        parts.append(f"  Zone 3 (Threshold): {_format_swim_pace(swim_zones.zone3_threshold[0])} - {_format_swim_pace(swim_zones.zone3_threshold[1])}")
        parts.append(f"  Zone 4 (VO2max): {_format_swim_pace(swim_zones.zone4_vo2max[0])} - {_format_swim_pace(swim_zones.zone4_vo2max[1])}")
        parts.append(f"  Zone 5 (Sprint): {_format_swim_pace(swim_zones.zone5_sprint[0])} - {_format_swim_pace(swim_zones.zone5_sprint[1])}")
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

    # Power metrics (cycling/running with power)
    if workout.get('avg_power'):
        parts.append(f"Avg Power: {workout.get('avg_power')}W")
    if workout.get('max_power'):
        parts.append(f"Max Power: {workout.get('max_power')}W")
    if workout.get('normalized_power'):
        parts.append(f"Normalized Power: {workout.get('normalized_power')}W")
    if workout.get('tss') or workout.get('power_tss'):
        tss = workout.get('tss') or workout.get('power_tss')
        parts.append(f"TSS: {tss:.1f}")
    if workout.get('intensity_factor'):
        parts.append(f"Intensity Factor: {workout.get('intensity_factor'):.2f}")
    if workout.get('variability_index'):
        parts.append(f"Variability Index: {workout.get('variability_index'):.2f}")
    if workout.get('cycling_cadence'):
        parts.append(f"Avg Cadence: {workout.get('cycling_cadence')} rpm")

    # Zone distribution if available
    zones = []
    for i in range(1, 6):
        zone_key = f"zone{i}_pct"
        if workout.get(zone_key):
            zones.append(f"Z{i}: {workout.get(zone_key):.0f}%")
    if zones:
        parts.append(f"HR Zones: {', '.join(zones)}")

    return "\n".join(parts)
