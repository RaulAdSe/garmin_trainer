"""
Workout Recommendation Engine

Determines what type of workout to do based on:
- Readiness score
- Training load status (ACWR)
- Recent workout patterns
- Periodization phase
"""

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class WorkoutType(Enum):
    """Types of workouts that can be recommended."""

    REST = "rest"
    RECOVERY = "recovery"           # Very easy, <60% max HR
    EASY = "easy"                   # Zone 1-2
    LONG = "long"                   # Extended Zone 2
    TEMPO = "tempo"                 # Zone 3-4
    THRESHOLD = "threshold"         # Zone 4
    INTERVALS = "intervals"         # Zone 4-5
    SPEED = "speed"                 # Short, fast reps

    @property
    def intensity_level(self) -> int:
        """Return relative intensity level (0-5)."""
        intensity_map = {
            WorkoutType.REST: 0,
            WorkoutType.RECOVERY: 1,
            WorkoutType.EASY: 2,
            WorkoutType.LONG: 2,
            WorkoutType.TEMPO: 3,
            WorkoutType.THRESHOLD: 4,
            WorkoutType.INTERVALS: 5,
            WorkoutType.SPEED: 5,
        }
        return intensity_map.get(self, 2)


@dataclass
class WorkoutRecommendation:
    """Complete workout recommendation."""

    workout_type: WorkoutType
    duration_min: int
    intensity_description: str      # "Easy pace, conversational"
    hr_zone_target: Optional[str]   # "Zone 2" or "Zone 4-5"
    reason: str                     # Why this workout
    alternatives: List[str] = field(default_factory=list)  # Other acceptable options
    warnings: List[str] = field(default_factory=list)      # Any cautions
    confidence: float = 0.8         # How confident in this recommendation (0-1)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "workout_type": self.workout_type.value,
            "duration_min": self.duration_min,
            "intensity_description": self.intensity_description,
            "hr_zone_target": self.hr_zone_target,
            "reason": self.reason,
            "alternatives": self.alternatives,
            "warnings": self.warnings,
            "confidence": self.confidence,
        }


# Workout templates with default parameters
WORKOUT_TEMPLATES = {
    WorkoutType.REST: {
        "duration_range": (0, 0),
        "intensity_description": "Complete rest day - no structured exercise",
        "hr_zone_target": None,
    },
    WorkoutType.RECOVERY: {
        "duration_range": (20, 40),
        "intensity_description": "Very easy movement, barely breaking a sweat",
        "hr_zone_target": "Zone 1 (below 60% HRR)",
    },
    WorkoutType.EASY: {
        "duration_range": (30, 60),
        "intensity_description": "Easy, conversational pace throughout",
        "hr_zone_target": "Zone 1-2 (60-70% HRR)",
    },
    WorkoutType.LONG: {
        "duration_range": (60, 120),
        "intensity_description": "Steady aerobic effort, can speak in sentences",
        "hr_zone_target": "Zone 2 (65-75% HRR)",
    },
    WorkoutType.TEMPO: {
        "duration_range": (30, 60),
        "intensity_description": "Comfortably hard, can speak in short phrases",
        "hr_zone_target": "Zone 3-4 (75-85% HRR)",
    },
    WorkoutType.THRESHOLD: {
        "duration_range": (30, 50),
        "intensity_description": "Hard effort at lactate threshold, limited talking",
        "hr_zone_target": "Zone 4 (85-90% HRR)",
    },
    WorkoutType.INTERVALS: {
        "duration_range": (30, 60),
        "intensity_description": "Hard intervals with recovery periods",
        "hr_zone_target": "Zone 4-5 during intervals (85-95% HRR)",
    },
    WorkoutType.SPEED: {
        "duration_range": (20, 40),
        "intensity_description": "Short, fast repetitions with full recovery",
        "hr_zone_target": "Zone 5 during reps (90-100% HRR)",
    },
}


def _is_hard_workout(workout_type: WorkoutType) -> bool:
    """Determine if a workout type is considered 'hard'."""
    return workout_type.intensity_level >= 4


def _calculate_recommended_duration(
    workout_type: WorkoutType,
    weekly_load_so_far: float,
    target_weekly_load: float,
    readiness_score: float,
) -> int:
    """Calculate appropriate duration for the workout."""
    template = WORKOUT_TEMPLATES.get(workout_type, {})
    min_dur, max_dur = template.get("duration_range", (30, 60))

    if min_dur == 0 and max_dur == 0:
        return 0  # Rest day

    # Base duration on middle of range
    base_duration = (min_dur + max_dur) // 2

    # Adjust based on weekly load progress
    if target_weekly_load > 0:
        load_progress = weekly_load_so_far / target_weekly_load
        if load_progress < 0.5:
            # Behind on weekly load, suggest longer
            base_duration = int(base_duration * 1.1)
        elif load_progress > 0.9:
            # Already hit most of weekly target, suggest shorter
            base_duration = int(base_duration * 0.8)

    # Adjust based on readiness
    if readiness_score < 50:
        base_duration = int(base_duration * 0.8)
    elif readiness_score > 85:
        base_duration = int(base_duration * 1.1)

    # Clamp to template range
    return max(min_dur, min(max_dur, base_duration))


def recommend_workout(
    readiness_score: float,
    acwr: float,
    tsb: float,
    days_since_hard: int,
    days_since_long: int,
    weekly_load_so_far: float,
    target_weekly_load: float,
    is_race_week: bool = False,
    preferred_hard_days: Optional[List[int]] = None,  # 0=Mon, 6=Sun
    day_of_week: Optional[int] = None,
) -> WorkoutRecommendation:
    """
    Generate workout recommendation.

    Key rules:
    1. If readiness < 40: Rest or recovery only
    2. If ACWR > 1.3: Easy day to reduce acute load
    3. If yesterday was hard: Easy day (hard/easy pattern)
    4. If ACWR < 0.8 and readiness > 70: Can push harder
    5. Balance weekly load distribution

    Args:
        readiness_score: Overall readiness (0-100)
        acwr: Acute:Chronic Workload Ratio
        tsb: Training Stress Balance
        days_since_hard: Days since last hard workout
        days_since_long: Days since last long workout
        weekly_load_so_far: Accumulated load this week
        target_weekly_load: Target weekly load
        is_race_week: Whether this is a race/taper week
        preferred_hard_days: Preferred days for hard workouts
        day_of_week: Current day of week (0=Monday)

    Returns:
        WorkoutRecommendation with type, duration, and guidance
    """
    warnings = []
    alternatives = []
    confidence = 0.8

    # Rule 1: Low readiness - rest or recovery
    if readiness_score < 40:
        workout_type = WorkoutType.REST if readiness_score < 25 else WorkoutType.RECOVERY
        reason = "Low readiness score indicates need for recovery"

        if readiness_score < 30:
            warnings.append("Very low readiness - consider extra rest if needed")

        return WorkoutRecommendation(
            workout_type=workout_type,
            duration_min=_calculate_recommended_duration(
                workout_type, weekly_load_so_far, target_weekly_load, readiness_score
            ),
            intensity_description=WORKOUT_TEMPLATES[workout_type]["intensity_description"],
            hr_zone_target=WORKOUT_TEMPLATES[workout_type]["hr_zone_target"],
            reason=reason,
            alternatives=["Complete rest", "Light stretching", "Walk"],
            warnings=warnings,
            confidence=0.9,
        )

    # Rule 2: High ACWR (injury risk) - reduce load
    if acwr > 1.3:
        if acwr > 1.5:
            workout_type = WorkoutType.REST
            reason = "ACWR in danger zone (>1.5) - rest to reduce injury risk"
            warnings.append("Injury risk is elevated - prioritize recovery")
            alternatives = ["Complete rest", "Very light recovery only"]
            confidence = 0.95
        else:
            workout_type = WorkoutType.EASY
            reason = "ACWR elevated (>1.3) - easy day to manage training load"
            alternatives = ["Recovery run", "Cross-training"]
            confidence = 0.85

        return WorkoutRecommendation(
            workout_type=workout_type,
            duration_min=_calculate_recommended_duration(
                workout_type, weekly_load_so_far, target_weekly_load, readiness_score
            ),
            intensity_description=WORKOUT_TEMPLATES[workout_type]["intensity_description"],
            hr_zone_target=WORKOUT_TEMPLATES[workout_type]["hr_zone_target"],
            reason=reason,
            alternatives=alternatives,
            warnings=warnings,
            confidence=confidence,
        )

    # Rule 3: Hard/easy pattern - easy day after hard workout
    if days_since_hard == 0:
        workout_type = WorkoutType.EASY
        reason = "Hard workout yesterday - following hard/easy pattern"
        alternatives = ["Recovery run", "Easy cross-training"]

        if readiness_score < 60:
            workout_type = WorkoutType.RECOVERY
            reason = "Hard workout yesterday and moderate readiness - prioritize recovery"

        return WorkoutRecommendation(
            workout_type=workout_type,
            duration_min=_calculate_recommended_duration(
                workout_type, weekly_load_so_far, target_weekly_load, readiness_score
            ),
            intensity_description=WORKOUT_TEMPLATES[workout_type]["intensity_description"],
            hr_zone_target=WORKOUT_TEMPLATES[workout_type]["hr_zone_target"],
            reason=reason,
            alternatives=alternatives,
            warnings=warnings,
            confidence=0.85,
        )

    # Race week - taper logic
    if is_race_week:
        workout_type = WorkoutType.EASY
        reason = "Race week - maintaining fitness with reduced volume"
        alternatives = ["Short tempo efforts", "Strides"]
        warnings.append("Keep intensity brief, focus on staying fresh")

        return WorkoutRecommendation(
            workout_type=workout_type,
            duration_min=30,  # Short during taper
            intensity_description="Easy with a few short pickups to stay sharp",
            hr_zone_target="Zone 1-2, brief Zone 4 strides",
            reason=reason,
            alternatives=alternatives,
            warnings=warnings,
            confidence=0.8,
        )

    # Now we can consider harder workouts

    # Rule 4: Undertrained (ACWR < 0.8) and high readiness - push harder
    if acwr < 0.8 and readiness_score > 70:
        if readiness_score > 85:
            workout_type = WorkoutType.INTERVALS
            reason = "High readiness and undertrained - great day for intervals"
            alternatives = ["Threshold workout", "Tempo run"]
        else:
            workout_type = WorkoutType.TEMPO
            reason = "Good readiness and undertrained - build some intensity"
            alternatives = ["Threshold workout", "Long run with tempo finish"]

        return WorkoutRecommendation(
            workout_type=workout_type,
            duration_min=_calculate_recommended_duration(
                workout_type, weekly_load_so_far, target_weekly_load, readiness_score
            ),
            intensity_description=WORKOUT_TEMPLATES[workout_type]["intensity_description"],
            hr_zone_target=WORKOUT_TEMPLATES[workout_type]["hr_zone_target"],
            reason=reason,
            alternatives=alternatives,
            warnings=warnings,
            confidence=0.85,
        )

    # Standard decision tree based on readiness and training state
    if readiness_score >= 80:
        # High readiness - can do quality work
        if days_since_hard >= 2:
            # Well recovered, time for hard workout
            if days_since_long >= 6:
                workout_type = WorkoutType.LONG
                reason = "Well recovered and due for a long run"
                alternatives = ["Tempo run", "Threshold workout"]
            else:
                workout_type = WorkoutType.THRESHOLD
                reason = "High readiness and well recovered - quality session"
                alternatives = ["Intervals", "Tempo run"]
        else:
            # Only 1 day since hard, still suggest easier
            workout_type = WorkoutType.EASY
            reason = "High readiness but allow 48h recovery between hard efforts"
            alternatives = ["Long easy run", "Moderate aerobic"]

    elif readiness_score >= 60:
        # Moderate readiness
        if days_since_hard >= 2:
            # Can do moderate intensity
            if tsb > 0:
                workout_type = WorkoutType.TEMPO
                reason = "Positive form and recovered - tempo work appropriate"
                alternatives = ["Long easy run", "Threshold intervals"]
            else:
                workout_type = WorkoutType.EASY
                reason = "Moderate readiness with some fatigue - easy day"
                alternatives = ["Long slow run", "Cross-training"]
        else:
            workout_type = WorkoutType.EASY
            reason = "Moderate readiness - easy day in hard/easy pattern"
            alternatives = ["Recovery run", "Cross-training"]

    else:
        # Low-moderate readiness (40-60)
        workout_type = WorkoutType.EASY
        reason = "Below optimal readiness - keep it easy today"
        alternatives = ["Recovery run", "Rest"]
        warnings.append("Listen to your body - cut short if feeling off")

    # Rule 5: Weekly load distribution check
    if target_weekly_load > 0:
        load_remaining = target_weekly_load - weekly_load_so_far
        if day_of_week is not None and day_of_week >= 5:  # Weekend
            if load_remaining > target_weekly_load * 0.3:
                # Need to catch up on load
                if workout_type == WorkoutType.EASY:
                    workout_type = WorkoutType.LONG
                    reason += " (extended for weekly load goals)"

    return WorkoutRecommendation(
        workout_type=workout_type,
        duration_min=_calculate_recommended_duration(
            workout_type, weekly_load_so_far, target_weekly_load, readiness_score
        ),
        intensity_description=WORKOUT_TEMPLATES[workout_type]["intensity_description"],
        hr_zone_target=WORKOUT_TEMPLATES[workout_type]["hr_zone_target"],
        reason=reason,
        alternatives=alternatives,
        warnings=warnings,
        confidence=confidence,
    )


def get_workout_description(workout_type: WorkoutType) -> dict:
    """Get detailed description for a workout type."""
    descriptions = {
        WorkoutType.REST: {
            "name": "Rest Day",
            "summary": "Complete rest - no structured exercise",
            "purpose": "Allow full physical and mental recovery",
            "guidelines": [
                "No running or hard exercise",
                "Light walking is OK",
                "Focus on sleep and nutrition",
                "Gentle stretching if desired",
            ],
        },
        WorkoutType.RECOVERY: {
            "name": "Recovery Run",
            "summary": "Very easy movement to promote recovery",
            "purpose": "Active recovery without adding training stress",
            "guidelines": [
                "Keep heart rate in Zone 1",
                "Should feel effortless",
                "20-40 minutes maximum",
                "Walk breaks are fine",
            ],
        },
        WorkoutType.EASY: {
            "name": "Easy Run",
            "summary": "Relaxed aerobic running at conversational pace",
            "purpose": "Build aerobic base without accumulating fatigue",
            "guidelines": [
                "Stay in Zone 1-2",
                "Can hold conversation easily",
                "Don't chase pace - run by feel",
                "Include warm-up in total time",
            ],
        },
        WorkoutType.LONG: {
            "name": "Long Run",
            "summary": "Extended duration at easy-to-moderate effort",
            "purpose": "Build endurance and aerobic capacity",
            "guidelines": [
                "Stay in Zone 2 for most of run",
                "Start conservatively",
                "Hydrate and fuel for runs over 90min",
                "Finish feeling you could do more",
            ],
        },
        WorkoutType.TEMPO: {
            "name": "Tempo Run",
            "summary": "Sustained effort at comfortably hard pace",
            "purpose": "Improve lactate clearance and running economy",
            "guidelines": [
                "Zone 3-4 for tempo portions",
                "Can speak in short phrases",
                "20-40 minute tempo block typical",
                "Warm up and cool down properly",
            ],
        },
        WorkoutType.THRESHOLD: {
            "name": "Threshold Workout",
            "summary": "Efforts at or near lactate threshold",
            "purpose": "Raise lactate threshold and improve speed endurance",
            "guidelines": [
                "Zone 4 for threshold intervals",
                "5-15 minute intervals typical",
                "Recovery between intervals",
                "Hard but controlled effort",
            ],
        },
        WorkoutType.INTERVALS: {
            "name": "Interval Training",
            "summary": "High-intensity intervals with recovery periods",
            "purpose": "Improve VO2max and speed",
            "guidelines": [
                "Zone 4-5 during work intervals",
                "2-5 minute intervals typical",
                "Equal or slightly less recovery",
                "Quality over quantity",
            ],
        },
        WorkoutType.SPEED: {
            "name": "Speed Work",
            "summary": "Short, fast repetitions with full recovery",
            "purpose": "Develop speed, power, and running form",
            "guidelines": [
                "Near maximal effort for reps",
                "30 seconds to 2 minutes typical",
                "Full recovery between reps",
                "Focus on form at high speed",
            ],
        },
    }

    return descriptions.get(workout_type, {
        "name": workout_type.value.title(),
        "summary": "Standard workout",
        "purpose": "General fitness",
        "guidelines": [],
    })
