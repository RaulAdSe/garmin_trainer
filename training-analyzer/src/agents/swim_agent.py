"""
Swimming Workout Design Agent for AI-powered swim workout creation.

Uses LLM to generate personalized structured swim workouts based on
athlete context, CSS, swim zones, and workout goals.
"""

from typing import List, Optional

from ..models.workouts import (
    IntensityZone,
    IntervalType,
    PoolLength,
    StructuredWorkout,
    SwimAthleteContext,
    SwimStrokeType,
    SwimWorkoutInterval,
    WorkoutSport,
)
from ..llm.providers import LLMClient, get_llm_client


# Common swim drills by stroke
SWIM_DRILLS = {
    SwimStrokeType.FREESTYLE: [
        ("Catch-up", "Touch hands before next stroke, focus on catch"),
        ("Fingertip Drag", "Drag fingertips along water surface, high elbow recovery"),
        ("Fist Drill", "Swim with closed fists, focus on forearm catch"),
        ("Single Arm", "One arm at a time, other extended"),
        ("6-3-6", "6 kicks on side, 3 strokes, 6 kicks on other side"),
        ("Tarzan", "Head up freestyle, focus on high elbow catch"),
        ("Zipper", "Thumb traces from hip to armpit during recovery"),
    ],
    SwimStrokeType.BACKSTROKE: [
        ("Single Arm", "One arm at a time, other at side"),
        ("Double Arm", "Both arms pull simultaneously"),
        ("Catch-up", "Wait for arm to finish before starting other"),
        ("Rotation Drill", "Exaggerate body rotation"),
    ],
    SwimStrokeType.BREASTSTROKE: [
        ("2-Kick 1-Pull", "Two kicks per arm pull"),
        ("Streamline Kick", "Kick only, arms extended"),
        ("Separation Drill", "Pause between pull and kick"),
        ("Pull with Fly Kick", "Breaststroke arms, dolphin kick"),
    ],
    SwimStrokeType.BUTTERFLY: [
        ("Single Arm", "One arm at a time"),
        ("3-3-3", "3 right, 3 left, 3 both"),
        ("Fly Kick on Back", "Kick only, on back"),
        ("Rhythm Drill", "Focus on 2-beat kick timing"),
    ],
}


class SwimWorkoutAgent:
    """
    AI agent for designing structured swim workouts.

    Uses athlete context (CSS, swim zones, preferences)
    to generate appropriate workout structures with pace targets.
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """Initialize the swim workout design agent."""
        self._llm_client = llm_client

    @property
    def llm(self) -> LLMClient:
        """Get LLM client, creating if needed."""
        if self._llm_client is None:
            self._llm_client = get_llm_client()
        return self._llm_client

    def design_workout(
        self,
        workout_type: str,
        duration_min: int,
        context: SwimAthleteContext,
    ) -> StructuredWorkout:
        """
        Design a structured swim workout using rule-based logic.

        Args:
            workout_type: Type of workout (endurance, threshold, speed, drill, etc.)
            duration_min: Duration in minutes
            context: Athlete's swim context

        Returns:
            A complete StructuredWorkout ready for execution
        """
        workout_type = workout_type.lower().replace(" ", "_")

        # Route to appropriate workout designer
        designers = {
            "endurance": self._design_endurance,
            "aerobic": self._design_endurance,
            "threshold": self._design_threshold,
            "css": self._design_threshold,
            "speed": self._design_speed,
            "sprint": self._design_speed,
            "drill": self._design_drill_focus,
            "technique": self._design_drill_focus,
            "mixed": self._design_mixed,
            "pyramid": self._design_pyramid,
            "descending": self._design_descending,
            "broken": self._design_broken_swim,
            "test": self._design_css_test,
            "css_test": self._design_css_test,
            "recovery": self._design_recovery,
            "easy": self._design_recovery,
        }

        designer = designers.get(workout_type, self._design_mixed)
        return designer(duration_min, context)

    def _get_pool_length(self, context: SwimAthleteContext) -> int:
        """Get pool length in meters."""
        if context.preferred_pool_length == PoolLength.LCM:
            return 50
        return 25  # Default to SCM

    def _format_set(
        self,
        reps: int,
        distance_m: int,
        interval_sec: int,
        description: str,
    ) -> str:
        """Format a swim set description."""
        interval_min = interval_sec // 60
        interval_remaining = interval_sec % 60
        if interval_remaining == 0:
            interval_str = f"{interval_min}:00"
        else:
            interval_str = f"{interval_min}:{interval_remaining:02d}"
        return f"{reps}x{distance_m}m @ {interval_str} - {description}"

    # ========================================================================
    # Workout Design Templates
    # ========================================================================

    def _design_endurance(
        self,
        duration_min: int,
        context: SwimAthleteContext,
    ) -> StructuredWorkout:
        """
        Aerobic endurance swim: Zone 2 pace.

        Focus on building aerobic base with steady-state swimming.
        """
        css = context.css_pace
        pool_length = self._get_pool_length(context)

        # Zone 2 pace: 105-115% of CSS
        z2_pace = int(css * 1.10)

        # Calculate main set distance based on duration
        # Assume ~2min per 100m at Z2 pace, plus rest
        available_min = duration_min - 15  # Warmup and cooldown
        main_distance = int(available_min * 50)  # ~50m per minute at easy pace

        intervals: List[SwimWorkoutInterval] = []

        # Warmup: 400m mixed
        intervals.append(
            SwimWorkoutInterval(
                type=IntervalType.WARMUP,
                distance_m=200,
                target_pace_per_100m=(int(css * 1.30), int(css * 1.40)),
                stroke_type=SwimStrokeType.FREESTYLE,
                notes="Easy freestyle, focus on smooth technique",
            )
        )
        intervals.append(
            SwimWorkoutInterval(
                type=IntervalType.WARMUP,
                distance_m=100,
                target_pace_per_100m=(int(css * 1.25), int(css * 1.35)),
                stroke_type=SwimStrokeType.MIXED,
                notes="Choice stroke or IM",
            )
        )
        intervals.append(
            SwimWorkoutInterval(
                type=IntervalType.WARMUP,
                distance_m=100,
                target_pace_per_100m=(int(css * 1.15), int(css * 1.25)),
                stroke_type=SwimStrokeType.FREESTYLE,
                notes="Build to Z2 pace",
            )
        )

        # Main set: Continuous swims at Z2
        set_distance = min(400, main_distance // 3)
        num_sets = max(3, main_distance // set_distance)

        for i in range(num_sets):
            intervals.append(
                SwimWorkoutInterval(
                    type=IntervalType.WORK,
                    distance_m=set_distance,
                    target_pace_per_100m=(int(css * 1.05), int(css * 1.15)),
                    stroke_type=SwimStrokeType.FREESTYLE,
                    notes=f"Set {i+1}/{num_sets}: {context.format_swim_pace(z2_pace)} pace",
                    intensity_zone=IntensityZone.AEROBIC,
                )
            )
            if i < num_sets - 1:
                intervals.append(
                    SwimWorkoutInterval(
                        type=IntervalType.REST,
                        duration_sec=20,
                        notes="20sec rest",
                    )
                )

        # Cooldown: 200m easy
        intervals.append(
            SwimWorkoutInterval(
                type=IntervalType.COOLDOWN,
                distance_m=200,
                target_pace_per_100m=(int(css * 1.30), int(css * 1.50)),
                stroke_type=SwimStrokeType.MIXED,
                notes="Easy choice stroke cooldown",
            )
        )

        total_distance = sum(i.distance_m or 0 for i in intervals)

        return StructuredWorkout.create(
            name="Aerobic Endurance",
            description=f"Zone 2 endurance swim: {total_distance}m at {context.format_swim_pace(z2_pace)}",
            intervals=intervals,
            sport=WorkoutSport.SWIMMING,
            estimated_load=duration_min * 0.7,
        )

    def _design_threshold(
        self,
        duration_min: int,
        context: SwimAthleteContext,
    ) -> StructuredWorkout:
        """
        CSS/Threshold swim: Zone 3 pace.

        Sustained efforts at or near CSS to improve lactate threshold.
        """
        css = context.css_pace
        pool_length = self._get_pool_length(context)

        intervals: List[SwimWorkoutInterval] = []

        # Warmup: 600m progressive
        intervals.extend([
            SwimWorkoutInterval(
                type=IntervalType.WARMUP,
                distance_m=200,
                stroke_type=SwimStrokeType.FREESTYLE,
                notes="Easy freestyle",
            ),
            SwimWorkoutInterval(
                type=IntervalType.WARMUP,
                distance_m=200,
                stroke_type=SwimStrokeType.MIXED,
                is_drill=True,
                drill_name="Catch-up Drill",
                notes="200m drill: 50 catch-up, 50 fingertip drag x2",
            ),
            SwimWorkoutInterval(
                type=IntervalType.WARMUP,
                distance_m=200,
                target_pace_per_100m=(int(css * 1.05), int(css * 1.15)),
                stroke_type=SwimStrokeType.FREESTYLE,
                notes="Build to threshold pace",
            ),
        ])

        # Main set: 5-8 x 200m at CSS
        available_min = duration_min - 20
        num_reps = max(4, min(8, available_min // 5))  # ~5min per 200m with rest

        for i in range(num_reps):
            intervals.append(
                SwimWorkoutInterval(
                    type=IntervalType.WORK,
                    distance_m=200,
                    target_pace_per_100m=(int(css * 0.98), int(css * 1.02)),
                    stroke_type=SwimStrokeType.FREESTYLE,
                    notes=f"Threshold {i+1}/{num_reps}: hold {context.format_swim_pace(css)}",
                    intensity_zone=IntensityZone.THRESHOLD,
                )
            )
            if i < num_reps - 1:
                intervals.append(
                    SwimWorkoutInterval(
                        type=IntervalType.REST,
                        duration_sec=30,
                        notes="30sec rest - recover for next rep",
                    )
                )

        # Cooldown: 300m
        intervals.extend([
            SwimWorkoutInterval(
                type=IntervalType.COOLDOWN,
                distance_m=200,
                stroke_type=SwimStrokeType.FREESTYLE,
                notes="Easy freestyle",
            ),
            SwimWorkoutInterval(
                type=IntervalType.COOLDOWN,
                distance_m=100,
                stroke_type=SwimStrokeType.BACKSTROKE,
                notes="Easy backstroke",
            ),
        ])

        total_distance = sum(i.distance_m or 0 for i in intervals)

        return StructuredWorkout.create(
            name="CSS Threshold",
            description=f"{num_reps}x200m at CSS ({context.format_swim_pace(css)}). Total: {total_distance}m",
            intervals=intervals,
            sport=WorkoutSport.SWIMMING,
            estimated_load=duration_min * 1.0,
        )

    def _design_speed(
        self,
        duration_min: int,
        context: SwimAthleteContext,
    ) -> StructuredWorkout:
        """
        Speed/Sprint workout: Zone 4-5 pace.

        Short, fast repeats with ample recovery for neuromuscular development.
        """
        css = context.css_pace
        sprint_pace = context.sprint_pace or int(css * 0.80)

        intervals: List[SwimWorkoutInterval] = []

        # Warmup: 600m with speed prep
        intervals.extend([
            SwimWorkoutInterval(
                type=IntervalType.WARMUP,
                distance_m=300,
                stroke_type=SwimStrokeType.FREESTYLE,
                notes="Easy freestyle",
            ),
            SwimWorkoutInterval(
                type=IntervalType.WARMUP,
                distance_m=200,
                is_drill=True,
                stroke_type=SwimStrokeType.FREESTYLE,
                notes="200m: 50 drill / 50 swim",
            ),
            SwimWorkoutInterval(
                type=IntervalType.WARMUP,
                distance_m=100,
                target_pace_per_100m=(int(css * 0.95), int(css * 1.05)),
                stroke_type=SwimStrokeType.FREESTYLE,
                notes="4x25m build to fast (10sec rest)",
                repetitions=4,
            ),
        ])

        # Main set: 8-12 x 50m fast with long rest
        num_reps = 10

        for i in range(num_reps):
            intervals.append(
                SwimWorkoutInterval(
                    type=IntervalType.WORK,
                    distance_m=50,
                    target_pace_per_100m=(int(css * 0.80), int(css * 0.90)),
                    stroke_type=SwimStrokeType.FREESTYLE,
                    notes=f"Sprint {i+1}/{num_reps}: FAST! Target {context.format_swim_pace(sprint_pace)}",
                    intensity_zone=IntensityZone.VO2MAX,
                )
            )
            intervals.append(
                SwimWorkoutInterval(
                    type=IntervalType.REST,
                    duration_sec=30,
                    notes="30sec full recovery",
                )
            )

        # Secondary set: 4 x 100m descending
        intervals.append(
            SwimWorkoutInterval(
                type=IntervalType.WORK,
                distance_m=100,
                target_pace_per_100m=(int(css * 1.00), int(css * 1.10)),
                stroke_type=SwimStrokeType.FREESTYLE,
                notes="4x100m descending 1-4 (20sec rest)",
                repetitions=4,
                intensity_zone=IntensityZone.THRESHOLD,
            )
        )

        # Cooldown
        intervals.append(
            SwimWorkoutInterval(
                type=IntervalType.COOLDOWN,
                distance_m=300,
                stroke_type=SwimStrokeType.MIXED,
                notes="Easy mixed stroke cooldown",
            )
        )

        total_distance = sum((i.distance_m or 0) * i.repetitions for i in intervals)

        return StructuredWorkout.create(
            name="Speed Work",
            description=f"{num_reps}x50m sprints + 4x100m descending. Total: {total_distance}m",
            intervals=intervals,
            sport=WorkoutSport.SWIMMING,
            estimated_load=duration_min * 1.1,
        )

    def _design_drill_focus(
        self,
        duration_min: int,
        context: SwimAthleteContext,
    ) -> StructuredWorkout:
        """
        Technique/Drill-focused workout.

        Emphasis on drill work with swim integration.
        """
        css = context.css_pace
        stroke = context.preferred_stroke
        drills = SWIM_DRILLS.get(stroke, SWIM_DRILLS[SwimStrokeType.FREESTYLE])

        intervals: List[SwimWorkoutInterval] = []

        # Warmup
        intervals.append(
            SwimWorkoutInterval(
                type=IntervalType.WARMUP,
                distance_m=300,
                stroke_type=SwimStrokeType.MIXED,
                notes="Easy mixed warm-up",
            )
        )

        # Drill sets with swim integration
        for i, (drill_name, drill_desc) in enumerate(drills[:4]):
            # Drill
            intervals.append(
                SwimWorkoutInterval(
                    type=IntervalType.WORK,
                    distance_m=50,
                    stroke_type=stroke,
                    is_drill=True,
                    drill_name=drill_name,
                    notes=f"Drill: {drill_name} - {drill_desc}",
                    repetitions=2,
                )
            )
            # Swim with focus
            intervals.append(
                SwimWorkoutInterval(
                    type=IntervalType.WORK,
                    distance_m=100,
                    stroke_type=stroke,
                    target_pace_per_100m=(int(css * 1.10), int(css * 1.20)),
                    notes=f"Swim focusing on {drill_name} feeling",
                )
            )
            intervals.append(
                SwimWorkoutInterval(
                    type=IntervalType.REST,
                    duration_sec=20,
                    notes="20sec rest",
                )
            )

        # Main swim set with technique focus
        intervals.append(
            SwimWorkoutInterval(
                type=IntervalType.WORK,
                distance_m=200,
                stroke_type=SwimStrokeType.FREESTYLE,
                target_pace_per_100m=(int(css * 1.05), int(css * 1.15)),
                target_swolf=55,
                notes="4x200m with focus on SWOLF efficiency (20sec rest)",
                repetitions=4,
                intensity_zone=IntensityZone.AEROBIC,
            )
        )

        # Cooldown
        intervals.append(
            SwimWorkoutInterval(
                type=IntervalType.COOLDOWN,
                distance_m=200,
                stroke_type=SwimStrokeType.BACKSTROKE,
                notes="Easy backstroke cooldown",
            )
        )

        total_distance = sum((i.distance_m or 0) * i.repetitions for i in intervals)

        return StructuredWorkout.create(
            name="Technique Focus",
            description=f"Drill-focused workout with stroke integration. Total: {total_distance}m",
            intervals=intervals,
            sport=WorkoutSport.SWIMMING,
            estimated_load=duration_min * 0.6,
        )

    def _design_mixed(
        self,
        duration_min: int,
        context: SwimAthleteContext,
    ) -> StructuredWorkout:
        """
        Mixed workout: variety of intensities and strokes.

        Good all-around swim workout for general fitness.
        """
        css = context.css_pace

        intervals: List[SwimWorkoutInterval] = []

        # Warmup: 400m
        intervals.extend([
            SwimWorkoutInterval(
                type=IntervalType.WARMUP,
                distance_m=200,
                stroke_type=SwimStrokeType.FREESTYLE,
                notes="Easy freestyle",
            ),
            SwimWorkoutInterval(
                type=IntervalType.WARMUP,
                distance_m=100,
                stroke_type=SwimStrokeType.BACKSTROKE,
                notes="Easy backstroke",
            ),
            SwimWorkoutInterval(
                type=IntervalType.WARMUP,
                distance_m=100,
                is_drill=True,
                stroke_type=SwimStrokeType.FREESTYLE,
                notes="Drill choice",
            ),
        ])

        # Set 1: Pull set (with pull buoy)
        intervals.append(
            SwimWorkoutInterval(
                type=IntervalType.WORK,
                distance_m=200,
                stroke_type=SwimStrokeType.FREESTYLE,
                target_pace_per_100m=(int(css * 1.05), int(css * 1.15)),
                equipment=["pull_buoy"],
                notes="4x200m pull (15sec rest)",
                repetitions=4,
                intensity_zone=IntensityZone.AEROBIC,
            )
        )

        # Set 2: Threshold 100s
        intervals.append(
            SwimWorkoutInterval(
                type=IntervalType.WORK,
                distance_m=100,
                stroke_type=SwimStrokeType.FREESTYLE,
                target_pace_per_100m=(int(css * 0.98), int(css * 1.02)),
                notes="6x100m at CSS (15sec rest)",
                repetitions=6,
                intensity_zone=IntensityZone.THRESHOLD,
            )
        )

        # Set 3: Fast 50s
        intervals.append(
            SwimWorkoutInterval(
                type=IntervalType.WORK,
                distance_m=50,
                stroke_type=SwimStrokeType.FREESTYLE,
                target_pace_per_100m=(int(css * 0.85), int(css * 0.95)),
                notes="4x50m fast (20sec rest)",
                repetitions=4,
                intensity_zone=IntensityZone.VO2MAX,
            )
        )

        # Cooldown
        intervals.append(
            SwimWorkoutInterval(
                type=IntervalType.COOLDOWN,
                distance_m=200,
                stroke_type=SwimStrokeType.MIXED,
                notes="Easy mixed cooldown",
            )
        )

        total_distance = sum((i.distance_m or 0) * i.repetitions for i in intervals)

        return StructuredWorkout.create(
            name="Mixed Swim",
            description=f"Variety workout: pull, threshold, speed. Total: {total_distance}m",
            intervals=intervals,
            sport=WorkoutSport.SWIMMING,
            estimated_load=duration_min * 0.85,
        )

    def _design_pyramid(
        self,
        duration_min: int,
        context: SwimAthleteContext,
    ) -> StructuredWorkout:
        """
        Pyramid set: ascending then descending distances.

        Classic swim workout for pacing and mental challenge.
        """
        css = context.css_pace

        intervals: List[SwimWorkoutInterval] = []

        # Warmup
        intervals.append(
            SwimWorkoutInterval(
                type=IntervalType.WARMUP,
                distance_m=400,
                stroke_type=SwimStrokeType.MIXED,
                notes="400m easy mixed (100 free, 100 back, 100 free, 100 choice)",
            )
        )

        # Pyramid: 50-100-150-200-150-100-50
        pyramid_distances = [50, 100, 150, 200, 150, 100, 50]

        for i, distance in enumerate(pyramid_distances):
            # Adjust pace based on distance (shorter = faster)
            if distance <= 50:
                pace_mult = 0.90
                zone = IntensityZone.VO2MAX
            elif distance <= 100:
                pace_mult = 0.95
                zone = IntensityZone.THRESHOLD
            else:
                pace_mult = 1.00
                zone = IntensityZone.THRESHOLD

            intervals.append(
                SwimWorkoutInterval(
                    type=IntervalType.WORK,
                    distance_m=distance,
                    stroke_type=SwimStrokeType.FREESTYLE,
                    target_pace_per_100m=(int(css * (pace_mult - 0.03)), int(css * pace_mult)),
                    notes=f"Pyramid {i+1}/7: {distance}m",
                    intensity_zone=zone,
                )
            )
            if i < len(pyramid_distances) - 1:
                rest_sec = 10 + (distance // 50) * 5  # Rest scales with distance
                intervals.append(
                    SwimWorkoutInterval(
                        type=IntervalType.REST,
                        duration_sec=rest_sec,
                        notes=f"{rest_sec}sec rest",
                    )
                )

        # Cooldown
        intervals.append(
            SwimWorkoutInterval(
                type=IntervalType.COOLDOWN,
                distance_m=300,
                stroke_type=SwimStrokeType.MIXED,
                notes="Easy cooldown",
            )
        )

        total_distance = sum((i.distance_m or 0) for i in intervals)

        return StructuredWorkout.create(
            name="Pyramid Set",
            description=f"50-100-150-200-150-100-50 pyramid at CSS. Total: {total_distance}m",
            intervals=intervals,
            sport=WorkoutSport.SWIMMING,
            estimated_load=duration_min * 0.9,
        )

    def _design_descending(
        self,
        duration_min: int,
        context: SwimAthleteContext,
    ) -> StructuredWorkout:
        """
        Descending set: getting faster each repeat.

        Teaches pacing and negative splitting.
        """
        css = context.css_pace

        intervals: List[SwimWorkoutInterval] = []

        # Warmup
        intervals.append(
            SwimWorkoutInterval(
                type=IntervalType.WARMUP,
                distance_m=500,
                stroke_type=SwimStrokeType.MIXED,
                notes="500m easy mixed",
            )
        )

        # Main set: 3 rounds of descending 4x100
        for round_num in range(3):
            paces = [1.15, 1.10, 1.05, 1.00]  # Descending multipliers
            for i, pace_mult in enumerate(paces):
                intervals.append(
                    SwimWorkoutInterval(
                        type=IntervalType.WORK,
                        distance_m=100,
                        stroke_type=SwimStrokeType.FREESTYLE,
                        target_pace_per_100m=(int(css * (pace_mult - 0.03)), int(css * pace_mult)),
                        notes=f"Round {round_num+1}, Rep {i+1}/4: descend to {context.format_swim_pace(int(css * pace_mult))}",
                        intensity_zone=IntensityZone.THRESHOLD if pace_mult <= 1.05 else IntensityZone.AEROBIC,
                    )
                )
                intervals.append(
                    SwimWorkoutInterval(
                        type=IntervalType.REST,
                        duration_sec=15,
                        notes="15sec rest",
                    )
                )

            # Extra rest between rounds
            if round_num < 2:
                intervals.append(
                    SwimWorkoutInterval(
                        type=IntervalType.REST,
                        duration_sec=60,
                        notes="60sec rest between rounds",
                    )
                )

        # Cooldown
        intervals.append(
            SwimWorkoutInterval(
                type=IntervalType.COOLDOWN,
                distance_m=300,
                stroke_type=SwimStrokeType.BACKSTROKE,
                notes="Easy backstroke cooldown",
            )
        )

        total_distance = sum((i.distance_m or 0) for i in intervals)

        return StructuredWorkout.create(
            name="Descending Set",
            description=f"3 rounds of 4x100m descending 1-4. Total: {total_distance}m",
            intervals=intervals,
            sport=WorkoutSport.SWIMMING,
            estimated_load=duration_min * 0.85,
        )

    def _design_broken_swim(
        self,
        duration_min: int,
        context: SwimAthleteContext,
    ) -> StructuredWorkout:
        """
        Broken swim: race-pace segments with short rest.

        Simulates race effort while allowing recovery.
        """
        css = context.css_pace
        race_pace = int(css * 0.95)

        intervals: List[SwimWorkoutInterval] = []

        # Warmup
        intervals.extend([
            SwimWorkoutInterval(
                type=IntervalType.WARMUP,
                distance_m=400,
                stroke_type=SwimStrokeType.FREESTYLE,
                notes="Easy freestyle",
            ),
            SwimWorkoutInterval(
                type=IntervalType.WARMUP,
                distance_m=200,
                stroke_type=SwimStrokeType.FREESTYLE,
                target_pace_per_100m=(int(css * 0.95), int(css * 1.05)),
                notes="4x50m build to race pace (10sec rest)",
                repetitions=4,
            ),
        ])

        # Main set: 3 x broken 400 (4x100 with 10sec rest)
        for broken_num in range(3):
            for segment in range(4):
                intervals.append(
                    SwimWorkoutInterval(
                        type=IntervalType.WORK,
                        distance_m=100,
                        stroke_type=SwimStrokeType.FREESTYLE,
                        target_pace_per_100m=(int(css * 0.93), int(css * 0.97)),
                        notes=f"Broken 400 #{broken_num+1} - segment {segment+1}/4: race pace!",
                        intensity_zone=IntensityZone.THRESHOLD,
                    )
                )
                intervals.append(
                    SwimWorkoutInterval(
                        type=IntervalType.REST,
                        duration_sec=10,
                        notes="10sec rest (just touch wall, quick breath)",
                    )
                )

            # Rest between broken swims
            if broken_num < 2:
                intervals.append(
                    SwimWorkoutInterval(
                        type=IntervalType.REST,
                        duration_sec=120,
                        notes="2min rest between broken 400s",
                    )
                )

        # Cooldown
        intervals.append(
            SwimWorkoutInterval(
                type=IntervalType.COOLDOWN,
                distance_m=400,
                stroke_type=SwimStrokeType.MIXED,
                notes="Extended easy cooldown",
            )
        )

        total_distance = sum((i.distance_m or 0) for i in intervals)

        return StructuredWorkout.create(
            name="Broken 400s",
            description=f"3 x Broken 400m at race pace. Total: {total_distance}m",
            intervals=intervals,
            sport=WorkoutSport.SWIMMING,
            estimated_load=duration_min * 1.1,
        )

    def _design_css_test(
        self,
        duration_min: int,
        context: SwimAthleteContext,
    ) -> StructuredWorkout:
        """
        CSS test workout: 400m and 200m time trials.

        Used to calculate Critical Swim Speed.
        """
        intervals: List[SwimWorkoutInterval] = []

        # Warmup: 800m progressive
        intervals.extend([
            SwimWorkoutInterval(
                type=IntervalType.WARMUP,
                distance_m=400,
                stroke_type=SwimStrokeType.FREESTYLE,
                notes="Easy freestyle warmup",
            ),
            SwimWorkoutInterval(
                type=IntervalType.WARMUP,
                distance_m=200,
                stroke_type=SwimStrokeType.FREESTYLE,
                notes="6x50m: 25 drill / 25 swim (15sec rest)",
                repetitions=4,
            ),
            SwimWorkoutInterval(
                type=IntervalType.WARMUP,
                distance_m=200,
                stroke_type=SwimStrokeType.FREESTYLE,
                notes="4x50m build to fast (10sec rest)",
                repetitions=4,
            ),
        ])

        # Rest before test
        intervals.append(
            SwimWorkoutInterval(
                type=IntervalType.REST,
                duration_sec=180,
                notes="3min rest - prepare for 400m TT",
            )
        )

        # Test 1: 400m time trial
        intervals.append(
            SwimWorkoutInterval(
                type=IntervalType.WORK,
                distance_m=400,
                stroke_type=SwimStrokeType.FREESTYLE,
                notes="400m TIME TRIAL - MAX EFFORT! Even pacing!",
                intensity_zone=IntensityZone.THRESHOLD,
            )
        )

        # Recovery between tests
        intervals.append(
            SwimWorkoutInterval(
                type=IntervalType.RECOVERY,
                duration_sec=420,  # 7 minutes
                distance_m=200,
                stroke_type=SwimStrokeType.BACKSTROKE,
                notes="7min recovery: 200m easy backstroke + rest",
            )
        )

        # Test 2: 200m time trial
        intervals.append(
            SwimWorkoutInterval(
                type=IntervalType.WORK,
                distance_m=200,
                stroke_type=SwimStrokeType.FREESTYLE,
                notes="200m TIME TRIAL - FASTER than 400m pace!",
                intensity_zone=IntensityZone.VO2MAX,
            )
        )

        # Cooldown
        intervals.append(
            SwimWorkoutInterval(
                type=IntervalType.COOLDOWN,
                distance_m=400,
                stroke_type=SwimStrokeType.MIXED,
                notes="Extended easy cooldown",
            )
        )

        return StructuredWorkout.create(
            name="CSS Test",
            description="400m + 200m time trials for CSS calculation",
            intervals=intervals,
            sport=WorkoutSport.SWIMMING,
            estimated_load=85.0,
        )

    def _design_recovery(
        self,
        duration_min: int,
        context: SwimAthleteContext,
    ) -> StructuredWorkout:
        """
        Easy recovery swim: Zone 1 pace.

        Active recovery with focus on technique.
        """
        css = context.css_pace

        intervals: List[SwimWorkoutInterval] = []

        # Continuous easy swimming with variety
        intervals.extend([
            SwimWorkoutInterval(
                type=IntervalType.WORK,
                distance_m=200,
                stroke_type=SwimStrokeType.FREESTYLE,
                target_pace_per_100m=(int(css * 1.25), int(css * 1.40)),
                notes="Easy freestyle - focus on long strokes",
                intensity_zone=IntensityZone.RECOVERY,
            ),
            SwimWorkoutInterval(
                type=IntervalType.WORK,
                distance_m=200,
                stroke_type=SwimStrokeType.BACKSTROKE,
                notes="Easy backstroke",
                intensity_zone=IntensityZone.RECOVERY,
            ),
            SwimWorkoutInterval(
                type=IntervalType.WORK,
                distance_m=200,
                stroke_type=SwimStrokeType.FREESTYLE,
                is_drill=True,
                notes="Drill choice - technique focus",
                intensity_zone=IntensityZone.RECOVERY,
            ),
            SwimWorkoutInterval(
                type=IntervalType.WORK,
                distance_m=200,
                stroke_type=SwimStrokeType.MIXED,
                notes="Choice stroke - stay relaxed",
                intensity_zone=IntensityZone.RECOVERY,
            ),
            SwimWorkoutInterval(
                type=IntervalType.WORK,
                distance_m=200,
                stroke_type=SwimStrokeType.FREESTYLE,
                equipment=["pull_buoy"],
                notes="Easy pull - focus on catch",
                intensity_zone=IntensityZone.RECOVERY,
            ),
        ])

        total_distance = sum((i.distance_m or 0) for i in intervals)

        return StructuredWorkout.create(
            name="Recovery Swim",
            description=f"Easy recovery swim with variety. Total: {total_distance}m",
            intervals=intervals,
            sport=WorkoutSport.SWIMMING,
            estimated_load=duration_min * 0.4,
        )


# Singleton instance
_swim_agent: Optional[SwimWorkoutAgent] = None


def get_swim_agent() -> SwimWorkoutAgent:
    """Get the swim workout agent singleton."""
    global _swim_agent
    if _swim_agent is None:
        _swim_agent = SwimWorkoutAgent()
    return _swim_agent

