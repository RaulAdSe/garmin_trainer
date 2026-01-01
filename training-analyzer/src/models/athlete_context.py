"""
Unified AthleteContext model for the trAIner App.

This module provides a single, comprehensive AthleteContext dataclass that
consolidates all athlete-related context needed across different modules:
- Workout analysis
- Training plan generation
- Workout design

This replaces the previously scattered AthleteContext definitions in:
- models/analysis.py
- models/plans.py
- models/workouts.py
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, Any


@dataclass
class AthleteContext:
    """
    Unified athlete context for all training-related operations.

    This context provides comprehensive athlete information used for:
    - Workout analysis (understanding how a workout fits into training)
    - Plan generation (building periodized training plans)
    - Workout design (creating personalized workout structures)

    Attributes:
        # Fitness Metrics
        ctl: Chronic Training Load (fitness indicator)
        atl: Acute Training Load (fatigue indicator)
        tsb: Training Stress Balance (form indicator)
        acwr: Acute:Chronic Workload Ratio (injury risk indicator)
        risk_zone: Current risk assessment (undertraining/optimal/overreaching/danger)

        # Physiology
        max_hr: Maximum heart rate
        rest_hr: Resting heart rate
        threshold_hr: Lactate threshold heart rate (LTHR)
        vdot: VDOT estimate for pace calculations

        # Recent Training
        recent_weekly_load: Average weekly load over last 4 weeks
        recent_weekly_hours: Average weekly hours over last 4 weeks
        recent_load_7d: Training load in the last 7 days
        days_since_hard: Days since last hard workout

        # Readiness
        readiness_score: Current readiness score (0-100)
        readiness_zone: Readiness zone (green/yellow/red)

        # HR Zones (as tuples of (min, max) bpm)
        hr_zones: Dictionary mapping zone number to (min_hr, max_hr)

        # Training Paces (in seconds per km)
        training_paces: Dictionary mapping pace name to seconds/km
            Typical keys: easy, long, tempo, threshold, interval, race

        # Goals
        race_goal: Target race distance (e.g., "marathon", "half")
        race_date: Target race date (ISO format string)
        target_time: Target finish time (formatted string)
    """

    # Fitness metrics
    ctl: float = 0.0
    atl: float = 0.0
    tsb: float = 0.0
    acwr: float = 1.0
    risk_zone: str = "unknown"

    # Physiology
    max_hr: int = 185
    rest_hr: int = 55
    threshold_hr: int = 165
    vdot: Optional[float] = None

    # Recent training
    recent_weekly_load: float = 0.0
    recent_weekly_hours: float = 0.0
    recent_load_7d: float = 0.0
    days_since_hard: int = 0

    # Readiness
    readiness_score: float = 50.0
    readiness_zone: str = "yellow"

    # HR Zones (as tuples of (min, max))
    hr_zones: Dict[int, Tuple[int, int]] = field(default_factory=dict)

    # Training paces (in seconds per km)
    training_paces: Dict[str, int] = field(default_factory=dict)

    # Goals
    race_goal: Optional[str] = None
    race_date: Optional[str] = None
    target_time: Optional[str] = None

    def __post_init__(self):
        """Initialize default HR zones and training paces if not provided."""
        if not self.hr_zones:
            self.hr_zones = self._calculate_hr_zones()
        if not self.training_paces:
            self.training_paces = self._default_training_paces()

    def _calculate_hr_zones(self) -> Dict[int, Tuple[int, int]]:
        """Calculate HR zones using Karvonen method."""
        hr_reserve = self.max_hr - self.rest_hr
        return {
            1: (int(self.rest_hr + hr_reserve * 0.50), int(self.rest_hr + hr_reserve * 0.60)),
            2: (int(self.rest_hr + hr_reserve * 0.60), int(self.rest_hr + hr_reserve * 0.70)),
            3: (int(self.rest_hr + hr_reserve * 0.70), int(self.rest_hr + hr_reserve * 0.80)),
            4: (int(self.rest_hr + hr_reserve * 0.80), int(self.rest_hr + hr_reserve * 0.90)),
            5: (int(self.rest_hr + hr_reserve * 0.90), self.max_hr),
        }

    def _default_training_paces(self) -> Dict[str, int]:
        """Return default training paces in seconds per km."""
        return {
            "easy": 360,       # 6:00/km
            "long": 345,       # 5:45/km
            "tempo": 300,      # 5:00/km
            "threshold": 285,  # 4:45/km
            "interval": 270,   # 4:30/km
            "race": 290,       # 4:50/km
        }

    def get_hr_zone_range(self, zone: int) -> Tuple[int, int]:
        """
        Get HR range for a given zone (1-5).

        Args:
            zone: Zone number (1-5)

        Returns:
            Tuple of (min_hr, max_hr)
        """
        if zone in self.hr_zones:
            return self.hr_zones[zone]
        # Recalculate if zone not found
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
        """
        Get the appropriate pace (sec/km) for a workout type.

        Args:
            workout_type: Type of workout (easy, long, tempo, threshold, interval, race)

        Returns:
            Pace in seconds per km
        """
        pace_map = {
            "easy": self.training_paces.get("easy", 360),
            "long": self.training_paces.get("long", 345),
            "tempo": self.training_paces.get("tempo", 300),
            "threshold": self.training_paces.get("threshold", 285),
            "intervals": self.training_paces.get("interval", 270),
            "interval": self.training_paces.get("interval", 270),
            "race": self.training_paces.get("race", 290),
        }
        return pace_map.get(workout_type.lower(), self.training_paces.get("easy", 360))

    def format_pace(self, pace_sec: int) -> str:
        """
        Format pace in sec/km to mm:ss format.

        Args:
            pace_sec: Pace in seconds per km

        Returns:
            Formatted pace string (e.g., "5:30/km")
        """
        minutes = pace_sec // 60
        seconds = pace_sec % 60
        return f"{minutes}:{seconds:02d}/km"

    def format_hr_zones(self) -> str:
        """Format HR zones for prompt injection."""
        zone_strs = []
        for zone, (min_hr, max_hr) in sorted(self.hr_zones.items()):
            zone_strs.append(f"Z{zone}: {min_hr}-{max_hr} bpm")
        return ", ".join(zone_strs)

    def format_training_paces(self) -> str:
        """Format training paces for prompt injection."""
        pace_strs = []
        for name, pace_sec in self.training_paces.items():
            pace_strs.append(f"{name}: {self.format_pace(pace_sec)}")
        return ", ".join(pace_strs)

    def to_prompt_context(self) -> str:
        """Convert to formatted string for LLM prompt injection."""
        lines = [
            f"CTL: {self.ctl:.1f} | ATL: {self.atl:.1f} | TSB: {self.tsb:.1f}",
            f"ACWR: {self.acwr:.2f} | Risk Zone: {self.risk_zone}",
            f"Readiness: {self.readiness_score:.0f}/100 ({self.readiness_zone})",
        ]

        if self.vdot:
            lines.append(f"VDOT: {self.vdot:.1f}")

        if self.race_goal:
            goal_line = f"Target Race: {self.race_goal}"
            if self.target_time:
                goal_line += f" in {self.target_time}"
            if self.race_date:
                goal_line += f" on {self.race_date}"
            lines.append(goal_line)

        if self.training_paces:
            lines.append(f"Training Paces: {self.format_training_paces()}")

        lines.append(f"HR Zones: {self.format_hr_zones()}")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "ctl": self.ctl,
            "atl": self.atl,
            "tsb": self.tsb,
            "acwr": self.acwr,
            "risk_zone": self.risk_zone,
            "max_hr": self.max_hr,
            "rest_hr": self.rest_hr,
            "threshold_hr": self.threshold_hr,
            "vdot": self.vdot,
            "recent_weekly_load": self.recent_weekly_load,
            "recent_weekly_hours": self.recent_weekly_hours,
            "recent_load_7d": self.recent_load_7d,
            "days_since_hard": self.days_since_hard,
            "readiness_score": self.readiness_score,
            "readiness_zone": self.readiness_zone,
            "hr_zones": {
                f"zone{k}": {"min": v[0], "max": v[1]}
                for k, v in self.hr_zones.items()
            },
            "training_paces": {
                name: self.format_pace(pace_sec)
                for name, pace_sec in self.training_paces.items()
            },
            "race_goal": self.race_goal,
            "race_date": self.race_date,
            "target_time": self.target_time,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AthleteContext":
        """
        Create AthleteContext from dictionary.

        Args:
            data: Dictionary with athlete context data

        Returns:
            AthleteContext instance
        """
        # Handle hr_zones which might be in different formats
        hr_zones = {}
        if "hr_zones" in data:
            raw_zones = data["hr_zones"]
            if isinstance(raw_zones, dict):
                for key, value in raw_zones.items():
                    zone_num = int(key.replace("zone", "")) if isinstance(key, str) else key
                    if isinstance(value, dict):
                        hr_zones[zone_num] = (value.get("min", 0), value.get("max", 0))
                    elif isinstance(value, (list, tuple)):
                        hr_zones[zone_num] = tuple(value)

        # Handle training_paces which might be formatted strings
        training_paces = {}
        if "training_paces" in data:
            raw_paces = data["training_paces"]
            if isinstance(raw_paces, dict):
                for name, value in raw_paces.items():
                    if isinstance(value, int):
                        training_paces[name] = value
                    elif isinstance(value, str):
                        # Parse "5:30/km" format
                        parts = value.replace("/km", "").split(":")
                        if len(parts) == 2:
                            training_paces[name] = int(parts[0]) * 60 + int(parts[1])

        return cls(
            ctl=data.get("ctl", data.get("current_ctl", 0.0)),
            atl=data.get("atl", data.get("current_atl", 0.0)),
            tsb=data.get("tsb", 0.0),
            acwr=data.get("acwr", 1.0),
            risk_zone=data.get("risk_zone", "unknown"),
            max_hr=data.get("max_hr", 185),
            rest_hr=data.get("rest_hr", 55),
            threshold_hr=data.get("threshold_hr", data.get("lthr", 165)),
            vdot=data.get("vdot"),
            recent_weekly_load=data.get("recent_weekly_load", 0.0),
            recent_weekly_hours=data.get("recent_weekly_hours", 0.0),
            recent_load_7d=data.get("recent_load_7d", 0.0),
            days_since_hard=data.get("days_since_hard", 0),
            readiness_score=data.get("readiness_score", 50.0),
            readiness_zone=data.get("readiness_zone", "yellow"),
            hr_zones=hr_zones if hr_zones else {},
            training_paces=training_paces if training_paces else {},
            race_goal=data.get("race_goal"),
            race_date=data.get("race_date"),
            target_time=data.get("target_time"),
        )


# Type aliases for backward compatibility
AnalysisAthleteContext = AthleteContext
PlanAthleteContext = AthleteContext
WorkoutAthleteContext = AthleteContext
