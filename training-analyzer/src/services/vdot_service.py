"""
VDOT Service - Pace Zones Calculation Service

Provides a service layer wrapper around the VDOT pace zones calculator
for use throughout the application. Implements caching and user-specific
pace zone management.

Based on Jack Daniels' Running Formula for calculating training paces.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from functools import lru_cache

from ..metrics.vdot import (
    calculate_vdot,
    calculate_vdot_from_race,
    get_pace_zones,
    predict_race_times,
    parse_race_time,
    pace_km_to_mile,
    format_pace_per_mile,
    RaceDistance,
    PaceZone,
    VDOTCalculation,
)

logger = logging.getLogger(__name__)


@dataclass
class UserPaceZones:
    """User's saved pace zone configuration."""
    user_id: str
    vdot: float
    source_distance: Optional[str]
    source_time_sec: Optional[int]
    pace_zones: Dict[str, Dict[str, Any]]
    race_predictions: Dict[str, Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "user_id": self.user_id,
            "vdot": self.vdot,
            "source_distance": self.source_distance,
            "source_time_sec": self.source_time_sec,
            "pace_zones": self.pace_zones,
            "race_predictions": self.race_predictions,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class VDOTService:
    """
    Service for VDOT-based pace zone calculations.

    This service provides:
    - VDOT calculation from race results
    - Training pace zone generation
    - Race time predictions
    - User pace zone persistence
    """

    def __init__(self, db=None):
        """
        Initialize the VDOT service.

        Args:
            db: Optional database connection for persisting user zones
        """
        self._db = db
        self._cache: Dict[str, UserPaceZones] = {}
        self._cache_ttl = timedelta(hours=1)

    def calculate_vdot_from_race(
        self,
        distance: str,
        time_str: str,
        custom_distance_m: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Calculate VDOT from a race result.

        Args:
            distance: Race distance ('5K', '10K', 'half', 'marathon', or 'custom')
            time_str: Race time as string (e.g., '25:30' or '1:45:00')
            custom_distance_m: Custom distance in meters if distance is 'custom'

        Returns:
            Dictionary with VDOT value, pace zones, and race predictions

        Raises:
            ValueError: If distance or time format is invalid
        """
        try:
            result = calculate_vdot_from_race(
                distance=distance,
                time_str=time_str,
                custom_distance_m=custom_distance_m,
            )

            return self._format_vdot_result(result)

        except ValueError as e:
            logger.warning(f"Invalid VDOT calculation input: {e}")
            raise
        except Exception as e:
            logger.error(f"Error calculating VDOT: {e}")
            raise ValueError(f"Failed to calculate VDOT: {e}")

    def get_pace_zones_for_vdot(self, vdot: float) -> Dict[str, Any]:
        """
        Get pace zones for a specific VDOT value.

        Args:
            vdot: VDOT value (typically 30-85)

        Returns:
            Dictionary of pace zones with formatted paces
        """
        if not 25 <= vdot <= 90:
            raise ValueError(f"VDOT must be between 25 and 90, got {vdot}")

        zones = get_pace_zones(vdot)
        return self._format_pace_zones(zones)

    def get_race_predictions(self, vdot: float) -> Dict[str, Any]:
        """
        Get race time predictions for a VDOT value.

        Args:
            vdot: VDOT value

        Returns:
            Dictionary with predicted times for standard distances
        """
        if not 25 <= vdot <= 90:
            raise ValueError(f"VDOT must be between 25 and 90, got {vdot}")

        predictions = predict_race_times(vdot)
        return self._format_race_predictions(predictions)

    def save_user_zones(
        self,
        user_id: str,
        vdot: float,
        source_distance: Optional[str] = None,
        source_time_sec: Optional[int] = None,
    ) -> UserPaceZones:
        """
        Save pace zones for a user.

        Args:
            user_id: User's unique identifier
            vdot: Calculated VDOT value
            source_distance: Race distance used for calculation
            source_time_sec: Race time in seconds used for calculation

        Returns:
            UserPaceZones object with saved data
        """
        zones = get_pace_zones(vdot)
        predictions = predict_race_times(vdot)

        now = datetime.utcnow()

        user_zones = UserPaceZones(
            user_id=user_id,
            vdot=vdot,
            source_distance=source_distance,
            source_time_sec=source_time_sec,
            pace_zones=self._format_pace_zones(zones),
            race_predictions=self._format_race_predictions(predictions),
            created_at=now,
            updated_at=now,
        )

        # Cache the result
        self._cache[user_id] = user_zones

        # Persist if database is available
        if self._db:
            try:
                self._persist_user_zones(user_zones)
            except Exception as e:
                logger.error(f"Failed to persist user zones: {e}")

        return user_zones

    def get_user_zones(self, user_id: str) -> Optional[UserPaceZones]:
        """
        Retrieve a user's saved pace zones.

        Args:
            user_id: User's unique identifier

        Returns:
            UserPaceZones if found, None otherwise
        """
        # Check cache first
        if user_id in self._cache:
            return self._cache[user_id]

        # Try database
        if self._db:
            try:
                zones = self._load_user_zones(user_id)
                if zones:
                    self._cache[user_id] = zones
                return zones
            except Exception as e:
                logger.error(f"Failed to load user zones: {e}")

        return None

    def estimate_vdot_from_training(
        self,
        easy_pace_sec_per_km: float,
        threshold_pace_sec_per_km: Optional[float] = None,
    ) -> float:
        """
        Estimate VDOT from training paces (for users without race data).

        This uses a simplified estimation based on easy pace, which is
        less accurate than race-based calculation but useful for beginners.

        Args:
            easy_pace_sec_per_km: User's comfortable easy run pace
            threshold_pace_sec_per_km: Optional threshold/tempo pace

        Returns:
            Estimated VDOT value
        """
        # Easy pace is typically 65-79% of VDOT-equivalent pace
        # Using 72% as midpoint for estimation
        # VDOT pace formula: pace = 60000 / velocity
        # where velocity = f(VDOT * intensity)

        # This is a rough estimation - binary search for VDOT
        # that produces easy pace close to the given value

        for test_vdot in range(25, 91):
            zones = get_pace_zones(float(test_vdot))
            easy_zone = zones.get('easy')
            if easy_zone:
                mid_easy_pace = (
                    easy_zone.min_pace_sec_per_km +
                    easy_zone.max_pace_sec_per_km
                ) / 2

                if mid_easy_pace <= easy_pace_sec_per_km:
                    return float(test_vdot)

        return 30.0  # Default for very slow paces

    def _format_vdot_result(self, result: VDOTCalculation) -> Dict[str, Any]:
        """Format VDOT calculation result for API response."""
        result_dict = result.to_dict()

        # Add mile paces to zones
        formatted_zones = {}
        for name, zone_data in result_dict['pace_zones'].items():
            zone_data['min_pace_per_mile'] = format_pace_per_mile(
                zone_data['min_pace_sec_per_km']
            )
            zone_data['max_pace_per_mile'] = format_pace_per_mile(
                zone_data['max_pace_sec_per_km']
            )
            formatted_zones[name] = zone_data

        result_dict['pace_zones'] = formatted_zones

        # Add mile paces to predictions
        for pred in result_dict['race_predictions'].values():
            pred['pace_per_mile'] = format_pace_per_mile(pred['pace_sec_per_km'])

        return result_dict

    def _format_pace_zones(self, zones: Dict[str, PaceZone]) -> Dict[str, Dict[str, Any]]:
        """Format pace zones for API response."""
        formatted = {}
        for name, zone in zones.items():
            zone_dict = zone.to_dict()
            zone_dict['min_pace_per_mile'] = format_pace_per_mile(
                zone.min_pace_sec_per_km
            )
            zone_dict['max_pace_per_mile'] = format_pace_per_mile(
                zone.max_pace_sec_per_km
            )
            formatted[name] = zone_dict
        return formatted

    def _format_race_predictions(
        self,
        predictions: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """Format race predictions for API response."""
        formatted = {}
        for name, pred in predictions.items():
            pred['pace_per_mile'] = format_pace_per_mile(pred['pace_sec_per_km'])
            formatted[name] = pred
        return formatted

    def _persist_user_zones(self, user_zones: UserPaceZones) -> None:
        """Persist user zones to database."""
        if not self._db:
            return

        try:
            self._db.set_user_preference(
                user_zones.user_id,
                'vdot_zones',
                {
                    'vdot': user_zones.vdot,
                    'source_distance': user_zones.source_distance,
                    'source_time_sec': user_zones.source_time_sec,
                    'saved_at': user_zones.updated_at.isoformat(),
                }
            )
        except Exception as e:
            logger.error(f"Error persisting user zones: {e}")
            raise

    def _load_user_zones(self, user_id: str) -> Optional[UserPaceZones]:
        """Load user zones from database."""
        if not self._db:
            return None

        try:
            prefs = self._db.get_user_preference(user_id, 'vdot_zones')
            if not prefs or 'vdot' not in prefs:
                return None

            vdot = prefs['vdot']
            zones = get_pace_zones(vdot)
            predictions = predict_race_times(vdot)

            saved_at = datetime.fromisoformat(
                prefs.get('saved_at', datetime.utcnow().isoformat())
            )

            return UserPaceZones(
                user_id=user_id,
                vdot=vdot,
                source_distance=prefs.get('source_distance'),
                source_time_sec=prefs.get('source_time_sec'),
                pace_zones=self._format_pace_zones(zones),
                race_predictions=self._format_race_predictions(predictions),
                created_at=saved_at,
                updated_at=saved_at,
            )
        except Exception as e:
            logger.error(f"Error loading user zones: {e}")
            return None


# Singleton instance for application-wide use
_vdot_service: Optional[VDOTService] = None


def get_vdot_service(db=None) -> VDOTService:
    """
    Get the VDOT service singleton.

    Args:
        db: Optional database connection

    Returns:
        VDOTService instance
    """
    global _vdot_service

    if _vdot_service is None:
        _vdot_service = VDOTService(db)
    elif db is not None and _vdot_service._db is None:
        _vdot_service._db = db

    return _vdot_service


# Convenience functions for quick calculations
@lru_cache(maxsize=100)
def quick_vdot_calc(distance: str, time_str: str) -> float:
    """
    Quick VDOT calculation (cached).

    Args:
        distance: Race distance
        time_str: Race time

    Returns:
        VDOT value
    """
    result = calculate_vdot_from_race(distance, time_str)
    return result.vdot


@lru_cache(maxsize=50)
def quick_pace_zones(vdot: float) -> Dict[str, str]:
    """
    Quick pace zones summary (cached).

    Args:
        vdot: VDOT value

    Returns:
        Dictionary with zone name -> pace range string
    """
    zones = get_pace_zones(vdot)
    return {
        name: zone.pace_range_formatted
        for name, zone in zones.items()
    }
