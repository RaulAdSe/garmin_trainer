"""Workout data models for structured workouts and FIT export."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Tuple
import uuid


class IntervalType(str, Enum):
    """Types of workout intervals."""
    WARMUP = "warmup"
    WORK = "work"
    RECOVERY = "recovery"
    COOLDOWN = "cooldown"
    REST = "rest"
    ACTIVE_RECOVERY = "active_recovery"


class WorkoutSport(str, Enum):
    """Supported sports for workouts."""
    RUNNING = "running"
    CYCLING = "cycling"
    SWIMMING = "swimming"


class IntensityZone(str, Enum):
    """Training intensity zones."""
    RECOVERY = "recovery"      # Zone 1
    AEROBIC = "aerobic"        # Zone 2
    TEMPO = "tempo"            # Zone 3
    THRESHOLD = "threshold"    # Zone 4
    VO2MAX = "vo2max"          # Zone 5
    ANAEROBIC = "anaerobic"    # Zone 5+


@dataclass
class WorkoutInterval:
    """
    A single interval within a structured workout.

    Can be defined by duration OR distance (not both typically).
    Includes target pace and HR ranges for Garmin device guidance.
    """
    type: IntervalType
    duration_sec: Optional[int] = None
    distance_m: Optional[int] = None
    target_pace_range: Optional[Tuple[int, int]] = None  # (min, max) sec/km
    target_hr_range: Optional[Tuple[int, int]] = None    # (min, max) bpm
    repetitions: int = 1
    notes: Optional[str] = None
    intensity_zone: Optional[IntensityZone] = None

    def __post_init__(self):
        """Validate interval after initialization."""
        if isinstance(self.type, str):
            self.type = IntervalType(self.type)
        if isinstance(self.intensity_zone, str):
            self.intensity_zone = IntensityZone(self.intensity_zone)

    @property
    def total_duration_sec(self) -> Optional[int]:
        """Total duration including repetitions."""
        if self.duration_sec:
            return self.duration_sec * self.repetitions
        return None

    @property
    def total_distance_m(self) -> Optional[int]:
        """Total distance including repetitions."""
        if self.distance_m:
            return self.distance_m * self.repetitions
        return None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.type.value if isinstance(self.type, IntervalType) else self.type,
            "duration_sec": self.duration_sec,
            "distance_m": self.distance_m,
            "target_pace_range": list(self.target_pace_range) if self.target_pace_range else None,
            "target_hr_range": list(self.target_hr_range) if self.target_hr_range else None,
            "repetitions": self.repetitions,
            "notes": self.notes,
            "intensity_zone": self.intensity_zone.value if self.intensity_zone else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorkoutInterval":
        """Create from dictionary."""
        return cls(
            type=IntervalType(data["type"]),
            duration_sec=data.get("duration_sec"),
            distance_m=data.get("distance_m"),
            target_pace_range=tuple(data["target_pace_range"]) if data.get("target_pace_range") else None,
            target_hr_range=tuple(data["target_hr_range"]) if data.get("target_hr_range") else None,
            repetitions=data.get("repetitions", 1),
            notes=data.get("notes"),
            intensity_zone=IntensityZone(data["intensity_zone"]) if data.get("intensity_zone") else None,
        )


@dataclass
class StructuredWorkout:
    """
    A complete structured workout ready for FIT export.

    Contains all intervals with their targets, plus metadata
    for display and tracking purposes.
    """
    id: str
    name: str
    description: str
    sport: WorkoutSport
    intervals: List[WorkoutInterval]
    estimated_duration_min: int
    estimated_load: float = 0.0
    estimated_distance_m: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate workout after initialization."""
        if isinstance(self.sport, str):
            self.sport = WorkoutSport(self.sport)
        # Ensure intervals are WorkoutInterval objects
        processed_intervals = []
        for interval in self.intervals:
            if isinstance(interval, dict):
                processed_intervals.append(WorkoutInterval.from_dict(interval))
            else:
                processed_intervals.append(interval)
        self.intervals = processed_intervals

    @classmethod
    def create(
        cls,
        name: str,
        description: str,
        intervals: List[WorkoutInterval],
        sport: WorkoutSport = WorkoutSport.RUNNING,
        estimated_load: float = 0.0,
    ) -> "StructuredWorkout":
        """Factory method to create a new workout with auto-generated ID."""
        workout_id = f"workout_{uuid.uuid4().hex[:12]}"

        # Calculate estimated duration from intervals
        total_duration_sec = 0
        total_distance_m = 0

        for interval in intervals:
            if interval.duration_sec:
                total_duration_sec += interval.duration_sec * interval.repetitions
            if interval.distance_m:
                total_distance_m += interval.distance_m * interval.repetitions

        estimated_duration_min = max(1, total_duration_sec // 60)

        return cls(
            id=workout_id,
            name=name,
            description=description,
            sport=sport,
            intervals=intervals,
            estimated_duration_min=estimated_duration_min,
            estimated_load=estimated_load,
            estimated_distance_m=total_distance_m if total_distance_m > 0 else None,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "sport": self.sport.value if isinstance(self.sport, WorkoutSport) else self.sport,
            "intervals": [i.to_dict() for i in self.intervals],
            "estimated_duration_min": self.estimated_duration_min,
            "estimated_load": self.estimated_load,
            "estimated_distance_m": self.estimated_distance_m,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StructuredWorkout":
        """Create from dictionary."""
        intervals = [WorkoutInterval.from_dict(i) for i in data.get("intervals", [])]
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            sport=WorkoutSport(data["sport"]),
            intervals=intervals,
            estimated_duration_min=data["estimated_duration_min"],
            estimated_load=data.get("estimated_load", 0.0),
            estimated_distance_m=data.get("estimated_distance_m"),
            created_at=created_at or datetime.now(),
        )

    def get_total_work_duration_sec(self) -> int:
        """Get total duration of 'work' intervals."""
        return sum(
            (i.duration_sec or 0) * i.repetitions
            for i in self.intervals
            if i.type == IntervalType.WORK
        )

    def get_interval_count(self) -> int:
        """Get count of work intervals (including repetitions)."""
        return sum(
            i.repetitions
            for i in self.intervals
            if i.type == IntervalType.WORK
        )


@dataclass
class WorkoutDesignRequest:
    """Request parameters for AI workout design."""
    workout_type: str  # "easy", "tempo", "intervals", "threshold", "long", "fartlek"
    duration_min: Optional[int] = None
    target_load: Optional[float] = None
    focus: Optional[str] = None  # "speed", "endurance", "threshold", "recovery"
    intensity_preference: Optional[str] = None  # "conservative", "moderate", "aggressive"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "workout_type": self.workout_type,
            "duration_min": self.duration_min,
            "target_load": self.target_load,
            "focus": self.focus,
            "intensity_preference": self.intensity_preference,
        }


@dataclass
class AthleteContext:
    """
    Context about the athlete for personalized workout design.

    Includes fitness metrics, training paces, HR zones, and goals.
    """
    max_hr: int = 185
    rest_hr: int = 55
    lthr: int = 165
    ctl: float = 40.0  # Chronic Training Load (fitness)
    atl: float = 40.0  # Acute Training Load (fatigue)
    tsb: float = 0.0   # Training Stress Balance (form)
    readiness_score: int = 75

    # Training paces (sec/km)
    easy_pace: int = 360      # 6:00/km
    long_pace: int = 345      # 5:45/km
    tempo_pace: int = 300     # 5:00/km
    threshold_pace: int = 285 # 4:45/km
    interval_pace: int = 270  # 4:30/km
    race_pace: int = 290      # 4:50/km

    def get_hr_zone_range(self, zone: int) -> Tuple[int, int]:
        """
        Get HR range for a given zone (1-5) using Karvonen method.

        Zone 1: 50-60% HRR
        Zone 2: 60-70% HRR
        Zone 3: 70-80% HRR
        Zone 4: 80-90% HRR
        Zone 5: 90-100% HRR
        """
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

    def get_pace_for_type(self, workout_type: str) -> int:
        """Get the appropriate pace (sec/km) for a workout type."""
        pace_map = {
            "easy": self.easy_pace,
            "long": self.long_pace,
            "tempo": self.tempo_pace,
            "threshold": self.threshold_pace,
            "intervals": self.interval_pace,
            "interval": self.interval_pace,
            "race": self.race_pace,
        }
        return pace_map.get(workout_type.lower(), self.easy_pace)

    def format_pace(self, pace_sec: int) -> str:
        """Format pace in sec/km to mm:ss format."""
        minutes = pace_sec // 60
        seconds = pace_sec % 60
        return f"{minutes}:{seconds:02d}/km"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "max_hr": self.max_hr,
            "rest_hr": self.rest_hr,
            "lthr": self.lthr,
            "ctl": self.ctl,
            "atl": self.atl,
            "tsb": self.tsb,
            "readiness_score": self.readiness_score,
            "training_paces": {
                "easy": self.format_pace(self.easy_pace),
                "long": self.format_pace(self.long_pace),
                "tempo": self.format_pace(self.tempo_pace),
                "threshold": self.format_pace(self.threshold_pace),
                "interval": self.format_pace(self.interval_pace),
                "race": self.format_pace(self.race_pace),
            },
            "hr_zones": {
                f"zone{i}": self.get_hr_zone_range(i)
                for i in range(1, 6)
            },
        }
