"""Data models for wellness metrics."""

from dataclasses import dataclass, asdict
from datetime import datetime, date
from typing import Optional
import json


@dataclass
class SleepData:
    """Sleep metrics for a single night."""
    date: str
    sleep_start: Optional[str] = None
    sleep_end: Optional[str] = None
    total_sleep_seconds: int = 0
    deep_sleep_seconds: int = 0
    light_sleep_seconds: int = 0
    rem_sleep_seconds: int = 0
    awake_seconds: int = 0
    sleep_score: Optional[int] = None
    sleep_efficiency: Optional[float] = None
    avg_spo2: Optional[float] = None
    avg_respiration: Optional[float] = None

    @property
    def total_sleep_hours(self) -> float:
        return round(self.total_sleep_seconds / 3600, 2)

    @property
    def deep_sleep_pct(self) -> float:
        if self.total_sleep_seconds == 0:
            return 0
        return round(self.deep_sleep_seconds / self.total_sleep_seconds * 100, 1)

    @property
    def rem_sleep_pct(self) -> float:
        if self.total_sleep_seconds == 0:
            return 0
        return round(self.rem_sleep_seconds / self.total_sleep_seconds * 100, 1)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["total_sleep_hours"] = self.total_sleep_hours
        d["deep_sleep_pct"] = self.deep_sleep_pct
        d["rem_sleep_pct"] = self.rem_sleep_pct
        return d


@dataclass
class HRVData:
    """Heart Rate Variability metrics."""
    date: str
    hrv_weekly_avg: Optional[int] = None
    hrv_last_night_avg: Optional[int] = None
    hrv_last_night_5min_high: Optional[int] = None
    hrv_status: Optional[str] = None  # BALANCED, LOW, HIGH
    baseline_low: Optional[int] = None
    baseline_balanced_low: Optional[int] = None
    baseline_balanced_upper: Optional[int] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class StressData:
    """Stress and Body Battery metrics."""
    date: str
    avg_stress_level: Optional[int] = None
    max_stress_level: Optional[int] = None
    rest_stress_duration: int = 0
    low_stress_duration: int = 0
    medium_stress_duration: int = 0
    high_stress_duration: int = 0
    body_battery_charged: Optional[int] = None
    body_battery_drained: Optional[int] = None
    body_battery_high: Optional[int] = None
    body_battery_low: Optional[int] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ActivityData:
    """Daily activity metrics."""
    date: str
    steps: int = 0
    steps_goal: int = 10000
    total_distance_m: int = 0
    active_calories: Optional[int] = None
    total_calories: Optional[int] = None
    intensity_minutes: int = 0
    floors_climbed: int = 0

    @property
    def steps_pct(self) -> float:
        if self.steps_goal == 0:
            return 0
        return round(self.steps / self.steps_goal * 100, 1)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["steps_pct"] = self.steps_pct
        return d


@dataclass
class DailyWellness:
    """Combined daily wellness record."""
    date: str
    fetched_at: str

    # Sleep
    sleep: Optional[SleepData] = None

    # HRV
    hrv: Optional[HRVData] = None

    # Stress & Body Battery
    stress: Optional[StressData] = None

    # Activity
    activity: Optional[ActivityData] = None

    # Resting Heart Rate
    resting_heart_rate: Optional[int] = None

    # Training Readiness (if available)
    training_readiness_score: Optional[int] = None
    training_readiness_level: Optional[str] = None

    # Raw JSON for debugging
    raw_json: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "fetched_at": self.fetched_at,
            "sleep": self.sleep.to_dict() if self.sleep else None,
            "hrv": self.hrv.to_dict() if self.hrv else None,
            "stress": self.stress.to_dict() if self.stress else None,
            "activity": self.activity.to_dict() if self.activity else None,
            "resting_heart_rate": self.resting_heart_rate,
            "training_readiness_score": self.training_readiness_score,
            "training_readiness_level": self.training_readiness_level,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class TrainingReadiness:
    """Garmin Training Readiness data."""
    date: str
    score: Optional[int] = None  # 0-100
    level: Optional[str] = None  # LOW, FAIR, GOOD, PRIME
    hrv_feedback: Optional[str] = None
    sleep_feedback: Optional[str] = None
    recovery_feedback: Optional[str] = None
    acclimation_feedback: Optional[str] = None
    primary_feedback: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PersonalBaselines:
    """Personal baselines calculated from historical data."""
    date: str
    hrv_7d_avg: Optional[float] = None
    hrv_30d_avg: Optional[float] = None
    rhr_7d_avg: Optional[float] = None
    rhr_30d_avg: Optional[float] = None
    sleep_7d_avg: Optional[float] = None  # hours
    sleep_30d_avg: Optional[float] = None  # hours
    strain_7d_avg: Optional[float] = None
    recovery_7d_avg: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)
