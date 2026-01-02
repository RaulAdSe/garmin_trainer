# Sports Science Features - Implementation Specification

## Overview

This document provides detailed implementation specifications for advanced sports science features in the trAIner workout app. Each feature includes Python code, database schemas, API endpoints, and mathematical formulas.

---

## Table of Contents

1. [Pace Zones (Daniels' VDOT)](#1-pace-zones-daniels-vdot)
2. [Enhanced Recovery Module](#2-enhanced-recovery-module)
3. [Running Economy Tracking](#3-running-economy-tracking)
4. [Cardiac Drift Detection](#4-cardiac-drift-detection)
5. [Exponential Taper Implementation](#5-exponential-taper-implementation)
6. [Race Pacing Strategy Generator](#6-race-pacing-strategy-generator)

---

## 1. Pace Zones (Daniels' VDOT)

### File Structure

```
training-analyzer/src/
  metrics/
    vdot.py              # VDOT calculations and pace zones
  api/routes/
    pace_zones.py        # API endpoints
```

### 1.1 Core VDOT Module

**File: `/training-analyzer/src/metrics/vdot.py`**

```python
"""
Daniels' VDOT pace zone calculations.

VDOT is a measure of running ability developed by Jack Daniels.
It allows prediction of race times and calculation of optimal training paces.
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum


class RaceDistance(Enum):
    """Standard race distances with meters."""
    MILE = 1609.34
    FIVE_K = 5000
    TEN_K = 10000
    HALF_MARATHON = 21097.5
    MARATHON = 42195


@dataclass
class PaceZone:
    """A single pace training zone."""
    name: str
    description: str
    min_pace_sec_km: int  # Slowest pace (sec/km)
    max_pace_sec_km: int  # Fastest pace (sec/km)
    purpose: str
    typical_duration: str
    hr_zone_correlation: str


@dataclass
class VDOTPaceZones:
    """Complete VDOT-based pace zones for an athlete."""
    vdot: float
    easy: PaceZone
    marathon: PaceZone
    threshold: PaceZone
    interval: PaceZone
    repetition: PaceZone

    def to_dict(self) -> Dict:
        return {
            "vdot": round(self.vdot, 1),
            "zones": {
                "easy": self._zone_to_dict(self.easy),
                "marathon": self._zone_to_dict(self.marathon),
                "threshold": self._zone_to_dict(self.threshold),
                "interval": self._zone_to_dict(self.interval),
                "repetition": self._zone_to_dict(self.repetition),
            }
        }

    def _zone_to_dict(self, zone: PaceZone) -> Dict:
        return {
            "name": zone.name,
            "description": zone.description,
            "min_pace_sec_km": zone.min_pace_sec_km,
            "max_pace_sec_km": zone.max_pace_sec_km,
            "min_pace_formatted": format_pace(zone.min_pace_sec_km),
            "max_pace_formatted": format_pace(zone.max_pace_sec_km),
            "purpose": zone.purpose,
            "typical_duration": zone.typical_duration,
            "hr_zone_correlation": zone.hr_zone_correlation,
        }


def format_pace(sec_per_km: int) -> str:
    """Format pace as M:SS/km."""
    minutes = sec_per_km // 60
    seconds = sec_per_km % 60
    return f"{minutes}:{seconds:02d}/km"


def calculate_vdot_from_race(
    time_seconds: int,
    distance: RaceDistance
) -> float:
    """
    Calculate VDOT from a race performance.

    Uses Daniels' formula:
    VDOT = (-4.60 + 0.182258 * v + 0.000104 * v^2) /
           (0.8 + 0.1894393 * e^(-0.012778 * t) + 0.2989558 * e^(-0.1932605 * t))

    Where:
    - v = velocity in meters/minute
    - t = time in minutes

    Args:
        time_seconds: Race finish time in seconds
        distance: Race distance enum

    Returns:
        VDOT value (typically 30-85 for recreational to elite runners)
    """
    distance_m = distance.value
    time_min = time_seconds / 60

    # Velocity in meters per minute
    velocity = distance_m / time_min

    # Percent VO2max based on race time (Daniels' formula for %VO2max)
    # This represents the fraction of VO2max that can be sustained
    pct_vo2max = (
        0.8 +
        0.1894393 * math.exp(-0.012778 * time_min) +
        0.2989558 * math.exp(-0.1932605 * time_min)
    )

    # VO2 at race velocity (ml/kg/min)
    vo2_at_velocity = (
        -4.60 +
        0.182258 * velocity +
        0.000104 * velocity ** 2
    )

    # VDOT = VO2 at velocity / percent of VO2max used
    vdot = vo2_at_velocity / pct_vo2max

    return vdot


def predict_race_time(vdot: float, distance: RaceDistance) -> int:
    """
    Predict race time from VDOT using inverse of the calculation.

    Uses iterative Newton-Raphson method to find time that produces given VDOT.

    Args:
        vdot: Athlete's VDOT value
        distance: Target race distance

    Returns:
        Predicted race time in seconds
    """
    distance_m = distance.value

    # Initial guess based on simple linear approximation
    # Typical running speed correlates roughly with VDOT
    initial_velocity = 3.0 * vdot  # m/min approximation
    time_guess = distance_m / initial_velocity

    # Newton-Raphson iteration
    for _ in range(20):
        current_vdot = calculate_vdot_from_race(int(time_guess * 60), distance)
        error = current_vdot - vdot

        if abs(error) < 0.01:
            break

        # Adjust time: if VDOT is too high, we ran too fast (need more time)
        # Sensitivity: ~0.1 VDOT per 1% time change
        time_guess *= (1 + error / vdot * 0.5)

    return int(time_guess * 60)


def calculate_pace_zones(vdot: float) -> VDOTPaceZones:
    """
    Calculate Daniels' 5 pace zones from VDOT.

    Zone definitions (from Jack Daniels' Running Formula):

    1. Easy (E): 59-74% VO2max
       - Purpose: Recovery, aerobic development
       - Typical: 20-150 minutes continuous

    2. Marathon (M): 75-84% VO2max
       - Purpose: Race-specific endurance
       - Typical: 40-110 minutes

    3. Threshold (T): 83-88% VO2max (lactate threshold)
       - Purpose: Improve lactate clearance
       - Typical: 20-60 minutes (tempo) or 3-15 min intervals

    4. Interval (I): 95-100% VO2max
       - Purpose: Improve VO2max
       - Typical: 3-5 minute repeats

    5. Repetition (R): 105-120% VO2max
       - Purpose: Running economy, speed
       - Typical: 200m-400m repeats

    Args:
        vdot: Athlete's VDOT value

    Returns:
        VDOTPaceZones with all five zones
    """
    # Calculate velocity at VO2max (m/min)
    # Inverse of the VO2-velocity relationship
    # VO2 = -4.60 + 0.182258*v + 0.000104*v^2
    # Solving for v when VO2 = VDOT
    a = 0.000104
    b = 0.182258
    c = -4.60 - vdot

    vo2max_velocity = (-b + math.sqrt(b**2 - 4*a*c)) / (2*a)  # m/min

    # Zone velocities as fractions of VO2max velocity
    # These correspond to the %VO2max targets
    zone_fractions = {
        "easy_slow": 0.59,
        "easy_fast": 0.74,
        "marathon_slow": 0.75,
        "marathon_fast": 0.84,
        "threshold_slow": 0.83,
        "threshold_fast": 0.88,
        "interval_slow": 0.95,
        "interval_fast": 1.00,
        "repetition_slow": 1.00,
        "repetition_fast": 1.10,
    }

    def velocity_to_pace(velocity_mpm: float) -> int:
        """Convert m/min to sec/km."""
        if velocity_mpm <= 0:
            return 600  # 10:00/km fallback
        km_per_min = velocity_mpm / 1000
        return int(60 / km_per_min)

    # Velocity at each %VO2max requires the inverse relationship
    # %VO2 = (VO2_at_v / VO2max)
    # We solve for v given target %VO2
    def velocity_at_pct_vo2(pct: float) -> float:
        """Calculate velocity at given %VO2max."""
        target_vo2 = vdot * pct
        # Solve: target_vo2 = -4.60 + 0.182258*v + 0.000104*v^2
        c = -4.60 - target_vo2
        return (-b + math.sqrt(b**2 - 4*a*c)) / (2*a)

    # Calculate pace ranges for each zone
    easy = PaceZone(
        name="Easy",
        description="Comfortable, conversational pace",
        min_pace_sec_km=velocity_to_pace(velocity_at_pct_vo2(0.74)),  # faster end
        max_pace_sec_km=velocity_to_pace(velocity_at_pct_vo2(0.59)),  # slower end
        purpose="Aerobic development, active recovery, injury prevention",
        typical_duration="30-150 minutes",
        hr_zone_correlation="Zone 1-2 (65-75% max HR)",
    )

    marathon = PaceZone(
        name="Marathon",
        description="Goal marathon race pace",
        min_pace_sec_km=velocity_to_pace(velocity_at_pct_vo2(0.84)),
        max_pace_sec_km=velocity_to_pace(velocity_at_pct_vo2(0.75)),
        purpose="Marathon-specific endurance, fuel efficiency",
        typical_duration="40-90 minutes in training",
        hr_zone_correlation="Zone 2-3 (75-82% max HR)",
    )

    threshold = PaceZone(
        name="Threshold",
        description="Comfortably hard, lactate threshold pace",
        min_pace_sec_km=velocity_to_pace(velocity_at_pct_vo2(0.88)),
        max_pace_sec_km=velocity_to_pace(velocity_at_pct_vo2(0.83)),
        purpose="Improve lactate clearance, sustainable speed",
        typical_duration="20-40 min tempo or 5-15 min cruise intervals",
        hr_zone_correlation="Zone 4 (82-88% max HR)",
    )

    interval = PaceZone(
        name="Interval",
        description="Hard, VO2max development pace",
        min_pace_sec_km=velocity_to_pace(velocity_at_pct_vo2(1.00)),
        max_pace_sec_km=velocity_to_pace(velocity_at_pct_vo2(0.95)),
        purpose="Maximize aerobic capacity (VO2max)",
        typical_duration="3-5 minute repeats, equal recovery",
        hr_zone_correlation="Zone 5 (88-95% max HR)",
    )

    repetition = PaceZone(
        name="Repetition",
        description="Fast, neuromuscular/economy work",
        min_pace_sec_km=velocity_to_pace(velocity_at_pct_vo2(1.10)),
        max_pace_sec_km=velocity_to_pace(velocity_at_pct_vo2(1.00)),
        purpose="Improve running economy, leg speed, anaerobic capacity",
        typical_duration="200-400m repeats, full recovery",
        hr_zone_correlation="Above Zone 5 (anaerobic)",
    )

    return VDOTPaceZones(
        vdot=vdot,
        easy=easy,
        marathon=marathon,
        threshold=threshold,
        interval=interval,
        repetition=repetition,
    )


def calculate_equivalent_performances(vdot: float) -> Dict[str, Dict]:
    """
    Calculate equivalent race performances across distances.

    Returns predicted times for common race distances at the given VDOT.
    """
    performances = {}

    for distance in RaceDistance:
        time_sec = predict_race_time(vdot, distance)
        hours = time_sec // 3600
        minutes = (time_sec % 3600) // 60
        seconds = time_sec % 60

        if hours > 0:
            formatted = f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            formatted = f"{minutes}:{seconds:02d}"

        pace_sec_km = int(time_sec / (distance.value / 1000))

        performances[distance.name.lower()] = {
            "distance_m": distance.value,
            "time_seconds": time_sec,
            "time_formatted": formatted,
            "pace_sec_km": pace_sec_km,
            "pace_formatted": format_pace(pace_sec_km),
        }

    return performances


def estimate_vdot_improvement(
    current_vdot: float,
    weeks_training: int,
    training_quality: str = "moderate"
) -> float:
    """
    Estimate VDOT improvement over a training period.

    Based on typical adaptation rates:
    - Beginners: 1-2 VDOT per 8 weeks
    - Intermediate: 0.5-1 VDOT per 8 weeks
    - Advanced: 0.2-0.5 VDOT per 8 weeks

    Args:
        current_vdot: Starting VDOT
        weeks_training: Weeks of consistent training
        training_quality: "low", "moderate", "high"

    Returns:
        Projected VDOT after training period
    """
    # Improvement rate decreases with higher VDOT (diminishing returns)
    if current_vdot < 35:
        base_rate = 0.15  # VDOT per week
    elif current_vdot < 45:
        base_rate = 0.10
    elif current_vdot < 55:
        base_rate = 0.06
    elif current_vdot < 65:
        base_rate = 0.03
    else:
        base_rate = 0.015

    # Adjust for training quality
    quality_multipliers = {
        "low": 0.5,
        "moderate": 1.0,
        "high": 1.5,
    }
    multiplier = quality_multipliers.get(training_quality, 1.0)

    # Apply diminishing returns over time
    total_improvement = 0
    for week in range(weeks_training):
        weekly_gain = base_rate * multiplier * (0.98 ** week)  # 2% weekly decay
        total_improvement += weekly_gain

    return current_vdot + total_improvement
```

### 1.2 API Endpoints

**File: `/training-analyzer/src/api/routes/pace_zones.py`**

```python
"""Pace zones API endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import get_current_user, get_training_db, CurrentUser
from ...metrics.vdot import (
    calculate_vdot_from_race,
    calculate_pace_zones,
    calculate_equivalent_performances,
    RaceDistance,
    format_pace,
)


router = APIRouter(prefix="/pace-zones", tags=["pace-zones"])


class RaceTimeInput(BaseModel):
    """Input for VDOT calculation from race time."""
    distance: str = Field(..., description="Race distance: mile, 5k, 10k, half, marathon")
    time_seconds: int = Field(..., ge=60, description="Race time in seconds")


class VDOTResponse(BaseModel):
    """VDOT calculation response."""
    vdot: float
    equivalent_performances: dict
    pace_zones: dict


class PaceZonesResponse(BaseModel):
    """Pace zones for a given VDOT."""
    vdot: float
    zones: dict


@router.post("/calculate-vdot", response_model=VDOTResponse)
async def calculate_vdot(
    race_input: RaceTimeInput,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Calculate VDOT from a race performance.

    Provide a recent race time to get your VDOT score and all derived
    training paces according to Jack Daniels' methodology.
    """
    # Map distance string to enum
    distance_map = {
        "mile": RaceDistance.MILE,
        "5k": RaceDistance.FIVE_K,
        "10k": RaceDistance.TEN_K,
        "half": RaceDistance.HALF_MARATHON,
        "half_marathon": RaceDistance.HALF_MARATHON,
        "marathon": RaceDistance.MARATHON,
    }

    distance = distance_map.get(race_input.distance.lower())
    if not distance:
        raise HTTPException(400, f"Invalid distance: {race_input.distance}")

    vdot = calculate_vdot_from_race(race_input.time_seconds, distance)
    zones = calculate_pace_zones(vdot)
    equivalents = calculate_equivalent_performances(vdot)

    return VDOTResponse(
        vdot=round(vdot, 1),
        equivalent_performances=equivalents,
        pace_zones=zones.to_dict()["zones"],
    )


@router.get("/zones/{vdot}", response_model=PaceZonesResponse)
async def get_pace_zones(
    vdot: float = Query(..., ge=20, le=90, description="VDOT value"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Get pace zones for a given VDOT value.

    Use this if you already know your VDOT and want to see the training paces.
    """
    zones = calculate_pace_zones(vdot)
    return PaceZonesResponse(
        vdot=round(vdot, 1),
        zones=zones.to_dict()["zones"],
    )


@router.get("/my-zones", response_model=PaceZonesResponse)
async def get_my_pace_zones(
    current_user: CurrentUser = Depends(get_current_user),
    training_db = Depends(get_training_db),
):
    """
    Get pace zones based on athlete's current fitness data.

    Uses Garmin VO2max or race goal to estimate VDOT.
    """
    # Try Garmin VO2max first
    latest_garmin = training_db.get_latest_garmin_fitness_data()

    if latest_garmin and latest_garmin.vo2max_running:
        # VO2max roughly equals VDOT for well-trained runners
        vdot = latest_garmin.vo2max_running
    else:
        # Fall back to race goals
        goals = training_db.get_race_goals(upcoming_only=True)
        if not goals:
            raise HTTPException(
                404,
                "No fitness data available. Sync Garmin or set a race goal."
            )

        # Use first goal to estimate VDOT
        goal = goals[0]
        distance_map = {
            "5k": RaceDistance.FIVE_K,
            "10k": RaceDistance.TEN_K,
            "half": RaceDistance.HALF_MARATHON,
            "marathon": RaceDistance.MARATHON,
        }
        distance = distance_map.get(goal["distance"], RaceDistance.TEN_K)
        vdot = calculate_vdot_from_race(goal["target_time_sec"], distance)

    zones = calculate_pace_zones(vdot)
    return PaceZonesResponse(
        vdot=round(vdot, 1),
        zones=zones.to_dict()["zones"],
    )
```

---

## 2. Enhanced Recovery Module

### File Structure

```
training-analyzer/src/
  services/
    recovery_service.py    # Enhanced recovery calculations
  api/routes/
    recovery.py           # Recovery API endpoints
```

### 2.1 Recovery Service

**File: `/training-analyzer/src/services/recovery_service.py`**

```python
"""
Enhanced Recovery Module with sleep debt, HRV analysis, and multi-factor scoring.

Based on sports science research:
- Sleep debt: Belenky et al. (2003) - cumulative sleep restriction effects
- HRV analysis: Plews et al. (2013) - HRV monitoring in athletes
- Recovery estimation: Banister (1991) - impulse-response model
"""

import math
import statistics
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple


class WorkoutType(str, Enum):
    """Workout types with recovery impact."""
    EASY = "easy"
    LONG = "long"
    TEMPO = "tempo"
    THRESHOLD = "threshold"
    INTERVALS = "intervals"
    HILLS = "hills"
    RACE = "race"


@dataclass
class SleepData:
    """Daily sleep data."""
    date: date
    hours_slept: float
    sleep_quality: Optional[float] = None  # 0-100
    deep_sleep_pct: Optional[float] = None
    rem_sleep_pct: Optional[float] = None
    awakenings: Optional[int] = None


@dataclass
class HRVData:
    """Daily HRV measurement."""
    date: date
    rmssd: float  # Root mean square of successive differences (ms)
    sdnn: Optional[float] = None  # Standard deviation of NN intervals
    morning_hr: Optional[int] = None  # Resting HR at measurement


@dataclass
class SleepDebtAnalysis:
    """Sleep debt analysis result."""
    current_debt_hours: float
    trend: str  # "accumulating", "stable", "recovering"
    days_analyzed: int
    avg_sleep_hours: float
    target_sleep_hours: float
    recovery_impact: str  # "minimal", "moderate", "significant", "severe"
    recommendation: str


@dataclass
class HRVTrendAnalysis:
    """HRV trend analysis result."""
    current_rmssd: float
    baseline_rmssd: float
    cv_percent: float  # Coefficient of variation
    trend: str  # "improving", "stable", "declining", "highly_variable"
    days_analyzed: int
    readiness_signal: str  # "good", "normal", "caution", "warning"
    recommendation: str


@dataclass
class RecoveryTimeEstimate:
    """Recovery time estimate for a workout."""
    workout_type: WorkoutType
    base_recovery_hours: float
    adjusted_recovery_hours: float
    factors: Dict[str, float]  # Multipliers applied
    ready_for_easy: datetime
    ready_for_hard: datetime
    confidence: float  # 0-1


@dataclass
class RecoveryScore:
    """Multi-factor recovery score."""
    overall_score: float  # 0-100
    components: Dict[str, float]  # Individual scores
    weights: Dict[str, float]  # Weights used
    limiting_factor: str
    status: str  # "optimal", "good", "moderate", "poor", "critical"
    recommendation: str


class RecoveryService:
    """
    Enhanced recovery analysis service.

    Combines multiple recovery indicators:
    1. Sleep debt (7-day rolling)
    2. HRV trends with CV analysis
    3. Training load history
    4. Subjective metrics
    """

    # Default sleep target by age group
    SLEEP_TARGETS = {
        "18-25": 8.0,
        "26-35": 7.5,
        "36-45": 7.0,
        "46-55": 7.0,
        "56+": 7.0,
    }

    # Base recovery hours by workout type
    BASE_RECOVERY_HOURS = {
        WorkoutType.EASY: 12,
        WorkoutType.LONG: 36,
        WorkoutType.TEMPO: 24,
        WorkoutType.THRESHOLD: 24,
        WorkoutType.INTERVALS: 36,
        WorkoutType.HILLS: 30,
        WorkoutType.RACE: 72,  # Full marathon equivalent
    }

    # Recovery score weights
    DEFAULT_WEIGHTS = {
        "sleep": 0.25,
        "hrv": 0.25,
        "training_load": 0.25,
        "subjective": 0.15,
        "time_since_hard": 0.10,
    }

    def __init__(self):
        self._sleep_history: List[SleepData] = []
        self._hrv_history: List[HRVData] = []
        self._hrv_baseline: Optional[float] = None

    def calculate_sleep_debt(
        self,
        sleep_data: List[SleepData],
        target_hours: float = 7.5,
        rolling_days: int = 7,
    ) -> SleepDebtAnalysis:
        """
        Calculate rolling sleep debt.

        Sleep debt formula:
        debt = sum(target - actual) for past N days

        Research shows:
        - <5 hours debt: minimal impact
        - 5-10 hours: moderate impairment
        - 10-20 hours: significant impairment
        - >20 hours: severe impairment

        Args:
            sleep_data: List of daily sleep records
            target_hours: Target sleep per night
            rolling_days: Days to analyze (default 7)

        Returns:
            SleepDebtAnalysis with current debt and recommendations
        """
        if not sleep_data:
            return SleepDebtAnalysis(
                current_debt_hours=0,
                trend="unknown",
                days_analyzed=0,
                avg_sleep_hours=0,
                target_sleep_hours=target_hours,
                recovery_impact="unknown",
                recommendation="No sleep data available",
            )

        # Sort by date and take last N days
        sorted_data = sorted(sleep_data, key=lambda x: x.date)[-rolling_days:]

        # Calculate debt
        total_deficit = sum(
            target_hours - s.hours_slept
            for s in sorted_data
        )

        avg_sleep = statistics.mean(s.hours_slept for s in sorted_data)

        # Determine trend (compare first half vs second half)
        if len(sorted_data) >= 4:
            mid = len(sorted_data) // 2
            first_half_avg = statistics.mean(s.hours_slept for s in sorted_data[:mid])
            second_half_avg = statistics.mean(s.hours_slept for s in sorted_data[mid:])

            if second_half_avg > first_half_avg + 0.3:
                trend = "recovering"
            elif second_half_avg < first_half_avg - 0.3:
                trend = "accumulating"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        # Determine impact level
        if total_deficit < 5:
            impact = "minimal"
            recommendation = "Sleep debt is manageable. Maintain current habits."
        elif total_deficit < 10:
            impact = "moderate"
            recommendation = "Consider adding 30-60 min sleep nightly to recover."
        elif total_deficit < 20:
            impact = "significant"
            recommendation = "Reduce training intensity. Prioritize 8+ hours sleep."
        else:
            impact = "severe"
            recommendation = "Take rest days. Sleep debt is affecting recovery capacity."

        return SleepDebtAnalysis(
            current_debt_hours=round(total_deficit, 1),
            trend=trend,
            days_analyzed=len(sorted_data),
            avg_sleep_hours=round(avg_sleep, 1),
            target_sleep_hours=target_hours,
            recovery_impact=impact,
            recommendation=recommendation,
        )

    def analyze_hrv_trend(
        self,
        hrv_data: List[HRVData],
        baseline_days: int = 30,
        analysis_days: int = 7,
    ) -> HRVTrendAnalysis:
        """
        Analyze HRV trends with coefficient of variation.

        Key metrics:
        - RMSSD: Primary parasympathetic indicator
        - CV (coefficient of variation): Measures day-to-day variability
          - CV < 5%: Very stable (possible ceiling effect)
          - CV 5-10%: Normal, healthy variability
          - CV > 10%: High variability (stress, recovery issues)

        Trend interpretation:
        - RMSSD increasing + low CV: Good adaptation
        - RMSSD stable + normal CV: Maintenance
        - RMSSD decreasing OR high CV: Possible overreaching

        Args:
            hrv_data: List of HRV measurements
            baseline_days: Days to establish baseline (default 30)
            analysis_days: Recent days to analyze (default 7)

        Returns:
            HRVTrendAnalysis with trend and recommendations
        """
        if len(hrv_data) < 7:
            return HRVTrendAnalysis(
                current_rmssd=hrv_data[-1].rmssd if hrv_data else 0,
                baseline_rmssd=0,
                cv_percent=0,
                trend="insufficient_data",
                days_analyzed=len(hrv_data),
                readiness_signal="unknown",
                recommendation="Need at least 7 days of HRV data for analysis.",
            )

        sorted_data = sorted(hrv_data, key=lambda x: x.date)

        # Calculate baseline (rolling 30-day or available)
        baseline_data = sorted_data[-baseline_days:]
        baseline_rmssd = statistics.mean(h.rmssd for h in baseline_data)

        # Analyze recent period
        recent_data = sorted_data[-analysis_days:]
        recent_rmssd = [h.rmssd for h in recent_data]
        current_rmssd = recent_rmssd[-1]
        recent_mean = statistics.mean(recent_rmssd)

        # Calculate coefficient of variation
        if len(recent_rmssd) >= 2:
            recent_std = statistics.stdev(recent_rmssd)
            cv_percent = (recent_std / recent_mean) * 100
        else:
            cv_percent = 0

        # Determine trend
        pct_change = ((recent_mean - baseline_rmssd) / baseline_rmssd) * 100 if baseline_rmssd > 0 else 0

        if cv_percent > 15:
            trend = "highly_variable"
            readiness = "warning"
            recommendation = "High HRV variability suggests stress or recovery issues. Consider easy training."
        elif pct_change > 5:
            trend = "improving"
            readiness = "good"
            recommendation = "HRV trending up indicates good recovery. Can push training if feeling good."
        elif pct_change < -5:
            trend = "declining"
            readiness = "caution"
            recommendation = "HRV trending down. Monitor fatigue and consider reducing load."
        else:
            trend = "stable"
            readiness = "normal"
            recommendation = "HRV stable within normal range. Continue planned training."

        return HRVTrendAnalysis(
            current_rmssd=round(current_rmssd, 1),
            baseline_rmssd=round(baseline_rmssd, 1),
            cv_percent=round(cv_percent, 1),
            trend=trend,
            days_analyzed=len(recent_data),
            readiness_signal=readiness,
            recommendation=recommendation,
        )

    def estimate_recovery_time(
        self,
        workout_type: WorkoutType,
        workout_load: float,
        athlete_ctl: float,
        sleep_debt_hours: float = 0,
        hrv_status: str = "normal",
        age: int = 30,
    ) -> RecoveryTimeEstimate:
        """
        Estimate recovery time for a workout.

        Base recovery adjusted by:
        - Workout intensity relative to fitness (load/CTL ratio)
        - Sleep debt
        - HRV status
        - Age

        Formula:
        adjusted_hours = base_hours * intensity_factor * sleep_factor * hrv_factor * age_factor

        Args:
            workout_type: Type of workout performed
            workout_load: HRSS/TSS of the workout
            athlete_ctl: Chronic Training Load (fitness level)
            sleep_debt_hours: Current sleep debt
            hrv_status: "good", "normal", "caution", "warning"
            age: Athlete age in years

        Returns:
            RecoveryTimeEstimate with adjusted recovery times
        """
        base_hours = self.BASE_RECOVERY_HOURS[workout_type]
        factors = {}

        # Intensity factor: how hard was this relative to fitness
        if athlete_ctl > 0:
            intensity_ratio = workout_load / athlete_ctl
            if intensity_ratio > 1.5:
                intensity_factor = 1.5
            elif intensity_ratio > 1.0:
                intensity_factor = 1.0 + (intensity_ratio - 1.0) * 0.5
            else:
                intensity_factor = 0.8 + intensity_ratio * 0.2
        else:
            intensity_factor = 1.2  # Conservative for new athletes
        factors["intensity"] = round(intensity_factor, 2)

        # Sleep debt factor
        if sleep_debt_hours < 5:
            sleep_factor = 1.0
        elif sleep_debt_hours < 10:
            sleep_factor = 1.15
        elif sleep_debt_hours < 20:
            sleep_factor = 1.3
        else:
            sleep_factor = 1.5
        factors["sleep_debt"] = round(sleep_factor, 2)

        # HRV factor
        hrv_factors = {
            "good": 0.9,
            "normal": 1.0,
            "caution": 1.2,
            "warning": 1.4,
        }
        hrv_factor = hrv_factors.get(hrv_status, 1.0)
        factors["hrv"] = round(hrv_factor, 2)

        # Age factor (recovery slows ~1% per year after 30)
        if age > 30:
            age_factor = 1.0 + (age - 30) * 0.01
        else:
            age_factor = 1.0
        age_factor = min(age_factor, 1.5)  # Cap at 50% increase
        factors["age"] = round(age_factor, 2)

        # Calculate adjusted recovery
        adjusted_hours = base_hours * intensity_factor * sleep_factor * hrv_factor * age_factor

        # Calculate ready times
        now = datetime.now()
        ready_easy = now + timedelta(hours=adjusted_hours * 0.5)
        ready_hard = now + timedelta(hours=adjusted_hours)

        # Confidence based on data availability
        confidence = 0.7  # Base confidence
        if sleep_debt_hours == 0:
            confidence -= 0.1  # No sleep data
        if hrv_status == "unknown":
            confidence -= 0.1  # No HRV data

        return RecoveryTimeEstimate(
            workout_type=workout_type,
            base_recovery_hours=base_hours,
            adjusted_recovery_hours=round(adjusted_hours, 1),
            factors=factors,
            ready_for_easy=ready_easy,
            ready_for_hard=ready_hard,
            confidence=round(confidence, 2),
        )

    def calculate_recovery_score(
        self,
        sleep_score: float,
        hrv_score: float,
        training_load_score: float,
        subjective_score: Optional[float] = None,
        hours_since_hard: Optional[float] = None,
        weights: Optional[Dict[str, float]] = None,
    ) -> RecoveryScore:
        """
        Calculate multi-factor recovery score (0-100).

        Components:
        1. Sleep score: Based on quantity and quality
        2. HRV score: Based on current vs baseline
        3. Training load score: Based on TSB (form)
        4. Subjective score: Self-reported wellness
        5. Time since hard workout

        Args:
            sleep_score: 0-100 based on sleep analysis
            hrv_score: 0-100 based on HRV analysis
            training_load_score: 0-100 based on TSB
            subjective_score: 0-100 self-reported (optional)
            hours_since_hard: Hours since last hard workout (optional)
            weights: Custom component weights (optional)

        Returns:
            RecoveryScore with overall score and components
        """
        w = weights or self.DEFAULT_WEIGHTS.copy()

        components = {
            "sleep": sleep_score,
            "hrv": hrv_score,
            "training_load": training_load_score,
        }

        # Handle optional components
        if subjective_score is not None:
            components["subjective"] = subjective_score
        else:
            # Redistribute weight
            w["sleep"] += w["subjective"] / 3
            w["hrv"] += w["subjective"] / 3
            w["training_load"] += w["subjective"] / 3
            w["subjective"] = 0

        if hours_since_hard is not None:
            # Convert hours to score (48+ hours = 100)
            time_score = min(100, (hours_since_hard / 48) * 100)
            components["time_since_hard"] = time_score
        else:
            # Redistribute weight
            w["training_load"] += w["time_since_hard"]
            w["time_since_hard"] = 0

        # Calculate weighted score
        overall = sum(components.get(k, 0) * w.get(k, 0) for k in components)

        # Identify limiting factor
        limiting_factor = min(components, key=lambda k: components[k])

        # Determine status
        if overall >= 80:
            status = "optimal"
            recommendation = "Fully recovered. Ready for any workout intensity."
        elif overall >= 60:
            status = "good"
            recommendation = "Well recovered. Can train as planned."
        elif overall >= 40:
            status = "moderate"
            recommendation = f"Partial recovery. Consider easier training. {limiting_factor.replace('_', ' ').title()} is the limiting factor."
        elif overall >= 20:
            status = "poor"
            recommendation = f"Recovery compromised. Light activity only. Focus on improving {limiting_factor.replace('_', ' ')}."
        else:
            status = "critical"
            recommendation = "Rest day strongly recommended. Multiple recovery factors are low."

        return RecoveryScore(
            overall_score=round(overall, 1),
            components={k: round(v, 1) for k, v in components.items()},
            weights=w,
            limiting_factor=limiting_factor,
            status=status,
            recommendation=recommendation,
        )

    def sleep_hours_to_score(self, hours: float, target: float = 7.5) -> float:
        """Convert sleep hours to 0-100 score."""
        ratio = hours / target
        if ratio >= 1.0:
            return min(100, 80 + ratio * 20)  # Bonus for extra sleep
        elif ratio >= 0.8:
            return 60 + (ratio - 0.8) / 0.2 * 20
        elif ratio >= 0.6:
            return 30 + (ratio - 0.6) / 0.2 * 30
        else:
            return ratio / 0.6 * 30

    def hrv_to_score(self, current: float, baseline: float) -> float:
        """Convert HRV reading to 0-100 score based on baseline."""
        if baseline <= 0:
            return 50  # No baseline

        ratio = current / baseline
        if ratio >= 1.1:
            return min(100, 85 + (ratio - 1.1) * 50)
        elif ratio >= 0.95:
            return 70 + (ratio - 0.95) / 0.15 * 15
        elif ratio >= 0.85:
            return 50 + (ratio - 0.85) / 0.10 * 20
        elif ratio >= 0.75:
            return 30 + (ratio - 0.75) / 0.10 * 20
        else:
            return max(0, ratio / 0.75 * 30)

    def tsb_to_score(self, tsb: float) -> float:
        """Convert Training Stress Balance to 0-100 recovery score."""
        # TSB range: typically -30 to +30
        # Positive = fresh, negative = fatigued
        if tsb > 20:
            return 90 + min(10, tsb - 20)  # Very fresh
        elif tsb > 10:
            return 75 + (tsb - 10)
        elif tsb > 0:
            return 60 + tsb * 1.5
        elif tsb > -10:
            return 45 + tsb * 1.5
        elif tsb > -20:
            return 25 + (tsb + 10) * 2
        else:
            return max(0, 10 + (tsb + 20) * 0.5)
```

### 2.2 Database Schema Changes

**Add to `/training-analyzer/src/db/schema.py`:**

```sql
-- ========================================================================
-- Enhanced Recovery Module Tables
-- ========================================================================

-- Daily sleep data
CREATE TABLE IF NOT EXISTS sleep_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT DEFAULT 'default',
    date TEXT NOT NULL,
    hours_slept REAL NOT NULL,
    sleep_quality REAL,           -- 0-100
    deep_sleep_pct REAL,
    rem_sleep_pct REAL,
    awakenings INTEGER,
    bedtime TEXT,                 -- ISO timestamp
    wake_time TEXT,               -- ISO timestamp
    source TEXT DEFAULT 'manual', -- 'garmin', 'apple', 'manual'
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, date)
);

-- Daily HRV measurements
CREATE TABLE IF NOT EXISTS hrv_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT DEFAULT 'default',
    date TEXT NOT NULL,
    rmssd REAL NOT NULL,          -- Primary metric (ms)
    sdnn REAL,                    -- Optional
    morning_hr INTEGER,           -- Resting HR at measurement
    measurement_time TEXT,        -- When measured
    source TEXT DEFAULT 'manual', -- 'garmin', 'whoop', 'oura', 'manual'
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, date)
);

-- Recovery scores (calculated daily)
CREATE TABLE IF NOT EXISTS recovery_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT DEFAULT 'default',
    date TEXT NOT NULL,
    overall_score REAL NOT NULL,  -- 0-100
    sleep_score REAL,
    hrv_score REAL,
    training_load_score REAL,
    subjective_score REAL,
    status TEXT,                  -- 'optimal', 'good', 'moderate', 'poor', 'critical'
    limiting_factor TEXT,
    recommendation TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, date)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_sleep_data_date ON sleep_data(user_id, date);
CREATE INDEX IF NOT EXISTS idx_hrv_data_date ON hrv_data(user_id, date);
CREATE INDEX IF NOT EXISTS idx_recovery_scores_date ON recovery_scores(user_id, date);
```

---

## 3. Running Economy Tracking

### File Structure

```
training-analyzer/src/
  metrics/
    running_economy.py    # Economy calculations
  api/routes/
    economy.py           # API endpoints
```

### 3.1 Running Economy Module

**File: `/training-analyzer/src/metrics/running_economy.py`**

```python
"""
Running Economy Tracking Module.

Running economy (RE) measures how efficiently you use oxygen at a given pace.
Better economy = less oxygen needed = faster sustainable pace.

Key metrics:
- Pace-to-HR ratio: Primary efficiency indicator
- Economy score: Normalized metric for tracking
- Efficiency Factor (EF): Power-to-HR ratio for power runners
"""

import statistics
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple


@dataclass
class EconomyDataPoint:
    """Single economy measurement from a workout."""
    date: date
    workout_id: str
    avg_pace_sec_km: int
    avg_hr: int
    duration_min: float
    distance_km: float
    elevation_gain_m: Optional[float] = None
    temperature_c: Optional[float] = None

    @property
    def pace_hr_ratio(self) -> float:
        """
        Pace-to-HR ratio (lower = better economy).

        Normalized: seconds/km divided by HR
        """
        if self.avg_hr <= 0:
            return 0
        return self.avg_pace_sec_km / self.avg_hr


@dataclass
class NormalizedEconomyPoint:
    """Economy normalized to a standard intensity."""
    date: date
    workout_id: str
    raw_ratio: float
    normalized_ratio: float
    hr_pct_of_max: float
    adjustments: Dict[str, float]


@dataclass
class EconomyTrend:
    """Economy trend analysis."""
    current_score: float
    baseline_score: float
    change_percent: float
    trend: str  # "improving", "stable", "declining"
    days_analyzed: int
    data_points: int
    confidence: float


@dataclass
class EconomyComparison:
    """Compare economy across different workout types or periods."""
    period1_avg: float
    period2_avg: float
    improvement_percent: float
    statistically_significant: bool
    sample_size_1: int
    sample_size_2: int


class RunningEconomyTracker:
    """
    Tracks and analyzes running economy over time.

    Economy is measured as pace-to-HR ratio, normalized for:
    - Intensity (% of max HR)
    - Temperature
    - Elevation
    - Cardiac drift (workout duration)
    """

    # Standard conditions for normalization
    REFERENCE_HR_PCT = 0.75  # 75% max HR (aerobic threshold)
    REFERENCE_TEMP_C = 15    # Ideal running temperature

    # Adjustment factors
    TEMP_COEFFICIENT = 0.015  # 1.5% per degree above/below reference
    ELEVATION_COEFFICIENT = 0.0001  # Per meter of elevation gain
    DRIFT_COEFFICIENT = 0.002  # 0.2% per minute after 30 min

    def __init__(self, max_hr: int = 185):
        self.max_hr = max_hr
        self._data_points: List[EconomyDataPoint] = []

    def calculate_economy_score(
        self,
        pace_sec_km: int,
        avg_hr: int,
        duration_min: float = 60,
        elevation_gain_m: float = 0,
        temperature_c: float = 15,
        normalize: bool = True,
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculate running economy score.

        Formula:
        raw_ratio = pace / HR
        normalized_ratio = raw_ratio * intensity_adj * temp_adj * elev_adj * drift_adj
        economy_score = 100 - (normalized_ratio - baseline) * scale

        Higher score = better economy

        Args:
            pace_sec_km: Average pace in seconds per kilometer
            avg_hr: Average heart rate
            duration_min: Workout duration in minutes
            elevation_gain_m: Total elevation gain
            temperature_c: Temperature during workout
            normalize: Whether to apply normalization adjustments

        Returns:
            Tuple of (economy_score, adjustments_dict)
        """
        if avg_hr <= 0 or pace_sec_km <= 0:
            return 0, {}

        raw_ratio = pace_sec_km / avg_hr
        adjustments = {"raw_ratio": raw_ratio}

        if not normalize:
            # Convert to 0-100 score (lower ratio = higher score)
            # Typical range: 1.5 (excellent) to 3.0 (poor)
            score = max(0, min(100, (3.5 - raw_ratio) / 2.0 * 100))
            return score, adjustments

        # Intensity normalization
        current_hr_pct = avg_hr / self.max_hr
        intensity_adj = current_hr_pct / self.REFERENCE_HR_PCT
        adjustments["intensity"] = round(intensity_adj, 3)

        # Temperature adjustment
        temp_diff = temperature_c - self.REFERENCE_TEMP_C
        temp_adj = 1 + (temp_diff * self.TEMP_COEFFICIENT)
        adjustments["temperature"] = round(temp_adj, 3)

        # Elevation adjustment (more elevation = higher HR for same pace)
        elev_per_km = elevation_gain_m / max(1, pace_sec_km * 1000 / 60 / duration_min)
        elev_adj = 1 + (elev_per_km * self.ELEVATION_COEFFICIENT)
        adjustments["elevation"] = round(elev_adj, 3)

        # Cardiac drift adjustment (HR rises over long workouts)
        if duration_min > 30:
            drift_adj = 1 - ((duration_min - 30) * self.DRIFT_COEFFICIENT)
        else:
            drift_adj = 1.0
        adjustments["drift"] = round(drift_adj, 3)

        # Apply all adjustments
        normalized_ratio = raw_ratio * intensity_adj * temp_adj * elev_adj * drift_adj
        adjustments["normalized_ratio"] = round(normalized_ratio, 3)

        # Convert to score (100 = excellent economy)
        # Baseline ratio of 2.0 = score of 75
        score = max(0, min(100, 125 - normalized_ratio * 25))

        return round(score, 1), adjustments

    def add_workout(self, data_point: EconomyDataPoint) -> None:
        """Add a workout data point for tracking."""
        self._data_points.append(data_point)

    def calculate_trend(
        self,
        days: int = 90,
        min_workouts: int = 5,
    ) -> EconomyTrend:
        """
        Calculate economy trend over a period.

        Compares recent workouts to historical baseline.

        Args:
            days: Number of days to analyze
            min_workouts: Minimum workouts needed for analysis

        Returns:
            EconomyTrend with trend direction and statistics
        """
        cutoff = date.today() - timedelta(days=days)
        recent_data = [d for d in self._data_points if d.date >= cutoff]

        if len(recent_data) < min_workouts:
            return EconomyTrend(
                current_score=0,
                baseline_score=0,
                change_percent=0,
                trend="insufficient_data",
                days_analyzed=days,
                data_points=len(recent_data),
                confidence=0,
            )

        # Calculate scores for all workouts
        scores = []
        for dp in recent_data:
            score, _ = self.calculate_economy_score(
                dp.avg_pace_sec_km,
                dp.avg_hr,
                dp.duration_min,
                dp.elevation_gain_m or 0,
                dp.temperature_c or self.REFERENCE_TEMP_C,
            )
            scores.append((dp.date, score))

        # Sort by date
        scores.sort(key=lambda x: x[0])

        # Split into baseline (first 60%) and recent (last 40%)
        split_idx = int(len(scores) * 0.6)
        baseline_scores = [s[1] for s in scores[:split_idx]]
        recent_scores = [s[1] for s in scores[split_idx:]]

        baseline_avg = statistics.mean(baseline_scores) if baseline_scores else 0
        recent_avg = statistics.mean(recent_scores) if recent_scores else 0
        current = recent_scores[-1] if recent_scores else 0

        # Calculate change
        if baseline_avg > 0:
            change_pct = ((recent_avg - baseline_avg) / baseline_avg) * 100
        else:
            change_pct = 0

        # Determine trend
        if change_pct > 3:
            trend = "improving"
        elif change_pct < -3:
            trend = "declining"
        else:
            trend = "stable"

        # Confidence based on sample size and variance
        if len(scores) >= 20:
            confidence = 0.9
        elif len(scores) >= 10:
            confidence = 0.7
        else:
            confidence = 0.5

        return EconomyTrend(
            current_score=round(current, 1),
            baseline_score=round(baseline_avg, 1),
            change_percent=round(change_pct, 1),
            trend=trend,
            days_analyzed=days,
            data_points=len(scores),
            confidence=confidence,
        )

    def compare_periods(
        self,
        period1_start: date,
        period1_end: date,
        period2_start: date,
        period2_end: date,
    ) -> EconomyComparison:
        """
        Compare economy between two time periods.

        Useful for before/after training block comparisons.
        """
        period1_data = [
            d for d in self._data_points
            if period1_start <= d.date <= period1_end
        ]
        period2_data = [
            d for d in self._data_points
            if period2_start <= d.date <= period2_end
        ]

        def calc_avg_score(data: List[EconomyDataPoint]) -> float:
            if not data:
                return 0
            scores = [
                self.calculate_economy_score(
                    d.avg_pace_sec_km, d.avg_hr, d.duration_min,
                    d.elevation_gain_m or 0, d.temperature_c or 15
                )[0]
                for d in data
            ]
            return statistics.mean(scores)

        avg1 = calc_avg_score(period1_data)
        avg2 = calc_avg_score(period2_data)

        improvement = ((avg2 - avg1) / avg1 * 100) if avg1 > 0 else 0

        # Simple significance check (need proper stats in production)
        significant = (
            len(period1_data) >= 5 and
            len(period2_data) >= 5 and
            abs(improvement) > 5
        )

        return EconomyComparison(
            period1_avg=round(avg1, 1),
            period2_avg=round(avg2, 1),
            improvement_percent=round(improvement, 1),
            statistically_significant=significant,
            sample_size_1=len(period1_data),
            sample_size_2=len(period2_data),
        )

    def get_efficiency_recommendations(
        self,
        current_score: float,
        trend: str,
    ) -> List[str]:
        """Get recommendations to improve running economy."""
        recommendations = []

        if current_score < 50:
            recommendations.append("Focus on easy aerobic running to build base efficiency")
            recommendations.append("Consider running form drills: high knees, butt kicks, A-skips")

        if trend == "declining":
            recommendations.append("Economy declining - check for overtraining or inadequate recovery")
            recommendations.append("Ensure adequate easy running (80% of volume at easy pace)")

        if current_score >= 50 and current_score < 70:
            recommendations.append("Add strides (6x100m) after easy runs to improve neuromuscular efficiency")
            recommendations.append("Include one tempo run per week to improve lactate clearance")

        if current_score >= 70:
            recommendations.append("Good economy! Maintain with regular strides and tempo work")
            recommendations.append("Focus on race-specific training to capitalize on efficiency")

        return recommendations
```

---

## 4. Cardiac Drift Detection

### 4.1 Core Module

**File: `/training-analyzer/src/metrics/cardiac_drift.py`**

```python
"""
Cardiac Drift Detection Module.

Cardiac drift = HR increase over time at constant pace/power.
Normal drift: 3-5% over 60+ minutes in trained athletes.
High drift (>5%): Indicates aerobic deficiency, dehydration, or overheating.

Key metric: Decoupling percentage (Pw:Hr or Pa:Hr)
- Compares first half to second half of workout
- Decoupling = ((EF1 - EF2) / EF1) * 100
- Where EF = Efficiency Factor (pace/HR or power/HR)
"""

import statistics
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import date


@dataclass
class HRSample:
    """Time-series HR sample."""
    timestamp_sec: int  # Seconds from workout start
    heart_rate: int
    pace_sec_km: Optional[int] = None
    power_watts: Optional[int] = None
    altitude_m: Optional[float] = None


@dataclass
class CardiacDriftResult:
    """Result of cardiac drift analysis."""
    decoupling_pct: float
    first_half_avg_hr: float
    second_half_avg_hr: float
    first_half_efficiency: float
    second_half_efficiency: float
    hr_drift_pct: float
    assessment: str  # "excellent", "good", "moderate", "high", "concerning"
    is_aerobically_deficient: bool
    recommendation: str
    confidence: float


@dataclass
class DriftTrend:
    """Trend in cardiac drift over time."""
    recent_avg_decoupling: float
    historical_avg_decoupling: float
    trend: str  # "improving", "stable", "worsening"
    best_session: float
    worst_session: float


class CardiacDriftAnalyzer:
    """
    Analyzes cardiac drift in long aerobic sessions.

    Use cases:
    - Long runs (90+ minutes)
    - Easy runs (45+ minutes)
    - Aerobic base building assessment

    Methodology:
    1. Split workout into two halves
    2. Calculate Efficiency Factor for each half
    3. Compare efficiency factors (decoupling)
    """

    # Thresholds for decoupling assessment
    EXCELLENT_THRESHOLD = 2.0    # <2% = excellent aerobic fitness
    GOOD_THRESHOLD = 5.0         # 2-5% = well-developed aerobic base
    MODERATE_THRESHOLD = 7.5     # 5-7.5% = developing aerobic base
    HIGH_THRESHOLD = 10.0        # 7.5-10% = aerobic deficiency
    # >10% = significant aerobic deficiency

    def __init__(self):
        self._history: List[Tuple[date, float]] = []

    def analyze_workout(
        self,
        hr_samples: List[HRSample],
        min_duration_min: int = 45,
        use_power: bool = False,
    ) -> CardiacDriftResult:
        """
        Analyze cardiac drift for a single workout.

        Formula for decoupling:
        EF = pace (or power) / HR
        Decoupling = ((EF_first_half - EF_second_half) / EF_first_half) * 100

        Args:
            hr_samples: Time-series data with HR and pace/power
            min_duration_min: Minimum duration for valid analysis
            use_power: Use power instead of pace for EF calculation

        Returns:
            CardiacDriftResult with drift analysis
        """
        if not hr_samples:
            return self._empty_result("No data provided")

        # Check duration
        duration_sec = hr_samples[-1].timestamp_sec - hr_samples[0].timestamp_sec
        duration_min = duration_sec / 60

        if duration_min < min_duration_min:
            return self._empty_result(f"Workout too short ({duration_min:.0f} min < {min_duration_min} min)")

        # Split into halves
        mid_time = hr_samples[0].timestamp_sec + duration_sec // 2
        first_half = [s for s in hr_samples if s.timestamp_sec < mid_time]
        second_half = [s for s in hr_samples if s.timestamp_sec >= mid_time]

        if len(first_half) < 10 or len(second_half) < 10:
            return self._empty_result("Insufficient samples in each half")

        # Calculate averages for each half
        first_hr = statistics.mean(s.heart_rate for s in first_half)
        second_hr = statistics.mean(s.heart_rate for s in second_half)

        # Calculate efficiency factor
        if use_power:
            # Power-based EF (for power runners/cyclists)
            first_power = [s.power_watts for s in first_half if s.power_watts]
            second_power = [s.power_watts for s in second_half if s.power_watts]

            if not first_power or not second_power:
                return self._empty_result("No power data for analysis")

            first_ef = statistics.mean(first_power) / first_hr
            second_ef = statistics.mean(second_power) / second_hr
        else:
            # Pace-based EF (convert to speed for consistency)
            first_pace = [s.pace_sec_km for s in first_half if s.pace_sec_km]
            second_pace = [s.pace_sec_km for s in second_half if s.pace_sec_km]

            if not first_pace or not second_pace:
                return self._empty_result("No pace data for analysis")

            # Convert pace to speed (m/s) for positive correlation with HR
            first_speed = 1000 / statistics.mean(first_pace)
            second_speed = 1000 / statistics.mean(second_pace)

            first_ef = first_speed / first_hr * 100  # Scale for readability
            second_ef = second_speed / second_hr * 100

        # Calculate decoupling
        if first_ef > 0:
            decoupling = ((first_ef - second_ef) / first_ef) * 100
        else:
            decoupling = 0

        # HR drift (simple percentage increase)
        hr_drift = ((second_hr - first_hr) / first_hr) * 100

        # Assess the result
        assessment, is_deficient, recommendation = self._assess_decoupling(
            decoupling, hr_drift, duration_min
        )

        # Confidence based on duration and data quality
        confidence = min(1.0, duration_min / 90)  # Full confidence at 90+ min

        return CardiacDriftResult(
            decoupling_pct=round(decoupling, 2),
            first_half_avg_hr=round(first_hr, 1),
            second_half_avg_hr=round(second_hr, 1),
            first_half_efficiency=round(first_ef, 3),
            second_half_efficiency=round(second_ef, 3),
            hr_drift_pct=round(hr_drift, 2),
            assessment=assessment,
            is_aerobically_deficient=is_deficient,
            recommendation=recommendation,
            confidence=round(confidence, 2),
        )

    def _assess_decoupling(
        self,
        decoupling: float,
        hr_drift: float,
        duration_min: float,
    ) -> Tuple[str, bool, str]:
        """Assess decoupling level and provide recommendations."""

        # Adjust thresholds for shorter workouts (drift naturally higher)
        duration_factor = min(1.0, duration_min / 90)
        adjusted_threshold = self.GOOD_THRESHOLD / duration_factor

        if decoupling < self.EXCELLENT_THRESHOLD:
            return (
                "excellent",
                False,
                "Excellent aerobic fitness. Minimal cardiac drift indicates strong aerobic base.",
            )
        elif decoupling < self.GOOD_THRESHOLD:
            return (
                "good",
                False,
                "Good aerobic development. Continue building aerobic base with long easy runs.",
            )
        elif decoupling < self.MODERATE_THRESHOLD:
            return (
                "moderate",
                False,
                "Developing aerobic base. Increase easy/long run volume gradually.",
            )
        elif decoupling < self.HIGH_THRESHOLD:
            return (
                "high",
                True,
                "Aerobic deficiency detected. Prioritize Zone 2 training and reduce intensity work temporarily.",
            )
        else:
            # Check for external factors
            if hr_drift > 15:
                return (
                    "concerning",
                    True,
                    "Significant drift may indicate dehydration, heat, or illness. Check hydration and recovery.",
                )
            return (
                "concerning",
                True,
                "Notable aerobic deficiency. Focus exclusively on easy aerobic running for 4-6 weeks.",
            )

    def _empty_result(self, reason: str) -> CardiacDriftResult:
        """Return empty result with reason."""
        return CardiacDriftResult(
            decoupling_pct=0,
            first_half_avg_hr=0,
            second_half_avg_hr=0,
            first_half_efficiency=0,
            second_half_efficiency=0,
            hr_drift_pct=0,
            assessment="insufficient_data",
            is_aerobically_deficient=False,
            recommendation=reason,
            confidence=0,
        )

    def add_result(self, workout_date: date, decoupling: float) -> None:
        """Add result to history for trend analysis."""
        self._history.append((workout_date, decoupling))

    def analyze_trend(self, days: int = 90) -> DriftTrend:
        """Analyze drift trend over time."""
        from datetime import timedelta

        cutoff = date.today() - timedelta(days=days)
        recent = [d for d in self._history if d[0] >= cutoff]

        if len(recent) < 3:
            return DriftTrend(
                recent_avg_decoupling=0,
                historical_avg_decoupling=0,
                trend="insufficient_data",
                best_session=0,
                worst_session=0,
            )

        # Sort by date
        recent.sort(key=lambda x: x[0])

        # Split into periods
        mid = len(recent) // 2
        earlier = [r[1] for r in recent[:mid]]
        later = [r[1] for r in recent[mid:]]

        earlier_avg = statistics.mean(earlier)
        later_avg = statistics.mean(later)

        all_values = [r[1] for r in recent]

        # Determine trend (lower is better)
        diff = earlier_avg - later_avg
        if diff > 1.0:
            trend = "improving"
        elif diff < -1.0:
            trend = "worsening"
        else:
            trend = "stable"

        return DriftTrend(
            recent_avg_decoupling=round(later_avg, 2),
            historical_avg_decoupling=round(earlier_avg, 2),
            trend=trend,
            best_session=round(min(all_values), 2),
            worst_session=round(max(all_values), 2),
        )
```

---

## 5. Exponential Taper Implementation

### 5.1 Core Module

**File: `/training-analyzer/src/services/taper_service.py`**

```python
"""
Exponential Taper Implementation.

Replaces linear taper with research-backed exponential decay model.

Based on Mujika & Padilla (2003) meta-analysis:
- Exponential tapers more effective than linear
- Optimal duration: 8-14 days depending on distance
- Volume reduction: 40-60% over taper period
- Intensity maintained or slightly increased
- Frequency reduced last 2-3 days only

Taper Formula:
Training_Load(day) = Baseline_Load * e^(-day/time_constant)

Where time_constant controls decay rate (typically 3-7 days).
"""

import math
from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple


class RaceDistance(str, Enum):
    """Race distances with optimal taper parameters."""
    FIVE_K = "5k"
    TEN_K = "10k"
    HALF_MARATHON = "half"
    MARATHON = "marathon"
    ULTRA = "ultra"


@dataclass
class TaperParameters:
    """Taper parameters for a race distance."""
    duration_days: int
    time_constant: float  # Controls exponential decay rate
    final_volume_pct: float  # Target volume on race week
    intensity_multiplier: float  # 1.0 = maintain, 1.05 = slight increase
    frequency_reduction_day: int  # Day to reduce frequency (from race)


# Research-based taper parameters by distance
TAPER_PARAMS = {
    RaceDistance.FIVE_K: TaperParameters(
        duration_days=7,
        time_constant=3.0,
        final_volume_pct=0.50,
        intensity_multiplier=1.02,  # Slight intensity increase OK
        frequency_reduction_day=2,
    ),
    RaceDistance.TEN_K: TaperParameters(
        duration_days=10,
        time_constant=4.0,
        final_volume_pct=0.45,
        intensity_multiplier=1.0,
        frequency_reduction_day=3,
    ),
    RaceDistance.HALF_MARATHON: TaperParameters(
        duration_days=14,
        time_constant=5.0,
        final_volume_pct=0.40,
        intensity_multiplier=1.0,
        frequency_reduction_day=3,
    ),
    RaceDistance.MARATHON: TaperParameters(
        duration_days=21,
        time_constant=7.0,
        final_volume_pct=0.35,
        intensity_multiplier=0.98,  # Slightly reduce intensity
        frequency_reduction_day=4,
    ),
    RaceDistance.ULTRA: TaperParameters(
        duration_days=28,
        time_constant=10.0,
        final_volume_pct=0.30,
        intensity_multiplier=0.95,
        frequency_reduction_day=5,
    ),
}


@dataclass
class TaperDay:
    """Single day in taper plan."""
    date: date
    days_to_race: int
    volume_pct: float
    target_load: float
    intensity_zone: str  # "easy", "moderate", "race_pace_strides"
    suggested_workout: str
    notes: str


@dataclass
class TaperPlan:
    """Complete taper plan."""
    race_date: date
    race_distance: RaceDistance
    start_date: date
    duration_days: int
    baseline_weekly_load: float
    days: List[TaperDay]
    total_taper_load: float
    volume_reduction_pct: float
    summary: str


@dataclass
class TaperRecommendation:
    """Volume/intensity split recommendation."""
    volume_reduction_pct: float
    intensity_maintenance: str
    frequency_change: str
    key_sessions_to_keep: List[str]
    sessions_to_cut: List[str]
    rationale: str


class ExponentialTaperService:
    """
    Generates exponential taper plans for races.

    Key features:
    - Distance-specific taper duration and decay
    - Preserves key intensity sessions
    - Reduces volume progressively
    - Research-backed parameters
    """

    def generate_taper_plan(
        self,
        race_date: date,
        race_distance: RaceDistance,
        baseline_weekly_load: float,
        current_days_per_week: int = 5,
    ) -> TaperPlan:
        """
        Generate an exponential taper plan.

        Args:
            race_date: Date of the race
            race_distance: Race distance category
            baseline_weekly_load: Recent average weekly load (HRSS/TSS)
            current_days_per_week: Current training days per week

        Returns:
            TaperPlan with day-by-day schedule
        """
        params = TAPER_PARAMS[race_distance]

        start_date = race_date - timedelta(days=params.duration_days)

        days = []
        total_load = 0

        # Daily baseline from weekly average
        daily_baseline = baseline_weekly_load / current_days_per_week

        for day_offset in range(params.duration_days):
            current_date = start_date + timedelta(days=day_offset)
            days_to_race = params.duration_days - day_offset

            # Exponential decay formula
            # volume_pct = e^(-days_from_start / time_constant)
            days_from_start = day_offset
            volume_pct = math.exp(-days_from_start / params.time_constant)

            # Ensure we reach target final volume
            # Adjust to hit final_volume_pct on last day
            scale = (1 - params.final_volume_pct) / (1 - math.exp(-params.duration_days / params.time_constant))
            volume_pct = 1 - scale * (1 - volume_pct)
            volume_pct = max(params.final_volume_pct, min(1.0, volume_pct))

            # Calculate target load
            target_load = daily_baseline * volume_pct * params.intensity_multiplier
            total_load += target_load

            # Determine workout type
            intensity_zone, suggested_workout, notes = self._get_workout_suggestion(
                days_to_race,
                volume_pct,
                race_distance,
                params,
            )

            days.append(TaperDay(
                date=current_date,
                days_to_race=days_to_race,
                volume_pct=round(volume_pct, 2),
                target_load=round(target_load, 1),
                intensity_zone=intensity_zone,
                suggested_workout=suggested_workout,
                notes=notes,
            ))

        # Calculate overall volume reduction
        normal_load = baseline_weekly_load * (params.duration_days / 7)
        reduction_pct = ((normal_load - total_load) / normal_load) * 100

        summary = self._generate_summary(race_distance, params, reduction_pct)

        return TaperPlan(
            race_date=race_date,
            race_distance=race_distance,
            start_date=start_date,
            duration_days=params.duration_days,
            baseline_weekly_load=baseline_weekly_load,
            days=days,
            total_taper_load=round(total_load, 1),
            volume_reduction_pct=round(reduction_pct, 1),
            summary=summary,
        )

    def _get_workout_suggestion(
        self,
        days_to_race: int,
        volume_pct: float,
        race_distance: RaceDistance,
        params: TaperParameters,
    ) -> Tuple[str, str, str]:
        """Get workout suggestion for a taper day."""

        # Rest day before race
        if days_to_race == 1:
            return (
                "rest",
                "Rest or 15-20 min very easy jog with strides",
                "Keep legs fresh. Light movement only.",
            )

        # Race week: short with race-pace touches
        if days_to_race <= 3:
            return (
                "race_pace_strides",
                f"Easy {int(20 + volume_pct * 10)} min + 4-6 strides at race pace",
                "Stay sharp. Keep it short.",
            )

        # Mid-taper: maintain one quality session
        if days_to_race <= params.duration_days // 2:
            if days_to_race % 3 == 0:  # One tempo touch
                return (
                    "moderate",
                    f"Easy {int(25 + volume_pct * 15)} min + 10 min at tempo",
                    "Maintain fitness. Don't push hard.",
                )
            return (
                "easy",
                f"Easy run {int(30 + volume_pct * 20)} min",
                "Recovery focus. Conversational pace.",
            )

        # Early taper: gradually reduce
        if days_to_race == params.duration_days:
            return (
                "moderate",
                "Last quality session (reduced volume)",
                "Final hard effort before taper. Reduce volume by 20%.",
            )

        return (
            "easy",
            f"Easy run {int(40 + volume_pct * 20)} min",
            "Building freshness. Keep effort easy.",
        )

    def _generate_summary(
        self,
        race_distance: RaceDistance,
        params: TaperParameters,
        reduction_pct: float,
    ) -> str:
        """Generate taper summary text."""
        return (
            f"{params.duration_days}-day exponential taper for {race_distance.value}. "
            f"Volume reduces by {reduction_pct:.0f}% while maintaining intensity touches. "
            f"Key: Stay fresh but not flat. Include short race-pace strides in final week."
        )

    def get_volume_intensity_recommendation(
        self,
        race_distance: RaceDistance,
    ) -> TaperRecommendation:
        """
        Get volume/intensity split recommendations for taper.
        """
        params = TAPER_PARAMS[race_distance]

        # Sessions to keep (intensity maintenance)
        key_sessions = []
        if race_distance in [RaceDistance.FIVE_K, RaceDistance.TEN_K]:
            key_sessions = [
                "Short intervals (200-400m) at race pace or faster",
                "Strides after easy runs (4-6 x 20 sec)",
                "One tempo run (reduced to 10-15 min at tempo)",
            ]
        elif race_distance == RaceDistance.HALF_MARATHON:
            key_sessions = [
                "One moderate tempo run (15-20 min)",
                "Race pace segments (2-3 x 1 mile)",
                "Strides to maintain leg speed",
            ]
        else:  # Marathon and ultra
            key_sessions = [
                "Easy marathon pace segments (2-3 miles)",
                "Strides for neuromuscular activation",
                "One final moderate long run early in taper",
            ]

        # Sessions to eliminate/reduce
        cut_sessions = [
            "Long runs (reduce length significantly)",
            "High-volume interval sessions",
            "Hill repeats and strength work",
            "Cross-training (reduce intensity)",
            "Back-to-back hard days",
        ]

        intensity_guidance = {
            RaceDistance.FIVE_K: "Maintain or slightly increase intensity of reduced-volume speed work",
            RaceDistance.TEN_K: "Maintain intensity but reduce volume by 50-60%",
            RaceDistance.HALF_MARATHON: "Maintain moderate intensity touches, no new hard efforts",
            RaceDistance.MARATHON: "Reduce intensity slightly, focus on staying loose",
            RaceDistance.ULTRA: "Significant intensity reduction, focus on recovery",
        }

        return TaperRecommendation(
            volume_reduction_pct=round((1 - params.final_volume_pct) * 100),
            intensity_maintenance=intensity_guidance[race_distance],
            frequency_change=f"Reduce training days {params.frequency_reduction_day} days before race",
            key_sessions_to_keep=key_sessions,
            sessions_to_cut=cut_sessions,
            rationale=(
                "Research shows exponential tapers outperform linear tapers. "
                "Volume reduction allows glycogen supercompensation and muscle repair "
                "while intensity maintenance prevents detraining of fast-twitch fibers."
            ),
        )
```

---

## 6. Race Pacing Strategy Generator

### 6.1 Core Module

**File: `/training-analyzer/src/services/race_pacing_service.py`**

```python
"""
Race Pacing Strategy Generator.

Generates optimal pacing strategies based on:
- Course elevation profile
- Weather conditions (temperature, humidity, wind)
- Athlete fitness level (VDOT)
- Race distance and target time

Pacing strategies:
- Even split: Consistent pace throughout
- Negative split: Faster second half
- Positive split: Faster first half (usually sub-optimal)
- Variable: Adjusted for terrain
"""

import math
from dataclasses import dataclass, field
from datetime import timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple


class PacingStrategy(str, Enum):
    """Available pacing strategies."""
    EVEN = "even"
    NEGATIVE = "negative"
    POSITIVE = "positive"  # Generally not recommended
    VARIABLE = "variable"  # Terrain-adjusted


class CourseProfile(str, Enum):
    """Course elevation profile types."""
    FLAT = "flat"           # <100m total elevation
    ROLLING = "rolling"     # 100-300m total elevation
    HILLY = "hilly"         # 300-600m total elevation
    MOUNTAINOUS = "mountainous"  # >600m total elevation
    NET_DOWNHILL = "net_downhill"


@dataclass
class ElevationSegment:
    """Elevation data for a course segment."""
    start_km: float
    end_km: float
    elevation_change_m: float  # Positive = uphill
    avg_grade_pct: float


@dataclass
class WeatherConditions:
    """Weather conditions affecting pace."""
    temperature_c: float
    humidity_pct: float = 50
    wind_speed_kmh: float = 0
    wind_direction: str = "calm"  # "headwind", "tailwind", "crosswind", "calm"
    precipitation: bool = False


@dataclass
class PaceSplit:
    """Pace for a single kilometer/mile."""
    distance_km: float
    target_pace_sec_km: int
    adjusted_pace_sec_km: int
    cumulative_time_sec: int
    adjustment_factors: Dict[str, float]
    notes: str


@dataclass
class RacePlan:
    """Complete race pacing plan."""
    race_distance_km: float
    target_time_sec: int
    strategy: PacingStrategy
    splits: List[PaceSplit]
    predicted_finish_time_sec: int
    weather_impact_sec: int
    elevation_impact_sec: int
    summary: str
    warnings: List[str]


class RacePacingService:
    """
    Generates race pacing strategies with environmental adjustments.

    Adjustment factors based on research:
    - Temperature: +1.5-2% per degree above 15C
    - Humidity: +0.5% per 10% above 50%
    - Headwind: +4-6% for strong winds
    - Uphills: +12-15 sec/km per 1% grade
    - Downhills: -6-8 sec/km per 1% grade (capped)
    """

    # Temperature adjustment (Ely et al., 2007)
    # Performance degrades ~1.5% per degree C above optimal
    OPTIMAL_TEMP_C = 12
    TEMP_PENALTY_PER_DEGREE = 0.015  # 1.5%

    # Humidity adjustment (above 50% starts affecting performance)
    HUMIDITY_PENALTY_PER_10PCT = 0.005  # 0.5%

    # Wind adjustment (strong headwind significantly impacts pace)
    HEADWIND_PENALTY = {
        "light": 0.02,    # <15 km/h: 2%
        "moderate": 0.04, # 15-25 km/h: 4%
        "strong": 0.06,   # >25 km/h: 6%
    }
    TAILWIND_BENEFIT = 0.01  # 1% benefit max

    # Elevation adjustments (Minetti et al., 2002)
    UPHILL_PENALTY_PER_PCT = 15   # +15 sec/km per 1% grade
    DOWNHILL_BENEFIT_PER_PCT = 7  # -7 sec/km per 1% grade
    MAX_DOWNHILL_BENEFIT = 20     # Cap at 20 sec/km benefit

    def generate_race_plan(
        self,
        target_time_sec: int,
        race_distance_km: float,
        strategy: PacingStrategy = PacingStrategy.EVEN,
        weather: Optional[WeatherConditions] = None,
        elevation_segments: Optional[List[ElevationSegment]] = None,
        athlete_experience: str = "intermediate",
    ) -> RacePlan:
        """
        Generate a complete race pacing plan.

        Args:
            target_time_sec: Goal finish time in seconds
            race_distance_km: Race distance in kilometers
            strategy: Pacing strategy to use
            weather: Weather conditions (optional)
            elevation_segments: Course elevation profile (optional)
            athlete_experience: "beginner", "intermediate", "advanced"

        Returns:
            RacePlan with kilometer splits and adjustments
        """
        base_pace = target_time_sec / race_distance_km
        splits = []
        cumulative_time = 0
        warnings = []

        total_weather_impact = 0
        total_elevation_impact = 0

        for km in range(1, int(race_distance_km) + 1):
            adjustments = {}
            notes_parts = []

            # Base pace for this km based on strategy
            km_pace = self._get_strategy_pace(
                km, race_distance_km, base_pace, strategy
            )

            # Weather adjustments
            if weather:
                weather_factor, weather_notes = self._calculate_weather_adjustment(
                    weather, km, race_distance_km
                )
                adjustments["weather"] = weather_factor
                km_pace *= weather_factor
                total_weather_impact += (km_pace - base_pace) * weather_factor
                if weather_notes:
                    notes_parts.append(weather_notes)

            # Elevation adjustments
            if elevation_segments:
                elev_adj, elev_notes = self._calculate_elevation_adjustment(
                    km, elevation_segments
                )
                adjustments["elevation"] = elev_adj
                km_pace += elev_adj  # Additive for elevation
                total_elevation_impact += elev_adj
                if elev_notes:
                    notes_parts.append(elev_notes)

            cumulative_time += int(km_pace)

            splits.append(PaceSplit(
                distance_km=km,
                target_pace_sec_km=int(base_pace),
                adjusted_pace_sec_km=int(km_pace),
                cumulative_time_sec=cumulative_time,
                adjustment_factors=adjustments,
                notes="; ".join(notes_parts) if notes_parts else "",
            ))

        # Handle partial final km if distance isn't whole
        partial = race_distance_km - int(race_distance_km)
        if partial > 0.01:
            partial_pace = base_pace * partial
            cumulative_time += int(partial_pace)

        predicted_finish = cumulative_time

        # Generate warnings
        warnings = self._generate_warnings(
            weather, elevation_segments, strategy, athlete_experience
        )

        # Generate summary
        summary = self._generate_summary(
            target_time_sec, predicted_finish, strategy, weather, elevation_segments
        )

        return RacePlan(
            race_distance_km=race_distance_km,
            target_time_sec=target_time_sec,
            strategy=strategy,
            splits=splits,
            predicted_finish_time_sec=predicted_finish,
            weather_impact_sec=int(total_weather_impact),
            elevation_impact_sec=int(total_elevation_impact),
            summary=summary,
            warnings=warnings,
        )

    def _get_strategy_pace(
        self,
        km: int,
        total_km: float,
        base_pace: float,
        strategy: PacingStrategy,
    ) -> float:
        """Calculate pace for this km based on strategy."""
        progress = km / total_km

        if strategy == PacingStrategy.EVEN:
            return base_pace

        elif strategy == PacingStrategy.NEGATIVE:
            # Start 3% slower, finish 3% faster
            # Linear transition
            adjustment = 0.03 - (0.06 * progress)
            return base_pace * (1 + adjustment)

        elif strategy == PacingStrategy.POSITIVE:
            # Not recommended but sometimes requested
            # Start 3% faster, finish 5% slower
            adjustment = -0.03 + (0.08 * progress)
            return base_pace * (1 + adjustment)

        elif strategy == PacingStrategy.VARIABLE:
            # Start controlled, surge in middle, strong finish
            if progress < 0.2:
                return base_pace * 1.02  # Conservative start
            elif progress < 0.7:
                return base_pace  # Settle into rhythm
            else:
                return base_pace * 0.98  # Strong finish

        return base_pace

    def _calculate_weather_adjustment(
        self,
        weather: WeatherConditions,
        km: int,
        total_km: float,
    ) -> Tuple[float, str]:
        """Calculate weather-based pace adjustment."""
        factor = 1.0
        notes = []

        # Temperature adjustment
        if weather.temperature_c > self.OPTIMAL_TEMP_C:
            temp_penalty = (weather.temperature_c - self.OPTIMAL_TEMP_C) * self.TEMP_PENALTY_PER_DEGREE
            factor += temp_penalty
            if temp_penalty > 0.03:
                notes.append(f"Heat: +{temp_penalty*100:.1f}%")

        # Humidity adjustment (compounds with temperature)
        if weather.humidity_pct > 50 and weather.temperature_c > 15:
            humidity_penalty = ((weather.humidity_pct - 50) / 10) * self.HUMIDITY_PENALTY_PER_10PCT
            factor += humidity_penalty
            if humidity_penalty > 0.01:
                notes.append(f"Humidity: +{humidity_penalty*100:.1f}%")

        # Wind adjustment
        if weather.wind_direction == "headwind":
            if weather.wind_speed_kmh > 25:
                factor += self.HEADWIND_PENALTY["strong"]
                notes.append("Strong headwind")
            elif weather.wind_speed_kmh > 15:
                factor += self.HEADWIND_PENALTY["moderate"]
                notes.append("Moderate headwind")
            elif weather.wind_speed_kmh > 5:
                factor += self.HEADWIND_PENALTY["light"]
        elif weather.wind_direction == "tailwind" and weather.wind_speed_kmh > 10:
            factor -= self.TAILWIND_BENEFIT
            notes.append("Tailwind assist")

        return factor, ", ".join(notes)

    def _calculate_elevation_adjustment(
        self,
        km: int,
        segments: List[ElevationSegment],
    ) -> Tuple[float, str]:
        """Calculate elevation-based pace adjustment in seconds."""
        # Find segment for this km
        for seg in segments:
            if seg.start_km <= km <= seg.end_km:
                if seg.avg_grade_pct > 0:
                    # Uphill penalty
                    penalty = seg.avg_grade_pct * self.UPHILL_PENALTY_PER_PCT
                    return penalty, f"Uphill {seg.avg_grade_pct:.1f}%"
                elif seg.avg_grade_pct < 0:
                    # Downhill benefit (capped)
                    benefit = min(
                        abs(seg.avg_grade_pct) * self.DOWNHILL_BENEFIT_PER_PCT,
                        self.MAX_DOWNHILL_BENEFIT
                    )
                    return -benefit, f"Downhill {abs(seg.avg_grade_pct):.1f}%"

        return 0, ""

    def _generate_warnings(
        self,
        weather: Optional[WeatherConditions],
        elevation: Optional[List[ElevationSegment]],
        strategy: PacingStrategy,
        experience: str,
    ) -> List[str]:
        """Generate race day warnings."""
        warnings = []

        if weather:
            if weather.temperature_c > 25:
                warnings.append("HEAT WARNING: Temperatures above 25C significantly impact performance. Consider adjusting goal time by 5-10%.")
            if weather.temperature_c > 20 and weather.humidity_pct > 70:
                warnings.append("HIGH HUMIDITY: Humid conditions impair cooling. Hydrate aggressively and adjust pace expectations.")
            if weather.wind_speed_kmh > 30:
                warnings.append("STRONG WIND: Expect significant pace variation. Draft when possible.")

        if strategy == PacingStrategy.POSITIVE:
            warnings.append("PACING: Positive split strategy often leads to significant fade. Consider negative or even splits.")

        if experience == "beginner" and strategy != PacingStrategy.EVEN:
            warnings.append("EXPERIENCE: For newer racers, even pacing is generally safest. Variable strategies require race experience.")

        return warnings

    def _generate_summary(
        self,
        target: int,
        predicted: int,
        strategy: PacingStrategy,
        weather: Optional[WeatherConditions],
        elevation: Optional[List[ElevationSegment]],
    ) -> str:
        """Generate race plan summary."""
        diff = predicted - target

        parts = [f"{strategy.value.title()} split strategy"]

        if diff > 60:
            parts.append(f"Conditions add ~{diff//60}:{diff%60:02d} to your goal")
        elif diff < -30:
            parts.append(f"Favorable conditions may help by ~{abs(diff)//60}:{abs(diff)%60:02d}")

        if weather and weather.temperature_c > 20:
            parts.append("Heat management critical")

        if elevation:
            total_gain = sum(s.elevation_change_m for s in elevation if s.elevation_change_m > 0)
            if total_gain > 200:
                parts.append(f"Save energy on climbs ({total_gain:.0f}m gain)")

        return ". ".join(parts) + "."

    def recommend_strategy(
        self,
        race_distance_km: float,
        course_profile: CourseProfile,
        athlete_experience: str,
        weather: Optional[WeatherConditions] = None,
    ) -> Tuple[PacingStrategy, str]:
        """
        Recommend optimal pacing strategy.

        Returns recommended strategy and rationale.
        """
        # Default recommendation based on research
        # Negative splits generally optimal but harder to execute

        if athlete_experience == "beginner":
            return (
                PacingStrategy.EVEN,
                "Even pacing is safest for newer racers. Focus on consistent effort rather than splits."
            )

        if course_profile == CourseProfile.NET_DOWNHILL:
            return (
                PacingStrategy.NEGATIVE,
                "Net downhill course favors controlled start. Save energy for fast finish."
            )

        if course_profile in [CourseProfile.HILLY, CourseProfile.MOUNTAINOUS]:
            return (
                PacingStrategy.VARIABLE,
                "Terrain-adjusted pacing best for hilly courses. Match effort to grade, not pace."
            )

        if weather and weather.temperature_c > 22:
            return (
                PacingStrategy.NEGATIVE,
                "Heat conditions favor conservative start. Bank time when cool, hang on when hot."
            )

        if race_distance_km >= 42:
            return (
                PacingStrategy.EVEN,
                "Marathon distance rewards patience. Even pacing or slight negative split optimal."
            )

        if race_distance_km <= 10:
            if athlete_experience == "advanced":
                return (
                    PacingStrategy.NEGATIVE,
                    "Experienced racers can execute negative splits in shorter races for optimal performance."
                )

        return (
            PacingStrategy.EVEN,
            "Even pacing provides reliable results across most conditions."
        )
```

---

## Integration Summary

### New Database Tables

```sql
-- Sleep tracking
CREATE TABLE sleep_data (...)

-- HRV tracking
CREATE TABLE hrv_data (...)

-- Recovery scores
CREATE TABLE recovery_scores (...)

-- Running economy history
CREATE TABLE economy_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT DEFAULT 'default',
    workout_id TEXT NOT NULL,
    date TEXT NOT NULL,
    avg_pace_sec_km INTEGER NOT NULL,
    avg_hr INTEGER NOT NULL,
    duration_min REAL NOT NULL,
    distance_km REAL NOT NULL,
    economy_score REAL,
    normalized_ratio REAL,
    temperature_c REAL,
    elevation_gain_m REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workout_id) REFERENCES activity_metrics(activity_id)
);

-- Cardiac drift results
CREATE TABLE cardiac_drift_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT DEFAULT 'default',
    workout_id TEXT NOT NULL,
    date TEXT NOT NULL,
    decoupling_pct REAL NOT NULL,
    first_half_hr REAL,
    second_half_hr REAL,
    assessment TEXT,
    is_aerobically_deficient INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workout_id) REFERENCES activity_metrics(activity_id)
);

-- Taper plans
CREATE TABLE taper_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT DEFAULT 'default',
    race_date TEXT NOT NULL,
    race_distance TEXT NOT NULL,
    start_date TEXT NOT NULL,
    duration_days INTEGER NOT NULL,
    baseline_weekly_load REAL,
    plan_json TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Race plans
CREATE TABLE race_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT DEFAULT 'default',
    race_date TEXT NOT NULL,
    race_distance_km REAL NOT NULL,
    target_time_sec INTEGER NOT NULL,
    strategy TEXT NOT NULL,
    splits_json TEXT NOT NULL,
    weather_json TEXT,
    elevation_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### New API Routes

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/pace-zones/calculate-vdot` | POST | Calculate VDOT from race time |
| `/api/v1/pace-zones/zones/{vdot}` | GET | Get pace zones for VDOT |
| `/api/v1/pace-zones/my-zones` | GET | Get athlete's pace zones |
| `/api/v1/recovery/sleep-debt` | GET | Get sleep debt analysis |
| `/api/v1/recovery/hrv-trend` | GET | Get HRV trend analysis |
| `/api/v1/recovery/score` | GET | Get recovery score |
| `/api/v1/recovery/estimate/{workout_type}` | GET | Estimate recovery time |
| `/api/v1/economy/score` | POST | Calculate economy score |
| `/api/v1/economy/trend` | GET | Get economy trend |
| `/api/v1/cardiac-drift/analyze` | POST | Analyze cardiac drift |
| `/api/v1/cardiac-drift/trend` | GET | Get drift trend |
| `/api/v1/taper/generate` | POST | Generate taper plan |
| `/api/v1/taper/recommendation/{distance}` | GET | Get taper recommendations |
| `/api/v1/race-plan/generate` | POST | Generate race pacing plan |
| `/api/v1/race-plan/strategy` | GET | Get strategy recommendation |

### Module Dependencies

```
vdot.py
  └── Used by: pace_zones.py (API), plan_service.py

recovery_service.py
  └── Used by: recovery.py (API), fatigue_prediction.py

running_economy.py
  └── Used by: economy.py (API), analysis_service.py

cardiac_drift.py
  └── Used by: drift.py (API), workout analysis

taper_service.py
  └── Used by: taper.py (API), plan_service.py

race_pacing_service.py
  └── Used by: race_plan.py (API), plan_service.py
```

---

## Testing Requirements

Each module should include:
1. Unit tests for core calculations
2. Integration tests for API endpoints
3. Edge case handling (zero values, missing data)
4. Performance benchmarks for batch operations

Example test structure:
```
tests/
  test_vdot.py
  test_recovery_service.py
  test_running_economy.py
  test_cardiac_drift.py
  test_taper_service.py
  test_race_pacing.py
```
