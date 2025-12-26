"""Workout data models for structured workouts and FIT export."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple
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


class SwimStrokeType(str, Enum):
    """Swimming stroke types."""
    FREESTYLE = "freestyle"
    BACKSTROKE = "backstroke"
    BREASTSTROKE = "breaststroke"
    BUTTERFLY = "butterfly"
    INDIVIDUAL_MEDLEY = "im"
    MIXED = "mixed"


class PoolLength(int, Enum):
    """Standard pool lengths in meters."""
    SCM = 25   # Short Course Meters
    LCM = 50   # Long Course Meters
    SCY = 25   # Short Course Yards (converted to ~23m)


@dataclass
class SwimWorkoutInterval(WorkoutInterval):
    """
    A swim-specific interval within a structured swim workout.

    Extends WorkoutInterval with swimming-specific attributes like
    stroke type, drill indicators, and equipment requirements.
    """
    stroke_type: SwimStrokeType = SwimStrokeType.FREESTYLE
    is_drill: bool = False
    drill_name: Optional[str] = None
    equipment: Optional[List[str]] = None  # e.g., ["pull_buoy", "paddles", "fins"]
    target_swolf: Optional[int] = None
    target_stroke_count: Optional[int] = None
    target_pace_per_100m: Optional[Tuple[int, int]] = None  # (min, max) sec/100m

    def __post_init__(self):
        """Validate swim interval after initialization."""
        super().__post_init__()
        if isinstance(self.stroke_type, str):
            self.stroke_type = SwimStrokeType(self.stroke_type)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        base_dict = super().to_dict()
        base_dict.update({
            "stroke_type": self.stroke_type.value if isinstance(self.stroke_type, SwimStrokeType) else self.stroke_type,
            "is_drill": self.is_drill,
            "drill_name": self.drill_name,
            "equipment": self.equipment,
            "target_swolf": self.target_swolf,
            "target_stroke_count": self.target_stroke_count,
            "target_pace_per_100m": list(self.target_pace_per_100m) if self.target_pace_per_100m else None,
        })
        return base_dict

    @classmethod
    def from_dict(cls, data: dict) -> "SwimWorkoutInterval":
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
            stroke_type=SwimStrokeType(data.get("stroke_type", "freestyle")),
            is_drill=data.get("is_drill", False),
            drill_name=data.get("drill_name"),
            equipment=data.get("equipment"),
            target_swolf=data.get("target_swolf"),
            target_stroke_count=data.get("target_stroke_count"),
            target_pace_per_100m=tuple(data["target_pace_per_100m"]) if data.get("target_pace_per_100m") else None,
        )


@dataclass
class SwimAthleteContext:
    """
    Swim-specific athlete context for personalized swim workout design.

    Contains CSS (Critical Swim Speed), preferred stroke, pool preferences,
    and swim-specific training zones.
    """
    # Critical Swim Speed (threshold pace in sec/100m)
    css_pace: int = 100  # 1:40/100m default

    # CSS test times (for recalculation)
    css_test_400m_sec: Optional[float] = None
    css_test_200m_sec: Optional[float] = None

    # Preferences
    preferred_stroke: SwimStrokeType = SwimStrokeType.FREESTYLE
    preferred_pool_length: PoolLength = PoolLength.SCM

    # Fitness metrics (swim-specific)
    swim_ctl: float = 30.0  # Swim-specific Chronic Training Load
    swim_atl: float = 30.0  # Swim-specific Acute Training Load

    # Stroke efficiencies (average SWOLF per stroke type)
    freestyle_swolf: Optional[int] = None
    backstroke_swolf: Optional[int] = None
    breaststroke_swolf: Optional[int] = None
    butterfly_swolf: Optional[int] = None

    # Swim paces by zone (sec/100m)
    recovery_pace: Optional[int] = None   # Zone 1
    aerobic_pace: Optional[int] = None    # Zone 2
    threshold_pace: Optional[int] = None  # Zone 3 (same as CSS)
    vo2max_pace: Optional[int] = None     # Zone 4
    sprint_pace: Optional[int] = None     # Zone 5

    def __post_init__(self):
        """Initialize zone paces from CSS if not provided."""
        if isinstance(self.preferred_stroke, str):
            self.preferred_stroke = SwimStrokeType(self.preferred_stroke)
        if isinstance(self.preferred_pool_length, int) and self.preferred_pool_length not in [25, 50]:
            self.preferred_pool_length = PoolLength.SCM
        elif isinstance(self.preferred_pool_length, int):
            self.preferred_pool_length = PoolLength(self.preferred_pool_length)

        # Set default zone paces based on CSS if not provided
        if self.threshold_pace is None:
            self.threshold_pace = self.css_pace
        if self.recovery_pace is None:
            self.recovery_pace = int(self.css_pace * 1.20)  # 120% CSS
        if self.aerobic_pace is None:
            self.aerobic_pace = int(self.css_pace * 1.10)   # 110% CSS
        if self.vo2max_pace is None:
            self.vo2max_pace = int(self.css_pace * 0.90)    # 90% CSS
        if self.sprint_pace is None:
            self.sprint_pace = int(self.css_pace * 0.80)    # 80% CSS

    def recalculate_css(self) -> Optional[int]:
        """
        Recalculate CSS from test times if available.

        Returns:
            New CSS pace in sec/100m, or None if test times unavailable
        """
        if self.css_test_400m_sec and self.css_test_200m_sec:
            if self.css_test_400m_sec > self.css_test_200m_sec:
                css_speed = 200 / (self.css_test_400m_sec - self.css_test_200m_sec)
                self.css_pace = int(round(100 / css_speed))
                # Recalculate zone paces
                self.__post_init__()
                return self.css_pace
        return None

    def get_swim_zones(self) -> Dict[str, Tuple[int, int]]:
        """
        Get swim training zones based on CSS.

        Returns:
            Dictionary with zone names and (fast, slow) pace ranges in sec/100m
        """
        return {
            "zone1_recovery": (int(self.css_pace * 1.15), int(self.css_pace * 1.40)),
            "zone2_aerobic": (int(self.css_pace * 1.05), int(self.css_pace * 1.15)),
            "zone3_threshold": (int(self.css_pace * 0.95), int(self.css_pace * 1.05)),
            "zone4_vo2max": (int(self.css_pace * 0.85), int(self.css_pace * 0.95)),
            "zone5_sprint": (int(self.css_pace * 0.70), int(self.css_pace * 0.85)),
        }

    def format_swim_pace(self, pace_sec: int) -> str:
        """Format swim pace (sec/100m) to mm:ss format."""
        minutes = pace_sec // 60
        seconds = pace_sec % 60
        return f"{minutes}:{seconds:02d}/100m"

    def get_pace_for_zone(self, zone: int) -> int:
        """Get target pace for a given zone (1-5)."""
        zone_paces = {
            1: self.recovery_pace,
            2: self.aerobic_pace,
            3: self.threshold_pace,
            4: self.vo2max_pace,
            5: self.sprint_pace,
        }
        return zone_paces.get(zone, self.threshold_pace) or self.css_pace

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "css_pace": self.css_pace,
            "css_pace_formatted": self.format_swim_pace(self.css_pace),
            "css_test_400m_sec": self.css_test_400m_sec,
            "css_test_200m_sec": self.css_test_200m_sec,
            "preferred_stroke": self.preferred_stroke.value if isinstance(self.preferred_stroke, SwimStrokeType) else self.preferred_stroke,
            "preferred_pool_length": self.preferred_pool_length.value if isinstance(self.preferred_pool_length, PoolLength) else self.preferred_pool_length,
            "swim_ctl": self.swim_ctl,
            "swim_atl": self.swim_atl,
            "swolf_by_stroke": {
                "freestyle": self.freestyle_swolf,
                "backstroke": self.backstroke_swolf,
                "breaststroke": self.breaststroke_swolf,
                "butterfly": self.butterfly_swolf,
            },
            "zone_paces": {
                "recovery": self.format_swim_pace(self.recovery_pace) if self.recovery_pace else None,
                "aerobic": self.format_swim_pace(self.aerobic_pace) if self.aerobic_pace else None,
                "threshold": self.format_swim_pace(self.threshold_pace) if self.threshold_pace else None,
                "vo2max": self.format_swim_pace(self.vo2max_pace) if self.vo2max_pace else None,
                "sprint": self.format_swim_pace(self.sprint_pace) if self.sprint_pace else None,
            },
            "swim_zones": self.get_swim_zones(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SwimAthleteContext":
        """Create from dictionary."""
        return cls(
            css_pace=data.get("css_pace", 100),
            css_test_400m_sec=data.get("css_test_400m_sec"),
            css_test_200m_sec=data.get("css_test_200m_sec"),
            preferred_stroke=SwimStrokeType(data.get("preferred_stroke", "freestyle")),
            preferred_pool_length=PoolLength(data.get("preferred_pool_length", 25)),
            swim_ctl=data.get("swim_ctl", 30.0),
            swim_atl=data.get("swim_atl", 30.0),
            freestyle_swolf=data.get("swolf_by_stroke", {}).get("freestyle"),
            backstroke_swolf=data.get("swolf_by_stroke", {}).get("backstroke"),
            breaststroke_swolf=data.get("swolf_by_stroke", {}).get("breaststroke"),
            butterfly_swolf=data.get("swolf_by_stroke", {}).get("butterfly"),
        )
