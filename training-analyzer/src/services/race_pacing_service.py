"""Race pacing service for generating pacing plans.

This service handles:
- Pacing plan generation based on target time and distance
- Weather-based pace adjustments
- Elevation-based pace adjustments
- Strategy recommendations (even, negative split, course-specific)
"""

import logging
import math
from typing import List, Optional, Tuple

from ..models.race_pacing import (
    PacingPlan,
    PacingStrategy,
    RaceDistance,
    RACE_DISTANCES_KM,
    CourseProfile,
    WeatherConditions,
    WeatherAdjustment,
    SplitTarget,
    StrategyRecommendation,
    GeneratePacingPlanRequest,
    WeatherAdjustmentRequest,
    format_pace,
    format_time,
)


logger = logging.getLogger(__name__)


# Weather adjustment factors (percentage per unit)
WEATHER_ADJUSTMENTS = {
    'temperature': 0.015,    # +1.5% per degree above 12C (optimal temp)
    'humidity': 0.005,       # +0.5% per 10% above 60%
    'wind': 0.01,            # +1% per 10km/h headwind
    'altitude': 0.02,        # +2% per 1000m elevation
}

# Optimal running temperature
OPTIMAL_TEMPERATURE_C = 12.0
OPTIMAL_HUMIDITY_PCT = 60.0

# Elevation adjustment factors
UPHILL_ADJUSTMENT_PER_PCT = 0.08     # +8% pace per 1% grade uphill
DOWNHILL_ADJUSTMENT_PER_PCT = -0.03  # -3% pace per 1% grade downhill (capped)
MAX_DOWNHILL_ADJUSTMENT = -0.06      # Max 6% faster on downhills


class RacePacingService:
    """Service for generating race pacing plans and strategies."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def generate_pacing_plan(
        self,
        target_time_sec: float,
        distance_km: float,
        race_distance: RaceDistance = RaceDistance.CUSTOM,
        race_name: Optional[str] = None,
        course_profile: Optional[CourseProfile] = None,
        weather_conditions: Optional[WeatherConditions] = None,
        strategy: Optional[PacingStrategy] = None,
        split_unit: str = "km",
    ) -> PacingPlan:
        """
        Generate a complete pacing plan for a race.

        Args:
            target_time_sec: Target finish time in seconds
            distance_km: Total race distance in kilometers
            race_distance: Race distance category
            race_name: Optional name for the race
            course_profile: Optional course elevation profile
            weather_conditions: Optional weather conditions
            strategy: Preferred pacing strategy (auto-selected if None)
            split_unit: Unit for splits ("km" or "mile")

        Returns:
            PacingPlan with all splits and recommendations
        """
        self.logger.info(
            f"Generating pacing plan: {distance_km}km in {format_time(target_time_sec)}"
        )

        # Calculate base pace
        base_pace_sec_km = target_time_sec / distance_km

        # Determine strategy if not specified
        if strategy is None:
            strategy, strategy_rec = self._recommend_strategy(
                distance_km, course_profile, weather_conditions
            )
        else:
            strategy_rec = StrategyRecommendation(
                strategy=strategy,
                confidence=1.0,
                reasoning=f"User selected {strategy.value} strategy"
            )

        # Calculate weather adjustments
        weather_adjustment = None
        if weather_conditions:
            weather_adjustment = self.calculate_weather_adjustment(
                base_pace_sec_km, weather_conditions
            )

        # Calculate elevation adjustments for the course
        elevation_adjustments = []
        if course_profile and course_profile.elevation_points:
            course_profile.calculate_elevation_metrics()
            elevation_adjustments = self._calculate_elevation_adjustments(
                course_profile, distance_km
            )

        # Generate splits based on strategy
        splits = self._generate_splits(
            target_time_sec=target_time_sec,
            distance_km=distance_km,
            base_pace_sec_km=base_pace_sec_km,
            strategy=strategy,
            elevation_adjustments=elevation_adjustments,
            weather_adjustment=weather_adjustment,
            split_unit=split_unit,
        )

        # Generate tips
        tips = self._generate_tips(
            strategy, distance_km, course_profile, weather_conditions
        )

        return PacingPlan(
            race_name=race_name,
            race_distance=race_distance,
            distance_km=distance_km,
            target_time_sec=target_time_sec,
            target_time_formatted=format_time(target_time_sec),
            base_pace_sec_km=base_pace_sec_km,
            base_pace_formatted=format_pace(base_pace_sec_km),
            strategy=strategy,
            strategy_recommendation=strategy_rec,
            splits=splits,
            weather_conditions=weather_conditions,
            weather_adjustment=weather_adjustment,
            course_profile=course_profile,
            tips=tips,
        )

    def calculate_weather_adjustment(
        self,
        base_pace_sec_km: float,
        conditions: WeatherConditions,
    ) -> WeatherAdjustment:
        """
        Calculate pace adjustments for weather conditions.

        Args:
            base_pace_sec_km: Base target pace in seconds/km
            conditions: Weather conditions

        Returns:
            WeatherAdjustment with all adjustment factors
        """
        # Temperature adjustment: +1.5% per degree above 12C
        temp_diff = max(0, conditions.temperature_c - OPTIMAL_TEMPERATURE_C)
        temp_adjustment_pct = temp_diff * WEATHER_ADJUSTMENTS['temperature'] * 100

        # Humidity adjustment: +0.5% per 10% above 60%
        humidity_diff = max(0, conditions.humidity_pct - OPTIMAL_HUMIDITY_PCT)
        humidity_adjustment_pct = (humidity_diff / 10) * WEATHER_ADJUSTMENTS['humidity'] * 100

        # Wind adjustment: +1% per 10km/h headwind
        wind_adjustment_pct = 0.0
        if conditions.wind_direction.value == 'headwind':
            wind_adjustment_pct = (conditions.wind_speed_kmh / 10) * WEATHER_ADJUSTMENTS['wind'] * 100
        elif conditions.wind_direction.value == 'tailwind':
            # Tailwind helps but not as much as headwind hurts
            wind_adjustment_pct = -(conditions.wind_speed_kmh / 10) * WEATHER_ADJUSTMENTS['wind'] * 100 * 0.5
        elif conditions.wind_direction.value == 'crosswind':
            # Crosswind is 50% as bad as headwind
            wind_adjustment_pct = (conditions.wind_speed_kmh / 10) * WEATHER_ADJUSTMENTS['wind'] * 100 * 0.5

        # Altitude adjustment: +2% per 1000m above sea level
        altitude_adjustment_pct = (conditions.altitude_m / 1000) * WEATHER_ADJUSTMENTS['altitude'] * 100

        # Total adjustment
        total_adjustment_pct = (
            temp_adjustment_pct +
            humidity_adjustment_pct +
            wind_adjustment_pct +
            altitude_adjustment_pct
        )

        # Calculate adjusted pace
        adjusted_pace = base_pace_sec_km * (1 + total_adjustment_pct / 100)

        return WeatherAdjustment(
            temperature_adjustment_pct=round(temp_adjustment_pct, 2),
            humidity_adjustment_pct=round(humidity_adjustment_pct, 2),
            wind_adjustment_pct=round(wind_adjustment_pct, 2),
            altitude_adjustment_pct=round(altitude_adjustment_pct, 2),
            total_adjustment_pct=round(total_adjustment_pct, 2),
            adjusted_target_pace_sec_km=round(adjusted_pace, 1),
        )

    def _calculate_elevation_adjustments(
        self,
        profile: CourseProfile,
        distance_km: float,
    ) -> List[float]:
        """
        Calculate per-km pace adjustments based on elevation profile.

        Args:
            profile: Course elevation profile
            distance_km: Total distance

        Returns:
            List of percentage adjustments per km
        """
        if not profile.elevation_points or len(profile.elevation_points) < 2:
            return [0.0] * int(math.ceil(distance_km))

        adjustments = []
        num_splits = int(math.ceil(distance_km))

        for km in range(num_splits):
            km_start = float(km)
            km_end = min(float(km + 1), distance_km)

            # Interpolate elevation at km_start and km_end
            elev_start = self._interpolate_elevation(profile.elevation_points, km_start)
            elev_end = self._interpolate_elevation(profile.elevation_points, km_end)

            # Calculate grade percentage
            distance_m = (km_end - km_start) * 1000
            elevation_change_m = elev_end - elev_start
            grade_pct = (elevation_change_m / distance_m) * 100 if distance_m > 0 else 0

            # Calculate adjustment
            if grade_pct > 0:
                # Uphill: slower
                adjustment = grade_pct * UPHILL_ADJUSTMENT_PER_PCT * 100
            else:
                # Downhill: faster, but capped
                adjustment = max(
                    MAX_DOWNHILL_ADJUSTMENT * 100,
                    grade_pct * DOWNHILL_ADJUSTMENT_PER_PCT * 100
                )

            adjustments.append(round(adjustment, 2))

        return adjustments

    def _interpolate_elevation(
        self,
        points: List,
        distance_km: float,
    ) -> float:
        """Interpolate elevation at a given distance."""
        if not points:
            return 0.0

        # Find surrounding points
        for i, point in enumerate(points):
            if point.distance_km >= distance_km:
                if i == 0:
                    return point.elevation_m
                prev_point = points[i - 1]
                # Linear interpolation
                ratio = (distance_km - prev_point.distance_km) / (
                    point.distance_km - prev_point.distance_km
                )
                return prev_point.elevation_m + ratio * (
                    point.elevation_m - prev_point.elevation_m
                )

        # Beyond last point
        return points[-1].elevation_m

    def _recommend_strategy(
        self,
        distance_km: float,
        course_profile: Optional[CourseProfile],
        weather_conditions: Optional[WeatherConditions],
    ) -> Tuple[PacingStrategy, StrategyRecommendation]:
        """
        Recommend a pacing strategy based on conditions.

        Returns:
            Tuple of (strategy, recommendation)
        """
        reasoning_parts = []

        # Check for course-specific needs
        has_significant_hills = False
        if course_profile and course_profile.total_elevation_gain_m:
            gain_per_km = course_profile.total_elevation_gain_m / distance_km
            if gain_per_km > 10:  # More than 10m gain per km
                has_significant_hills = True
                reasoning_parts.append(
                    f"Course has significant elevation ({course_profile.total_elevation_gain_m:.0f}m gain)"
                )

        # Check weather impact
        has_challenging_weather = False
        if weather_conditions:
            if weather_conditions.temperature_c > 20:
                has_challenging_weather = True
                reasoning_parts.append(f"Warm conditions ({weather_conditions.temperature_c}C)")
            if weather_conditions.wind_speed_kmh > 20 and weather_conditions.wind_direction.value == 'headwind':
                has_challenging_weather = True
                reasoning_parts.append(f"Strong headwind ({weather_conditions.wind_speed_kmh}km/h)")

        # Decision logic
        if has_significant_hills:
            strategy = PacingStrategy.COURSE_SPECIFIC
            confidence = 0.9
            reasoning_parts.insert(0, "Course-specific pacing recommended:")
            reasoning_parts.append("Adjust effort on hills rather than maintaining constant pace")
        elif has_challenging_weather:
            strategy = PacingStrategy.EVEN
            confidence = 0.8
            reasoning_parts.insert(0, "Even pacing recommended:")
            reasoning_parts.append("Conserve energy in challenging conditions with consistent effort")
        elif distance_km >= 21.0:  # Half marathon or longer
            strategy = PacingStrategy.NEGATIVE_SPLIT
            confidence = 0.85
            reasoning_parts.insert(0, "Negative split recommended:")
            reasoning_parts.append("For longer distances, start conservatively and finish strong")
        else:
            strategy = PacingStrategy.EVEN
            confidence = 0.75
            reasoning_parts.insert(0, "Even pacing recommended:")
            reasoning_parts.append("Consistent pace is efficient for shorter distances")

        return strategy, StrategyRecommendation(
            strategy=strategy,
            confidence=confidence,
            reasoning=" ".join(reasoning_parts),
        )

    def _generate_splits(
        self,
        target_time_sec: float,
        distance_km: float,
        base_pace_sec_km: float,
        strategy: PacingStrategy,
        elevation_adjustments: List[float],
        weather_adjustment: Optional[WeatherAdjustment],
        split_unit: str = "km",
    ) -> List[SplitTarget]:
        """Generate splits based on strategy and adjustments."""
        splits = []
        num_splits = int(math.ceil(distance_km))
        cumulative_time = 0.0

        # Get base pace (potentially weather-adjusted)
        effective_base_pace = base_pace_sec_km
        if weather_adjustment:
            effective_base_pace = weather_adjustment.adjusted_target_pace_sec_km or base_pace_sec_km

        for i in range(num_splits):
            split_num = i + 1
            split_distance = min(1.0, distance_km - i)  # Handle partial last split

            # Calculate pace modifiers based on strategy
            strategy_modifier = self._get_strategy_modifier(
                split_num, num_splits, strategy
            )

            # Get elevation adjustment for this split
            elev_adjustment_pct = elevation_adjustments[i] if i < len(elevation_adjustments) else 0.0

            # Calculate target pace for this split
            target_pace = effective_base_pace * (1 + strategy_modifier / 100) * (1 + elev_adjustment_pct / 100)

            # Calculate time for this split
            split_time = target_pace * split_distance
            cumulative_time += split_time

            # Generate notes
            notes = self._generate_split_notes(
                split_num, num_splits, strategy, elev_adjustment_pct
            )

            splits.append(SplitTarget(
                split_number=split_num,
                distance_km=round(split_num * 1.0 if split_num < num_splits else distance_km, 3),
                target_pace_sec_km=round(target_pace, 1),
                target_pace_formatted=format_pace(target_pace),
                cumulative_time_sec=round(cumulative_time, 1),
                cumulative_time_formatted=format_time(cumulative_time),
                elevation_adjustment_pct=elev_adjustment_pct,
                notes=notes,
            ))

        return splits

    def _get_strategy_modifier(
        self,
        split_num: int,
        total_splits: int,
        strategy: PacingStrategy,
    ) -> float:
        """
        Get pace modifier percentage for a split based on strategy.

        Returns positive values for slower pace, negative for faster.
        """
        progress = split_num / total_splits

        if strategy == PacingStrategy.EVEN:
            return 0.0

        elif strategy == PacingStrategy.NEGATIVE_SPLIT:
            # Start 3% slower, finish 3% faster than target
            # Linear progression from +3% to -3%
            return 3.0 - (progress * 6.0)

        elif strategy == PacingStrategy.POSITIVE_SPLIT:
            # Start 3% faster, finish 3% slower
            return -3.0 + (progress * 6.0)

        elif strategy == PacingStrategy.COURSE_SPECIFIC:
            # For course-specific, rely on elevation adjustments
            return 0.0

        return 0.0

    def _generate_split_notes(
        self,
        split_num: int,
        total_splits: int,
        strategy: PacingStrategy,
        elev_adjustment_pct: float,
    ) -> Optional[str]:
        """Generate helpful notes for a split."""
        notes = []

        # Elevation notes
        if elev_adjustment_pct > 5:
            notes.append("Steep uphill - maintain effort, let pace slow")
        elif elev_adjustment_pct > 2:
            notes.append("Uphill section - stay controlled")
        elif elev_adjustment_pct < -4:
            notes.append("Steep downhill - don't overwork the quads")
        elif elev_adjustment_pct < -1:
            notes.append("Downhill - use momentum wisely")

        # Strategy notes
        progress = split_num / total_splits
        if strategy == PacingStrategy.NEGATIVE_SPLIT:
            if progress < 0.25:
                notes.append("Start conservative - hold back energy")
            elif progress > 0.75:
                notes.append("Time to pick it up - finish strong!")

        # Position notes
        if split_num == 1:
            notes.append("Find your rhythm")
        elif split_num == total_splits // 2:
            notes.append("Halfway point - assess how you feel")
        elif split_num == total_splits:
            notes.append("Final push to the finish!")

        return "; ".join(notes) if notes else None

    def _generate_tips(
        self,
        strategy: PacingStrategy,
        distance_km: float,
        course_profile: Optional[CourseProfile],
        weather_conditions: Optional[WeatherConditions],
    ) -> List[str]:
        """Generate race execution tips based on conditions."""
        tips = []

        # Strategy-specific tips
        if strategy == PacingStrategy.EVEN:
            tips.append("Focus on consistent effort throughout the race")
            tips.append("Use your watch but also listen to your body")
        elif strategy == PacingStrategy.NEGATIVE_SPLIT:
            tips.append("Start conservatively - the first 25% should feel easy")
            tips.append("Build pace gradually after the halfway point")
            tips.append("Save your best effort for the final third")
        elif strategy == PacingStrategy.COURSE_SPECIFIC:
            tips.append("Run by effort, not pace - let the terrain guide you")
            tips.append("Attack downhills carefully to preserve leg strength")

        # Weather tips
        if weather_conditions:
            if weather_conditions.temperature_c > 20:
                tips.append(f"Warm conditions ({weather_conditions.temperature_c}C) - increase fluid intake")
                tips.append("Consider slowing in the hottest sections")
            elif weather_conditions.temperature_c < 5:
                tips.append("Cold conditions - ensure proper warmup")

            if weather_conditions.wind_speed_kmh > 15:
                tips.append("Use other runners as windbreaks when possible")

            if weather_conditions.humidity_pct > 80:
                tips.append("High humidity - expect higher perceived effort")

        # Distance-specific tips
        if distance_km >= 42:
            tips.append("Take nutrition at regular intervals - don't wait until you're depleted")
            tips.append("The race really begins at mile 20 - pace conservatively until then")
        elif distance_km >= 21:
            tips.append("Consider taking fluids at each aid station")
            tips.append("Monitor your breathing - heavy breathing too early is a warning sign")

        # Course tips
        if course_profile and course_profile.total_elevation_gain_m:
            gain = course_profile.total_elevation_gain_m
            if gain > 200:
                tips.append(f"Significant elevation ({gain:.0f}m) - practice hill running in training")
                tips.append("On uphills, shorten your stride and maintain effort")

        return tips[:6]  # Limit to 6 most relevant tips


# Singleton instance
_race_pacing_service: Optional[RacePacingService] = None


def get_race_pacing_service() -> RacePacingService:
    """Get the race pacing service singleton."""
    global _race_pacing_service
    if _race_pacing_service is None:
        _race_pacing_service = RacePacingService()
    return _race_pacing_service
