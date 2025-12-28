"""
Workout Recommendation Engine

Determines what type of workout to do based on:
- Readiness score
- Training load status (ACWR)
- Recent workout patterns
- Periodization phase

This module also provides full explainability for transparency.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

from ..models.explanations import (
    ImpactType,
    DataSourceType,
    DataSource,
    ExplanationFactor,
    ExplainedRecommendation,
    ExplainedWorkoutRecommendation,
)


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


def recommend_explained_workout(
    readiness_score: float,
    acwr: float,
    tsb: float,
    days_since_hard: int,
    days_since_long: int,
    weekly_load_so_far: float,
    target_weekly_load: float,
    is_race_week: bool = False,
    preferred_hard_days: Optional[List[int]] = None,
    day_of_week: Optional[int] = None,
) -> ExplainedWorkoutRecommendation:
    """
    Generate workout recommendation with full explainability.

    This extends recommend_workout to provide complete transparency
    into the decision-making process, showing the exact logic path
    and how each factor influenced the recommendation.

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
        ExplainedWorkoutRecommendation with full decision tree
    """
    # Get the base recommendation
    rec = recommend_workout(
        readiness_score=readiness_score,
        acwr=acwr,
        tsb=tsb,
        days_since_hard=days_since_hard,
        days_since_long=days_since_long,
        weekly_load_so_far=weekly_load_so_far,
        target_weekly_load=target_weekly_load,
        is_race_week=is_race_week,
        preferred_hard_days=preferred_hard_days,
        day_of_week=day_of_week,
    )

    # Build the decision tree (logic path)
    decision_tree: List[str] = []
    factors: List[ExplanationFactor] = []
    data_points: Dict[str, Any] = {
        "readiness_score": readiness_score,
        "acwr": acwr,
        "tsb": tsb,
        "days_since_hard": days_since_hard,
        "days_since_long": days_since_long,
        "weekly_load_so_far": weekly_load_so_far,
        "target_weekly_load": target_weekly_load,
        "is_race_week": is_race_week,
        "day_of_week": day_of_week,
    }

    # Track influence scores
    readiness_influence = 0.0
    load_influence = 0.0
    pattern_influence = 0.0

    # Evaluate each decision rule and build the tree
    decision_tree.append(f"Input: Readiness={readiness_score:.0f}, ACWR={acwr:.2f}, TSB={tsb:+.1f}")
    decision_tree.append(f"       Days since hard={days_since_hard}, Days since long={days_since_long}")

    # Rule 1: Low readiness check
    if readiness_score < 40:
        decision_tree.append(f"RULE 1: Readiness ({readiness_score:.0f}) < 40 -> Recovery/Rest required")
        readiness_influence = 1.0
        factors.append(_create_readiness_factor(readiness_score, True))
    else:
        decision_tree.append(f"RULE 1: Readiness ({readiness_score:.0f}) >= 40 -> Training possible")

    # Rule 2: High ACWR check
    if acwr > 1.3:
        if acwr > 1.5:
            decision_tree.append(f"RULE 2: ACWR ({acwr:.2f}) > 1.5 -> DANGER ZONE, rest required")
        else:
            decision_tree.append(f"RULE 2: ACWR ({acwr:.2f}) > 1.3 -> Elevated risk, easy day")
        load_influence = 0.8
        factors.append(_create_acwr_factor(acwr))
    else:
        decision_tree.append(f"RULE 2: ACWR ({acwr:.2f}) <= 1.3 -> Load manageable")

    # Rule 3: Hard/easy pattern
    if days_since_hard == 0 and readiness_score >= 40 and acwr <= 1.3:
        decision_tree.append(f"RULE 3: Hard workout yesterday -> Easy day (hard/easy pattern)")
        pattern_influence = 0.7
        factors.append(_create_pattern_factor(days_since_hard, True))
    elif days_since_hard >= 1:
        decision_tree.append(f"RULE 3: {days_since_hard} days since hard -> Pattern allows intensity")

    # Rule 4: Race week check
    if is_race_week:
        decision_tree.append(f"RULE 4: Race week -> Taper mode, reduced volume")

    # Rule 5: Undertrained check
    if acwr < 0.8 and readiness_score > 70:
        decision_tree.append(f"RULE 5: Undertrained (ACWR={acwr:.2f}) + High readiness -> Push harder")
        load_influence = max(load_influence, 0.5)
        factors.append(_create_undertrained_factor(acwr, readiness_score))

    # Rule 6: Quality work eligibility
    if readiness_score >= 80 and days_since_hard >= 2 and acwr <= 1.3:
        if days_since_long >= 6:
            decision_tree.append(f"RULE 6: High readiness + recovered + due for long -> Long run")
        else:
            decision_tree.append(f"RULE 6: High readiness + recovered -> Quality session possible")

    # Add TSB factor
    factors.append(_create_tsb_factor(tsb))

    # Add recovery days factor
    factors.append(_create_recovery_factor(days_since_hard))

    # Final decision
    decision_tree.append(f"")
    decision_tree.append(f"DECISION: {rec.workout_type.value.upper()}")
    decision_tree.append(f"REASON: {rec.reason}")

    # Calculate key driver
    key_driver = None
    if readiness_influence > load_influence and readiness_influence > pattern_influence:
        key_driver = "Readiness Score"
    elif load_influence > pattern_influence:
        key_driver = "Training Load (ACWR)"
    elif pattern_influence > 0:
        key_driver = "Hard/Easy Pattern"
    else:
        key_driver = "Fitness Balance (TSB)"

    # Build alternatives list
    alternatives = rec.alternatives if rec.alternatives else []
    if not alternatives:
        if rec.workout_type.intensity_level >= 3:
            alternatives = ["Easy run", "Cross-training"]
        else:
            alternatives = ["Complete rest", "Light stretching"]

    # Build the explained recommendation
    explained_rec = ExplainedRecommendation(
        recommendation=f"{rec.workout_type.value.title()} - {rec.intensity_description}",
        confidence=rec.confidence,
        confidence_explanation=_get_workout_confidence_explanation(rec.confidence, len(factors)),
        factors=factors,
        data_points=data_points,
        calculation_summary="\n".join(decision_tree),
        alternatives_considered=alternatives,
        key_driver=key_driver,
    )

    return ExplainedWorkoutRecommendation(
        workout_type=rec.workout_type.value,
        duration_min=rec.duration_min,
        intensity_description=rec.intensity_description,
        hr_zone_target=rec.hr_zone_target,
        recommendation=explained_rec,
        decision_tree=decision_tree,
        readiness_influence=readiness_influence,
        load_influence=load_influence,
        pattern_influence=pattern_influence,
    )


def _create_readiness_factor(score: float, is_limiting: bool) -> ExplanationFactor:
    """Create readiness explanation factor."""
    if score >= 80:
        impact = ImpactType.POSITIVE
        explanation = f"High readiness ({score:.0f}/100) enables quality training."
    elif score >= 60:
        impact = ImpactType.NEUTRAL
        explanation = f"Moderate readiness ({score:.0f}/100) allows normal training."
    elif score >= 40:
        impact = ImpactType.NEUTRAL
        explanation = f"Below optimal readiness ({score:.0f}/100) - caution advised."
    else:
        impact = ImpactType.NEGATIVE
        explanation = f"Low readiness ({score:.0f}/100) indicates recovery is needed."

    return ExplanationFactor(
        name="Readiness Score",
        value=score,
        display_value=f"{score:.0f}/100",
        impact=impact,
        weight=0.35,
        contribution_points=score * 0.35 if not is_limiting else -20,
        explanation=explanation,
        threshold="Green zone: >= 67, Yellow: 34-66, Red: < 34",
        baseline=70,
        data_sources=[
            DataSource(
                source_type=DataSourceType.CALCULATED_TSB,
                source_name="Combined Readiness Assessment",
                confidence=0.90,
            )
        ],
    )


def _create_acwr_factor(acwr: float) -> ExplanationFactor:
    """Create ACWR explanation factor."""
    if 0.8 <= acwr <= 1.3:
        impact = ImpactType.POSITIVE
        explanation = f"Optimal training load ratio ({acwr:.2f}) - in the sweet spot for adaptation."
    elif acwr < 0.8:
        impact = ImpactType.NEUTRAL
        explanation = f"Undertrained ({acwr:.2f}) - you can safely increase training load."
    elif acwr <= 1.5:
        impact = ImpactType.NEGATIVE
        explanation = f"Elevated load ratio ({acwr:.2f}) - injury risk is increasing, reduce load."
    else:
        impact = ImpactType.NEGATIVE
        explanation = f"Danger zone ({acwr:.2f}) - high injury risk, rest recommended."

    # Score contribution: 1.0 is optimal (100 points), deviations reduce
    if 0.8 <= acwr <= 1.3:
        score = 100 - abs(acwr - 1.0) * 50
    elif acwr < 0.8:
        score = 60
    else:
        score = max(0, 60 - (acwr - 1.3) * 100)

    return ExplanationFactor(
        name="Training Load Ratio (ACWR)",
        value=acwr,
        display_value=f"{acwr:.2f}",
        impact=impact,
        weight=0.30,
        contribution_points=score * 0.30,
        explanation=explanation,
        threshold="Optimal: 0.8-1.3, Caution: 1.3-1.5, Danger: >1.5",
        baseline=1.0,
        data_sources=[
            DataSource(
                source_type=DataSourceType.CALCULATED_ACWR,
                source_name="Acute:Chronic Workload Ratio",
                confidence=0.90,
            )
        ],
    )


def _create_tsb_factor(tsb: float) -> ExplanationFactor:
    """Create TSB explanation factor."""
    if tsb > 20:
        impact = ImpactType.POSITIVE
        explanation = f"Very fresh (TSB: {tsb:+.1f}) - well-rested and ready for intensity."
    elif tsb > 0:
        impact = ImpactType.POSITIVE
        explanation = f"Fresh (TSB: {tsb:+.1f}) - positive form, good for quality work."
    elif tsb > -10:
        impact = ImpactType.NEUTRAL
        explanation = f"Neutral (TSB: {tsb:+.1f}) - balanced fitness and fatigue."
    elif tsb > -25:
        impact = ImpactType.NEGATIVE
        explanation = f"Fatigued (TSB: {tsb:+.1f}) - accumulated training stress."
    else:
        impact = ImpactType.NEGATIVE
        explanation = f"Very fatigued (TSB: {tsb:+.1f}) - recovery strongly needed."

    # Score: TSB of 10 = 80, TSB of -20 = 40
    score = max(0, min(100, 70 + tsb * 1.5))

    return ExplanationFactor(
        name="Form (TSB)",
        value=tsb,
        display_value=f"{tsb:+.1f}",
        impact=impact,
        weight=0.20,
        contribution_points=score * 0.20,
        explanation=explanation,
        threshold="Fresh: >0, Neutral: -10 to 0, Fatigued: <-10",
        baseline=10,
        data_sources=[
            DataSource(
                source_type=DataSourceType.CALCULATED_TSB,
                source_name="Training Stress Balance",
                confidence=0.90,
            )
        ],
    )


def _create_pattern_factor(days_since_hard: int, forces_easy: bool) -> ExplanationFactor:
    """Create hard/easy pattern explanation factor."""
    if days_since_hard == 0:
        impact = ImpactType.NEGATIVE if forces_easy else ImpactType.NEUTRAL
        explanation = "Hard workout was yesterday - following hard/easy principle for recovery."
        score = 30
    elif days_since_hard == 1:
        impact = ImpactType.NEUTRAL
        explanation = "One day since hard effort - partial recovery, moderate intensity OK."
        score = 60
    elif days_since_hard >= 2:
        impact = ImpactType.POSITIVE
        explanation = f"{days_since_hard} days since hard workout - fully recovered for intensity."
        score = 90
    else:
        impact = ImpactType.NEUTRAL
        explanation = "Recovery pattern analyzed."
        score = 70

    return ExplanationFactor(
        name="Hard/Easy Pattern",
        value=days_since_hard,
        display_value=f"{days_since_hard} days",
        impact=impact,
        weight=0.15,
        contribution_points=score * 0.15,
        explanation=explanation,
        threshold="Allow 48+ hours between hard sessions",
        baseline=2,
        data_sources=[
            DataSource(
                source_type=DataSourceType.ACTIVITY_HISTORY,
                source_name="Recent Workouts",
                confidence=1.0,
            )
        ],
    )


def _create_recovery_factor(days_since_hard: int) -> ExplanationFactor:
    """Create recovery days factor."""
    if days_since_hard >= 3:
        impact = ImpactType.POSITIVE
        explanation = f"{days_since_hard} full days of recovery - primed for hard effort."
        score = 95
    elif days_since_hard == 2:
        impact = ImpactType.POSITIVE
        explanation = "Two days recovery - good window for quality training."
        score = 85
    elif days_since_hard == 1:
        impact = ImpactType.NEUTRAL
        explanation = "One day recovery - suitable for moderate efforts."
        score = 60
    else:
        impact = ImpactType.NEGATIVE
        explanation = "Hard workout yesterday - body still adapting."
        score = 30

    return ExplanationFactor(
        name="Recovery Days",
        value=days_since_hard,
        display_value=f"{days_since_hard} days since hard",
        impact=impact,
        weight=0.10,
        contribution_points=score * 0.10,
        explanation=explanation,
        threshold="Optimal: 2+ days between hard sessions",
        baseline=2,
        data_sources=[
            DataSource(
                source_type=DataSourceType.ACTIVITY_HISTORY,
                source_name="Workout History",
                confidence=1.0,
            )
        ],
    )


def _create_undertrained_factor(acwr: float, readiness: float) -> ExplanationFactor:
    """Create undertrained opportunity factor."""
    return ExplanationFactor(
        name="Training Opportunity",
        value={"acwr": acwr, "readiness": readiness},
        display_value=f"Undertrained with high readiness",
        impact=ImpactType.POSITIVE,
        weight=0.10,
        contribution_points=15,
        explanation=f"Low ACWR ({acwr:.2f}) combined with high readiness ({readiness:.0f}) indicates opportunity to build fitness.",
        threshold="ACWR < 0.8 with readiness > 70",
        baseline=None,
        data_sources=[
            DataSource(
                source_type=DataSourceType.CALCULATED_ACWR,
                source_name="Training Load Analysis",
                confidence=0.85,
            )
        ],
    )


def _get_workout_confidence_explanation(confidence: float, num_factors: int) -> str:
    """Explain the workout recommendation confidence."""
    if confidence >= 0.9:
        return "High confidence - clear decision based on multiple aligned factors."
    elif confidence >= 0.8:
        return "Good confidence - recommendation supported by key metrics."
    elif confidence >= 0.7:
        return "Moderate confidence - some factors point in different directions."
    else:
        return "Lower confidence - limited data or conflicting signals."
