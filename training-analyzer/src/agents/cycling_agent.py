"""
Cycling Workout Design Agent for AI-powered cycling workout creation.

Uses LLM to generate personalized structured cycling workouts based on
athlete context, FTP, power zones, and workout goals.
"""

import json
import re
from typing import Any, Dict, List, Optional

from ..models.workouts import (
    IntensityZone,
    IntervalType,
    StructuredWorkout,
    WorkoutInterval,
    WorkoutSport,
)
from ..metrics.power import calculate_power_zones, get_power_zone_names
from ..llm.providers import LLMClient, ModelType, get_llm_client


class CyclingAthleteContext:
    """
    Cycling-specific athlete context for personalized workout design.

    Contains FTP, power zones, and cycling-specific fitness metrics.
    """

    def __init__(
        self,
        ftp: int = 200,
        max_hr: int = 185,
        rest_hr: int = 55,
        lthr: int = 165,
        ctl: float = 40.0,
        atl: float = 40.0,
        tsb: float = 0.0,
        readiness_score: int = 75,
        weight_kg: Optional[float] = None,
    ):
        self.ftp = ftp
        self.max_hr = max_hr
        self.rest_hr = rest_hr
        self.lthr = lthr
        self.ctl = ctl
        self.atl = atl
        self.tsb = tsb
        self.readiness_score = readiness_score
        self.weight_kg = weight_kg

        # Calculate power zones from FTP
        self._power_zones = calculate_power_zones(ftp)
        self._zone_names = get_power_zone_names()

    @property
    def power_zones(self) -> Dict[int, tuple]:
        """Get power zones based on FTP."""
        return self._power_zones

    def get_power_zone_range(self, zone: int) -> tuple:
        """Get power range for a zone (1-7)."""
        return self._power_zones.get(zone, (0, 0))

    def get_hr_zone_range(self, zone: int) -> tuple:
        """Get HR range for a zone (1-5) using Karvonen method."""
        hr_reserve = self.max_hr - self.rest_hr
        zone_boundaries = [
            (0.50, 0.60),  # Zone 1
            (0.60, 0.70),  # Zone 2
            (0.70, 0.80),  # Zone 3
            (0.80, 0.90),  # Zone 4
            (0.90, 1.00),  # Zone 5
        ]
        if 1 <= zone <= 5:
            low_pct, high_pct = zone_boundaries[zone - 1]
            return (
                int(self.rest_hr + hr_reserve * low_pct),
                int(self.rest_hr + hr_reserve * high_pct),
            )
        return (self.rest_hr, self.max_hr)

    def get_power_to_weight(self) -> Optional[float]:
        """Get FTP power-to-weight ratio if weight is known."""
        if self.weight_kg and self.weight_kg > 0:
            return round(self.ftp / self.weight_kg, 2)
        return None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "ftp": self.ftp,
            "max_hr": self.max_hr,
            "rest_hr": self.rest_hr,
            "lthr": self.lthr,
            "ctl": self.ctl,
            "atl": self.atl,
            "tsb": self.tsb,
            "readiness_score": self.readiness_score,
            "weight_kg": self.weight_kg,
            "power_to_weight": self.get_power_to_weight(),
            "power_zones": {
                f"zone{z}": {
                    "name": self._zone_names[z],
                    "range": self._power_zones[z],
                }
                for z in range(1, 8)
            },
        }


class CyclingWorkoutInterval(WorkoutInterval):
    """
    Cycling-specific workout interval with power and cadence targets.

    Extends WorkoutInterval with cycling-specific attributes.
    """

    def __init__(
        self,
        type: IntervalType,
        duration_sec: Optional[int] = None,
        distance_m: Optional[int] = None,
        target_power_range: Optional[tuple] = None,  # (min, max) watts
        target_power_pct_ftp: Optional[tuple] = None,  # (min, max) % of FTP
        target_cadence_range: Optional[tuple] = None,  # (min, max) rpm
        target_hr_range: Optional[tuple] = None,
        erg_mode: bool = False,  # ERG mode (fixed power)
        erg_power: Optional[int] = None,  # Target power for ERG mode
        repetitions: int = 1,
        notes: Optional[str] = None,
        intensity_zone: Optional[IntensityZone] = None,
    ):
        super().__init__(
            type=type,
            duration_sec=duration_sec,
            distance_m=distance_m,
            target_hr_range=target_hr_range,
            repetitions=repetitions,
            notes=notes,
            intensity_zone=intensity_zone,
        )
        self.target_power_range = target_power_range
        self.target_power_pct_ftp = target_power_pct_ftp
        self.target_cadence_range = target_cadence_range
        self.erg_mode = erg_mode
        self.erg_power = erg_power

    def get_power_range_from_ftp(self, ftp: int) -> Optional[tuple]:
        """Calculate absolute power range from FTP percentage."""
        if self.target_power_pct_ftp:
            low_pct, high_pct = self.target_power_pct_ftp
            return (int(ftp * low_pct / 100), int(ftp * high_pct / 100))
        return self.target_power_range

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        base_dict = super().to_dict()
        base_dict.update({
            "target_power_range": list(self.target_power_range) if self.target_power_range else None,
            "target_power_pct_ftp": list(self.target_power_pct_ftp) if self.target_power_pct_ftp else None,
            "target_cadence_range": list(self.target_cadence_range) if self.target_cadence_range else None,
            "erg_mode": self.erg_mode,
            "erg_power": self.erg_power,
        })
        return base_dict


class CyclingWorkoutAgent:
    """
    AI agent for designing structured cycling workouts.

    Uses athlete context (FTP, power zones, fitness metrics)
    to generate appropriate workout structures with power targets.
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """Initialize the cycling workout design agent."""
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
        context: CyclingAthleteContext,
    ) -> StructuredWorkout:
        """
        Design a structured cycling workout using rule-based logic.

        Args:
            workout_type: Type of workout (sweet_spot, vo2max, endurance, etc.)
            duration_min: Duration in minutes
            context: Athlete's cycling context

        Returns:
            A complete StructuredWorkout ready for FIT export
        """
        workout_type = workout_type.lower().replace(" ", "_")

        # Route to appropriate workout designer
        designers = {
            "sweet_spot": self._design_sweet_spot,
            "vo2max": self._design_vo2max,
            "vo2_max": self._design_vo2max,
            "endurance": self._design_endurance,
            "recovery": self._design_recovery,
            "threshold": self._design_threshold,
            "over_unders": self._design_over_unders,
            "over_under": self._design_over_unders,
            "tempo": self._design_tempo,
            "sprint": self._design_sprint,
            "ramp": self._design_ramp_test,
            "ramp_test": self._design_ramp_test,
            "ftp_test": self._design_ftp_test,
        }

        designer = designers.get(workout_type, self._design_endurance)
        return designer(duration_min, context)

    # ========================================================================
    # Workout Design Templates
    # ========================================================================

    def _design_sweet_spot(
        self,
        duration_min: int,
        context: CyclingAthleteContext,
    ) -> StructuredWorkout:
        """
        Sweet Spot workout: 88-94% FTP.

        Highly effective for building FTP with less recovery cost than threshold.
        """
        ftp = context.ftp
        ss_low = int(ftp * 0.88)
        ss_high = int(ftp * 0.94)

        # Calculate interval structure based on duration
        warmup_min = 10
        cooldown_min = 5
        available_min = duration_min - warmup_min - cooldown_min

        # Sweet spot intervals: 2-3 x 15-20min or 3-4 x 10-12min
        if available_min >= 45:
            num_intervals = 3
            interval_min = 15
        elif available_min >= 30:
            num_intervals = 2
            interval_min = 15
        else:
            num_intervals = 3
            interval_min = max(8, available_min // 4)

        recovery_min = 5

        intervals = [
            CyclingWorkoutInterval(
                type=IntervalType.WARMUP,
                duration_sec=warmup_min * 60,
                target_power_pct_ftp=(50, 70),
                target_cadence_range=(85, 95),
                notes="Progressive warmup with 3x30s spin-ups",
            ),
        ]

        for i in range(num_intervals):
            intervals.append(
                CyclingWorkoutInterval(
                    type=IntervalType.WORK,
                    duration_sec=interval_min * 60,
                    target_power_range=(ss_low, ss_high),
                    target_power_pct_ftp=(88, 94),
                    target_cadence_range=(85, 95),
                    erg_mode=True,
                    erg_power=int(ftp * 0.91),  # Target 91% FTP
                    notes=f"Sweet Spot {i+1}/{num_intervals}: {ss_low}-{ss_high}W",
                    intensity_zone=IntensityZone.TEMPO,
                )
            )
            if i < num_intervals - 1:
                intervals.append(
                    CyclingWorkoutInterval(
                        type=IntervalType.RECOVERY,
                        duration_sec=recovery_min * 60,
                        target_power_pct_ftp=(40, 55),
                        target_cadence_range=(80, 90),
                        notes="Easy spinning recovery",
                        intensity_zone=IntensityZone.RECOVERY,
                    )
                )

        intervals.append(
            CyclingWorkoutInterval(
                type=IntervalType.COOLDOWN,
                duration_sec=cooldown_min * 60,
                target_power_pct_ftp=(40, 55),
                target_cadence_range=(80, 90),
                notes="Easy spin, gradually decreasing effort",
            )
        )

        return StructuredWorkout.create(
            name="Sweet Spot",
            description=f"{num_intervals}x{interval_min}min at 88-94% FTP ({ss_low}-{ss_high}W)",
            intervals=intervals,
            sport=WorkoutSport.CYCLING,
            estimated_load=duration_min * 0.85,
        )

    def _design_vo2max(
        self,
        duration_min: int,
        context: CyclingAthleteContext,
    ) -> StructuredWorkout:
        """
        VO2max intervals: 106-120% FTP.

        High-intensity intervals to improve aerobic power.
        Typical: 5x3min or 6x4min with equal recovery.
        """
        ftp = context.ftp
        vo2_low = int(ftp * 1.06)
        vo2_high = int(ftp * 1.20)

        warmup_min = 15  # Extended warmup for hard effort
        cooldown_min = 10

        # 3-5min intervals with equal recovery
        interval_min = 3
        recovery_min = 3
        available_min = duration_min - warmup_min - cooldown_min
        num_intervals = max(4, min(8, available_min // (interval_min + recovery_min)))

        intervals = [
            CyclingWorkoutInterval(
                type=IntervalType.WARMUP,
                duration_sec=warmup_min * 60,
                target_power_pct_ftp=(50, 75),
                target_cadence_range=(85, 100),
                notes="Progressive warmup with 3x1min builds to threshold",
            ),
        ]

        for i in range(num_intervals):
            intervals.append(
                CyclingWorkoutInterval(
                    type=IntervalType.WORK,
                    duration_sec=interval_min * 60,
                    target_power_range=(vo2_low, vo2_high),
                    target_power_pct_ftp=(106, 120),
                    target_cadence_range=(95, 110),
                    erg_mode=True,
                    erg_power=int(ftp * 1.12),  # Target 112% FTP
                    notes=f"VO2max {i+1}/{num_intervals}: MAX sustainable effort!",
                    intensity_zone=IntensityZone.VO2MAX,
                )
            )
            if i < num_intervals - 1:
                intervals.append(
                    CyclingWorkoutInterval(
                        type=IntervalType.RECOVERY,
                        duration_sec=recovery_min * 60,
                        target_power_pct_ftp=(40, 50),
                        target_cadence_range=(80, 90),
                        notes="Easy spinning - recover fully before next interval",
                        intensity_zone=IntensityZone.RECOVERY,
                    )
                )

        intervals.append(
            CyclingWorkoutInterval(
                type=IntervalType.COOLDOWN,
                duration_sec=cooldown_min * 60,
                target_power_pct_ftp=(40, 55),
                target_cadence_range=(80, 90),
                notes="Extended cooldown after hard effort",
            )
        )

        return StructuredWorkout.create(
            name="VO2max Intervals",
            description=f"{num_intervals}x{interval_min}min at 106-120% FTP ({vo2_low}-{vo2_high}W)",
            intervals=intervals,
            sport=WorkoutSport.CYCLING,
            estimated_load=duration_min * 1.3,
        )

    def _design_threshold(
        self,
        duration_min: int,
        context: CyclingAthleteContext,
    ) -> StructuredWorkout:
        """
        Threshold workout: 95-105% FTP.

        Sustained efforts at or near FTP to raise threshold power.
        """
        ftp = context.ftp
        threshold_low = int(ftp * 0.95)
        threshold_high = int(ftp * 1.05)

        warmup_min = 15
        cooldown_min = 10
        available_min = duration_min - warmup_min - cooldown_min

        # 2x20min or 3x12min threshold intervals
        if available_min >= 50:
            num_intervals = 2
            interval_min = 20
        elif available_min >= 40:
            num_intervals = 3
            interval_min = 12
        else:
            num_intervals = 2
            interval_min = max(10, available_min // 3)

        recovery_min = 5

        intervals = [
            CyclingWorkoutInterval(
                type=IntervalType.WARMUP,
                duration_sec=warmup_min * 60,
                target_power_pct_ftp=(50, 75),
                target_cadence_range=(85, 95),
                notes="Progressive warmup with openers",
            ),
        ]

        for i in range(num_intervals):
            intervals.append(
                CyclingWorkoutInterval(
                    type=IntervalType.WORK,
                    duration_sec=interval_min * 60,
                    target_power_range=(threshold_low, threshold_high),
                    target_power_pct_ftp=(95, 105),
                    target_cadence_range=(85, 95),
                    erg_mode=True,
                    erg_power=ftp,
                    notes=f"Threshold {i+1}/{num_intervals}: steady at FTP",
                    intensity_zone=IntensityZone.THRESHOLD,
                )
            )
            if i < num_intervals - 1:
                intervals.append(
                    CyclingWorkoutInterval(
                        type=IntervalType.RECOVERY,
                        duration_sec=recovery_min * 60,
                        target_power_pct_ftp=(40, 55),
                        target_cadence_range=(80, 90),
                        notes="Recovery spin",
                        intensity_zone=IntensityZone.RECOVERY,
                    )
                )

        intervals.append(
            CyclingWorkoutInterval(
                type=IntervalType.COOLDOWN,
                duration_sec=cooldown_min * 60,
                target_power_pct_ftp=(40, 55),
                target_cadence_range=(80, 90),
                notes="Easy cooldown",
            )
        )

        return StructuredWorkout.create(
            name="Threshold",
            description=f"{num_intervals}x{interval_min}min at 95-105% FTP",
            intervals=intervals,
            sport=WorkoutSport.CYCLING,
            estimated_load=duration_min * 1.1,
        )

    def _design_over_unders(
        self,
        duration_min: int,
        context: CyclingAthleteContext,
    ) -> StructuredWorkout:
        """
        Over-Under intervals: alternating above and below threshold.

        Develops ability to clear lactate while maintaining high power.
        Typically 2min at 95% / 1min at 105% repeated.
        """
        ftp = context.ftp
        under_power = int(ftp * 0.95)
        over_power = int(ftp * 1.05)

        warmup_min = 15
        cooldown_min = 10
        available_min = duration_min - warmup_min - cooldown_min

        # Each over-under block is typically 9-12 minutes
        block_duration = 9  # 3 cycles of 2min under + 1min over
        num_blocks = max(2, min(4, available_min // (block_duration + 5)))
        recovery_min = 5

        intervals = [
            CyclingWorkoutInterval(
                type=IntervalType.WARMUP,
                duration_sec=warmup_min * 60,
                target_power_pct_ftp=(50, 75),
                target_cadence_range=(85, 95),
                notes="Progressive warmup",
            ),
        ]

        for block in range(num_blocks):
            # 3 over-under cycles per block
            for cycle in range(3):
                # Under (2 minutes at 95%)
                intervals.append(
                    CyclingWorkoutInterval(
                        type=IntervalType.WORK,
                        duration_sec=120,
                        target_power_range=(int(ftp * 0.93), under_power),
                        target_power_pct_ftp=(93, 95),
                        target_cadence_range=(85, 95),
                        erg_mode=True,
                        erg_power=under_power,
                        notes=f"Block {block+1} - UNDER: steady just below threshold",
                        intensity_zone=IntensityZone.THRESHOLD,
                    )
                )
                # Over (1 minute at 105%)
                intervals.append(
                    CyclingWorkoutInterval(
                        type=IntervalType.WORK,
                        duration_sec=60,
                        target_power_range=(over_power, int(ftp * 1.08)),
                        target_power_pct_ftp=(105, 108),
                        target_cadence_range=(90, 100),
                        erg_mode=True,
                        erg_power=over_power,
                        notes=f"Block {block+1} - OVER: push above threshold!",
                        intensity_zone=IntensityZone.THRESHOLD,
                    )
                )

            if block < num_blocks - 1:
                intervals.append(
                    CyclingWorkoutInterval(
                        type=IntervalType.RECOVERY,
                        duration_sec=recovery_min * 60,
                        target_power_pct_ftp=(40, 55),
                        target_cadence_range=(80, 90),
                        notes="Full recovery between blocks",
                        intensity_zone=IntensityZone.RECOVERY,
                    )
                )

        intervals.append(
            CyclingWorkoutInterval(
                type=IntervalType.COOLDOWN,
                duration_sec=cooldown_min * 60,
                target_power_pct_ftp=(40, 55),
                target_cadence_range=(80, 90),
                notes="Easy cooldown",
            )
        )

        return StructuredWorkout.create(
            name="Over-Unders",
            description=f"{num_blocks} blocks of over-under intervals (95%/105% FTP)",
            intervals=intervals,
            sport=WorkoutSport.CYCLING,
            estimated_load=duration_min * 1.15,
        )

    def _design_endurance(
        self,
        duration_min: int,
        context: CyclingAthleteContext,
    ) -> StructuredWorkout:
        """
        Endurance ride: 55-75% FTP (Zone 2).

        Base building aerobic ride. Focus on time in zone.
        """
        ftp = context.ftp
        z2_low = int(ftp * 0.55)
        z2_high = int(ftp * 0.75)

        intervals = [
            CyclingWorkoutInterval(
                type=IntervalType.WARMUP,
                duration_sec=300,
                target_power_pct_ftp=(45, 55),
                target_cadence_range=(80, 90),
                notes="Easy start",
            ),
            CyclingWorkoutInterval(
                type=IntervalType.WORK,
                duration_sec=(duration_min - 10) * 60,
                target_power_range=(z2_low, z2_high),
                target_power_pct_ftp=(55, 75),
                target_cadence_range=(85, 95),
                notes=f"Steady Zone 2: {z2_low}-{z2_high}W. Stay conversational.",
                intensity_zone=IntensityZone.AEROBIC,
            ),
            CyclingWorkoutInterval(
                type=IntervalType.COOLDOWN,
                duration_sec=300,
                target_power_pct_ftp=(40, 55),
                target_cadence_range=(80, 90),
                notes="Easy finish",
            ),
        ]

        return StructuredWorkout.create(
            name="Endurance Ride",
            description=f"Zone 2 endurance: {z2_low}-{z2_high}W for {duration_min-10}min",
            intervals=intervals,
            sport=WorkoutSport.CYCLING,
            estimated_load=duration_min * 0.6,
        )

    def _design_recovery(
        self,
        duration_min: int,
        context: CyclingAthleteContext,
    ) -> StructuredWorkout:
        """
        Recovery ride: <55% FTP (Zone 1).

        Active recovery spin. Keep it EASY.
        """
        ftp = context.ftp
        z1_max = int(ftp * 0.55)

        intervals = [
            CyclingWorkoutInterval(
                type=IntervalType.WORK,
                duration_sec=duration_min * 60,
                target_power_range=(0, z1_max),
                target_power_pct_ftp=(40, 55),
                target_cadence_range=(85, 100),
                notes=f"Easy spin <{z1_max}W. This should feel TOO easy.",
                intensity_zone=IntensityZone.RECOVERY,
            ),
        ]

        return StructuredWorkout.create(
            name="Recovery Ride",
            description=f"Active recovery: <{z1_max}W ({duration_min}min)",
            intervals=intervals,
            sport=WorkoutSport.CYCLING,
            estimated_load=duration_min * 0.4,
        )

    def _design_tempo(
        self,
        duration_min: int,
        context: CyclingAthleteContext,
    ) -> StructuredWorkout:
        """
        Tempo ride: 76-87% FTP (Zone 3).

        Sustained moderate intensity. Uncomfortable but manageable.
        """
        ftp = context.ftp
        tempo_low = int(ftp * 0.76)
        tempo_high = int(ftp * 0.87)

        warmup_min = 10
        cooldown_min = 5
        tempo_min = duration_min - warmup_min - cooldown_min

        intervals = [
            CyclingWorkoutInterval(
                type=IntervalType.WARMUP,
                duration_sec=warmup_min * 60,
                target_power_pct_ftp=(50, 70),
                target_cadence_range=(85, 95),
                notes="Progressive warmup",
            ),
            CyclingWorkoutInterval(
                type=IntervalType.WORK,
                duration_sec=tempo_min * 60,
                target_power_range=(tempo_low, tempo_high),
                target_power_pct_ftp=(76, 87),
                target_cadence_range=(85, 95),
                notes=f"Tempo: {tempo_low}-{tempo_high}W. Uncomfortably sustainable.",
                intensity_zone=IntensityZone.TEMPO,
            ),
            CyclingWorkoutInterval(
                type=IntervalType.COOLDOWN,
                duration_sec=cooldown_min * 60,
                target_power_pct_ftp=(40, 55),
                target_cadence_range=(80, 90),
                notes="Easy cooldown",
            ),
        ]

        return StructuredWorkout.create(
            name="Tempo Ride",
            description=f"Tempo: {tempo_low}-{tempo_high}W for {tempo_min}min",
            intervals=intervals,
            sport=WorkoutSport.CYCLING,
            estimated_load=duration_min * 0.8,
        )

    def _design_sprint(
        self,
        duration_min: int,
        context: CyclingAthleteContext,
    ) -> StructuredWorkout:
        """
        Sprint workout: neuromuscular power development.

        Short maximal efforts with full recovery.
        """
        ftp = context.ftp

        warmup_min = 15
        cooldown_min = 10

        # 6-10 x 15-30sec sprints with 3-5min recovery
        num_sprints = 8
        sprint_sec = 20
        recovery_min = 4

        intervals = [
            CyclingWorkoutInterval(
                type=IntervalType.WARMUP,
                duration_sec=warmup_min * 60,
                target_power_pct_ftp=(50, 75),
                target_cadence_range=(85, 100),
                notes="Thorough warmup with 3x10sec openers",
            ),
        ]

        for i in range(num_sprints):
            intervals.append(
                CyclingWorkoutInterval(
                    type=IntervalType.WORK,
                    duration_sec=sprint_sec,
                    target_power_pct_ftp=(150, 300),  # Maximal effort
                    target_cadence_range=(110, 140),
                    notes=f"Sprint {i+1}/{num_sprints}: MAXIMUM EFFORT!",
                    intensity_zone=IntensityZone.ANAEROBIC,
                )
            )
            if i < num_sprints - 1:
                intervals.append(
                    CyclingWorkoutInterval(
                        type=IntervalType.RECOVERY,
                        duration_sec=recovery_min * 60,
                        target_power_pct_ftp=(40, 55),
                        target_cadence_range=(80, 90),
                        notes="Full recovery - spin easy until ready",
                        intensity_zone=IntensityZone.RECOVERY,
                    )
                )

        intervals.append(
            CyclingWorkoutInterval(
                type=IntervalType.COOLDOWN,
                duration_sec=cooldown_min * 60,
                target_power_pct_ftp=(40, 55),
                target_cadence_range=(80, 90),
                notes="Extended cooldown",
            )
        )

        return StructuredWorkout.create(
            name="Sprint Intervals",
            description=f"{num_sprints}x{sprint_sec}sec all-out sprints",
            intervals=intervals,
            sport=WorkoutSport.CYCLING,
            estimated_load=duration_min * 1.0,
        )

    def _design_ramp_test(
        self,
        duration_min: int,
        context: CyclingAthleteContext,
    ) -> StructuredWorkout:
        """
        Ramp test for FTP estimation.

        Progressive 1-minute steps until failure.
        FTP estimated as 75% of max 1-minute power.
        """
        ftp = context.ftp

        # Start at 50% FTP, increase 6% per minute
        starting_pct = 50
        step_pct = 6
        num_steps = 15  # Goes up to ~140% FTP

        intervals = [
            CyclingWorkoutInterval(
                type=IntervalType.WARMUP,
                duration_sec=300,
                target_power_pct_ftp=(45, 55),
                target_cadence_range=(85, 95),
                notes="Easy warmup spin",
            ),
        ]

        for step in range(num_steps):
            pct = starting_pct + (step * step_pct)
            power = int(ftp * pct / 100)

            intervals.append(
                CyclingWorkoutInterval(
                    type=IntervalType.WORK,
                    duration_sec=60,
                    target_power_range=(power, power + 5),
                    target_power_pct_ftp=(pct, pct + 2),
                    target_cadence_range=(85, 95),
                    erg_mode=True,
                    erg_power=power,
                    notes=f"Step {step+1}: {power}W ({pct}% FTP)",
                    intensity_zone=IntensityZone.THRESHOLD if pct >= 90 else IntensityZone.TEMPO,
                )
            )

        intervals.append(
            CyclingWorkoutInterval(
                type=IntervalType.COOLDOWN,
                duration_sec=600,
                target_power_pct_ftp=(40, 50),
                target_cadence_range=(80, 90),
                notes="Extended cooldown after max effort",
            )
        )

        return StructuredWorkout.create(
            name="Ramp Test",
            description="FTP ramp test: 1min steps increasing 6% until failure",
            intervals=intervals,
            sport=WorkoutSport.CYCLING,
            estimated_load=80.0,  # Fixed load for test
        )

    def _design_ftp_test(
        self,
        duration_min: int,
        context: CyclingAthleteContext,
    ) -> StructuredWorkout:
        """
        20-minute FTP test.

        Standard 20-minute all-out effort. FTP = 95% of avg power.
        """
        ftp = context.ftp

        intervals = [
            CyclingWorkoutInterval(
                type=IntervalType.WARMUP,
                duration_sec=1200,  # 20min
                target_power_pct_ftp=(50, 70),
                target_cadence_range=(85, 95),
                notes="20min progressive warmup with 3x1min at threshold",
            ),
            CyclingWorkoutInterval(
                type=IntervalType.WORK,
                duration_sec=300,  # 5min
                target_power_pct_ftp=(100, 110),
                target_cadence_range=(90, 100),
                notes="5min hard effort to blow out legs (important!)",
                intensity_zone=IntensityZone.VO2MAX,
            ),
            CyclingWorkoutInterval(
                type=IntervalType.RECOVERY,
                duration_sec=600,  # 10min
                target_power_pct_ftp=(40, 55),
                target_cadence_range=(80, 90),
                notes="Easy recovery - get ready for the test",
                intensity_zone=IntensityZone.RECOVERY,
            ),
            CyclingWorkoutInterval(
                type=IntervalType.WORK,
                duration_sec=1200,  # 20min
                target_power_pct_ftp=(95, 105),
                target_cadence_range=(85, 95),
                notes="THE TEST: 20min ALL OUT! Pace evenly, give everything.",
                intensity_zone=IntensityZone.THRESHOLD,
            ),
            CyclingWorkoutInterval(
                type=IntervalType.COOLDOWN,
                duration_sec=600,  # 10min
                target_power_pct_ftp=(40, 50),
                target_cadence_range=(80, 90),
                notes="Extended cooldown",
            ),
        ]

        return StructuredWorkout.create(
            name="20min FTP Test",
            description="Standard FTP test: 20min all-out effort. FTP = 95% of avg power.",
            intervals=intervals,
            sport=WorkoutSport.CYCLING,
            estimated_load=90.0,
        )


# Singleton instance
_cycling_agent: Optional[CyclingWorkoutAgent] = None


def get_cycling_agent() -> CyclingWorkoutAgent:
    """Get the cycling workout agent singleton."""
    global _cycling_agent
    if _cycling_agent is None:
        _cycling_agent = CyclingWorkoutAgent()
    return _cycling_agent

