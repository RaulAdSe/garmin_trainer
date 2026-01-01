"""
Workout Design Agent for AI-powered workout creation.

Uses LLM to generate personalized structured workouts based on
athlete context, training paces, and workout goals.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from ..models.workouts import (
    AthleteContext,
    IntensityZone,
    IntervalType,
    StructuredWorkout,
    WorkoutDesignRequest,
    WorkoutInterval,
    WorkoutSport,
)
from ..llm.providers import LLMClient, ModelType, get_llm_client
from ..llm.prompts import WORKOUT_DESIGN_SYSTEM, WORKOUT_DESIGN_USER


class WorkoutDesignAgent:
    """
    AI agent for designing structured running workouts.

    Uses athlete context (HR zones, training paces, fitness metrics)
    to generate appropriate workout structures with intervals.
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Initialize the workout design agent.

        Args:
            llm_client: Optional LLM client instance. If not provided,
                       uses the default singleton.
        """
        self._llm_client = llm_client

    @property
    def llm(self) -> LLMClient:
        """Get LLM client, creating if needed."""
        if self._llm_client is None:
            self._llm_client = get_llm_client()
        return self._llm_client

    def design_workout(
        self,
        request: WorkoutDesignRequest,
        athlete_context: AthleteContext,
    ) -> StructuredWorkout:
        """
        Design a structured workout using rule-based logic.

        This is the synchronous fallback method that doesn't require LLM.
        Use design_workout_async for AI-powered generation.

        Args:
            request: Workout design parameters
            athlete_context: Athlete's training context

        Returns:
            A complete StructuredWorkout ready for FIT export
        """
        workout_type = request.workout_type.lower()
        duration = request.duration_min or 45

        # Build intervals based on workout type
        if workout_type == "easy":
            return self._design_easy_workout(duration, athlete_context)
        elif workout_type == "tempo":
            return self._design_tempo_workout(duration, athlete_context)
        elif workout_type in ("intervals", "interval"):
            return self._design_interval_workout(duration, athlete_context)
        elif workout_type == "threshold":
            return self._design_threshold_workout(duration, athlete_context)
        elif workout_type == "long":
            duration = request.duration_min or 90
            return self._design_long_workout(duration, athlete_context)
        elif workout_type == "fartlek":
            return self._design_fartlek_workout(duration, athlete_context)
        else:
            # Default to easy run
            return self._design_easy_workout(duration, athlete_context)

    async def design_workout_async(
        self,
        request: WorkoutDesignRequest,
        athlete_context: AthleteContext,
    ) -> StructuredWorkout:
        """
        Design a workout using AI for more nuanced, personalized results.

        Args:
            request: Workout design parameters
            athlete_context: Athlete's training context

        Returns:
            AI-designed structured workout
        """
        # Format training paces for prompt
        training_paces = self._format_training_paces(athlete_context)

        # Format HR zones for prompt
        hr_zones = self._format_hr_zones(athlete_context)

        # Build athlete context string
        context_str = self._format_athlete_context(athlete_context)

        # Prepare system prompt
        system_prompt = WORKOUT_DESIGN_SYSTEM.format(athlete_context=context_str)

        # Prepare user prompt
        user_prompt = WORKOUT_DESIGN_USER.format(
            workout_type=request.workout_type,
            duration_min=request.duration_min or 45,
            target_load=request.target_load or "auto",
            focus=request.focus or "general fitness",
            training_paces=training_paces,
            hr_zones=hr_zones,
        )

        try:
            # Call LLM
            response = await self.llm.completion(
                system=system_prompt,
                user=user_prompt,
                model=ModelType.SMART,
                temperature=0.7,
                max_tokens=1500,
            )

            # Parse JSON response
            workout_data = self._parse_llm_response(response)

            # Convert to StructuredWorkout
            return self._create_workout_from_llm_response(workout_data, request)

        except Exception as e:
            # Fallback to rule-based design
            logger.warning(f"LLM workout design failed: {e}, falling back to rules")
            return self.design_workout(request, athlete_context)

    def _format_training_paces(self, context: AthleteContext) -> str:
        """Format training paces for LLM prompt."""
        return f"""- Easy: {context.format_pace(context.easy_pace)}
- Long Run: {context.format_pace(context.long_pace)}
- Tempo: {context.format_pace(context.tempo_pace)}
- Threshold: {context.format_pace(context.threshold_pace)}
- Interval: {context.format_pace(context.interval_pace)}
- Race Pace: {context.format_pace(context.race_pace)}"""

    def _format_hr_zones(self, context: AthleteContext) -> str:
        """Format HR zones for LLM prompt."""
        lines = []
        zone_names = ["Recovery", "Aerobic", "Tempo", "Threshold", "VO2max"]
        for i, name in enumerate(zone_names, 1):
            low, high = context.get_hr_zone_range(i)
            lines.append(f"- Zone {i} ({name}): {low}-{high} bpm")
        return "\n".join(lines)

    def _format_athlete_context(self, context: AthleteContext) -> str:
        """Format athlete context for LLM prompt."""
        return f"""Fitness Metrics:
- CTL (fitness): {context.ctl:.1f}
- ATL (fatigue): {context.atl:.1f}
- TSB (form): {context.tsb:.1f}
- Readiness: {context.readiness_score}/100

Physiology:
- Max HR: {context.max_hr} bpm
- Resting HR: {context.rest_hr} bpm
- Lactate Threshold HR: {context.lthr} bpm"""

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response."""
        # Try to extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # Try to parse entire response as JSON
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            raise ValueError(f"Could not parse LLM response as JSON: {response[:200]}")

    def _create_workout_from_llm_response(
        self,
        data: Dict[str, Any],
        request: WorkoutDesignRequest,
    ) -> StructuredWorkout:
        """Create StructuredWorkout from parsed LLM response."""
        intervals = []

        for interval_data in data.get("intervals", []):
            interval = WorkoutInterval(
                type=IntervalType(interval_data.get("type", "work")),
                duration_sec=interval_data.get("duration_sec"),
                distance_m=interval_data.get("distance_m"),
                target_pace_range=(
                    interval_data.get("target_pace_min"),
                    interval_data.get("target_pace_max"),
                ) if interval_data.get("target_pace_min") else None,
                target_hr_range=(
                    interval_data.get("target_hr_min"),
                    interval_data.get("target_hr_max"),
                ) if interval_data.get("target_hr_min") else None,
                repetitions=interval_data.get("repetitions", 1),
                notes=interval_data.get("notes"),
            )
            intervals.append(interval)

        return StructuredWorkout.create(
            name=data.get("name", f"{request.workout_type.title()} Workout"),
            description=data.get("description", "AI-designed workout"),
            intervals=intervals,
            sport=WorkoutSport.RUNNING,
            estimated_load=data.get("estimated_load", 0.0),
        )

    # ========================================================================
    # Rule-based workout design methods
    # ========================================================================

    def _design_easy_workout(
        self,
        duration_min: int,
        context: AthleteContext,
    ) -> StructuredWorkout:
        """Design an easy recovery/base run."""
        hr_zone = context.get_hr_zone_range(1)
        easy_pace = context.easy_pace

        intervals = [
            WorkoutInterval(
                type=IntervalType.WARMUP,
                duration_sec=300,  # 5 min
                notes="Walk or very easy jog to warm up",
            ),
            WorkoutInterval(
                type=IntervalType.WORK,
                duration_sec=(duration_min - 10) * 60,
                target_pace_range=(easy_pace - 15, easy_pace + 30),
                target_hr_range=hr_zone,
                notes="Easy conversational pace - you should be able to hold a conversation",
                intensity_zone=IntensityZone.RECOVERY,
            ),
            WorkoutInterval(
                type=IntervalType.COOLDOWN,
                duration_sec=300,  # 5 min
                notes="Easy jog transitioning to walk",
            ),
        ]

        return StructuredWorkout.create(
            name="Easy Run",
            description="Recovery/base building run at conversational pace",
            intervals=intervals,
            estimated_load=duration_min * 0.6,  # Low stress
        )

    def _design_tempo_workout(
        self,
        duration_min: int,
        context: AthleteContext,
    ) -> StructuredWorkout:
        """Design a tempo/threshold run."""
        easy_hr = context.get_hr_zone_range(2)
        tempo_hr = context.get_hr_zone_range(3)
        easy_pace = context.easy_pace
        tempo_pace = context.tempo_pace

        # Tempo portion is typically 20-40 minutes
        tempo_duration = min(30, max(15, duration_min - 20))

        intervals = [
            WorkoutInterval(
                type=IntervalType.WARMUP,
                duration_sec=600,  # 10 min
                target_pace_range=(easy_pace - 15, easy_pace + 30),
                target_hr_range=easy_hr,
                notes="Easy jog, include 4-6 strides at end",
            ),
            WorkoutInterval(
                type=IntervalType.WORK,
                duration_sec=tempo_duration * 60,
                target_pace_range=(tempo_pace - 10, tempo_pace + 10),
                target_hr_range=tempo_hr,
                notes="Comfortably hard - can speak in short phrases only",
                intensity_zone=IntensityZone.TEMPO,
            ),
            WorkoutInterval(
                type=IntervalType.COOLDOWN,
                duration_sec=600,  # 10 min
                target_pace_range=(easy_pace, easy_pace + 60),
                target_hr_range=easy_hr,
                notes="Easy jog to recover",
            ),
        ]

        return StructuredWorkout.create(
            name="Tempo Run",
            description="Sustained effort at lactate threshold pace",
            intervals=intervals,
            estimated_load=duration_min * 1.2,
        )

    def _design_interval_workout(
        self,
        duration_min: int,
        context: AthleteContext,
    ) -> StructuredWorkout:
        """Design a high-intensity interval workout."""
        easy_hr = context.get_hr_zone_range(2)
        vo2max_hr = context.get_hr_zone_range(5)
        recovery_hr = context.get_hr_zone_range(1)
        easy_pace = context.easy_pace
        interval_pace = context.interval_pace

        # Calculate number of intervals (3min work + 2min recovery = 5min per set)
        available_time = duration_min - 20  # Warmup + cooldown
        num_intervals = max(4, min(8, available_time // 5))

        intervals = [
            WorkoutInterval(
                type=IntervalType.WARMUP,
                duration_sec=600,  # 10 min
                target_pace_range=(easy_pace - 15, easy_pace + 30),
                target_hr_range=easy_hr,
                notes="Easy jog, include 4-6 strides to prepare for intensity",
            ),
        ]

        # Add work/recovery pairs
        for i in range(num_intervals):
            intervals.append(
                WorkoutInterval(
                    type=IntervalType.WORK,
                    duration_sec=180,  # 3 min (~800m-1000m)
                    target_pace_range=(interval_pace - 10, interval_pace + 10),
                    target_hr_range=vo2max_hr,
                    notes=f"Interval {i+1}/{num_intervals} - hard but controlled effort",
                    intensity_zone=IntensityZone.VO2MAX,
                )
            )
            if i < num_intervals - 1:  # No recovery after last interval
                intervals.append(
                    WorkoutInterval(
                        type=IntervalType.RECOVERY,
                        duration_sec=120,  # 2 min
                        target_hr_range=recovery_hr,
                        notes="Easy jog recovery - let HR drop below Z2",
                        intensity_zone=IntensityZone.RECOVERY,
                    )
                )

        intervals.append(
            WorkoutInterval(
                type=IntervalType.COOLDOWN,
                duration_sec=600,  # 10 min
                target_pace_range=(easy_pace, easy_pace + 60),
                target_hr_range=easy_hr,
                notes="Easy jog to recover, gradually slowing",
            )
        )

        return StructuredWorkout.create(
            name="Interval Session",
            description=f"VO2max intervals: {num_intervals}x3min with 2min recovery",
            intervals=intervals,
            estimated_load=duration_min * 1.5,
        )

    def _design_threshold_workout(
        self,
        duration_min: int,
        context: AthleteContext,
    ) -> StructuredWorkout:
        """Design a threshold/cruise interval workout."""
        easy_hr = context.get_hr_zone_range(2)
        threshold_hr = context.get_hr_zone_range(4)
        recovery_hr = context.get_hr_zone_range(1)
        easy_pace = context.easy_pace
        threshold_pace = context.threshold_pace

        # 3x8min or 4x6min threshold intervals
        available_time = duration_min - 20
        if available_time >= 30:
            num_intervals = 3
            interval_duration = 480  # 8 min
        else:
            num_intervals = 4
            interval_duration = 360  # 6 min

        intervals = [
            WorkoutInterval(
                type=IntervalType.WARMUP,
                duration_sec=600,  # 10 min
                target_pace_range=(easy_pace - 15, easy_pace + 30),
                target_hr_range=easy_hr,
                notes="Easy jog with 4-6 strides",
            ),
        ]

        # Add threshold intervals with short recovery
        for i in range(num_intervals):
            intervals.append(
                WorkoutInterval(
                    type=IntervalType.WORK,
                    duration_sec=interval_duration,
                    target_pace_range=(threshold_pace - 10, threshold_pace + 10),
                    target_hr_range=threshold_hr,
                    notes=f"Cruise interval {i+1}/{num_intervals} - comfortably hard, sustainable effort",
                    intensity_zone=IntensityZone.THRESHOLD,
                )
            )
            if i < num_intervals - 1:
                intervals.append(
                    WorkoutInterval(
                        type=IntervalType.RECOVERY,
                        duration_sec=90,  # 90 sec recovery (short for cruise intervals)
                        target_hr_range=recovery_hr,
                        notes="Short recovery jog",
                        intensity_zone=IntensityZone.RECOVERY,
                    )
                )

        intervals.append(
            WorkoutInterval(
                type=IntervalType.COOLDOWN,
                duration_sec=600,  # 10 min
                target_pace_range=(easy_pace, easy_pace + 60),
                target_hr_range=easy_hr,
                notes="Easy jog to recover",
            )
        )

        return StructuredWorkout.create(
            name="Threshold Workout",
            description=f"Cruise intervals: {num_intervals}x{interval_duration//60}min at threshold",
            intervals=intervals,
            estimated_load=duration_min * 1.3,
        )

    def _design_long_workout(
        self,
        duration_min: int,
        context: AthleteContext,
    ) -> StructuredWorkout:
        """Design a long endurance run."""
        aerobic_hr = context.get_hr_zone_range(2)
        long_pace = context.long_pace

        intervals = [
            WorkoutInterval(
                type=IntervalType.WARMUP,
                duration_sec=300,  # 5 min
                notes="Very easy start - walk/jog",
            ),
            WorkoutInterval(
                type=IntervalType.WORK,
                duration_sec=(duration_min - 10) * 60,
                target_pace_range=(long_pace - 15, long_pace + 30),
                target_hr_range=aerobic_hr,
                notes="Steady aerobic pace - stay relaxed and patient",
                intensity_zone=IntensityZone.AEROBIC,
            ),
            WorkoutInterval(
                type=IntervalType.COOLDOWN,
                duration_sec=300,  # 5 min
                notes="Easy finish, walk if needed",
            ),
        ]

        return StructuredWorkout.create(
            name="Long Run",
            description="Extended aerobic endurance run",
            intervals=intervals,
            estimated_load=duration_min * 0.9,
        )

    def _design_fartlek_workout(
        self,
        duration_min: int,
        context: AthleteContext,
    ) -> StructuredWorkout:
        """Design a fartlek (speed play) workout."""
        easy_hr = context.get_hr_zone_range(2)
        tempo_hr = context.get_hr_zone_range(3)
        vo2max_hr = context.get_hr_zone_range(5)
        easy_pace = context.easy_pace
        tempo_pace = context.tempo_pace
        interval_pace = context.interval_pace

        intervals = [
            WorkoutInterval(
                type=IntervalType.WARMUP,
                duration_sec=600,  # 10 min
                target_pace_range=(easy_pace - 15, easy_pace + 30),
                target_hr_range=easy_hr,
                notes="Easy jog",
            ),
        ]

        # Fartlek pattern: varied surges
        surges = [
            (60, "short burst", IntensityZone.VO2MAX, interval_pace, vo2max_hr),
            (120, "recovery", IntensityZone.AEROBIC, easy_pace, easy_hr),
            (90, "tempo surge", IntensityZone.TEMPO, tempo_pace, tempo_hr),
            (90, "recovery", IntensityZone.AEROBIC, easy_pace, easy_hr),
            (45, "fast burst", IntensityZone.VO2MAX, interval_pace, vo2max_hr),
            (150, "recovery", IntensityZone.AEROBIC, easy_pace, easy_hr),
            (120, "tempo surge", IntensityZone.TEMPO, tempo_pace, tempo_hr),
            (90, "recovery", IntensityZone.AEROBIC, easy_pace, easy_hr),
            (60, "short burst", IntensityZone.VO2MAX, interval_pace, vo2max_hr),
        ]

        for duration_sec, notes, zone, pace, hr_range in surges:
            interval_type = IntervalType.WORK if zone != IntensityZone.AEROBIC else IntervalType.RECOVERY
            intervals.append(
                WorkoutInterval(
                    type=interval_type,
                    duration_sec=duration_sec,
                    target_pace_range=(pace - 15, pace + 15),
                    target_hr_range=hr_range,
                    notes=notes.capitalize(),
                    intensity_zone=zone,
                )
            )

        intervals.append(
            WorkoutInterval(
                type=IntervalType.COOLDOWN,
                duration_sec=600,  # 10 min
                target_pace_range=(easy_pace, easy_pace + 60),
                target_hr_range=easy_hr,
                notes="Easy jog to recover",
            )
        )

        return StructuredWorkout.create(
            name="Fartlek Run",
            description="Speed play with varied intensity surges",
            intervals=intervals,
            estimated_load=duration_min * 1.1,
        )


# Singleton instance
_workout_agent: Optional[WorkoutDesignAgent] = None


def get_workout_agent() -> WorkoutDesignAgent:
    """Get the workout design agent singleton."""
    global _workout_agent
    if _workout_agent is None:
        _workout_agent = WorkoutDesignAgent()
    return _workout_agent
