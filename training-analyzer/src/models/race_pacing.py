"""Race pacing models for the pacing strategy generator.

This module defines Pydantic models for:
- Course profiles with elevation data
- Weather conditions and adjustments
- Pacing plans and split targets
- Strategy recommendations
"""

from datetime import timedelta
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class PacingStrategy(str, Enum):
    """Available pacing strategies for race execution."""
    EVEN = "even"
    NEGATIVE_SPLIT = "negative_split"
    POSITIVE_SPLIT = "positive_split"
    COURSE_SPECIFIC = "course_specific"


class RaceDistance(str, Enum):
    """Common race distances."""
    FIVE_K = "5K"
    TEN_K = "10K"
    HALF_MARATHON = "half_marathon"
    MARATHON = "marathon"
    CUSTOM = "custom"


# Race distances in kilometers
RACE_DISTANCES_KM = {
    RaceDistance.FIVE_K: 5.0,
    RaceDistance.TEN_K: 10.0,
    RaceDistance.HALF_MARATHON: 21.0975,
    RaceDistance.MARATHON: 42.195,
}


class ElevationPoint(BaseModel):
    """A single point in the course elevation profile."""
    distance_km: float = Field(..., ge=0, description="Distance from start in km")
    elevation_m: float = Field(..., description="Elevation in meters")

    class Config:
        json_schema_extra = {
            "example": {"distance_km": 5.0, "elevation_m": 150.0}
        }


class CourseProfile(BaseModel):
    """Course elevation profile for race pacing calculations.

    Contains elevation data points that define the course topology,
    enabling effort-based pace adjustments.
    """
    name: Optional[str] = Field(None, description="Course/race name")
    total_distance_km: float = Field(..., gt=0, description="Total course distance in km")
    elevation_points: List[ElevationPoint] = Field(
        default_factory=list,
        description="Ordered list of elevation points along the course"
    )
    total_elevation_gain_m: Optional[float] = Field(None, ge=0, description="Total elevation gain in meters")
    total_elevation_loss_m: Optional[float] = Field(None, ge=0, description="Total elevation loss in meters")

    @field_validator('elevation_points')
    @classmethod
    def validate_elevation_points(cls, v, info):
        """Ensure elevation points are ordered by distance."""
        if len(v) > 1:
            for i in range(1, len(v)):
                if v[i].distance_km <= v[i-1].distance_km:
                    raise ValueError("Elevation points must be ordered by increasing distance")
        return v

    def calculate_elevation_metrics(self) -> None:
        """Calculate total elevation gain and loss from points if not provided."""
        if not self.elevation_points or len(self.elevation_points) < 2:
            return

        gain = 0.0
        loss = 0.0
        for i in range(1, len(self.elevation_points)):
            diff = self.elevation_points[i].elevation_m - self.elevation_points[i-1].elevation_m
            if diff > 0:
                gain += diff
            else:
                loss += abs(diff)

        if self.total_elevation_gain_m is None:
            self.total_elevation_gain_m = gain
        if self.total_elevation_loss_m is None:
            self.total_elevation_loss_m = loss

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Boston Marathon",
                "total_distance_km": 42.195,
                "elevation_points": [
                    {"distance_km": 0, "elevation_m": 150},
                    {"distance_km": 10, "elevation_m": 100},
                    {"distance_km": 21, "elevation_m": 50},
                    {"distance_km": 32, "elevation_m": 100},  # Heartbreak Hill
                    {"distance_km": 42.195, "elevation_m": 10}
                ],
                "total_elevation_gain_m": 250,
                "total_elevation_loss_m": 390
            }
        }


class WindDirection(str, Enum):
    """Wind direction relative to running direction."""
    HEADWIND = "headwind"
    TAILWIND = "tailwind"
    CROSSWIND = "crosswind"
    VARIABLE = "variable"


class WeatherConditions(BaseModel):
    """Weather conditions that affect race pacing.

    These conditions are used to calculate pace adjustments
    based on environmental factors.
    """
    temperature_c: float = Field(..., ge=-30, le=50, description="Temperature in Celsius")
    humidity_pct: float = Field(default=60, ge=0, le=100, description="Relative humidity percentage")
    wind_speed_kmh: float = Field(default=0, ge=0, le=100, description="Wind speed in km/h")
    wind_direction: WindDirection = Field(default=WindDirection.VARIABLE, description="Wind direction relative to course")
    altitude_m: float = Field(default=0, ge=0, le=5000, description="Race altitude in meters")

    @property
    def feels_like_c(self) -> float:
        """Calculate feels-like temperature (heat index approximation)."""
        if self.temperature_c < 27:
            return self.temperature_c
        # Simplified heat index calculation
        hi = self.temperature_c + 0.33 * (self.humidity_pct / 100 * 6.105 * 2.71828 ** (17.27 * self.temperature_c / (237.7 + self.temperature_c))) - 4
        return round(hi, 1)

    class Config:
        json_schema_extra = {
            "example": {
                "temperature_c": 18,
                "humidity_pct": 70,
                "wind_speed_kmh": 15,
                "wind_direction": "headwind",
                "altitude_m": 500
            }
        }


class WeatherAdjustment(BaseModel):
    """Calculated weather-based pace adjustments."""
    temperature_adjustment_pct: float = Field(default=0, description="Pace adjustment for temperature")
    humidity_adjustment_pct: float = Field(default=0, description="Pace adjustment for humidity")
    wind_adjustment_pct: float = Field(default=0, description="Pace adjustment for wind")
    altitude_adjustment_pct: float = Field(default=0, description="Pace adjustment for altitude")
    total_adjustment_pct: float = Field(default=0, description="Total combined pace adjustment")
    adjusted_target_pace_sec_km: Optional[float] = Field(None, description="Weather-adjusted target pace")

    class Config:
        json_schema_extra = {
            "example": {
                "temperature_adjustment_pct": 3.0,
                "humidity_adjustment_pct": 1.5,
                "wind_adjustment_pct": 1.0,
                "altitude_adjustment_pct": 1.0,
                "total_adjustment_pct": 6.5,
                "adjusted_target_pace_sec_km": 318
            }
        }


class SplitTarget(BaseModel):
    """Target pace and cumulative time for a single split (km or mile)."""
    split_number: int = Field(..., ge=1, description="Split number (1-indexed)")
    distance_km: float = Field(..., gt=0, description="Distance covered at this split")
    target_pace_sec_km: float = Field(..., gt=0, description="Target pace in seconds per km")
    target_pace_formatted: str = Field(..., description="Target pace as mm:ss/km string")
    cumulative_time_sec: float = Field(..., gt=0, description="Cumulative time at this split in seconds")
    cumulative_time_formatted: str = Field(..., description="Cumulative time as HH:MM:SS string")
    elevation_adjustment_pct: float = Field(default=0, description="Pace adjustment for elevation at this split")
    notes: Optional[str] = Field(None, description="Notes for this split (e.g., 'uphill section', 'hydration point')")

    class Config:
        json_schema_extra = {
            "example": {
                "split_number": 1,
                "distance_km": 1.0,
                "target_pace_sec_km": 300,
                "target_pace_formatted": "5:00",
                "cumulative_time_sec": 300,
                "cumulative_time_formatted": "0:05:00",
                "elevation_adjustment_pct": 2.5,
                "notes": "Slight uphill, stay controlled"
            }
        }


class StrategyRecommendation(BaseModel):
    """Strategy recommendation with reasoning."""
    strategy: PacingStrategy = Field(..., description="Recommended pacing strategy")
    confidence: float = Field(..., ge=0, le=1, description="Confidence in recommendation (0-1)")
    reasoning: str = Field(..., description="Explanation for the strategy recommendation")

    class Config:
        json_schema_extra = {
            "example": {
                "strategy": "negative_split",
                "confidence": 0.85,
                "reasoning": "Flat course and experienced runner - negative split allows for controlled start and strong finish"
            }
        }


class PacingPlan(BaseModel):
    """Complete pacing plan for a race.

    Contains all splits with target paces, strategy recommendations,
    and weather adjustments.
    """
    race_name: Optional[str] = Field(None, description="Name of the race")
    race_distance: RaceDistance = Field(..., description="Race distance category")
    distance_km: float = Field(..., gt=0, description="Total distance in km")
    target_time_sec: float = Field(..., gt=0, description="Target finish time in seconds")
    target_time_formatted: str = Field(..., description="Target time as HH:MM:SS string")
    base_pace_sec_km: float = Field(..., gt=0, description="Base target pace in seconds per km")
    base_pace_formatted: str = Field(..., description="Base pace as mm:ss/km string")

    strategy: PacingStrategy = Field(..., description="Pacing strategy used")
    strategy_recommendation: Optional[StrategyRecommendation] = Field(None, description="AI strategy recommendation")

    splits: List[SplitTarget] = Field(default_factory=list, description="Per-km split targets")

    weather_conditions: Optional[WeatherConditions] = Field(None, description="Weather conditions if provided")
    weather_adjustment: Optional[WeatherAdjustment] = Field(None, description="Weather-based adjustments")

    course_profile: Optional[CourseProfile] = Field(None, description="Course elevation profile if provided")

    tips: List[str] = Field(default_factory=list, description="Race execution tips")

    @property
    def predicted_finish_time_sec(self) -> float:
        """Calculate predicted finish time from splits."""
        if self.splits:
            return self.splits[-1].cumulative_time_sec
        return self.target_time_sec

    @property
    def predicted_finish_time_formatted(self) -> str:
        """Format predicted finish time."""
        return format_time(self.predicted_finish_time_sec)

    class Config:
        json_schema_extra = {
            "example": {
                "race_name": "Spring Half Marathon",
                "race_distance": "half_marathon",
                "distance_km": 21.0975,
                "target_time_sec": 6300,
                "target_time_formatted": "1:45:00",
                "base_pace_sec_km": 299,
                "base_pace_formatted": "4:59",
                "strategy": "negative_split",
                "splits": [],
                "tips": [
                    "Start conservatively - the first 5K should feel easy",
                    "Build pace gradually after the halfway point",
                    "Save your best effort for the final 5K"
                ]
            }
        }


class GeneratePacingPlanRequest(BaseModel):
    """Request to generate a pacing plan."""
    target_time_sec: float = Field(..., gt=0, description="Target finish time in seconds")
    distance_km: Optional[float] = Field(None, gt=0, description="Distance in km (required for custom distances)")
    race_distance: RaceDistance = Field(default=RaceDistance.CUSTOM, description="Race distance category")
    race_name: Optional[str] = Field(None, description="Optional race name")

    strategy: Optional[PacingStrategy] = Field(None, description="Preferred strategy (auto if not specified)")
    course_profile: Optional[CourseProfile] = Field(None, description="Course elevation profile")
    weather_conditions: Optional[WeatherConditions] = Field(None, description="Expected weather conditions")

    split_unit: str = Field(default="km", pattern="^(km|mile)$", description="Split unit (km or mile)")

    @field_validator('distance_km')
    @classmethod
    def validate_distance(cls, v, info):
        """Validate distance is provided for custom distances."""
        if v is None:
            race_distance = info.data.get('race_distance', RaceDistance.CUSTOM)
            if race_distance == RaceDistance.CUSTOM:
                raise ValueError("distance_km is required for custom race distances")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "target_time_sec": 6300,
                "race_distance": "half_marathon",
                "race_name": "Spring Half Marathon",
                "strategy": "negative_split",
                "weather_conditions": {
                    "temperature_c": 15,
                    "humidity_pct": 60
                }
            }
        }


class WeatherAdjustmentRequest(BaseModel):
    """Request to calculate weather impact on pace."""
    base_pace_sec_km: float = Field(..., gt=0, description="Base target pace in sec/km")
    weather_conditions: WeatherConditions = Field(..., description="Weather conditions")

    class Config:
        json_schema_extra = {
            "example": {
                "base_pace_sec_km": 300,
                "weather_conditions": {
                    "temperature_c": 25,
                    "humidity_pct": 80,
                    "wind_speed_kmh": 20,
                    "wind_direction": "headwind"
                }
            }
        }


class AvailableStrategiesResponse(BaseModel):
    """Response with available pacing strategies."""
    strategies: List[Dict[str, Any]] = Field(..., description="List of available strategies with descriptions")
    race_distances: List[Dict[str, Any]] = Field(..., description="List of supported race distances")


# Utility functions
def format_pace(seconds_per_km: float) -> str:
    """Format pace in seconds/km to mm:ss string."""
    minutes = int(seconds_per_km // 60)
    seconds = int(seconds_per_km % 60)
    return f"{minutes}:{seconds:02d}"


def format_time(total_seconds: float) -> str:
    """Format time in seconds to HH:MM:SS or H:MM:SS string."""
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)

    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def parse_time_string(time_str: str) -> float:
    """Parse HH:MM:SS or MM:SS time string to seconds."""
    parts = time_str.split(':')
    if len(parts) == 3:
        hours, minutes, seconds = map(float, parts)
        return hours * 3600 + minutes * 60 + seconds
    elif len(parts) == 2:
        minutes, seconds = map(float, parts)
        return minutes * 60 + seconds
    else:
        raise ValueError(f"Invalid time format: {time_str}")
