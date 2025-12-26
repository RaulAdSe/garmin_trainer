"""
Workout service for business logic around workouts.

Handles:
- Workout retrieval with filtering and pagination
- Workout validation
- FIT file export
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import logging

from pydantic import BaseModel, Field

from .base import BaseService, CacheProtocol, PaginationParams, PaginatedResult
from ..exceptions import (
    WorkoutNotFoundError,
    WorkoutValidationError,
    FITEncodingError,
)
from ..models.workouts import StructuredWorkout, WorkoutSport


class WorkoutFilters(BaseModel):
    """Filters for workout listing."""

    start_date: Optional[str] = None
    end_date: Optional[str] = None
    activity_type: Optional[str] = None
    min_distance_km: Optional[float] = None
    max_distance_km: Optional[float] = None
    search: Optional[str] = None


class WorkoutSummary(BaseModel):
    """Summary information about a workout for listing."""

    id: str
    name: str
    activity_type: str
    date: str
    duration_min: float
    distance_km: Optional[float] = None
    avg_hr: Optional[int] = None
    hrss: Optional[float] = None
    has_analysis: bool = False


class WorkoutDetail(BaseModel):
    """Full workout details."""

    id: str
    name: str
    activity_type: str
    date: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_min: float
    distance_km: Optional[float] = None
    avg_hr: Optional[int] = None
    max_hr: Optional[int] = None
    pace_sec_per_km: Optional[int] = None
    hrss: Optional[float] = None
    trimp: Optional[float] = None
    zone1_pct: float = 0.0
    zone2_pct: float = 0.0
    zone3_pct: float = 0.0
    zone4_pct: float = 0.0
    zone5_pct: float = 0.0
    cadence: Optional[int] = None
    elevation_gain: Optional[float] = None
    calories: Optional[int] = None
    notes: Optional[str] = None


class WorkoutService(BaseService):
    """
    Service for workout-related business logic.

    This service abstracts the data access layer and provides
    a clean interface for workout operations.
    """

    CACHE_TTL_SECONDS = 300  # 5 minutes

    def __init__(
        self,
        data_provider: Any,  # This would be your data access layer
        cache: Optional[CacheProtocol] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        super().__init__(cache=cache, logger=logger)
        self._data_provider = data_provider

    async def get_workout(self, workout_id: str) -> WorkoutDetail:
        """
        Get a single workout by ID.

        Args:
            workout_id: The workout identifier

        Returns:
            WorkoutDetail with full workout information

        Raises:
            WorkoutNotFoundError: If workout doesn't exist
        """
        # Try cache first
        cache_key = f"workout:{workout_id}"
        cached = await self._get_from_cache(cache_key)
        if cached:
            return WorkoutDetail.model_validate(cached)

        # Fetch from data provider
        workout_data = await self._fetch_workout_data(workout_id)
        if workout_data is None:
            raise WorkoutNotFoundError(workout_id)

        workout = WorkoutDetail.model_validate(workout_data)

        # Cache the result
        await self._set_in_cache(
            cache_key,
            workout.model_dump(),
            self.CACHE_TTL_SECONDS,
        )

        return workout

    async def get_workouts(
        self,
        pagination: PaginationParams,
        filters: Optional[WorkoutFilters] = None,
    ) -> PaginatedResult[WorkoutSummary]:
        """
        Get paginated list of workouts with optional filtering.

        Args:
            pagination: Pagination parameters
            filters: Optional filters to apply

        Returns:
            PaginatedResult containing workout summaries
        """
        # Build filter dict
        filter_dict = filters.model_dump(exclude_none=True) if filters else {}

        # Fetch from data provider
        workouts, total = await self._fetch_workouts(
            limit=pagination.limit,
            offset=pagination.offset,
            filters=filter_dict,
            sort_by=pagination.sort_by,
            sort_order=pagination.sort_order,
        )

        summaries = [WorkoutSummary.model_validate(w) for w in workouts]

        return PaginatedResult(
            items=summaries,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    async def get_recent_workouts(
        self,
        days: int = 7,
        limit: int = 10,
    ) -> List[WorkoutSummary]:
        """
        Get recent workouts within the specified number of days.

        Args:
            days: Number of days to look back
            limit: Maximum number of workouts to return

        Returns:
            List of recent workout summaries
        """
        # Calculate date range
        from datetime import datetime, timedelta

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        filters = WorkoutFilters(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )

        pagination = PaginationParams(page=1, page_size=limit, sort_by="date")

        result = await self.get_workouts(pagination, filters)
        return result.items

    async def get_similar_workouts(
        self,
        workout_id: str,
        limit: int = 5,
    ) -> List[WorkoutSummary]:
        """
        Find workouts similar to the specified workout.

        Similarity is based on activity type, duration, and distance.

        Args:
            workout_id: The reference workout ID
            limit: Maximum number of similar workouts to return

        Returns:
            List of similar workout summaries
        """
        # Get the reference workout
        reference = await self.get_workout(workout_id)

        # Find similar workouts
        similar = await self._find_similar_workouts(
            activity_type=reference.activity_type,
            duration_min=reference.duration_min,
            distance_km=reference.distance_km,
            exclude_id=workout_id,
            limit=limit,
        )

        return [WorkoutSummary.model_validate(w) for w in similar]

    async def export_to_fit(self, workout: StructuredWorkout) -> bytes:
        """
        Export a structured workout to FIT file format.

        Args:
            workout: The structured workout to export

        Returns:
            FIT file contents as bytes

        Raises:
            FITEncodingError: If encoding fails
        """
        from ..fit import encode_workout_to_fit

        try:
            return encode_workout_to_fit(workout)
        except Exception as e:
            self.logger.error(f"FIT encoding failed: {e}")
            raise FITEncodingError(
                message=f"Failed to encode workout to FIT format: {e}",
                workout_id=workout.name,
            )

    def validate_workout_data(self, data: Dict[str, Any]) -> WorkoutDetail:
        """
        Validate workout data.

        Args:
            data: Raw workout data dictionary

        Returns:
            Validated WorkoutDetail

        Raises:
            WorkoutValidationError: If validation fails
        """
        try:
            return WorkoutDetail.model_validate(data)
        except Exception as e:
            raise WorkoutValidationError(
                message=f"Invalid workout data: {e}",
                details={"validation_error": str(e)},
            )

    # ========================================================================
    # Private methods - data access abstraction
    # ========================================================================

    async def _fetch_workout_data(self, workout_id: str) -> Optional[Dict[str, Any]]:
        """Fetch raw workout data from the data provider."""
        # This would be implemented by the actual data layer
        # For now, delegate to the data provider
        if hasattr(self._data_provider, "get_activity"):
            activity = self._data_provider.get_activity(workout_id)
            if activity:
                return self._activity_to_workout_dict(activity)
        return None

    async def _fetch_workouts(
        self,
        limit: int,
        offset: int,
        filters: Dict[str, Any],
        sort_by: Optional[str],
        sort_order: str,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Fetch workouts from the data provider."""
        # This would be implemented by the actual data layer
        if hasattr(self._data_provider, "get_activities"):
            activities = self._data_provider.get_activities(
                limit=limit,
                offset=offset,
                filters=filters,
            )
            total = self._data_provider.count_activities(filters=filters)
            return [self._activity_to_workout_dict(a) for a in activities], total
        return [], 0

    async def _find_similar_workouts(
        self,
        activity_type: str,
        duration_min: float,
        distance_km: Optional[float],
        exclude_id: str,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Find similar workouts based on activity type, duration, and distance."""
        # This would use similarity matching in the actual implementation
        # For now, just filter by activity type
        filters = {"activity_type": activity_type}
        workouts, _ = await self._fetch_workouts(
            limit=limit + 1,  # +1 to account for potentially excluding self
            offset=0,
            filters=filters,
            sort_by="date",
            sort_order="desc",
        )
        # Filter out the reference workout
        return [w for w in workouts if w.get("id") != exclude_id][:limit]

    def _activity_to_workout_dict(self, activity: Any) -> Dict[str, Any]:
        """Convert an activity object to a workout dictionary."""
        # This would map fields from your data model
        if isinstance(activity, dict):
            return activity
        # Handle object attributes
        return {
            "id": getattr(activity, "activity_id", None) or getattr(activity, "id", ""),
            "name": getattr(activity, "activity_name", "") or getattr(activity, "name", ""),
            "activity_type": getattr(activity, "activity_type", "running"),
            "date": str(getattr(activity, "date", "")),
            "duration_min": getattr(activity, "duration_min", 0.0),
            "distance_km": getattr(activity, "distance_km", None),
            "avg_hr": getattr(activity, "avg_hr", None),
            "max_hr": getattr(activity, "max_hr", None),
            "pace_sec_per_km": getattr(activity, "pace_sec_per_km", None),
            "hrss": getattr(activity, "hrss", None),
            "trimp": getattr(activity, "trimp", None),
            "zone1_pct": getattr(activity, "zone1_pct", 0.0),
            "zone2_pct": getattr(activity, "zone2_pct", 0.0),
            "zone3_pct": getattr(activity, "zone3_pct", 0.0),
            "zone4_pct": getattr(activity, "zone4_pct", 0.0),
            "zone5_pct": getattr(activity, "zone5_pct", 0.0),
            "cadence": getattr(activity, "cadence", None),
            "elevation_gain": getattr(activity, "elevation_gain", None),
            "calories": getattr(activity, "calories", None),
            "has_analysis": getattr(activity, "has_analysis", False),
        }
