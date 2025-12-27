"""
Race Goal and Performance Prediction

Set goals and track progress toward them.
Includes VO2max-based training pace calculations and goal feasibility assessment.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import List, Optional, Dict, Any
import math


class RaceDistance(Enum):
    """Common race distances with values in kilometers."""

    FIVE_K = 5.0
    TEN_K = 10.0
    HALF_MARATHON = 21.0975
    MARATHON = 42.195

    @classmethod
    def from_string(cls, s: str) -> Optional["RaceDistance"]:
        """Parse race distance from string."""
        mapping = {
            "5k": cls.FIVE_K,
            "5km": cls.FIVE_K,
            "10k": cls.TEN_K,
            "10km": cls.TEN_K,
            "half": cls.HALF_MARATHON,
            "half_marathon": cls.HALF_MARATHON,
            "halfmarathon": cls.HALF_MARATHON,
            "21k": cls.HALF_MARATHON,
            "marathon": cls.MARATHON,
            "full": cls.MARATHON,
            "42k": cls.MARATHON,
        }
        return mapping.get(s.lower().replace("-", "_").replace(" ", "_"))

    @property
    def display_name(self) -> str:
        """Get human-readable name."""
        names = {
            RaceDistance.FIVE_K: "5K",
            RaceDistance.TEN_K: "10K",
            RaceDistance.HALF_MARATHON: "Half Marathon",
            RaceDistance.MARATHON: "Marathon",
        }
        return names.get(self, str(self.value) + "K")


@dataclass
class RaceGoal:
    """Race goal with target time."""

    race_date: date
    distance: RaceDistance
    target_time_sec: int
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    @property
    def target_pace(self) -> float:
        """Target pace in sec/km."""
        return self.target_time_sec / self.distance.value

    @property
    def target_pace_formatted(self) -> str:
        """Target pace as min:sec/km string."""
        pace_sec = self.target_pace
        minutes = int(pace_sec // 60)
        seconds = int(pace_sec % 60)
        return f"{minutes}:{seconds:02d}/km"

    @property
    def target_time_formatted(self) -> str:
        """Target time as H:MM:SS string."""
        total_sec = self.target_time_sec
        hours = int(total_sec // 3600)
        minutes = int((total_sec % 3600) // 60)
        seconds = int(total_sec % 60)

        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"

    @property
    def weeks_until_race(self) -> int:
        """Weeks remaining until race date."""
        days = (self.race_date - date.today()).days
        return max(0, days // 7)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "race_date": self.race_date.isoformat(),
            "distance": self.distance.value,
            "distance_name": self.distance.display_name,
            "target_time_sec": self.target_time_sec,
            "target_time_formatted": self.target_time_formatted,
            "target_pace": round(self.target_pace, 1),
            "target_pace_formatted": self.target_pace_formatted,
            "notes": self.notes,
            "weeks_until_race": self.weeks_until_race,
        }


@dataclass
class GoalProgress:
    """Progress toward a race goal."""

    goal: RaceGoal
    current_predicted_time: int
    gap_to_goal_sec: int
    weeks_remaining: int
    ctl_current: float
    ctl_needed_estimate: float
    on_track: bool
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "goal": self.goal.to_dict(),
            "current_predicted_time": self.current_predicted_time,
            "current_predicted_time_formatted": format_time(self.current_predicted_time),
            "gap_to_goal_sec": self.gap_to_goal_sec,
            "gap_to_goal_formatted": format_time(abs(self.gap_to_goal_sec)),
            "weeks_remaining": self.weeks_remaining,
            "ctl_current": round(self.ctl_current, 1),
            "ctl_needed_estimate": round(self.ctl_needed_estimate, 1),
            "on_track": self.on_track,
            "recommendations": self.recommendations,
        }


def format_time(seconds: int) -> str:
    """Format seconds as H:MM:SS or MM:SS string."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"


def parse_time(time_str: str) -> int:
    """Parse time string (H:MM:SS or MM:SS) to seconds."""
    parts = time_str.strip().split(":")

    if len(parts) == 3:
        hours, minutes, seconds = int(parts[0]), int(parts[1]), int(parts[2])
        return hours * 3600 + minutes * 60 + seconds
    elif len(parts) == 2:
        minutes, seconds = int(parts[0]), int(parts[1])
        return minutes * 60 + seconds
    else:
        raise ValueError(f"Invalid time format: {time_str}")


def predict_race_time(
    recent_race_time_sec: int,
    recent_race_distance: RaceDistance,
    target_distance: RaceDistance,
    riegel_exponent: float = 1.06
) -> int:
    """
    Predict race time using Riegel formula.

    The Riegel formula: T2 = T1 * (D2/D1)^exponent

    Where:
    - T1 = recent race time
    - D1 = recent race distance
    - T2 = predicted time
    - D2 = target distance
    - exponent = fatigue factor (typically 1.06, range 1.05-1.08)

    Args:
        recent_race_time_sec: Time in seconds for recent race
        recent_race_distance: Distance of recent race
        target_distance: Distance to predict
        riegel_exponent: Fatigue factor (default 1.06)

    Returns:
        Predicted time in seconds
    """
    distance_ratio = target_distance.value / recent_race_distance.value
    predicted_time = recent_race_time_sec * (distance_ratio ** riegel_exponent)
    return int(predicted_time)


def calculate_vdot(
    race_time_sec: int,
    race_distance: RaceDistance
) -> float:
    """
    Estimate VDOT (VO2max equivalent) from race performance.

    This is a simplified approximation of Jack Daniels' VDOT.

    Args:
        race_time_sec: Race time in seconds
        race_distance: Race distance

    Returns:
        Estimated VDOT value
    """
    # Pace in min/km
    pace_min_per_km = (race_time_sec / 60) / race_distance.value

    # Simplified VDOT estimation based on pace
    # This is an approximation - actual VDOT tables are more complex
    # Formula derived from VDOT tables for running

    if race_distance == RaceDistance.MARATHON:
        # Marathon-specific adjustment
        vdot = 50 - (pace_min_per_km - 4.5) * 8
    elif race_distance == RaceDistance.HALF_MARATHON:
        vdot = 52 - (pace_min_per_km - 4.2) * 9
    elif race_distance == RaceDistance.TEN_K:
        vdot = 54 - (pace_min_per_km - 4.0) * 10
    else:  # 5K
        vdot = 56 - (pace_min_per_km - 3.8) * 11

    return max(20, min(85, vdot))  # Clamp to reasonable range


def calculate_training_paces(goal: RaceGoal) -> Dict[str, Dict[str, Any]]:
    """
    Calculate training paces based on goal.

    Returns paces for different training types based on the goal race pace.

    Args:
        goal: RaceGoal with target time and distance

    Returns:
        Dictionary with easy, tempo, threshold, interval, and repetition paces
    """
    goal_pace = goal.target_pace  # sec/km

    # Estimate VDOT from goal
    vdot = calculate_vdot(goal.target_time_sec, goal.distance)

    # Training pace multipliers relative to race pace
    # These are based on Jack Daniels' training principles
    paces = {
        "easy": {
            "name": "Easy",
            "description": "Conversational pace for recovery and base building",
            "pace_sec": goal_pace * 1.25,  # 25% slower than race pace
            "hr_zone": "Zone 1-2",
            "purpose": "Aerobic base, active recovery",
        },
        "long": {
            "name": "Long Run",
            "description": "Extended easy pace for endurance",
            "pace_sec": goal_pace * 1.20,  # 20% slower than race pace
            "hr_zone": "Zone 2",
            "purpose": "Build endurance and fat metabolism",
        },
        "marathon": {
            "name": "Marathon Pace",
            "description": "Sustainable race pace",
            "pace_sec": goal_pace * 1.08,  # Slightly slower than goal 5K/10K
            "hr_zone": "Zone 3",
            "purpose": "Race-specific fitness",
        },
        "tempo": {
            "name": "Tempo",
            "description": "Comfortably hard, lactate threshold",
            "pace_sec": goal_pace * 1.02,  # Near race pace
            "hr_zone": "Zone 3-4",
            "purpose": "Improve lactate clearance",
        },
        "threshold": {
            "name": "Threshold",
            "description": "Hard but sustainable for 20-30 min",
            "pace_sec": goal_pace * 0.98,  # Slightly faster than race pace
            "hr_zone": "Zone 4",
            "purpose": "Raise lactate threshold",
        },
        "interval": {
            "name": "Interval",
            "description": "Hard efforts with recovery",
            "pace_sec": goal_pace * 0.92,  # 8% faster than race pace
            "hr_zone": "Zone 4-5",
            "purpose": "Improve VO2max",
        },
        "repetition": {
            "name": "Repetition",
            "description": "Short, fast repetitions",
            "pace_sec": goal_pace * 0.85,  # 15% faster than race pace
            "hr_zone": "Zone 5",
            "purpose": "Improve speed and running economy",
        },
    }

    # Add formatted paces
    for key in paces:
        pace_sec = paces[key]["pace_sec"]
        minutes = int(pace_sec // 60)
        seconds = int(pace_sec % 60)
        paces[key]["pace_formatted"] = f"{minutes}:{seconds:02d}/km"

        # Also add per-mile pace for reference
        pace_mile = pace_sec * 1.60934
        min_mile = int(pace_mile // 60)
        sec_mile = int(pace_mile % 60)
        paces[key]["pace_mile_formatted"] = f"{min_mile}:{sec_mile:02d}/mi"

    return paces


def estimate_ctl_for_goal(
    goal: RaceGoal,
    current_best_time: Optional[int] = None,
    current_ctl: float = 0
) -> float:
    """
    Estimate the CTL needed to achieve a goal.

    This is a rough approximation based on the relationship between
    fitness level and race performance.

    Args:
        goal: Race goal
        current_best_time: Current best time for this distance (seconds)
        current_ctl: Current CTL

    Returns:
        Estimated CTL needed
    """
    # Rough approximation: every 5 points of CTL = ~1-2% improvement
    # This varies significantly based on individual factors

    if current_best_time and current_ctl > 0:
        # Calculate improvement needed
        improvement_needed = (current_best_time - goal.target_time_sec) / current_best_time
        improvement_pct = improvement_needed * 100

        # Estimate CTL gain needed (rough: 2% improvement per 5 CTL)
        ctl_per_pct = 5 / 2  # 5 CTL per 2% improvement
        ctl_needed = current_ctl + (improvement_pct * ctl_per_pct)
        return max(current_ctl, ctl_needed)

    # Default estimation based on goal pace and distance
    # Higher VDOT requires higher CTL
    vdot = calculate_vdot(goal.target_time_sec, goal.distance)

    # Rough mapping: VDOT 40 = CTL 30, VDOT 60 = CTL 70
    ctl_estimate = 30 + (vdot - 40) * 2

    return max(20, ctl_estimate)


def assess_goal_progress(
    goal: RaceGoal,
    current_fitness: dict,
    recent_activities: List[dict]
) -> GoalProgress:
    """
    Assess progress toward a race goal.

    Args:
        goal: The race goal
        current_fitness: Dictionary with ctl, atl, tsb, acwr
        recent_activities: List of recent activity dictionaries

    Returns:
        GoalProgress with assessment and recommendations
    """
    weeks_remaining = goal.weeks_until_race
    current_ctl = current_fitness.get("ctl", 0) or 0

    # Find best recent effort for this or similar distance
    best_recent_time = None
    for activity in recent_activities:
        distance = activity.get("distance_km", 0) or 0
        duration_sec = (activity.get("duration_min", 0) or 0) * 60

        # Look for activities close to goal distance
        if distance >= goal.distance.value * 0.8 and distance <= goal.distance.value * 1.2:
            if best_recent_time is None or duration_sec < best_recent_time:
                best_recent_time = int(duration_sec)

    # If no direct match, try to predict from other distances
    if best_recent_time is None:
        for activity in recent_activities:
            distance = activity.get("distance_km", 0) or 0
            duration_sec = (activity.get("duration_min", 0) or 0) * 60

            # Find a qualifying race/hard effort
            hrss = activity.get("hrss", 0) or 0
            if distance >= 3.0 and hrss >= 50:  # At least 3km and moderate effort
                # Find matching RaceDistance
                if distance >= 4 and distance <= 6:
                    ref_distance = RaceDistance.FIVE_K
                elif distance >= 9 and distance <= 11:
                    ref_distance = RaceDistance.TEN_K
                elif distance >= 20 and distance <= 22:
                    ref_distance = RaceDistance.HALF_MARATHON
                elif distance >= 40:
                    ref_distance = RaceDistance.MARATHON
                else:
                    continue

                # Predict from this result
                predicted = predict_race_time(int(duration_sec), ref_distance, goal.distance)
                if best_recent_time is None or predicted < best_recent_time:
                    best_recent_time = predicted

    # Default prediction if no data
    if best_recent_time is None:
        # Use CTL-based rough estimate
        # Higher CTL = faster times
        base_pace = 360 - (current_ctl * 1.5)  # sec/km, rough estimate
        best_recent_time = int(base_pace * goal.distance.value)

    # Calculate gap
    gap_to_goal = best_recent_time - goal.target_time_sec

    # Estimate CTL needed
    ctl_needed = estimate_ctl_for_goal(goal, best_recent_time, current_ctl)

    # Determine if on track
    ctl_gap = ctl_needed - current_ctl
    ctl_gain_per_week = 2.5  # Reasonable expectation for consistent training
    weeks_to_build = ctl_gap / ctl_gain_per_week if ctl_gap > 0 else 0

    on_track = weeks_to_build <= weeks_remaining * 0.8  # 80% buffer

    # Generate recommendations
    recommendations = []

    if gap_to_goal > 0:
        gap_formatted = format_time(gap_to_goal)
        recommendations.append(
            f"You need to improve by {gap_formatted} to hit your goal."
        )
    else:
        ahead_formatted = format_time(abs(gap_to_goal))
        recommendations.append(
            f"You're currently {ahead_formatted} ahead of your goal pace!"
        )

    if ctl_gap > 10:
        recommendations.append(
            f"Build CTL from {current_ctl:.0f} to ~{ctl_needed:.0f} "
            f"({ctl_gap:.0f} points) through consistent training."
        )
    elif ctl_gap > 0:
        recommendations.append(
            "Your fitness is close to where it needs to be. "
            "Focus on race-specific workouts."
        )

    if weeks_remaining > 12:
        recommendations.append(
            "You have time for a full training block. "
            "Build base first, then add intensity."
        )
    elif weeks_remaining > 6:
        recommendations.append(
            "Focus on race-specific work: tempo runs and goal-pace sessions."
        )
    elif weeks_remaining > 2:
        recommendations.append(
            "Begin taper. Reduce volume but maintain some intensity."
        )
    else:
        recommendations.append(
            "Race week approaching! Rest well and stay fresh."
        )

    # Training pace recommendation
    paces = calculate_training_paces(goal)
    recommendations.append(
        f"Key paces: Easy {paces['easy']['pace_formatted']}, "
        f"Tempo {paces['tempo']['pace_formatted']}, "
        f"Interval {paces['interval']['pace_formatted']}"
    )

    return GoalProgress(
        goal=goal,
        current_predicted_time=best_recent_time,
        gap_to_goal_sec=gap_to_goal,
        weeks_remaining=weeks_remaining,
        ctl_current=current_ctl,
        ctl_needed_estimate=ctl_needed,
        on_track=on_track,
        recommendations=recommendations,
    )


def format_goal_progress(progress: GoalProgress) -> str:
    """
    Format goal progress for display.

    Args:
        progress: GoalProgress object

    Returns:
        Formatted string
    """
    lines = []

    # Header
    lines.append(f"Goal: {progress.goal.distance.display_name} in {progress.goal.target_time_formatted}")
    lines.append(f"Race Date: {progress.goal.race_date.strftime('%B %d, %Y')}")
    lines.append("=" * 50)
    lines.append("")

    # Timeline
    lines.append(f"Weeks remaining: {progress.weeks_remaining}")
    lines.append("")

    # Current vs target
    lines.append("Performance:")
    lines.append(f"  Target:    {progress.goal.target_time_formatted}")
    lines.append(f"  Current:   {format_time(progress.current_predicted_time)}")

    if progress.gap_to_goal_sec > 0:
        lines.append(f"  Gap:       {format_time(progress.gap_to_goal_sec)} to improve")
    else:
        lines.append(f"  Ahead by:  {format_time(abs(progress.gap_to_goal_sec))}")
    lines.append("")

    # Fitness
    lines.append("Fitness (CTL):")
    lines.append(f"  Current:   {progress.ctl_current:.0f}")
    lines.append(f"  Target:    ~{progress.ctl_needed_estimate:.0f}")
    lines.append("")

    # Status
    if progress.on_track:
        lines.append("Status: ON TRACK")
    else:
        lines.append("Status: NEEDS WORK - increase training consistency")
    lines.append("")

    # Recommendations
    lines.append("Recommendations:")
    for rec in progress.recommendations:
        lines.append(f"  - {rec}")

    return "\n".join(lines)


# ============================================================================
# VO2max-based Training Pace Calculation (Jack Daniels' VDOT)
# ============================================================================

# VDOT lookup table mapping VO2max to training paces in sec/km
# Based on Jack Daniels' Running Formula
# This is a simplified version - full tables have more granular values
VDOT_PACE_TABLE = {
    # VO2max: (easy_pace, marathon_pace, threshold_pace, interval_pace, repetition_pace)
    # All values in seconds per kilometer
    30: (450, 395, 365, 330, 300),  # Very slow
    35: (420, 365, 335, 305, 275),
    40: (390, 340, 310, 280, 255),
    45: (365, 315, 285, 260, 235),
    50: (340, 295, 265, 242, 218),
    55: (320, 275, 250, 225, 203),
    60: (300, 260, 235, 210, 190),
    65: (285, 245, 222, 198, 178),
    70: (270, 232, 210, 188, 168),
    75: (258, 220, 200, 178, 160),
    80: (246, 210, 190, 170, 153),
    85: (235, 200, 182, 162, 145),
}


def _interpolate_pace(vo2max: float, pace_index: int) -> int:
    """
    Interpolate a pace value from the VDOT table.

    Args:
        vo2max: VO2max value
        pace_index: Index of pace type (0=easy, 1=marathon, 2=threshold, 3=interval, 4=rep)

    Returns:
        Interpolated pace in seconds per kilometer
    """
    # Clamp to table range
    vo2max = max(30, min(85, vo2max))

    # Find surrounding values
    vdot_values = sorted(VDOT_PACE_TABLE.keys())

    # Find lower and upper bounds
    lower_vdot = 30
    upper_vdot = 85

    for v in vdot_values:
        if v <= vo2max:
            lower_vdot = v
        if v >= vo2max:
            upper_vdot = v
            break

    # If exact match
    if lower_vdot == upper_vdot:
        return VDOT_PACE_TABLE[lower_vdot][pace_index]

    # Linear interpolation
    lower_pace = VDOT_PACE_TABLE[lower_vdot][pace_index]
    upper_pace = VDOT_PACE_TABLE[upper_vdot][pace_index]

    ratio = (vo2max - lower_vdot) / (upper_vdot - lower_vdot)
    interpolated = lower_pace - (lower_pace - upper_pace) * ratio

    return int(round(interpolated))


def calculate_training_paces_from_vo2max(vo2max: float) -> Dict[str, int]:
    """
    Calculate training paces from VO2max using Jack Daniels' VDOT tables.

    This provides more accurate training paces than estimating from goal race pace,
    as it's based on actual measured fitness level.

    Args:
        vo2max: VO2max value in ml/kg/min (typically 30-85 for runners)

    Returns:
        Dictionary with paces in seconds per kilometer:
        - easy_pace: For recovery and base building (Zone 1-2)
        - marathon_pace: Sustainable race pace (Zone 3)
        - threshold_pace: Lactate threshold pace (Zone 4)
        - interval_pace: VO2max training pace (Zone 4-5)
        - repetition_pace: Speed/economy work (Zone 5)

    Example:
        >>> paces = calculate_training_paces_from_vo2max(55.0)
        >>> paces['easy_pace']  # ~5:20/km
        320
        >>> paces['threshold_pace']  # ~4:10/km
        250
    """
    if vo2max < 30:
        vo2max = 30
    elif vo2max > 85:
        vo2max = 85

    return {
        "easy_pace": _interpolate_pace(vo2max, 0),
        "marathon_pace": _interpolate_pace(vo2max, 1),
        "threshold_pace": _interpolate_pace(vo2max, 2),
        "interval_pace": _interpolate_pace(vo2max, 3),
        "repetition_pace": _interpolate_pace(vo2max, 4),
    }


def format_pace_from_seconds(pace_sec: int) -> str:
    """Format pace in seconds to min:sec/km string."""
    minutes = pace_sec // 60
    seconds = pace_sec % 60
    return f"{minutes}:{seconds:02d}/km"


def calculate_training_paces_from_vo2max_detailed(vo2max: float) -> Dict[str, Dict[str, Any]]:
    """
    Calculate training paces from VO2max with detailed information.

    Similar to calculate_training_paces_from_vo2max but includes formatted
    paces, descriptions, and heart rate zone information.

    Args:
        vo2max: VO2max value in ml/kg/min

    Returns:
        Dictionary with detailed pace information for each training type
    """
    base_paces = calculate_training_paces_from_vo2max(vo2max)

    pace_details = {
        "easy": {
            "name": "Easy",
            "pace_sec": base_paces["easy_pace"],
            "pace_formatted": format_pace_from_seconds(base_paces["easy_pace"]),
            "hr_zone": "Zone 1-2",
            "description": "Conversational pace for recovery and base building",
            "purpose": "Aerobic base, active recovery",
        },
        "marathon": {
            "name": "Marathon Pace",
            "pace_sec": base_paces["marathon_pace"],
            "pace_formatted": format_pace_from_seconds(base_paces["marathon_pace"]),
            "hr_zone": "Zone 3",
            "description": "Sustainable race pace for marathon distance",
            "purpose": "Race-specific fitness, fat metabolism",
        },
        "threshold": {
            "name": "Threshold",
            "pace_sec": base_paces["threshold_pace"],
            "pace_formatted": format_pace_from_seconds(base_paces["threshold_pace"]),
            "hr_zone": "Zone 4",
            "description": "Comfortably hard, sustainable for 20-60 min",
            "purpose": "Raise lactate threshold, improve endurance",
        },
        "interval": {
            "name": "Interval (VO2max)",
            "pace_sec": base_paces["interval_pace"],
            "pace_formatted": format_pace_from_seconds(base_paces["interval_pace"]),
            "hr_zone": "Zone 4-5",
            "description": "Hard efforts for 3-5 min intervals",
            "purpose": "Improve VO2max and aerobic power",
        },
        "repetition": {
            "name": "Repetition",
            "pace_sec": base_paces["repetition_pace"],
            "pace_formatted": format_pace_from_seconds(base_paces["repetition_pace"]),
            "hr_zone": "Zone 5",
            "description": "Fast, short repetitions with full recovery",
            "purpose": "Improve speed and running economy",
        },
    }

    # Add mile equivalents
    for pace_type in pace_details:
        pace_sec = pace_details[pace_type]["pace_sec"]
        pace_mile = int(pace_sec * 1.60934)
        min_mile = pace_mile // 60
        sec_mile = pace_mile % 60
        pace_details[pace_type]["pace_mile_formatted"] = f"{min_mile}:{sec_mile:02d}/mi"

    return pace_details


# ============================================================================
# Goal Feasibility Assessment
# ============================================================================

def assess_goal_feasibility(
    race_predictions: Dict[str, int],
    goal_distance: str,
    goal_time_sec: int,
) -> Dict[str, Any]:
    """
    Compare Garmin race predictions to goal time.

    Uses Garmin's race predictions (based on VO2max and training data) to
    assess how realistic a goal time is.

    Args:
        race_predictions: Dictionary with race predictions in seconds:
            - race_time_5k, race_time_10k, race_time_half, race_time_marathon
        goal_distance: Target race distance ("5k", "10k", "half_marathon", "marathon")
        goal_time_sec: Target finish time in seconds

    Returns:
        Dictionary with:
        - current_predicted: Predicted time for the goal distance (seconds)
        - current_predicted_formatted: Predicted time formatted as string
        - goal_time: Target time (seconds)
        - goal_time_formatted: Target time formatted as string
        - gap_seconds: Difference in seconds (positive = goal is faster than prediction)
        - gap_percent: How much faster the goal is vs prediction (%)
        - gap_formatted: Human-readable gap (e.g., "2:30 faster than prediction")
        - feasibility: Rating of goal difficulty
        - recommendation: What to focus on to achieve the goal

    Feasibility ratings:
        - "on_track": Goal matches or is slower than current prediction
        - "achievable": Goal is 0-3% faster than prediction (reasonable stretch)
        - "ambitious": Goal is 3-7% faster than prediction (requires significant improvement)
        - "very_ambitious": Goal is >7% faster than prediction (may need to adjust)

    Example:
        >>> predictions = {"race_time_5k": 1320, "race_time_10k": 2760}
        >>> result = assess_goal_feasibility(predictions, "5k", 1200)
        >>> result["feasibility"]
        "achievable"
    """
    # Map goal distance to prediction key
    distance_mapping = {
        "5k": "race_time_5k",
        "10k": "race_time_10k",
        "half_marathon": "race_time_half",
        "half": "race_time_half",
        "marathon": "race_time_marathon",
    }

    # Normalize goal distance
    goal_dist_normalized = goal_distance.lower().replace("-", "_").replace(" ", "_")
    prediction_key = distance_mapping.get(goal_dist_normalized)

    if not prediction_key:
        return {
            "error": f"Unknown goal distance: {goal_distance}",
            "feasibility": "unknown",
            "recommendation": "Please specify a valid race distance (5k, 10k, half_marathon, or marathon)",
        }

    # Get current prediction for goal distance
    current_predicted = race_predictions.get(prediction_key)

    # If no prediction for exact distance, try to estimate from other predictions
    if current_predicted is None:
        current_predicted = _estimate_prediction_from_other_distances(
            race_predictions, goal_dist_normalized
        )

    if current_predicted is None:
        return {
            "error": "No race predictions available",
            "feasibility": "unknown",
            "recommendation": "Sync more workouts to generate race predictions",
        }

    # Calculate gap
    gap_seconds = current_predicted - goal_time_sec  # Positive = goal is faster
    gap_percent = (gap_seconds / current_predicted) * 100 if current_predicted > 0 else 0

    # Determine feasibility
    if gap_percent <= 0:
        feasibility = "on_track"
        recommendation = "You're already performing at or better than your goal pace. Focus on maintaining fitness and race execution."
    elif gap_percent <= 3:
        feasibility = "achievable"
        recommendation = "Your goal is within reach with consistent training. Focus on race-specific workouts and threshold runs."
    elif gap_percent <= 7:
        feasibility = "ambitious"
        recommendation = "This goal requires significant improvement. Increase training volume gradually and incorporate more quality sessions."
    else:
        feasibility = "very_ambitious"
        recommendation = "This goal may be challenging to achieve in the near term. Consider adjusting your target or extending your timeline."

    # Format gap for display
    gap_abs = abs(gap_seconds)
    gap_min = gap_abs // 60
    gap_sec = gap_abs % 60

    if gap_seconds > 0:
        gap_formatted = f"{gap_min}:{gap_sec:02d} faster than prediction"
    elif gap_seconds < 0:
        gap_formatted = f"{gap_min}:{gap_sec:02d} ahead of goal"
    else:
        gap_formatted = "Exactly on target"

    return {
        "current_predicted": current_predicted,
        "current_predicted_formatted": format_time(current_predicted),
        "goal_time": goal_time_sec,
        "goal_time_formatted": format_time(goal_time_sec),
        "gap_seconds": gap_seconds,
        "gap_percent": round(gap_percent, 1),
        "gap_formatted": gap_formatted,
        "feasibility": feasibility,
        "recommendation": recommendation,
    }


def _estimate_prediction_from_other_distances(
    race_predictions: Dict[str, int],
    target_distance: str,
) -> Optional[int]:
    """
    Estimate race prediction for a distance using Riegel formula from other available predictions.

    Args:
        race_predictions: Available race predictions
        target_distance: Target distance to estimate

    Returns:
        Estimated time in seconds, or None if no predictions available
    """
    distance_km = {
        "5k": 5.0,
        "10k": 10.0,
        "half_marathon": 21.0975,
        "marathon": 42.195,
    }

    target_km = distance_km.get(target_distance)
    if not target_km:
        return None

    # Try to find a prediction to estimate from
    prediction_keys = [
        ("race_time_5k", 5.0),
        ("race_time_10k", 10.0),
        ("race_time_half", 21.0975),
        ("race_time_marathon", 42.195),
    ]

    for key, dist_km in prediction_keys:
        time_sec = race_predictions.get(key)
        if time_sec and time_sec > 0:
            # Use Riegel formula: T2 = T1 * (D2/D1)^1.06
            distance_ratio = target_km / dist_km
            predicted = time_sec * (distance_ratio ** 1.06)
            return int(predicted)

    return None


def get_goal_feasibility_summary(
    race_predictions: Dict[str, int],
    goals: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Assess feasibility of multiple goals.

    Args:
        race_predictions: Current race predictions from Garmin
        goals: List of race goals with distance and target_time_sec

    Returns:
        List of feasibility assessments for each goal
    """
    summaries = []

    for goal in goals:
        distance = goal.get("distance") or goal.get("distance_name", "")
        target_time = goal.get("target_time_sec", 0)

        if not distance or not target_time:
            continue

        assessment = assess_goal_feasibility(race_predictions, distance, target_time)
        assessment["goal_distance"] = distance
        assessment["race_date"] = goal.get("race_date")
        summaries.append(assessment)

    return summaries
