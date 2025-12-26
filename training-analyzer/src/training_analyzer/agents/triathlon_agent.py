"""
Triathlon Integration Agent for multi-sport workout planning.

Handles brick workouts, multi-sport days, fatigue carryover modeling,
and race-week tapering across disciplines.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional

from ..models.workouts import (
    AthleteContext,
    IntensityZone,
    IntervalType,
    StructuredWorkout,
    SwimAthleteContext,
    WorkoutInterval,
    WorkoutSport,
)
from .cycling_agent import CyclingAthleteContext, CyclingWorkoutAgent
from .swim_agent import SwimWorkoutAgent
from .workout_agent import WorkoutDesignAgent


class RaceDistance(str, Enum):
    """Standard triathlon race distances."""
    SPRINT = "sprint"           # 750m / 20km / 5km
    OLYMPIC = "olympic"         # 1500m / 40km / 10km
    HALF_IRONMAN = "70.3"       # 1900m / 90km / 21.1km
    IRONMAN = "140.6"           # 3800m / 180km / 42.2km
    CUSTOM = "custom"


@dataclass
class RaceDistanceSpecs:
    """Specifications for a triathlon race distance."""
    name: str
    swim_m: int
    bike_km: float
    run_km: float

    @classmethod
    def from_distance(cls, distance: RaceDistance) -> "RaceDistanceSpecs":
        """Create specs from a standard race distance."""
        specs = {
            RaceDistance.SPRINT: cls("Sprint", 750, 20.0, 5.0),
            RaceDistance.OLYMPIC: cls("Olympic", 1500, 40.0, 10.0),
            RaceDistance.HALF_IRONMAN: cls("70.3", 1900, 90.0, 21.1),
            RaceDistance.IRONMAN: cls("140.6", 3800, 180.0, 42.2),
        }
        return specs.get(distance, cls("Custom", 1500, 40.0, 10.0))


@dataclass
class TriathlonAthleteContext:
    """
    Combined athlete context for triathlon training.

    Contains contexts for all three disciplines plus tri-specific metrics.
    """
    # Individual sport contexts
    run_context: AthleteContext
    bike_context: CyclingAthleteContext
    swim_context: SwimAthleteContext

    # Triathlon-specific
    target_race: Optional[RaceDistance] = None
    race_date: Optional[date] = None
    weekly_hours_available: float = 10.0

    # Multi-sport fitness (combined load tracking)
    combined_ctl: float = 40.0
    combined_atl: float = 40.0

    # Discipline balance (target % of training time)
    swim_pct: float = 20.0
    bike_pct: float = 50.0
    run_pct: float = 30.0

    # Limiters (weakest discipline)
    primary_limiter: Optional[str] = None  # "swim", "bike", or "run"

    def get_combined_tsb(self) -> float:
        """Get combined training stress balance."""
        return self.combined_ctl - self.combined_atl

    def get_weeks_to_race(self) -> Optional[int]:
        """Calculate weeks until race date."""
        if self.race_date:
            delta = self.race_date - date.today()
            return max(0, delta.days // 7)
        return None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "run_context": self.run_context.to_dict(),
            "bike_context": self.bike_context.to_dict(),
            "swim_context": self.swim_context.to_dict(),
            "target_race": self.target_race.value if self.target_race else None,
            "race_date": self.race_date.isoformat() if self.race_date else None,
            "weekly_hours_available": self.weekly_hours_available,
            "combined_ctl": self.combined_ctl,
            "combined_atl": self.combined_atl,
            "combined_tsb": self.get_combined_tsb(),
            "discipline_balance": {
                "swim": self.swim_pct,
                "bike": self.bike_pct,
                "run": self.run_pct,
            },
            "primary_limiter": self.primary_limiter,
            "weeks_to_race": self.get_weeks_to_race(),
        }


@dataclass
class BrickWorkout:
    """
    A brick workout combining two disciplines back-to-back.

    Common types:
    - Bike-to-Run: Most common, simulates T2
    - Swim-to-Bike: Simulates T1
    - Run-to-Bike: Reverse brick for specific training
    """
    id: str
    name: str
    description: str
    first_workout: StructuredWorkout
    second_workout: StructuredWorkout
    transition_time_sec: int = 300  # 5 min default
    total_duration_min: int = 0
    total_estimated_load: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Calculate totals after initialization."""
        self.total_duration_min = (
            self.first_workout.estimated_duration_min +
            self.second_workout.estimated_duration_min +
            self.transition_time_sec // 60
        )
        # Brick workouts have higher load due to fatigue carryover
        base_load = (
            self.first_workout.estimated_load +
            self.second_workout.estimated_load
        )
        # 15% additional load for brick effect
        self.total_estimated_load = base_load * 1.15

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "first_workout": self.first_workout.to_dict(),
            "second_workout": self.second_workout.to_dict(),
            "transition_time_sec": self.transition_time_sec,
            "total_duration_min": self.total_duration_min,
            "total_estimated_load": self.total_estimated_load,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class MultiSportDay:
    """
    A training day with multiple workouts across disciplines.

    Used for planning two-a-day or three-a-day training.
    """
    date: date
    workouts: List[StructuredWorkout]
    brick_workouts: List[BrickWorkout]
    total_duration_min: int = 0
    total_load: float = 0.0
    notes: Optional[str] = None

    def __post_init__(self):
        """Calculate totals."""
        self.total_duration_min = (
            sum(w.estimated_duration_min for w in self.workouts) +
            sum(b.total_duration_min for b in self.brick_workouts)
        )
        self.total_load = (
            sum(w.estimated_load for w in self.workouts) +
            sum(b.total_estimated_load for b in self.brick_workouts)
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "date": self.date.isoformat(),
            "workouts": [w.to_dict() for w in self.workouts],
            "brick_workouts": [b.to_dict() for b in self.brick_workouts],
            "total_duration_min": self.total_duration_min,
            "total_load": self.total_load,
            "notes": self.notes,
        }


class FatigueCarryoverModel:
    """
    Models fatigue carryover between disciplines.

    Different activities affect subsequent training differently:
    - Swimming has minimal carryover to bike/run
    - Cycling creates significant leg fatigue affecting running
    - Running creates highest overall fatigue
    """

    # Fatigue multipliers: how much the first activity affects the second
    # Values > 1 mean increased difficulty for second workout
    CARRYOVER_MATRIX = {
        ("swim", "bike"): 1.05,   # Minimal effect
        ("swim", "run"): 1.05,    # Minimal effect
        ("bike", "swim"): 1.10,   # Some upper body fatigue from position
        ("bike", "run"): 1.25,    # Significant leg fatigue (brick effect)
        ("run", "swim"): 1.15,    # Increased HR, some fatigue
        ("run", "bike"): 1.20,    # Leg fatigue affects power
    }

    # Recovery time needed between workouts (hours)
    RECOVERY_HOURS = {
        ("swim", "bike"): 2,
        ("swim", "run"): 2,
        ("bike", "swim"): 3,
        ("bike", "run"): 0,  # Brick - no rest
        ("run", "swim"): 4,
        ("run", "bike"): 4,
    }

    @classmethod
    def get_carryover_factor(cls, first: str, second: str) -> float:
        """Get fatigue carryover factor between two disciplines."""
        key = (first.lower(), second.lower())
        return cls.CARRYOVER_MATRIX.get(key, 1.0)

    @classmethod
    def get_recovery_hours(cls, first: str, second: str) -> int:
        """Get recommended recovery hours between disciplines."""
        key = (first.lower(), second.lower())
        return cls.RECOVERY_HOURS.get(key, 4)

    @classmethod
    def adjust_second_workout_intensity(
        cls,
        first_sport: str,
        first_load: float,
        second_workout_target_load: float,
    ) -> float:
        """
        Adjust target load for second workout based on first workout fatigue.

        Returns the adjusted target load.
        """
        # Higher first workout load = more fatigue carryover
        fatigue_factor = min(1.5, 1.0 + (first_load / 100) * 0.1)

        # Reduce second workout target to account for fatigue
        return second_workout_target_load / fatigue_factor


class TriathlonAgent:
    """
    Agent for triathlon-specific workout planning.

    Coordinates across all three disciplines for integrated training.
    """

    def __init__(self):
        """Initialize with individual sport agents."""
        self.run_agent = WorkoutDesignAgent()
        self.bike_agent = CyclingWorkoutAgent()
        self.swim_agent = SwimWorkoutAgent()
        self.fatigue_model = FatigueCarryoverModel()

    def create_brick_workout(
        self,
        brick_type: str,
        duration_min: int,
        context: TriathlonAthleteContext,
        intensity: str = "moderate",
    ) -> BrickWorkout:
        """
        Create a brick workout.

        Args:
            brick_type: "bike_run", "swim_bike", or "run_bike"
            duration_min: Total duration in minutes
            context: Triathlon athlete context
            intensity: "easy", "moderate", or "hard"

        Returns:
            Complete BrickWorkout with both workouts
        """
        import uuid

        # Determine duration split based on brick type
        if brick_type == "bike_run":
            # Classic brick: 70% bike, 30% run
            bike_min = int(duration_min * 0.70)
            run_min = int(duration_min * 0.30)

            # Create bike workout
            bike_type = "endurance" if intensity == "easy" else "tempo"
            bike_workout = self.bike_agent.design_workout(
                bike_type, bike_min, context.bike_context
            )

            # Create run workout (off the bike)
            run_type = "easy" if intensity == "easy" else "tempo"
            run_workout = self.run_agent.design_workout(
                request=type('Request', (), {
                    'workout_type': run_type,
                    'duration_min': run_min,
                    'target_load': None,
                    'focus': "brick legs"
                })(),
                athlete_context=context.run_context,
            )

            # Adjust run description for brick context
            run_workout.description = f"OFF THE BIKE: {run_workout.description}"

            return BrickWorkout(
                id=f"brick_{uuid.uuid4().hex[:8]}",
                name=f"Bike-to-Run Brick ({intensity.title()})",
                description=f"{bike_min}min bike + {run_min}min run. Focus on T2 legs.",
                first_workout=bike_workout,
                second_workout=run_workout,
                transition_time_sec=180,  # 3 min T2
            )

        elif brick_type == "swim_bike":
            # T1 practice: 40% swim, 60% bike
            swim_min = int(duration_min * 0.40)
            bike_min = int(duration_min * 0.60)

            swim_workout = self.swim_agent.design_workout(
                "threshold" if intensity != "easy" else "endurance",
                swim_min,
                context.swim_context,
            )

            bike_workout = self.bike_agent.design_workout(
                "endurance" if intensity == "easy" else "sweet_spot",
                bike_min,
                context.bike_context,
            )

            bike_workout.description = f"OFF THE SWIM: {bike_workout.description}"

            return BrickWorkout(
                id=f"brick_{uuid.uuid4().hex[:8]}",
                name=f"Swim-to-Bike Brick ({intensity.title()})",
                description=f"{swim_min}min swim + {bike_min}min bike. T1 practice.",
                first_workout=swim_workout,
                second_workout=bike_workout,
                transition_time_sec=300,  # 5 min T1
            )

        else:  # run_bike (reverse brick)
            run_min = int(duration_min * 0.40)
            bike_min = int(duration_min * 0.60)

            run_workout = self.run_agent.design_workout(
                request=type('Request', (), {
                    'workout_type': "easy" if intensity == "easy" else "tempo",
                    'duration_min': run_min,
                    'target_load': None,
                    'focus': None
                })(),
                athlete_context=context.run_context,
            )

            bike_workout = self.bike_agent.design_workout(
                "recovery" if intensity == "easy" else "endurance",
                bike_min,
                context.bike_context,
            )

            return BrickWorkout(
                id=f"brick_{uuid.uuid4().hex[:8]}",
                name=f"Run-to-Bike (Reverse Brick)",
                description=f"{run_min}min run + {bike_min}min bike. Leg conditioning.",
                first_workout=run_workout,
                second_workout=bike_workout,
                transition_time_sec=180,
            )

    def plan_multi_sport_day(
        self,
        target_date: date,
        available_hours: float,
        context: TriathlonAthleteContext,
        include_brick: bool = False,
    ) -> MultiSportDay:
        """
        Plan a full training day with multiple disciplines.

        Args:
            target_date: Date for the training day
            available_hours: Total hours available
            context: Triathlon athlete context
            include_brick: Whether to include a brick workout

        Returns:
            Complete MultiSportDay plan
        """
        available_min = int(available_hours * 60)
        workouts: List[StructuredWorkout] = []
        brick_workouts: List[BrickWorkout] = []

        if include_brick:
            # Primary session: Brick workout (60% of time)
            brick_min = int(available_min * 0.60)
            brick = self.create_brick_workout(
                "bike_run", brick_min, context, "moderate"
            )
            brick_workouts.append(brick)

            # Secondary session: Swim (40% of time)
            swim_min = available_min - brick_min
            swim_workout = self.swim_agent.design_workout(
                "technique", swim_min, context.swim_context
            )
            workouts.append(swim_workout)

        else:
            # Two-a-day without brick
            # Morning: Swim (30%)
            swim_min = int(available_min * 0.30)
            swim_workout = self.swim_agent.design_workout(
                "threshold", swim_min, context.swim_context
            )
            workouts.append(swim_workout)

            # Afternoon: Bike or Run based on day/context
            # Alternate based on date (even = bike, odd = run)
            remaining_min = available_min - swim_min

            if target_date.day % 2 == 0:
                bike_workout = self.bike_agent.design_workout(
                    "endurance", remaining_min, context.bike_context
                )
                workouts.append(bike_workout)
            else:
                run_workout = self.run_agent.design_workout(
                    request=type('Request', (), {
                        'workout_type': "easy",
                        'duration_min': remaining_min,
                        'target_load': None,
                        'focus': None
                    })(),
                    athlete_context=context.run_context,
                )
                workouts.append(run_workout)

        return MultiSportDay(
            date=target_date,
            workouts=workouts,
            brick_workouts=brick_workouts,
            notes=f"Total {available_hours}h training day",
        )

    def create_taper_week(
        self,
        race_date: date,
        weeks_out: int,
        context: TriathlonAthleteContext,
    ) -> List[MultiSportDay]:
        """
        Create a race-week taper plan across all disciplines.

        Args:
            race_date: The race date
            weeks_out: Weeks until race (1 = race week)
            context: Triathlon athlete context

        Returns:
            List of MultiSportDay plans for the taper week
        """
        days: List[MultiSportDay] = []
        week_start = race_date - timedelta(days=race_date.weekday())

        if weeks_out == 1:  # Race week
            taper_schedule = [
                # (day_offset, swim_min, bike_min, run_min, notes)
                (0, 30, 45, 0, "Monday: Openers"),  # Mon
                (1, 20, 0, 30, "Tuesday: Short & sharp"),  # Tue
                (2, 0, 30, 0, "Wednesday: Easy spin"),  # Wed
                (3, 15, 0, 20, "Thursday: Shakeout"),  # Thu
                (4, 0, 20, 15, "Friday: Final activation"),  # Fri
                (5, 10, 0, 0, "Saturday: Swim only - REST"),  # Sat
                # Sunday = Race day
            ]
        else:  # Taper weeks 2-3
            reduction = 0.7 if weeks_out == 2 else 0.85
            taper_schedule = [
                (0, int(45 * reduction), int(60 * reduction), 0, f"Week -{weeks_out} Mon"),
                (1, 0, int(45 * reduction), int(45 * reduction), f"Week -{weeks_out} Tue"),
                (2, int(40 * reduction), 0, int(30 * reduction), f"Week -{weeks_out} Wed"),
                (3, 0, int(75 * reduction), 0, f"Week -{weeks_out} Thu"),
                (4, int(30 * reduction), 0, int(40 * reduction), f"Week -{weeks_out} Fri"),
                (5, 0, int(90 * reduction), int(20 * reduction), f"Week -{weeks_out} Sat"),
                (6, int(20 * reduction), 0, 0, f"Week -{weeks_out} Sun"),
            ]

        for day_offset, swim_min, bike_min, run_min, notes in taper_schedule:
            day_date = week_start + timedelta(days=day_offset)
            workouts: List[StructuredWorkout] = []

            if swim_min > 0:
                swim = self.swim_agent.design_workout(
                    "easy" if weeks_out == 1 else "mixed",
                    swim_min,
                    context.swim_context,
                )
                workouts.append(swim)

            if bike_min > 0:
                bike = self.bike_agent.design_workout(
                    "recovery" if weeks_out == 1 else "endurance",
                    bike_min,
                    context.bike_context,
                )
                workouts.append(bike)

            if run_min > 0:
                run = self.run_agent.design_workout(
                    request=type('Request', (), {
                        'workout_type': "easy",
                        'duration_min': run_min,
                        'target_load': None,
                        'focus': "legs fresh"
                    })(),
                    athlete_context=context.run_context,
                )
                workouts.append(run)

            if workouts:  # Only add days with workouts
                days.append(MultiSportDay(
                    date=day_date,
                    workouts=workouts,
                    brick_workouts=[],
                    notes=notes,
                ))

        return days

    def estimate_race_performance(
        self,
        race: RaceDistance,
        context: TriathlonAthleteContext,
    ) -> Dict[str, any]:
        """
        Estimate race performance based on current fitness.

        Returns predicted times for each discipline and total.
        """
        specs = RaceDistanceSpecs.from_distance(race)

        # Swim time (based on CSS)
        css = context.swim_context.css_pace
        # Race pace typically 5% faster than CSS for sprint/olympic
        race_swim_pace = int(css * 0.95) if race in [RaceDistance.SPRINT, RaceDistance.OLYMPIC] else css
        swim_time_sec = (specs.swim_m / 100) * race_swim_pace

        # Bike time (based on FTP)
        ftp = context.bike_context.ftp
        # Estimate sustainable power: 75% FTP for long, 85% for short
        if race in [RaceDistance.IRONMAN, RaceDistance.HALF_IRONMAN]:
            bike_power = int(ftp * 0.75)
        else:
            bike_power = int(ftp * 0.85)

        # Rough speed estimate: speed_kmh ≈ (power / 3.5) for flat course
        bike_speed_kmh = bike_power / 3.5
        bike_time_sec = (specs.bike_km / bike_speed_kmh) * 3600

        # Run time (based on threshold pace)
        threshold_pace = context.run_context.threshold_pace
        # Race run pace depends on distance
        if race == RaceDistance.IRONMAN:
            run_pace = int(threshold_pace * 1.25)  # Much slower off bike
        elif race == RaceDistance.HALF_IRONMAN:
            run_pace = int(threshold_pace * 1.15)
        else:
            run_pace = int(threshold_pace * 1.05)

        run_time_sec = specs.run_km * run_pace

        # Transitions
        t1_sec = 90 if race in [RaceDistance.SPRINT, RaceDistance.OLYMPIC] else 180
        t2_sec = 60 if race in [RaceDistance.SPRINT, RaceDistance.OLYMPIC] else 120

        total_sec = swim_time_sec + t1_sec + bike_time_sec + t2_sec + run_time_sec

        def format_time(seconds: float) -> str:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            if hours > 0:
                return f"{hours}:{minutes:02d}:{secs:02d}"
            return f"{minutes}:{secs:02d}"

        return {
            "race": race.value,
            "distances": {
                "swim_m": specs.swim_m,
                "bike_km": specs.bike_km,
                "run_km": specs.run_km,
            },
            "predicted_times": {
                "swim": format_time(swim_time_sec),
                "t1": format_time(t1_sec),
                "bike": format_time(bike_time_sec),
                "t2": format_time(t2_sec),
                "run": format_time(run_time_sec),
                "total": format_time(total_sec),
            },
            "pacing": {
                "swim_pace_100m": context.swim_context.format_swim_pace(race_swim_pace),
                "bike_power_w": bike_power,
                "bike_speed_kmh": round(bike_speed_kmh, 1),
                "run_pace_km": context.run_context.format_pace(run_pace),
            },
        }


# Singleton instance
_triathlon_agent: Optional[TriathlonAgent] = None


def get_triathlon_agent() -> TriathlonAgent:
    """Get the triathlon agent singleton."""
    global _triathlon_agent
    if _triathlon_agent is None:
        _triathlon_agent = TriathlonAgent()
    return _triathlon_agent

