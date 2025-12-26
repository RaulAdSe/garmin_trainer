"""Data models for training plans."""

from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import List, Optional, Dict, Any
import uuid


class PeriodizationType(str, Enum):
    """Types of periodization for training plans."""
    LINEAR = "linear"       # Traditional progressive build
    REVERSE = "reverse"     # Start with intensity, end with volume
    BLOCK = "block"         # Focused blocks of training emphasis
    UNDULATING = "undulating"  # Daily/weekly variation


class TrainingPhase(str, Enum):
    """Training phases within a periodized plan."""
    BASE = "base"           # Aerobic foundation building
    BUILD = "build"         # Progressive load increase
    PEAK = "peak"           # Race-specific intensity
    TAPER = "taper"         # Pre-race volume reduction
    RECOVERY = "recovery"   # Post-race or deload phase


class WorkoutType(str, Enum):
    """Types of training sessions."""
    EASY = "easy"
    LONG = "long"
    TEMPO = "tempo"
    THRESHOLD = "threshold"
    INTERVALS = "intervals"
    FARTLEK = "fartlek"
    HILLS = "hills"
    RECOVERY = "recovery"
    REST = "rest"
    CROSS_TRAINING = "cross_training"
    RACE = "race"


class RaceDistance(str, Enum):
    """Standard race distances."""
    FIVE_K = "5k"
    TEN_K = "10k"
    HALF_MARATHON = "half"
    MARATHON = "marathon"
    ULTRA = "ultra"
    CUSTOM = "custom"

    @classmethod
    def get_distance_km(cls, distance: "RaceDistance") -> float:
        """Get distance in kilometers."""
        distances = {
            cls.FIVE_K: 5.0,
            cls.TEN_K: 10.0,
            cls.HALF_MARATHON: 21.0975,
            cls.MARATHON: 42.195,
        }
        return distances.get(distance, 0.0)


@dataclass
class RaceGoal:
    """A race goal with target time and date."""
    race_date: date
    distance: RaceDistance
    target_time_seconds: int
    race_name: Optional[str] = None
    priority: int = 1  # 1 = A race, 2 = B race, 3 = C race
    custom_distance_km: Optional[float] = None

    @property
    def distance_km(self) -> float:
        """Get the distance in kilometers."""
        if self.distance == RaceDistance.CUSTOM and self.custom_distance_km:
            return self.custom_distance_km
        return RaceDistance.get_distance_km(self.distance)

    @property
    def target_time_formatted(self) -> str:
        """Format target time as H:MM:SS or MM:SS."""
        hours = self.target_time_seconds // 3600
        minutes = (self.target_time_seconds % 3600) // 60
        seconds = self.target_time_seconds % 60

        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

    @property
    def target_pace_per_km(self) -> float:
        """Calculate target pace in seconds per km."""
        if self.distance_km > 0:
            return self.target_time_seconds / self.distance_km
        return 0.0

    @property
    def target_pace_formatted(self) -> str:
        """Format target pace as M:SS/km."""
        pace = self.target_pace_per_km
        minutes = int(pace // 60)
        seconds = int(pace % 60)
        return f"{minutes}:{seconds:02d}/km"

    def weeks_until_race(self, from_date: Optional[date] = None) -> int:
        """Calculate weeks until the race."""
        if from_date is None:
            from_date = date.today()
        days = (self.race_date - from_date).days
        return max(0, days // 7)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "race_date": self.race_date.isoformat(),
            "distance": self.distance.value,
            "target_time_seconds": self.target_time_seconds,
            "target_time_formatted": self.target_time_formatted,
            "target_pace_formatted": self.target_pace_formatted,
            "race_name": self.race_name,
            "priority": self.priority,
            "distance_km": self.distance_km,
        }


@dataclass
class PlannedSession:
    """A planned training session within a week."""
    day_of_week: int  # 0=Monday, 6=Sunday
    workout_type: WorkoutType
    description: str
    target_duration_min: int
    target_load: float  # Expected training load (HRSS/TSS equivalent)
    target_pace: Optional[str] = None  # e.g., "5:30-5:45/km"
    target_hr_zone: Optional[str] = None  # e.g., "Zone 2" or "Zone 4-5"
    intervals: Optional[List[Dict[str, Any]]] = None  # Structured workout intervals
    notes: Optional[str] = None

    @property
    def day_name(self) -> str:
        """Get the day name."""
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        return days[self.day_of_week] if 0 <= self.day_of_week <= 6 else "Unknown"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "day_of_week": self.day_of_week,
            "day_name": self.day_name,
            "workout_type": self.workout_type.value,
            "description": self.description,
            "target_duration_min": self.target_duration_min,
            "target_load": self.target_load,
            "target_pace": self.target_pace,
            "target_hr_zone": self.target_hr_zone,
            "intervals": self.intervals,
            "notes": self.notes,
        }


@dataclass
class TrainingWeek:
    """A week of training within a plan."""
    week_number: int
    phase: TrainingPhase
    target_load: float  # Total weekly training load target
    sessions: List[PlannedSession] = field(default_factory=list)
    focus: Optional[str] = None  # e.g., "Aerobic endurance", "Speed development"
    notes: Optional[str] = None
    is_cutback: bool = False  # Recovery week with reduced load

    @property
    def planned_duration_min(self) -> int:
        """Total planned duration for the week."""
        return sum(s.target_duration_min for s in self.sessions)

    @property
    def workout_count(self) -> int:
        """Number of workout sessions (excluding rest)."""
        return sum(1 for s in self.sessions if s.workout_type != WorkoutType.REST)

    @property
    def quality_sessions(self) -> List[PlannedSession]:
        """Get quality (hard) sessions for the week."""
        quality_types = {
            WorkoutType.TEMPO,
            WorkoutType.THRESHOLD,
            WorkoutType.INTERVALS,
            WorkoutType.HILLS,
            WorkoutType.FARTLEK,
        }
        return [s for s in self.sessions if s.workout_type in quality_types]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "week_number": self.week_number,
            "phase": self.phase.value,
            "target_load": self.target_load,
            "planned_duration_min": self.planned_duration_min,
            "workout_count": self.workout_count,
            "quality_session_count": len(self.quality_sessions),
            "sessions": [s.to_dict() for s in self.sessions],
            "focus": self.focus,
            "notes": self.notes,
            "is_cutback": self.is_cutback,
        }


@dataclass
class PlanConstraints:
    """Athlete constraints for plan generation."""
    days_per_week: int = 5  # Training days per week
    long_run_day: int = 6  # 0=Monday, 6=Sunday
    rest_days: List[int] = field(default_factory=lambda: [5])  # Default Friday rest
    max_weekly_hours: float = 8.0
    max_session_duration_min: int = 150
    include_cross_training: bool = False
    back_to_back_hard_ok: bool = False  # Allow consecutive quality days
    morning_workouts: bool = True
    double_days_ok: bool = False  # Allow two workouts per day

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "days_per_week": self.days_per_week,
            "long_run_day": self.long_run_day,
            "rest_days": self.rest_days,
            "max_weekly_hours": self.max_weekly_hours,
            "max_session_duration_min": self.max_session_duration_min,
            "include_cross_training": self.include_cross_training,
            "back_to_back_hard_ok": self.back_to_back_hard_ok,
            "morning_workouts": self.morning_workouts,
            "double_days_ok": self.double_days_ok,
        }


@dataclass
class AthleteContext:
    """Current athlete context for plan generation."""
    current_ctl: float  # Current Chronic Training Load (fitness)
    current_atl: float  # Current Acute Training Load (fatigue)
    recent_weekly_load: float  # Average weekly load over last 4 weeks
    recent_weekly_hours: float  # Average weekly hours over last 4 weeks
    max_hr: int = 185
    rest_hr: int = 55
    threshold_hr: int = 165
    vdot: Optional[float] = None  # Estimated VDOT for pace calculations

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "current_ctl": self.current_ctl,
            "current_atl": self.current_atl,
            "recent_weekly_load": self.recent_weekly_load,
            "recent_weekly_hours": self.recent_weekly_hours,
            "max_hr": self.max_hr,
            "rest_hr": self.rest_hr,
            "threshold_hr": self.threshold_hr,
            "vdot": self.vdot,
        }


@dataclass
class TrainingPlan:
    """A complete periodized training plan."""
    id: str
    goal: RaceGoal
    weeks: List[TrainingWeek]
    periodization: PeriodizationType
    peak_week: int  # Week number of peak training
    created_at: datetime
    athlete_context: Optional[AthleteContext] = None
    constraints: Optional[PlanConstraints] = None
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = False
    updated_at: Optional[datetime] = None
    adaptation_history: List[Dict[str, Any]] = field(default_factory=list)

    @staticmethod
    def generate_id() -> str:
        """Generate a unique plan ID."""
        return f"plan_{uuid.uuid4().hex[:12]}"

    @property
    def total_weeks(self) -> int:
        """Total number of weeks in the plan."""
        return len(self.weeks)

    @property
    def total_planned_load(self) -> float:
        """Total planned training load for the plan."""
        return sum(w.target_load for w in self.weeks)

    @property
    def phases_summary(self) -> Dict[str, int]:
        """Summary of weeks per phase."""
        summary = {}
        for week in self.weeks:
            phase = week.phase.value
            summary[phase] = summary.get(phase, 0) + 1
        return summary

    def get_week(self, week_number: int) -> Optional[TrainingWeek]:
        """Get a specific week by number."""
        for week in self.weeks:
            if week.week_number == week_number:
                return week
        return None

    def get_current_week(self, from_date: Optional[date] = None) -> Optional[TrainingWeek]:
        """Get the current week based on date relative to race."""
        if from_date is None:
            from_date = date.today()

        weeks_until_race = self.goal.weeks_until_race(from_date)
        current_week_number = self.total_weeks - weeks_until_race

        if 1 <= current_week_number <= self.total_weeks:
            return self.get_week(current_week_number)
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "goal": self.goal.to_dict(),
            "periodization": self.periodization.value,
            "total_weeks": self.total_weeks,
            "peak_week": self.peak_week,
            "phases_summary": self.phases_summary,
            "total_planned_load": self.total_planned_load,
            "weeks": [w.to_dict() for w in self.weeks],
            "athlete_context": self.athlete_context.to_dict() if self.athlete_context else None,
            "constraints": self.constraints.to_dict() if self.constraints else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "adaptation_history": self.adaptation_history,
        }

    def to_summary_dict(self) -> Dict[str, Any]:
        """Convert to summary dictionary (without full week details)."""
        return {
            "id": self.id,
            "name": self.name,
            "goal": {
                "race_date": self.goal.race_date.isoformat(),
                "distance": self.goal.distance.value,
                "target_time": self.goal.target_time_formatted,
            },
            "periodization": self.periodization.value,
            "total_weeks": self.total_weeks,
            "phases_summary": self.phases_summary,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class PlanAdaptation:
    """Record of a plan adaptation."""
    timestamp: datetime
    reason: str
    changes: Dict[str, Any]
    weeks_affected: List[int]
    triggered_by: str  # "performance", "injury", "schedule", "manual"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "reason": self.reason,
            "changes": self.changes,
            "weeks_affected": self.weeks_affected,
            "triggered_by": self.triggered_by,
        }


# Pydantic models for API request/response validation
from pydantic import BaseModel, Field
from typing import List as PyList


class GoalInputSchema(BaseModel):
    """API input schema for race goal."""
    race_date: str = Field(..., description="Race date in YYYY-MM-DD format")
    distance: str = Field(..., description="Race distance: 5k, 10k, half, marathon, ultra, custom")
    target_time: str = Field(..., description="Target time in H:MM:SS or MM:SS format")
    race_name: Optional[str] = None
    priority: int = Field(1, ge=1, le=3)
    custom_distance_km: Optional[float] = None


class ConstraintsInputSchema(BaseModel):
    """API input schema for plan constraints."""
    days_per_week: int = Field(5, ge=3, le=7)
    long_run_day: str = Field("sunday", description="Day of week for long run")
    rest_days: PyList[str] = Field(default_factory=list)
    max_weekly_hours: float = Field(8.0, ge=2.0, le=20.0)
    max_session_duration_min: int = Field(150, ge=30, le=240)
    include_cross_training: bool = False
    back_to_back_hard_ok: bool = False


class GeneratePlanRequestSchema(BaseModel):
    """API request schema for plan generation."""
    goal: GoalInputSchema
    constraints: ConstraintsInputSchema = Field(default_factory=ConstraintsInputSchema)
    periodization_type: Optional[str] = None  # If not specified, agent decides


class PlanResponseSchema(BaseModel):
    """API response schema for training plan."""
    id: str
    name: Optional[str]
    goal: Dict[str, Any]
    periodization: str
    total_weeks: int
    peak_week: int
    phases_summary: Dict[str, int]
    weeks: PyList[Dict[str, Any]]
    is_active: bool
    created_at: str


class AdaptPlanRequestSchema(BaseModel):
    """API request schema for plan adaptation."""
    reason: Optional[str] = None
    force_recalculate: bool = False
    weeks_to_adapt: Optional[PyList[int]] = None  # None = adapt all remaining weeks


def parse_time_string(time_str: str) -> int:
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


def day_name_to_number(day_name: str) -> int:
    """Convert day name to number (0=Monday, 6=Sunday)."""
    days = {
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6,
        "mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6,
    }
    return days.get(day_name.lower().strip(), 6)


def parse_goal_input(goal_input: GoalInputSchema) -> RaceGoal:
    """Parse goal input schema to RaceGoal dataclass."""
    from datetime import datetime

    race_date = datetime.strptime(goal_input.race_date, "%Y-%m-%d").date()
    target_seconds = parse_time_string(goal_input.target_time)

    # Map distance string to enum
    distance_map = {
        "5k": RaceDistance.FIVE_K,
        "10k": RaceDistance.TEN_K,
        "half": RaceDistance.HALF_MARATHON,
        "half_marathon": RaceDistance.HALF_MARATHON,
        "marathon": RaceDistance.MARATHON,
        "ultra": RaceDistance.ULTRA,
        "custom": RaceDistance.CUSTOM,
    }
    distance = distance_map.get(goal_input.distance.lower(), RaceDistance.CUSTOM)

    return RaceGoal(
        race_date=race_date,
        distance=distance,
        target_time_seconds=target_seconds,
        race_name=goal_input.race_name,
        priority=goal_input.priority,
        custom_distance_km=goal_input.custom_distance_km,
    )


def parse_constraints_input(constraints_input: ConstraintsInputSchema) -> PlanConstraints:
    """Parse constraints input schema to PlanConstraints dataclass."""
    return PlanConstraints(
        days_per_week=constraints_input.days_per_week,
        long_run_day=day_name_to_number(constraints_input.long_run_day),
        rest_days=[day_name_to_number(d) for d in constraints_input.rest_days],
        max_weekly_hours=constraints_input.max_weekly_hours,
        max_session_duration_min=constraints_input.max_session_duration_min,
        include_cross_training=constraints_input.include_cross_training,
        back_to_back_hard_ok=constraints_input.back_to_back_hard_ok,
    )
