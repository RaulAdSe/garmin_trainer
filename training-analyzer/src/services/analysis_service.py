"""
Analysis service for workout analysis operations.

Handles:
- Workout analysis generation
- Streaming analysis
- Analysis caching and retrieval
- Similar workout comparison
"""

from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Tuple
from datetime import datetime
import asyncio
import json
import logging

from pydantic import BaseModel, Field

from .base import BaseService, CacheProtocol
from ..exceptions import (
    AnalysisError,
    WorkoutNotFoundError,
    LLMServiceUnavailableError,
    LLMTimeoutError,
    LLMResponseInvalidError,
)
from ..models.analysis import (
    AnalysisStatus,
    WorkoutAnalysisResult,
    AnalysisContext,
    WorkoutInsight,
    WorkoutExecutionRating,
    AthleteContext,
    WorkoutData,
)


class AnalysisRequest(BaseModel):
    """Request for workout analysis."""

    workout_id: str
    include_similar: bool = True
    include_context: bool = True
    force_refresh: bool = False


class StreamingAnalysisOptions(BaseModel):
    """Options for streaming analysis."""

    chunk_delay_ms: int = Field(default=0, ge=0, le=1000)
    include_metadata: bool = True


class AnalysisService(BaseService):
    """
    Service for workout analysis operations.

    This service orchestrates:
    - LLM-powered workout analysis
    - Streaming analysis with SSE
    - Caching of analysis results
    - Comparison with similar workouts
    """

    CACHE_TTL_SECONDS = 3600  # 1 hour
    ANALYSIS_TIMEOUT_SECONDS = 60

    def __init__(
        self,
        llm_client: Any,  # LLM client for analysis
        workout_service: Any,  # WorkoutService for fetching workouts
        coach_service: Any,  # CoachService for athlete context
        cache: Optional[CacheProtocol] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        super().__init__(cache=cache, logger=logger)
        self._llm_client = llm_client
        self._workout_service = workout_service
        self._coach_service = coach_service

    async def analyze_workout(
        self,
        request: AnalysisRequest,
    ) -> WorkoutAnalysisResult:
        """
        Analyze a workout and return the result.

        Args:
            request: Analysis request parameters

        Returns:
            WorkoutAnalysisResult with the analysis

        Raises:
            WorkoutNotFoundError: If workout doesn't exist
            AnalysisError: If analysis fails
        """
        workout_id = request.workout_id

        # Check cache unless force refresh
        if not request.force_refresh:
            cached = await self._get_cached_analysis(workout_id)
            if cached:
                cached.cached_at = datetime.utcnow()
                return cached

        # Get workout data
        workout_data = await self._get_workout_data(workout_id)

        # Get athlete context if requested
        athlete_context = None
        if request.include_context:
            athlete_context = await self._get_athlete_context()

        # Get similar workouts for comparison if requested
        similar_workouts: List[WorkoutData] = []
        if request.include_similar:
            similar_workouts = await self._get_similar_workouts(workout_id)

        # Perform analysis
        try:
            result = await self._perform_analysis(
                workout_data=workout_data,
                athlete_context=athlete_context,
                similar_workouts=similar_workouts,
            )
        except asyncio.TimeoutError:
            raise LLMTimeoutError(timeout_seconds=self.ANALYSIS_TIMEOUT_SECONDS)
        except Exception as e:
            self.logger.error(f"Analysis failed for workout {workout_id}: {e}")
            raise AnalysisError(
                message=f"Failed to analyze workout: {e}",
                workout_id=workout_id,
            )

        # Cache the result
        await self._cache_analysis(workout_id, result)

        return result

    async def stream_analysis(
        self,
        request: AnalysisRequest,
        options: Optional[StreamingAnalysisOptions] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream workout analysis with SSE-compatible output.

        Yields:
            Dictionary chunks with type and content/analysis

        Raises:
            WorkoutNotFoundError: If workout doesn't exist
        """
        options = options or StreamingAnalysisOptions()
        workout_id = request.workout_id

        # Check cache for complete analysis (unless force refresh)
        if not request.force_refresh:
            cached = await self._get_cached_analysis(workout_id)
            if cached:
                yield {"type": "content", "content": cached.summary}
                yield {"type": "done", "analysis": cached.model_dump()}
                return

        # Get workout data
        workout_data = await self._get_workout_data(workout_id)

        # Get athlete context
        athlete_context = None
        if request.include_context:
            athlete_context = await self._get_athlete_context()

        # Get similar workouts
        similar_workouts: List[WorkoutData] = []
        if request.include_similar:
            similar_workouts = await self._get_similar_workouts(workout_id)

        # Stream from LLM
        full_content = ""
        try:
            async for chunk in self._stream_llm_analysis(
                workout_data=workout_data,
                athlete_context=athlete_context,
                similar_workouts=similar_workouts,
            ):
                full_content += chunk
                yield {"type": "content", "content": chunk}

                # Optional delay between chunks
                if options.chunk_delay_ms > 0:
                    await asyncio.sleep(options.chunk_delay_ms / 1000)

        except Exception as e:
            self.logger.error(f"Streaming analysis failed: {e}")
            yield {"type": "error", "error": str(e)}
            return

        # Parse and cache the complete response
        try:
            result = await self._parse_analysis_response(
                workout_id=workout_id,
                raw_response=full_content,
                athlete_context=athlete_context,
            )
            await self._cache_analysis(workout_id, result)

            yield {
                "type": "done",
                "analysis": result.model_dump(mode="json"),
            }

        except Exception as e:
            self.logger.error(f"Failed to parse analysis: {e}")
            yield {"type": "error", "error": f"Failed to parse analysis: {e}"}

    async def get_cached_analysis(
        self,
        workout_id: str,
    ) -> Optional[WorkoutAnalysisResult]:
        """
        Get cached analysis if available.

        Args:
            workout_id: The workout ID

        Returns:
            Cached analysis or None
        """
        return await self._get_cached_analysis(workout_id)

    async def invalidate_analysis_cache(self, workout_id: str) -> None:
        """
        Invalidate cached analysis for a workout.

        Args:
            workout_id: The workout ID
        """
        cache_key = f"analysis:{workout_id}"
        await self._delete_from_cache(cache_key)
        self.logger.info(f"Invalidated analysis cache for workout {workout_id}")

    # ========================================================================
    # Private methods
    # ========================================================================

    async def _get_workout_data(self, workout_id: str) -> WorkoutData:
        """Fetch workout data for analysis."""
        try:
            workout = await self._workout_service.get_workout(workout_id)
            return WorkoutData.from_dict(workout.model_dump())
        except Exception as e:
            raise WorkoutNotFoundError(workout_id)

    async def _get_athlete_context(self) -> Optional[AthleteContext]:
        """Get athlete context from coach service."""
        try:
            if hasattr(self._coach_service, "get_llm_context"):
                return self._coach_service.get_llm_context()
        except Exception as e:
            self.logger.warning(f"Failed to get athlete context: {e}")
        return None

    async def _get_similar_workouts(
        self,
        workout_id: str,
        limit: int = 5,
    ) -> List[WorkoutData]:
        """Get similar workouts for comparison."""
        try:
            similar = await self._workout_service.get_similar_workouts(
                workout_id,
                limit=limit,
            )
            return [WorkoutData.from_dict(w.model_dump()) for w in similar]
        except Exception as e:
            self.logger.warning(f"Failed to get similar workouts: {e}")
            return []

    async def _get_cached_analysis(
        self,
        workout_id: str,
    ) -> Optional[WorkoutAnalysisResult]:
        """Get analysis from cache."""
        cache_key = f"analysis:{workout_id}"
        cached_data = await self._get_from_cache(cache_key)
        if cached_data:
            try:
                return WorkoutAnalysisResult.model_validate(cached_data)
            except Exception as e:
                self.logger.warning(f"Failed to parse cached analysis: {e}")
                await self._delete_from_cache(cache_key)
        return None

    async def _cache_analysis(
        self,
        workout_id: str,
        result: WorkoutAnalysisResult,
    ) -> None:
        """Cache the analysis result."""
        cache_key = f"analysis:{workout_id}"
        await self._set_in_cache(
            cache_key,
            result.model_dump(mode="json"),
            self.CACHE_TTL_SECONDS,
        )

    async def _perform_analysis(
        self,
        workout_data: WorkoutData,
        athlete_context: Optional[AthleteContext],
        similar_workouts: List[WorkoutData],
    ) -> WorkoutAnalysisResult:
        """Perform the actual LLM analysis."""
        from ..llm.prompts import (
            WORKOUT_ANALYSIS_SYSTEM,
            WORKOUT_ANALYSIS_USER,
        )

        # Build prompts
        athlete_context_str = (
            athlete_context.to_prompt_context() if athlete_context else "No context available"
        )

        similar_str = "\n\n".join(
            [f"Workout {i+1}:\n{w.to_prompt_data()}" for i, w in enumerate(similar_workouts)]
        ) if similar_workouts else "No similar workouts available"

        system_prompt = WORKOUT_ANALYSIS_SYSTEM.format(
            athlete_context=athlete_context_str,
        )
        user_prompt = WORKOUT_ANALYSIS_USER.format(
            workout_data=workout_data.to_prompt_data(),
            similar_workouts=similar_str,
        )

        # Call LLM with timeout
        async with asyncio.timeout(self.ANALYSIS_TIMEOUT_SECONDS):
            response = await self._llm_client.completion(
                system=system_prompt,
                user=user_prompt,
            )

        # Parse response
        return await self._parse_analysis_response(
            workout_id=workout_data.activity_id,
            raw_response=response,
            athlete_context=athlete_context,
        )

    async def _stream_llm_analysis(
        self,
        workout_data: WorkoutData,
        athlete_context: Optional[AthleteContext],
        similar_workouts: List[WorkoutData],
    ) -> AsyncIterator[str]:
        """Stream LLM analysis response."""
        from ..llm.prompts import (
            WORKOUT_ANALYSIS_SYSTEM,
            WORKOUT_ANALYSIS_USER,
        )

        # Build prompts
        athlete_context_str = (
            athlete_context.to_prompt_context() if athlete_context else "No context available"
        )

        similar_str = "\n\n".join(
            [f"Workout {i+1}:\n{w.to_prompt_data()}" for i, w in enumerate(similar_workouts)]
        ) if similar_workouts else "No similar workouts available"

        system_prompt = WORKOUT_ANALYSIS_SYSTEM.format(
            athlete_context=athlete_context_str,
        )
        user_prompt = WORKOUT_ANALYSIS_USER.format(
            workout_data=workout_data.to_prompt_data(),
            similar_workouts=similar_str,
        )

        # Stream from LLM
        async for chunk in self._llm_client.stream_completion(
            system=system_prompt,
            user=user_prompt,
        ):
            yield chunk

    async def _parse_analysis_response(
        self,
        workout_id: str,
        raw_response: str,
        athlete_context: Optional[AthleteContext],
    ) -> WorkoutAnalysisResult:
        """Parse LLM response into structured analysis."""
        import uuid

        # Extract sections from markdown-style response
        sections = self._extract_sections(raw_response)

        # Build context info
        context = None
        if athlete_context:
            context = AnalysisContext(
                ctl=athlete_context.ctl,
                atl=athlete_context.atl,
                tsb=athlete_context.tsb,
                acwr=athlete_context.acwr,
                readiness_score=athlete_context.readiness_score,
                readiness_zone=athlete_context.readiness_zone,
                recent_load_7d=athlete_context.recent_load_7d,
            )

        return WorkoutAnalysisResult(
            workout_id=workout_id,
            analysis_id=str(uuid.uuid4()),
            status=AnalysisStatus.COMPLETED,
            summary=sections.get("summary", ""),
            what_worked_well=sections.get("what_worked_well", []),
            observations=sections.get("observations", []),
            recommendations=sections.get("recommendations", []),
            execution_rating=self._infer_execution_rating(sections),
            training_fit=sections.get("training_fit"),
            context=context,
            raw_response=raw_response,
            created_at=datetime.utcnow(),
        )

    def _extract_sections(self, text: str) -> Dict[str, Any]:
        """Extract sections from markdown-formatted analysis."""
        sections: Dict[str, Any] = {}
        current_section = None
        current_items: List[str] = []

        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Check for section headers
            lower_line = line.lower()
            if "**summary**" in lower_line or lower_line.startswith("summary:"):
                if current_section and current_items:
                    sections[current_section] = current_items
                current_section = None
                # Extract inline summary
                if ":" in line:
                    sections["summary"] = line.split(":", 1)[1].strip()
            elif "**what worked well**" in lower_line or "what worked well:" in lower_line:
                current_section = "what_worked_well"
                current_items = []
            elif "**observations**" in lower_line or "observations:" in lower_line:
                if current_section and current_items:
                    sections[current_section] = current_items
                current_section = "observations"
                current_items = []
            elif "**recommendations**" in lower_line or "recommendations:" in lower_line:
                if current_section and current_items:
                    sections[current_section] = current_items
                current_section = "recommendations"
                current_items = []
            elif "**training fit**" in lower_line or "training fit:" in lower_line:
                if current_section and current_items:
                    sections[current_section] = current_items
                current_section = None
                if ":" in line:
                    sections["training_fit"] = line.split(":", 1)[1].strip()
            elif line.startswith("-") and current_section:
                # Bullet point item
                item = line[1:].strip()
                if item:
                    current_items.append(item)
            elif not line.startswith("**") and current_section is None and "summary" not in sections:
                # First non-header text is likely the summary
                sections["summary"] = line.strip("*").strip()

        # Don't forget the last section
        if current_section and current_items:
            sections[current_section] = current_items

        return sections

    def _infer_execution_rating(
        self,
        sections: Dict[str, Any],
    ) -> Optional[WorkoutExecutionRating]:
        """Infer execution rating from analysis content."""
        # Look for positive/negative signals
        well_items = len(sections.get("what_worked_well", []))
        observation_items = len(sections.get("observations", []))

        if well_items >= 3 and observation_items <= 1:
            return WorkoutExecutionRating.EXCELLENT
        elif well_items >= 2:
            return WorkoutExecutionRating.GOOD
        elif well_items >= 1:
            return WorkoutExecutionRating.FAIR
        elif observation_items >= 2:
            return WorkoutExecutionRating.NEEDS_IMPROVEMENT
        return None
