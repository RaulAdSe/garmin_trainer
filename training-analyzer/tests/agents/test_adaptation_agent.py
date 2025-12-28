"""Tests for the Adaptation Agent (LangGraph-based plan adaptation)."""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json

from training_analyzer.agents.adaptation_agent import (
    AdaptationAgent,
    AdaptationState,
    get_adaptation_agent,
    reset_adaptation_agent,
)
from training_analyzer.models.deviation import (
    DeviationType,
    AdaptationAction,
    DeviationMetrics,
    PlanDeviation,
    AdaptationSuggestion,
    SessionAdjustment,
)
from training_analyzer.models.plans import (
    TrainingPlan,
    TrainingWeek,
    PlannedSession,
    RaceGoal,
    PlanConstraints,
    AthleteContext,
    PeriodizationType,
    TrainingPhase,
    WorkoutType,
    RaceDistance,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_goal():
    """Create a sample race goal."""
    return RaceGoal(
        race_date=date.today() + timedelta(weeks=8),
        distance=RaceDistance.HALF_MARATHON,
        target_time_seconds=6000,
        race_name="Test Race",
        priority=1,
    )


@pytest.fixture
def sample_athlete_context():
    """Create sample athlete context."""
    return AthleteContext(
        current_ctl=45.0,
        current_atl=50.0,
        recent_weekly_load=300.0,
        recent_weekly_hours=5.0,
        max_hr=185,
        rest_hr=55,
        threshold_hr=165,
    )


@pytest.fixture
def sample_constraints():
    """Create sample plan constraints."""
    return PlanConstraints(
        days_per_week=5,
        long_run_day=6,
        rest_days=[4],
        max_weekly_hours=8.0,
    )


@pytest.fixture
def sample_plan(sample_goal, sample_athlete_context, sample_constraints):
    """Create a sample training plan."""
    weeks = []
    for week_num in range(1, 9):
        sessions = [
            PlannedSession(
                day_of_week=0,
                workout_type=WorkoutType.EASY,
                description="Easy run",
                target_duration_min=45,
                target_load=40.0,
                target_hr_zone="Zone 2",
            ),
            PlannedSession(
                day_of_week=2,
                workout_type=WorkoutType.TEMPO,
                description="Tempo run",
                target_duration_min=50,
                target_load=70.0,
                target_hr_zone="Zone 4",
            ),
            PlannedSession(
                day_of_week=4,
                workout_type=WorkoutType.REST,
                description="Rest day",
                target_duration_min=0,
                target_load=0.0,
            ),
            PlannedSession(
                day_of_week=6,
                workout_type=WorkoutType.LONG,
                description="Long run",
                target_duration_min=90,
                target_load=80.0,
                target_hr_zone="Zone 2",
            ),
        ]
        weeks.append(TrainingWeek(
            week_number=week_num,
            phase=TrainingPhase.BUILD,
            target_load=190.0,
            sessions=sessions,
        ))

    return TrainingPlan(
        id="plan_test_123",
        goal=sample_goal,
        weeks=weeks,
        periodization=PeriodizationType.LINEAR,
        peak_week=7,
        created_at=datetime.now(),
        athlete_context=sample_athlete_context,
        constraints=sample_constraints,
    )


@pytest.fixture
def harder_deviation(sample_plan):
    """Create a harder-than-planned deviation."""
    race_date = sample_plan.goal.race_date
    plan_start = race_date - timedelta(weeks=sample_plan.total_weeks)

    return PlanDeviation(
        plan_id=sample_plan.id,
        week_number=1,
        day_of_week=0,
        planned_date=plan_start,
        deviation_type=DeviationType.HARDER,
        metrics=DeviationMetrics(
            planned_duration_min=45,
            actual_duration_min=65,
            planned_load=40.0,
            actual_load=75.0,
        ),
        planned_workout_type="easy",
        actual_workout_id="act_123",
        actual_workout_type="running",
        severity="moderate",
    )


@pytest.fixture
def easier_deviation(sample_plan):
    """Create an easier-than-planned deviation."""
    race_date = sample_plan.goal.race_date
    plan_start = race_date - timedelta(weeks=sample_plan.total_weeks)

    return PlanDeviation(
        plan_id=sample_plan.id,
        week_number=1,
        day_of_week=0,
        planned_date=plan_start,
        deviation_type=DeviationType.EASIER,
        metrics=DeviationMetrics(
            planned_duration_min=45,
            actual_duration_min=30,
            planned_load=40.0,
            actual_load=25.0,
        ),
        planned_workout_type="easy",
        actual_workout_id="act_123",
        actual_workout_type="running",
        severity="moderate",
    )


@pytest.fixture
def skipped_deviation(sample_plan):
    """Create a skipped workout deviation."""
    race_date = sample_plan.goal.race_date
    plan_start = race_date - timedelta(weeks=sample_plan.total_weeks)

    return PlanDeviation(
        plan_id=sample_plan.id,
        week_number=1,
        day_of_week=2,
        planned_date=plan_start + timedelta(days=2),
        deviation_type=DeviationType.SKIPPED,
        metrics=DeviationMetrics(
            planned_duration_min=50,
            actual_duration_min=0,
            planned_load=70.0,
            actual_load=0.0,
        ),
        planned_workout_type="tempo",
        severity="significant",
    )


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    mock = AsyncMock()
    mock.completion_json.return_value = {
        "analysis": "Workout was harder than planned, suggesting fatigue.",
        "recommended_actions": ["reduce_intensity", "add_recovery"],
        "session_adjustments": [
            {
                "day_of_week": 2,
                "original_type": "tempo",
                "suggested_type": "easy",
                "original_duration_min": 50,
                "suggested_duration_min": 40,
                "original_load": 70.0,
                "suggested_load": 35.0,
                "rationale": "Convert tempo to easy after hard effort",
            }
        ],
        "explanation": "Your last workout was harder than planned. To prevent overtraining, we recommend converting tomorrow's tempo to an easy run.",
        "expected_load_change_pct": -25.0,
        "confidence": 0.85,
        "monitoring_notes": "Watch for continued fatigue signs",
    }
    return mock


# ============================================================================
# Test Agent Initialization
# ============================================================================

class TestAdaptationAgentInit:
    """Tests for AdaptationAgent initialization."""

    def test_init_without_llm_client(self):
        """Test initialization without providing LLM client."""
        agent = AdaptationAgent()
        assert agent._llm_client is None
        assert agent._graph is not None

    def test_init_with_llm_client(self, mock_llm_client):
        """Test initialization with custom LLM client."""
        agent = AdaptationAgent(llm_client=mock_llm_client)
        assert agent._llm_client is mock_llm_client


# ============================================================================
# Test Adaptation Suggestions
# ============================================================================

class TestAdaptationSuggestions:
    """Tests for adaptation suggestion generation."""

    @pytest.mark.asyncio
    async def test_suggest_adaptation_harder_workout(
        self,
        sample_plan,
        harder_deviation,
        mock_llm_client,
    ):
        """Test adaptation suggestion for harder workout."""
        agent = AdaptationAgent(llm_client=mock_llm_client)

        suggestion = await agent.suggest_adaptation(
            plan=sample_plan,
            deviation=harder_deviation,
            athlete_context={"current_ctl": 45.0, "current_atl": 50.0},
        )

        assert isinstance(suggestion, AdaptationSuggestion)
        assert suggestion.plan_id == sample_plan.id
        assert suggestion.deviation == harder_deviation
        # Should suggest recovery or reduce intensity
        assert any(
            action in (AdaptationAction.ADD_RECOVERY, AdaptationAction.REDUCE_INTENSITY)
            for action in suggestion.actions
        )

    @pytest.mark.asyncio
    async def test_suggest_adaptation_easier_workout(
        self,
        sample_plan,
        easier_deviation,
        mock_llm_client,
    ):
        """Test adaptation suggestion for easier workout."""
        mock_llm_client.completion_json.return_value = {
            "analysis": "Workout was easier than planned.",
            "recommended_actions": ["increase_intensity"],
            "session_adjustments": [],
            "explanation": "Your workout was lighter than planned. We'll slightly increase the next session.",
            "expected_load_change_pct": 10.0,
            "confidence": 0.8,
        }

        agent = AdaptationAgent(llm_client=mock_llm_client)

        suggestion = await agent.suggest_adaptation(
            plan=sample_plan,
            deviation=easier_deviation,
        )

        assert isinstance(suggestion, AdaptationSuggestion)
        # Should suggest maintaining or slight increase
        assert any(
            action in (AdaptationAction.MAINTAIN, AdaptationAction.INCREASE_INTENSITY)
            for action in suggestion.actions
        )

    @pytest.mark.asyncio
    async def test_suggest_adaptation_skipped_workout(
        self,
        sample_plan,
        skipped_deviation,
        mock_llm_client,
    ):
        """Test adaptation suggestion for skipped workout."""
        mock_llm_client.completion_json.return_value = {
            "analysis": "Workout was skipped. Redistributing load.",
            "recommended_actions": ["redistribute_load"],
            "session_adjustments": [
                {
                    "day_of_week": 6,
                    "original_type": "long",
                    "suggested_type": "long",
                    "original_duration_min": 90,
                    "suggested_duration_min": 95,
                    "original_load": 80.0,
                    "suggested_load": 87.0,
                    "rationale": "Slightly longer long run to compensate",
                }
            ],
            "explanation": "You missed the tempo session. We've redistributed some of that load to your long run.",
            "expected_load_change_pct": -20.0,
            "confidence": 0.75,
        }

        agent = AdaptationAgent(llm_client=mock_llm_client)

        suggestion = await agent.suggest_adaptation(
            plan=sample_plan,
            deviation=skipped_deviation,
        )

        assert isinstance(suggestion, AdaptationSuggestion)
        # Should suggest redistribute load
        assert AdaptationAction.REDISTRIBUTE_LOAD in suggestion.actions


# ============================================================================
# Test State Machine Steps
# ============================================================================

class TestStateMachineSteps:
    """Tests for individual state machine steps."""

    @pytest.mark.asyncio
    async def test_analyze_deviation_significant(self, mock_llm_client):
        """Test analysis of significant deviation."""
        agent = AdaptationAgent(llm_client=mock_llm_client)

        state: AdaptationState = {
            "plan_id": "plan_123",
            "deviation": {
                "deviation_type": "harder",
                "metrics": {"load_deviation_pct": 40.0, "duration_deviation_pct": 25.0},
            },
            "plan_context": {},
            "upcoming_sessions": [],
            "athlete_context": {},
            "actions": [],
            "session_adjustments": [],
            "explanation": "",
            "suggestion": None,
            "errors": [],
            "status": "initialized",
        }

        result = await agent._analyze_deviation(state)
        assert result["status"] == "analyzed"

    @pytest.mark.asyncio
    async def test_analyze_deviation_within_tolerance(self, mock_llm_client):
        """Test analysis of deviation within tolerance."""
        agent = AdaptationAgent(llm_client=mock_llm_client)

        state: AdaptationState = {
            "plan_id": "plan_123",
            "deviation": {
                "deviation_type": "easier",
                "metrics": {"load_deviation_pct": 10.0, "duration_deviation_pct": 5.0},
            },
            "plan_context": {},
            "upcoming_sessions": [],
            "athlete_context": {},
            "actions": [],
            "session_adjustments": [],
            "explanation": "",
            "suggestion": None,
            "errors": [],
            "status": "initialized",
        }

        result = await agent._analyze_deviation(state)
        assert result["status"] == "no_adaptation_needed"

    @pytest.mark.asyncio
    async def test_determine_actions_harder(self, mock_llm_client):
        """Test action determination for harder workout."""
        agent = AdaptationAgent(llm_client=mock_llm_client)

        state: AdaptationState = {
            "plan_id": "plan_123",
            "deviation": {
                "deviation_type": "harder",
                "metrics": {"load_deviation_pct": 50.0},
            },
            "plan_context": {"weeks_remaining": 6},
            "upcoming_sessions": [],
            "athlete_context": {},
            "actions": [],
            "session_adjustments": [],
            "explanation": "",
            "suggestion": None,
            "errors": [],
            "status": "analyzed",
        }

        result = await agent._determine_actions(state)

        assert result["status"] == "actions_determined"
        assert AdaptationAction.ADD_RECOVERY.value in result["actions"]

    @pytest.mark.asyncio
    async def test_determine_actions_skipped_close_to_race(self, mock_llm_client):
        """Test action determination for skipped workout close to race."""
        agent = AdaptationAgent(llm_client=mock_llm_client)

        state: AdaptationState = {
            "plan_id": "plan_123",
            "deviation": {
                "deviation_type": "skipped",
                "metrics": {"load_deviation_pct": -100.0},
            },
            "plan_context": {"weeks_remaining": 1},  # Close to race
            "upcoming_sessions": [],
            "athlete_context": {},
            "actions": [],
            "session_adjustments": [],
            "explanation": "",
            "suggestion": None,
            "errors": [],
            "status": "analyzed",
        }

        result = await agent._determine_actions(state)

        # Should maintain rather than redistribute close to race
        assert AdaptationAction.MAINTAIN.value in result["actions"]


# ============================================================================
# Test Session Adjustments
# ============================================================================

class TestSessionAdjustments:
    """Tests for session adjustment generation."""

    @pytest.mark.asyncio
    async def test_generate_adjustments_with_recovery(self, mock_llm_client):
        """Test adjustment generation with recovery action."""
        agent = AdaptationAgent(llm_client=mock_llm_client)

        state: AdaptationState = {
            "plan_id": "plan_123",
            "deviation": {"deviation_type": "harder", "metrics": {}},
            "plan_context": {},
            "upcoming_sessions": [
                {
                    "day_of_week": 2,
                    "workout_type": "tempo",
                    "target_duration_min": 50,
                    "target_load": 70.0,
                }
            ],
            "athlete_context": {},
            "actions": [AdaptationAction.ADD_RECOVERY.value],
            "session_adjustments": [],
            "explanation": "",
            "suggestion": None,
            "errors": [],
            "status": "actions_determined",
        }

        result = await agent._generate_adjustments(state)

        assert len(result["session_adjustments"]) > 0
        adj = result["session_adjustments"][0]
        assert adj["suggested_type"] == "recovery"
        assert adj["suggested_load"] < adj["original_load"]

    @pytest.mark.asyncio
    async def test_generate_adjustments_redistribute_load(self, mock_llm_client):
        """Test adjustment generation for load redistribution."""
        agent = AdaptationAgent(llm_client=mock_llm_client)

        state: AdaptationState = {
            "plan_id": "plan_123",
            "deviation": {
                "deviation_type": "skipped",
                "metrics": {"planned_load": 70.0},
            },
            "plan_context": {},
            "upcoming_sessions": [
                {
                    "day_of_week": 6,
                    "workout_type": "long",
                    "target_duration_min": 90,
                    "target_load": 80.0,
                },
                {
                    "day_of_week": 0,
                    "workout_type": "easy",
                    "target_duration_min": 45,
                    "target_load": 40.0,
                },
            ],
            "athlete_context": {},
            "actions": [AdaptationAction.REDISTRIBUTE_LOAD.value],
            "session_adjustments": [],
            "explanation": "",
            "suggestion": None,
            "errors": [],
            "status": "actions_determined",
        }

        result = await agent._generate_adjustments(state)

        # Should have adjustments for multiple sessions
        assert len(result["session_adjustments"]) >= 1
        # Adjusted loads should be higher
        for adj in result["session_adjustments"]:
            assert adj["suggested_load"] >= adj["original_load"]


# ============================================================================
# Test Explanation Generation
# ============================================================================

class TestExplanationGeneration:
    """Tests for LLM-based explanation generation."""

    @pytest.mark.asyncio
    async def test_generate_explanation_success(self, mock_llm_client):
        """Test successful explanation generation."""
        agent = AdaptationAgent(llm_client=mock_llm_client)

        state: AdaptationState = {
            "plan_id": "plan_123",
            "deviation": {"deviation_type": "harder", "metrics": {}},
            "plan_context": {"current_week": 3, "current_phase": "build", "weeks_remaining": 5},
            "upcoming_sessions": [],
            "athlete_context": {"current_ctl": 45.0},
            "actions": [AdaptationAction.REDUCE_INTENSITY.value],
            "session_adjustments": [],
            "explanation": "",
            "suggestion": None,
            "errors": [],
            "status": "adjustments_generated",
        }

        result = await agent._generate_explanation(state)

        assert result["explanation"] != ""
        assert result["status"] == "explanation_generated"

    @pytest.mark.asyncio
    async def test_generate_fallback_explanation(self, mock_llm_client):
        """Test fallback explanation when LLM fails."""
        mock_llm_client.completion_json.side_effect = Exception("LLM error")
        agent = AdaptationAgent(llm_client=mock_llm_client)

        state: AdaptationState = {
            "plan_id": "plan_123",
            "deviation": {"deviation_type": "harder", "metrics": {}},
            "plan_context": {},
            "upcoming_sessions": [],
            "athlete_context": {},
            "actions": [AdaptationAction.REDUCE_INTENSITY.value],
            "session_adjustments": [],
            "explanation": "",
            "suggestion": None,
            "errors": [],
            "status": "adjustments_generated",
        }

        result = await agent._generate_explanation(state)

        # Should have fallback explanation
        assert result["explanation"] != ""
        assert "harder than planned" in result["explanation"].lower()


# ============================================================================
# Test AdaptationSuggestion
# ============================================================================

class TestAdaptationSuggestionModel:
    """Tests for AdaptationSuggestion dataclass."""

    def test_suggestion_summary(self, harder_deviation):
        """Test suggestion summary generation."""
        suggestion = AdaptationSuggestion(
            plan_id="plan_123",
            deviation=harder_deviation,
            actions=[AdaptationAction.ADD_RECOVERY, AdaptationAction.REDUCE_INTENSITY],
            affected_weeks=[1, 2],
            session_adjustments=[],
            explanation="Test explanation",
            expected_load_change_pct=-15.0,
        )

        assert "Add Recovery" in suggestion.summary
        assert "Reduce Intensity" in suggestion.summary
        assert "[1, 2]" in suggestion.summary

    def test_suggestion_to_dict(self, harder_deviation):
        """Test suggestion to_dict serialization."""
        adjustment = SessionAdjustment(
            day_of_week=2,
            original_type="tempo",
            suggested_type="easy",
            original_duration_min=50,
            suggested_duration_min=40,
            original_load=70.0,
            suggested_load=35.0,
            rationale="Test rationale",
        )

        suggestion = AdaptationSuggestion(
            plan_id="plan_123",
            deviation=harder_deviation,
            actions=[AdaptationAction.REDUCE_INTENSITY],
            affected_weeks=[1],
            session_adjustments=[adjustment],
            explanation="Test explanation",
            expected_load_change_pct=-25.0,
            confidence=0.85,
        )

        data = suggestion.to_dict()

        assert data["plan_id"] == "plan_123"
        assert data["actions"] == ["reduce_intensity"]
        assert data["affected_weeks"] == [1]
        assert len(data["session_adjustments"]) == 1
        assert data["expected_load_change_pct"] == -25.0
        assert data["confidence"] == 0.85


# ============================================================================
# Test SessionAdjustment
# ============================================================================

class TestSessionAdjustmentModel:
    """Tests for SessionAdjustment dataclass."""

    def test_load_change_pct(self):
        """Test load change percentage calculation."""
        adjustment = SessionAdjustment(
            day_of_week=2,
            original_type="tempo",
            suggested_type="easy",
            original_duration_min=50,
            suggested_duration_min=40,
            original_load=70.0,
            suggested_load=35.0,
            rationale="Test",
        )

        assert adjustment.load_change_pct == -50.0

    def test_load_change_pct_zero_original(self):
        """Test load change with zero original load."""
        adjustment = SessionAdjustment(
            day_of_week=4,
            original_type="rest",
            suggested_type="recovery",
            original_duration_min=0,
            suggested_duration_min=30,
            original_load=0.0,
            suggested_load=20.0,
            rationale="Add recovery",
        )

        assert adjustment.load_change_pct == 0.0


# ============================================================================
# Test Factory Function
# ============================================================================

class TestAgentFactory:
    """Tests for agent factory functions."""

    def test_get_adaptation_agent_singleton(self):
        """Test that get_adaptation_agent returns singleton."""
        reset_adaptation_agent()

        agent1 = get_adaptation_agent()
        agent2 = get_adaptation_agent()

        assert agent1 is agent2

    def test_reset_adaptation_agent(self):
        """Test reset creates new instance."""
        agent1 = get_adaptation_agent()
        reset_adaptation_agent()
        agent2 = get_adaptation_agent()

        assert agent1 is not agent2
