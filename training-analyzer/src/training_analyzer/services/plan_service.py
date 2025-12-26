"""
Training plan service for plan-related business logic.

Handles:
- Plan creation, retrieval, and updates
- Plan generation via LLM
- Plan activation and lifecycle management
- Session management
"""

from typing import Any, AsyncIterator, Dict, List, Optional, Tuple
from datetime import datetime, date, timedelta
import asyncio
import json
import logging
import uuid

from pydantic import BaseModel, Field

from .base import BaseService, CacheProtocol, PaginationParams, PaginatedResult
from ..exceptions import (
    PlanNotFoundError,
    PlanValidationError,
    PlanGenerationError,
    PlanAdaptationError,
    PlanAlreadyActiveError,
)
from ..models.plans import (
    TrainingPlan,
    TrainingWeek,
    TrainingSession,
    PlanGoal,
    PlanConstraints,
    PlanPhase,
    PlanStatus,
    SessionType,
    CompletionStatus,
)


class PlanFilters(BaseModel):
    """Filters for plan listing."""

    status: Optional[str] = None
    start_date_from: Optional[str] = None
    start_date_to: Optional[str] = None


class PlanSummary(BaseModel):
    """Summary information about a plan for listing."""

    id: str
    name: str
    status: str
    goal_race: str
    goal_date: str
    total_weeks: int
    current_week: int
    compliance_pct: float = 0.0
    created_at: str


class CreatePlanRequest(BaseModel):
    """Request to create a new plan."""

    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    goal: PlanGoal
    constraints: PlanConstraints
    start_date: Optional[str] = None  # Defaults to next Monday


class GeneratePlanRequest(CreatePlanRequest):
    """Request to generate a plan with AI."""

    regenerate: bool = False


class UpdatePlanRequest(BaseModel):
    """Request to update a plan."""

    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class UpdateSessionRequest(BaseModel):
    """Request to update a session."""

    completion_status: Optional[str] = None
    actual_duration: Optional[int] = None
    actual_distance: Optional[float] = None
    actual_load: Optional[float] = None
    workout_id: Optional[str] = None
    notes: Optional[str] = None


class PlanService(BaseService):
    """
    Service for training plan operations.

    This service handles:
    - CRUD operations for training plans
    - AI-powered plan generation
    - Plan adaptation based on performance
    - Session tracking and updates
    """

    CACHE_TTL_SECONDS = 600  # 10 minutes
    GENERATION_TIMEOUT_SECONDS = 120

    def __init__(
        self,
        plan_agent: Any,  # LangGraph agent for plan generation
        workout_service: Any,  # WorkoutService
        coach_service: Any,  # CoachService for athlete context
        cache: Optional[CacheProtocol] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        super().__init__(cache=cache, logger=logger)
        self._plan_agent = plan_agent
        self._workout_service = workout_service
        self._coach_service = coach_service
        # In-memory storage for demo (replace with database)
        self._plans: Dict[str, TrainingPlan] = {}

    async def get_plan(self, plan_id: str) -> TrainingPlan:
        """
        Get a plan by ID.

        Args:
            plan_id: The plan identifier

        Returns:
            The training plan

        Raises:
            PlanNotFoundError: If plan doesn't exist
        """
        # Try cache first
        cache_key = f"plan:{plan_id}"
        cached = await self._get_from_cache(cache_key)
        if cached:
            return TrainingPlan.model_validate(cached)

        # Fetch from storage
        plan = self._plans.get(plan_id)
        if not plan:
            raise PlanNotFoundError(plan_id)

        # Cache the result
        await self._set_in_cache(
            cache_key,
            plan.model_dump(mode="json"),
            self.CACHE_TTL_SECONDS,
        )

        return plan

    async def get_plans(
        self,
        pagination: PaginationParams,
        filters: Optional[PlanFilters] = None,
    ) -> PaginatedResult[PlanSummary]:
        """
        Get paginated list of plans with optional filtering.

        Args:
            pagination: Pagination parameters
            filters: Optional filters to apply

        Returns:
            PaginatedResult containing plan summaries
        """
        # Filter plans
        plans = list(self._plans.values())

        if filters:
            if filters.status:
                plans = [p for p in plans if p.status.value == filters.status]

        # Sort
        sort_key = pagination.sort_by or "created_at"
        reverse = pagination.sort_order == "desc"
        plans.sort(key=lambda p: getattr(p, sort_key, ""), reverse=reverse)

        # Paginate
        total = len(plans)
        start = pagination.offset
        end = start + pagination.limit
        page_plans = plans[start:end]

        # Convert to summaries
        summaries = [self._plan_to_summary(p) for p in page_plans]

        return PaginatedResult(
            items=summaries,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    async def get_active_plan(self) -> Optional[TrainingPlan]:
        """
        Get the currently active plan.

        Returns:
            The active plan or None if no plan is active
        """
        for plan in self._plans.values():
            if plan.status == PlanStatus.ACTIVE:
                return plan
        return None

    async def create_plan(self, request: CreatePlanRequest) -> TrainingPlan:
        """
        Create a new plan without AI generation.

        Args:
            request: The plan creation request

        Returns:
            The created plan
        """
        # Calculate dates
        start_date = self._parse_start_date(request.start_date)
        end_date = self._calculate_end_date(start_date, request.goal.race_date)

        # Create plan
        plan_id = str(uuid.uuid4())
        plan = TrainingPlan(
            id=plan_id,
            name=request.name,
            description=request.description,
            goal=request.goal,
            constraints=request.constraints,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            total_weeks=self._calculate_weeks(start_date, end_date),
            current_week=1,
            status=PlanStatus.DRAFT,
            weeks=[],
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )

        self._plans[plan_id] = plan
        self.logger.info(f"Created plan {plan_id}: {request.name}")

        return plan

    async def generate_plan(
        self,
        request: GeneratePlanRequest,
    ) -> TrainingPlan:
        """
        Generate a training plan using AI.

        Args:
            request: The plan generation request

        Returns:
            The generated plan

        Raises:
            PlanGenerationError: If generation fails
        """
        # Create basic plan
        plan = await self.create_plan(request)

        # Generate weeks using agent
        try:
            async with asyncio.timeout(self.GENERATION_TIMEOUT_SECONDS):
                # Get athlete context
                athlete_context = self._get_athlete_context()

                # Run plan generation agent
                result = await self._plan_agent.generate_plan(
                    goal=request.goal.model_dump(),
                    constraints=request.constraints.model_dump(),
                    athlete_context=athlete_context,
                    total_weeks=plan.total_weeks,
                )

                # Update plan with generated weeks
                plan.weeks = self._parse_generated_weeks(result, plan)
                plan.updated_at = datetime.utcnow().isoformat()

                self._plans[plan.id] = plan
                await self._invalidate_plan_cache(plan.id)

        except asyncio.TimeoutError:
            # Cleanup the plan on timeout
            del self._plans[plan.id]
            raise PlanGenerationError(
                message="Plan generation timed out",
                phase="generation",
            )
        except Exception as e:
            # Cleanup on error
            del self._plans[plan.id]
            self.logger.error(f"Plan generation failed: {e}")
            raise PlanGenerationError(
                message=f"Failed to generate plan: {e}",
            )

        self.logger.info(f"Generated plan {plan.id} with {len(plan.weeks)} weeks")
        return plan

    async def stream_generate_plan(
        self,
        request: GeneratePlanRequest,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream plan generation progress.

        Yields:
            Progress updates and final plan
        """
        yield {
            "type": "progress",
            "phase": "initializing",
            "message": "Analyzing athlete profile...",
            "percentage": 10,
        }

        # Create basic plan
        try:
            plan = await self.create_plan(request)
        except Exception as e:
            yield {"type": "error", "error": str(e)}
            return

        yield {
            "type": "progress",
            "phase": "designing",
            "message": "Designing periodization structure...",
            "percentage": 25,
        }

        # Get athlete context
        athlete_context = self._get_athlete_context()

        yield {
            "type": "progress",
            "phase": "generating",
            "message": f"Generating {plan.total_weeks} weeks of training...",
            "percentage": 40,
        }

        # Generate weeks
        try:
            weeks = []
            weeks_per_progress = max(1, plan.total_weeks // 4)

            for i in range(plan.total_weeks):
                week = await self._generate_single_week(
                    plan=plan,
                    week_number=i + 1,
                    athlete_context=athlete_context,
                )
                weeks.append(week)

                if (i + 1) % weeks_per_progress == 0:
                    progress = 40 + int((i + 1) / plan.total_weeks * 50)
                    yield {
                        "type": "progress",
                        "phase": "generating",
                        "message": f"Generated week {i + 1} of {plan.total_weeks}...",
                        "percentage": progress,
                    }

            plan.weeks = weeks
            plan.updated_at = datetime.utcnow().isoformat()
            self._plans[plan.id] = plan

        except Exception as e:
            del self._plans[plan.id]
            yield {"type": "error", "error": str(e)}
            return

        yield {
            "type": "progress",
            "phase": "finalizing",
            "message": "Finalizing plan...",
            "percentage": 95,
        }

        yield {
            "type": "done",
            "plan": plan.model_dump(mode="json"),
        }

    async def update_plan(
        self,
        plan_id: str,
        request: UpdatePlanRequest,
    ) -> TrainingPlan:
        """
        Update a plan.

        Args:
            plan_id: The plan ID
            request: The update request

        Returns:
            The updated plan
        """
        plan = await self.get_plan(plan_id)

        if request.name is not None:
            plan.name = request.name
        if request.description is not None:
            plan.description = request.description
        if request.status is not None:
            plan.status = PlanStatus(request.status)

        plan.updated_at = datetime.utcnow().isoformat()
        self._plans[plan_id] = plan
        await self._invalidate_plan_cache(plan_id)

        return plan

    async def delete_plan(self, plan_id: str) -> None:
        """
        Delete a plan.

        Args:
            plan_id: The plan ID

        Raises:
            PlanNotFoundError: If plan doesn't exist
        """
        if plan_id not in self._plans:
            raise PlanNotFoundError(plan_id)

        del self._plans[plan_id]
        await self._invalidate_plan_cache(plan_id)
        self.logger.info(f"Deleted plan {plan_id}")

    async def activate_plan(self, plan_id: str) -> TrainingPlan:
        """
        Activate a plan.

        Args:
            plan_id: The plan ID

        Returns:
            The activated plan

        Raises:
            PlanAlreadyActiveError: If another plan is already active
        """
        # Check for existing active plan
        active = await self.get_active_plan()
        if active and active.id != plan_id:
            raise PlanAlreadyActiveError(active.id)

        plan = await self.get_plan(plan_id)
        plan.status = PlanStatus.ACTIVE
        plan.updated_at = datetime.utcnow().isoformat()

        self._plans[plan_id] = plan
        await self._invalidate_plan_cache(plan_id)

        self.logger.info(f"Activated plan {plan_id}")
        return plan

    async def pause_plan(self, plan_id: str) -> TrainingPlan:
        """
        Pause a plan.

        Args:
            plan_id: The plan ID

        Returns:
            The paused plan
        """
        plan = await self.get_plan(plan_id)
        plan.status = PlanStatus.PAUSED
        plan.updated_at = datetime.utcnow().isoformat()

        self._plans[plan_id] = plan
        await self._invalidate_plan_cache(plan_id)

        self.logger.info(f"Paused plan {plan_id}")
        return plan

    async def update_session(
        self,
        plan_id: str,
        session_id: str,
        request: UpdateSessionRequest,
    ) -> TrainingSession:
        """
        Update a session within a plan.

        Args:
            plan_id: The plan ID
            session_id: The session ID
            request: The update request

        Returns:
            The updated session
        """
        plan = await self.get_plan(plan_id)

        # Find the session
        session = None
        for week in plan.weeks:
            for sess in week.sessions:
                if sess.id == session_id:
                    session = sess
                    break
            if session:
                break

        if not session:
            raise PlanNotFoundError(session_id)

        # Update fields
        if request.completion_status is not None:
            session.completion_status = CompletionStatus(request.completion_status)
        if request.actual_duration is not None:
            session.actual_duration = request.actual_duration
        if request.actual_distance is not None:
            session.actual_distance = request.actual_distance
        if request.actual_load is not None:
            session.actual_load = request.actual_load
        if request.workout_id is not None:
            session.workout_id = request.workout_id
        if request.notes is not None:
            session.notes = request.notes

        plan.updated_at = datetime.utcnow().isoformat()
        self._plans[plan_id] = plan
        await self._invalidate_plan_cache(plan_id)

        return session

    async def adapt_plan(
        self,
        plan_id: str,
        reason: Optional[str] = None,
    ) -> TrainingPlan:
        """
        Adapt remaining weeks of a plan based on performance.

        Args:
            plan_id: The plan ID
            reason: Optional reason for adaptation

        Returns:
            The adapted plan
        """
        plan = await self.get_plan(plan_id)

        try:
            # Gather performance data
            performance_data = await self._gather_performance_data(plan)

            # Run adaptation agent
            adapted_weeks = await self._plan_agent.adapt_plan(
                plan=plan.model_dump(),
                performance_data=performance_data,
                reason=reason,
            )

            # Update remaining weeks
            current_week = plan.current_week
            for i, adapted_week in enumerate(adapted_weeks):
                week_index = current_week + i - 1
                if week_index < len(plan.weeks):
                    plan.weeks[week_index] = self._parse_week(
                        adapted_week,
                        plan,
                        week_index + 1,
                    )

            plan.updated_at = datetime.utcnow().isoformat()
            self._plans[plan_id] = plan
            await self._invalidate_plan_cache(plan_id)

        except Exception as e:
            self.logger.error(f"Plan adaptation failed: {e}")
            raise PlanAdaptationError(
                message=f"Failed to adapt plan: {e}",
                plan_id=plan_id,
            )

        self.logger.info(f"Adapted plan {plan_id}")
        return plan

    # ========================================================================
    # Private methods
    # ========================================================================

    def _plan_to_summary(self, plan: TrainingPlan) -> PlanSummary:
        """Convert a plan to a summary."""
        return PlanSummary(
            id=plan.id,
            name=plan.name,
            status=plan.status.value,
            goal_race=plan.goal.race_distance.value,
            goal_date=plan.goal.race_date,
            total_weeks=plan.total_weeks,
            current_week=plan.current_week,
            compliance_pct=self._calculate_compliance(plan),
            created_at=plan.created_at,
        )

    def _calculate_compliance(self, plan: TrainingPlan) -> float:
        """Calculate plan compliance percentage."""
        total_sessions = 0
        completed_sessions = 0

        for week in plan.weeks:
            for session in week.sessions:
                if session.session_type != SessionType.REST:
                    total_sessions += 1
                    if session.completion_status == CompletionStatus.COMPLETED:
                        completed_sessions += 1

        if total_sessions == 0:
            return 0.0
        return round((completed_sessions / total_sessions) * 100, 1)

    def _parse_start_date(self, date_str: Optional[str]) -> date:
        """Parse start date or default to next Monday."""
        if date_str:
            return date.fromisoformat(date_str)
        # Default to next Monday
        today = date.today()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        return today + timedelta(days=days_until_monday)

    def _calculate_end_date(self, start: date, race_date_str: str) -> date:
        """Calculate end date based on race date."""
        race_date = date.fromisoformat(race_date_str)
        return race_date

    def _calculate_weeks(self, start: date, end: date) -> int:
        """Calculate number of weeks between dates."""
        delta = end - start
        return max(1, delta.days // 7)

    def _get_athlete_context(self) -> Optional[Dict[str, Any]]:
        """Get athlete context from coach service."""
        try:
            if hasattr(self._coach_service, "get_llm_context"):
                ctx = self._coach_service.get_llm_context()
                return ctx.__dict__ if ctx else None
        except Exception as e:
            self.logger.warning(f"Failed to get athlete context: {e}")
        return None

    async def _generate_single_week(
        self,
        plan: TrainingPlan,
        week_number: int,
        athlete_context: Optional[Dict[str, Any]],
    ) -> TrainingWeek:
        """Generate a single week of training."""
        # This would use the plan agent to generate the week
        # For now, create a placeholder
        week_id = str(uuid.uuid4())
        start_date = date.fromisoformat(plan.start_date) + timedelta(weeks=week_number - 1)

        return TrainingWeek(
            id=week_id,
            plan_id=plan.id,
            week_number=week_number,
            start_date=start_date.isoformat(),
            end_date=(start_date + timedelta(days=6)).isoformat(),
            phase=self._determine_phase(week_number, plan.total_weeks),
            target_load=0,
            actual_load=0,
            sessions=[],
            focus_areas=[],
        )

    def _determine_phase(self, week_number: int, total_weeks: int) -> PlanPhase:
        """Determine the training phase for a week."""
        progress = week_number / total_weeks

        if progress < 0.3:
            return PlanPhase.BASE
        elif progress < 0.7:
            return PlanPhase.BUILD
        elif progress < 0.9:
            return PlanPhase.PEAK
        else:
            return PlanPhase.TAPER

    def _parse_generated_weeks(
        self,
        result: Dict[str, Any],
        plan: TrainingPlan,
    ) -> List[TrainingWeek]:
        """Parse weeks from agent result."""
        weeks = []
        for i, week_data in enumerate(result.get("weeks", [])):
            week = self._parse_week(week_data, plan, i + 1)
            weeks.append(week)
        return weeks

    def _parse_week(
        self,
        week_data: Dict[str, Any],
        plan: TrainingPlan,
        week_number: int,
    ) -> TrainingWeek:
        """Parse a single week from agent result."""
        week_id = str(uuid.uuid4())
        start_date = date.fromisoformat(plan.start_date) + timedelta(weeks=week_number - 1)

        sessions = []
        for sess_data in week_data.get("sessions", []):
            session = self._parse_session(sess_data, week_id, start_date)
            sessions.append(session)

        return TrainingWeek(
            id=week_id,
            plan_id=plan.id,
            week_number=week_number,
            start_date=start_date.isoformat(),
            end_date=(start_date + timedelta(days=6)).isoformat(),
            phase=PlanPhase(week_data.get("phase", "base")),
            target_load=week_data.get("target_load", 0),
            actual_load=0,
            sessions=sessions,
            focus_areas=week_data.get("focus_areas", []),
            notes=week_data.get("notes"),
        )

    def _parse_session(
        self,
        sess_data: Dict[str, Any],
        week_id: str,
        week_start: date,
    ) -> TrainingSession:
        """Parse a single session from agent result."""
        day_of_week = sess_data.get("day_of_week", 0)
        session_date = week_start + timedelta(days=day_of_week)

        return TrainingSession(
            id=str(uuid.uuid4()),
            week_id=week_id,
            day_of_week=day_of_week,
            date=session_date.isoformat(),
            session_type=SessionType(sess_data.get("workout_type", "easy")),
            name=sess_data.get("description", "Workout"),
            description=sess_data.get("notes", ""),
            target_duration=sess_data.get("target_duration_min", 0),
            target_load=sess_data.get("target_load", 0),
            completion_status=CompletionStatus.PENDING,
        )

    async def _gather_performance_data(
        self,
        plan: TrainingPlan,
    ) -> Dict[str, Any]:
        """Gather performance data for plan adaptation."""
        # Collect data from completed sessions
        completed_sessions = []
        for week in plan.weeks:
            for session in week.sessions:
                if session.completion_status == CompletionStatus.COMPLETED:
                    completed_sessions.append({
                        "date": session.date,
                        "type": session.session_type.value,
                        "planned_duration": session.target_duration,
                        "actual_duration": session.actual_duration,
                        "planned_load": session.target_load,
                        "actual_load": session.actual_load,
                    })

        return {
            "completed_sessions": completed_sessions,
            "compliance": self._calculate_compliance(plan),
            "current_week": plan.current_week,
        }

    async def _invalidate_plan_cache(self, plan_id: str) -> None:
        """Invalidate plan cache."""
        cache_key = f"plan:{plan_id}"
        await self._delete_from_cache(cache_key)
