"""
Race Goal and Performance Prediction

Set goals and track progress toward them.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import List, Optional, Dict, Any


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
