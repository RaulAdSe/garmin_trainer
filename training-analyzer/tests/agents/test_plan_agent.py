"""Tests for the Plan Agent (LangGraph-based plan generation)."""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json

from training_analyzer.agents.plan_agent import (
    PlanAgent,
    PlanState,
    PlanGenerationError,
    generate_plan_sync,
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
        race_date=date.today() + timedelta(weeks=16),
        distance=RaceDistance.MARATHON,
        target_time_seconds=12600,  # 3:30:00
        race_name="Test Marathon",
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
        vdot=50.0,
    )


@pytest.fixture
def sample_constraints():
    """Create sample plan constraints."""
    return PlanConstraints(
        days_per_week=5,
        long_run_day=6,  # Sunday
        rest_days=[4],  # Friday
        max_weekly_hours=8.0,
        max_session_duration_min=150,
        include_cross_training=False,
        back_to_back_hard_ok=False,
    )


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    mock = AsyncMock()
    mock.completion.return_value = json.dumps({
        "periodization_type": "linear",
        "rationale": "Best for this athlete",
        "phase_distribution": [
            {"phase": "base", "weeks": 4},
            {"phase": "build", "weeks": 8},
            {"phase": "peak", "weeks": 3},
            {"phase": "taper", "weeks": 1},
        ],
    })
    return mock


# ============================================================================
# Test PlanAgent Initialization
# ============================================================================

class TestPlanAgentInit:
    """Tests for PlanAgent initialization."""

    def test_init_without_llm_client(self):
        """Test initialization without providing LLM client."""
        agent = PlanAgent()
        assert agent._llm_client is None
        # Graph should be built
        assert agent._graph is not None

    def test_init_with_llm_client(self, mock_llm_client):
        """Test initialization with custom LLM client."""
        agent = PlanAgent(llm_client=mock_llm_client)
        assert agent._llm_client is mock_llm_client


# ============================================================================
# Test Plan Generation
# ============================================================================

class TestPlanGeneration:
    """Tests for plan generation functionality."""

    @pytest.mark.asyncio
    async def test_generate_plan_basic(
        self, sample_goal, sample_athlete_context, sample_constraints
    ):
        """Test basic plan generation (rule-based, no LLM needed)."""
        agent = PlanAgent()

        # The plan agent uses rule-based generation, no LLM mocking needed
        plan = await agent.generate_plan(
            goal=sample_goal,
            athlete_context=sample_athlete_context,
            constraints=sample_constraints,
        )

        assert isinstance(plan, TrainingPlan)
        assert plan.goal == sample_goal
        assert len(plan.weeks) > 0

    @pytest.mark.asyncio
    async def test_generate_plan_creates_correct_phases(
        self, sample_goal, sample_athlete_context, sample_constraints
    ):
        """Test that generated plan has correct phase distribution."""
        agent = PlanAgent()

        plan = await agent.generate_plan(
            goal=sample_goal,
            athlete_context=sample_athlete_context,
            constraints=sample_constraints,
        )

        # Check that we have expected phases
        phases = set(w.phase for w in plan.weeks)
        assert TrainingPhase.BUILD in phases or TrainingPhase.BASE in phases
        assert TrainingPhase.TAPER in phases

    @pytest.mark.asyncio
    async def test_generate_plan_respects_constraints(
        self, sample_goal, sample_athlete_context
    ):
        """Test that generated plan respects constraints."""
        constraints = PlanConstraints(
            days_per_week=4,
            long_run_day=6,
            rest_days=[4, 5],  # Friday, Saturday
            max_weekly_hours=6.0,
        )

        agent = PlanAgent()
        plan = await agent.generate_plan(
            goal=sample_goal,
            athlete_context=sample_athlete_context,
            constraints=constraints,
        )

        # Check each week
        for week in plan.weeks:
            # Count workout days (excluding rest)
            workout_days = [
                s for s in week.sessions
                if s.workout_type != WorkoutType.REST
            ]
            assert len(workout_days) <= constraints.days_per_week

    @pytest.mark.asyncio
    async def test_generate_plan_short_preparation(
        self, sample_athlete_context, sample_constraints
    ):
        """Test plan generation for short preparation (< 8 weeks)."""
        short_goal = RaceGoal(
            race_date=date.today() + timedelta(weeks=6),
            distance=RaceDistance.TEN_K,
            target_time_seconds=2700,  # 45:00
        )

        agent = PlanAgent()
        plan = await agent.generate_plan(
            goal=short_goal,
            athlete_context=sample_athlete_context,
            constraints=sample_constraints,
        )

        assert plan.total_weeks <= 6
        # Should still have taper
        taper_weeks = [w for w in plan.weeks if w.phase == TrainingPhase.TAPER]
        assert len(taper_weeks) >= 1

    @pytest.mark.asyncio
    async def test_generate_plan_different_distances(
        self, sample_athlete_context, sample_constraints
    ):
        """Test plan generation for different race distances."""
        distances = [
            (RaceDistance.FIVE_K, 1500),     # 25:00
            (RaceDistance.TEN_K, 2700),      # 45:00
            (RaceDistance.HALF_MARATHON, 6000),  # 1:40:00
            (RaceDistance.MARATHON, 12600),  # 3:30:00
        ]

        agent = PlanAgent()

        for distance, target_time in distances:
            goal = RaceGoal(
                race_date=date.today() + timedelta(weeks=12),
                distance=distance,
                target_time_seconds=target_time,
            )

            plan = await agent.generate_plan(
                goal=goal,
                athlete_context=sample_athlete_context,
                constraints=sample_constraints,
            )

            assert isinstance(plan, TrainingPlan)
            assert plan.goal.distance == distance


# ============================================================================
# Test Phase Distribution
# ============================================================================

class TestPhaseDistribution:
    """Tests for phase distribution logic."""

    def test_distribute_phases_16_weeks(self):
        """Test phase distribution for 16-week plan."""
        agent = PlanAgent()
        phases = agent._distribute_phases(
            weeks_available=16,
            periodization=PeriodizationType.LINEAR,
            current_ctl=40.0,
        )

        total_weeks = sum(p["weeks"] for p in phases)
        assert total_weeks == 16

        # Should have all phases
        phase_names = [p["phase"] for p in phases]
        assert "base" in phase_names
        assert "build" in phase_names
        assert "peak" in phase_names
        assert "taper" in phase_names

    def test_distribute_phases_short_plan(self):
        """Test phase distribution for short plan."""
        agent = PlanAgent()
        phases = agent._distribute_phases(
            weeks_available=6,
            periodization=PeriodizationType.LINEAR,
            current_ctl=40.0,
        )

        total_weeks = sum(p["weeks"] for p in phases)
        assert total_weeks == 6

        # Short plans might skip base phase
        phase_names = [p["phase"] for p in phases]
        assert "taper" in phase_names


# ============================================================================
# Test Session Generation
# ============================================================================

class TestSessionGeneration:
    """Tests for session generation logic."""

    def test_generate_week_sessions_base_phase(self):
        """Test session generation for base phase."""
        agent = PlanAgent()
        # Long run on Sunday (6), rest on Friday (4)
        # Training days: [0,1,2,3,5,6] minus rest [4] = [0,1,2,3,5,6][:5] = [0,1,2,3,5]
        # Since we want long run on day 6, we need 6 days per week or different rest pattern
        constraints = {
            "days_per_week": 6,  # Need 6 days to include Sunday
            "long_run_day": 6,
            "rest_days": [4],  # Friday rest
        }

        sessions = agent._generate_week_sessions(
            phase=TrainingPhase.BASE,
            week_in_phase=1,
            target_load=200.0,
            constraints=constraints,
            is_cutback=False,
        )

        assert len(sessions) == 7  # All days of week

        # Check that we have a long run on Sunday (day 6)
        long_sessions = [s for s in sessions if s["workout_type"] == "long"]
        assert len(long_sessions) == 1
        assert long_sessions[0]["day_of_week"] == 6

        # Check rest days
        rest_sessions = [s for s in sessions if s["workout_type"] == "rest"]
        assert len(rest_sessions) >= 1

    def test_generate_week_sessions_build_phase(self):
        """Test session generation for build phase includes quality."""
        agent = PlanAgent()
        constraints = {
            "days_per_week": 5,
            "long_run_day": 6,
            "rest_days": [4],
        }

        sessions = agent._generate_week_sessions(
            phase=TrainingPhase.BUILD,
            week_in_phase=2,
            target_load=250.0,
            constraints=constraints,
            is_cutback=False,
        )

        # Build phase should have quality sessions
        quality_types = ["tempo", "threshold", "intervals"]
        quality_sessions = [
            s for s in sessions
            if s["workout_type"] in quality_types
        ]
        assert len(quality_sessions) >= 1

    def test_generate_week_sessions_cutback_week(self):
        """Test that cutback weeks have reduced load."""
        agent = PlanAgent()
        constraints = {
            "days_per_week": 5,
            "long_run_day": 6,
            "rest_days": [4],
        }

        normal_sessions = agent._generate_week_sessions(
            phase=TrainingPhase.BUILD,
            week_in_phase=2,
            target_load=250.0,
            constraints=constraints,
            is_cutback=False,
        )

        cutback_sessions = agent._generate_week_sessions(
            phase=TrainingPhase.BUILD,
            week_in_phase=3,
            target_load=175.0,  # Reduced for cutback
            constraints=constraints,
            is_cutback=True,
        )

        # Cutback should have shorter durations
        normal_duration = sum(s["target_duration_min"] for s in normal_sessions)
        cutback_duration = sum(s["target_duration_min"] for s in cutback_sessions)
        assert cutback_duration < normal_duration


# ============================================================================
# Test Load Calculations
# ============================================================================

class TestLoadCalculations:
    """Tests for training load calculations."""

    def test_calculate_week_target_load_base_phase(self):
        """Test load calculation for base phase."""
        agent = PlanAgent()

        load = agent._calculate_week_target_load(
            phase=TrainingPhase.BASE,
            week_in_phase=1,
            total_phase_weeks=4,
            current_ctl=40.0,
            is_cutback=False,
        )

        # Base phase should be lower than build
        base_load = load

        build_load = agent._calculate_week_target_load(
            phase=TrainingPhase.BUILD,
            week_in_phase=1,
            total_phase_weeks=8,
            current_ctl=40.0,
            is_cutback=False,
        )

        assert base_load < build_load

    def test_calculate_week_target_load_taper(self):
        """Test load calculation for taper phase."""
        agent = PlanAgent()

        normal_load = agent._calculate_week_target_load(
            phase=TrainingPhase.BUILD,
            week_in_phase=4,
            total_phase_weeks=8,
            current_ctl=50.0,
            is_cutback=False,
        )

        taper_load = agent._calculate_week_target_load(
            phase=TrainingPhase.TAPER,
            week_in_phase=1,
            total_phase_weeks=1,
            current_ctl=50.0,
            is_cutback=False,
        )

        # Taper should be significantly lower
        assert taper_load < normal_load * 0.7

    def test_calculate_week_target_load_cutback(self):
        """Test that cutback reduces load."""
        agent = PlanAgent()

        normal = agent._calculate_week_target_load(
            phase=TrainingPhase.BUILD,
            week_in_phase=3,
            total_phase_weeks=8,
            current_ctl=45.0,
            is_cutback=False,
        )

        cutback = agent._calculate_week_target_load(
            phase=TrainingPhase.BUILD,
            week_in_phase=4,
            total_phase_weeks=8,
            current_ctl=45.0,
            is_cutback=True,
        )

        assert cutback < normal


# ============================================================================
# Test Cutback Week Detection
# ============================================================================

class TestCutbackWeekDetection:
    """Tests for cutback week detection."""

    def test_is_cutback_week_every_4th_week(self):
        """Test that every 4th week is a cutback."""
        agent = PlanAgent()

        # Week 4 should be cutback
        assert agent._is_cutback_week(
            week_number=4,
            phase=TrainingPhase.BUILD,
            week_in_phase=4,
            total_phase_weeks=8,
        ) is True

        # Week 8 should be cutback
        assert agent._is_cutback_week(
            week_number=8,
            phase=TrainingPhase.BUILD,
            week_in_phase=8,
            total_phase_weeks=8,
        ) is True

        # Week 3 should not be cutback
        assert agent._is_cutback_week(
            week_number=3,
            phase=TrainingPhase.BUILD,
            week_in_phase=3,
            total_phase_weeks=8,
        ) is False

    def test_taper_never_cutback(self):
        """Test that taper phase weeks are never marked as cutback."""
        agent = PlanAgent()

        # Even week 4 in taper is not cutback (taper is already reduced)
        assert agent._is_cutback_week(
            week_number=16,
            phase=TrainingPhase.TAPER,
            week_in_phase=1,
            total_phase_weeks=1,
        ) is False


# ============================================================================
# Test Periodization Selection
# ============================================================================

class TestPeriodizationSelection:
    """Tests for periodization type selection."""

    def test_select_periodization_long_prep_large_gap(self):
        """Test linear is selected for long prep with large fitness gap."""
        agent = PlanAgent()

        periodization = agent._select_periodization(
            weeks_available=20,
            fitness_gap=25,
            distance="marathon",
        )

        assert periodization == PeriodizationType.LINEAR

    def test_select_periodization_short_prep(self):
        """Test reverse is selected for short prep."""
        agent = PlanAgent()

        periodization = agent._select_periodization(
            weeks_available=6,
            fitness_gap=10,
            distance="10k",
        )

        assert periodization == PeriodizationType.REVERSE

    def test_select_periodization_experienced_athlete(self):
        """Test block for shorter prep with small fitness gap."""
        agent = PlanAgent()

        periodization = agent._select_periodization(
            weeks_available=10,
            fitness_gap=5,
            distance="half",
        )

        assert periodization == PeriodizationType.BLOCK


# ============================================================================
# Test Plan Adaptation
# ============================================================================

class TestPlanAdaptation:
    """Tests for plan adaptation functionality."""

    @pytest.fixture
    def sample_plan(self, sample_athlete_context, sample_constraints):
        """Create a sample plan for adaptation tests.

        Uses a goal that places us partway through the plan (8 weeks away for a 16-week plan).
        """
        # Goal with race 8 weeks away (so we're at week 9 of a 16-week plan)
        goal_partway = RaceGoal(
            race_date=date.today() + timedelta(weeks=8),
            distance=RaceDistance.MARATHON,
            target_time_seconds=12600,
            race_name="Test Marathon",
            priority=1,
        )

        weeks = []
        for i in range(1, 17):
            sessions = [
                PlannedSession(
                    day_of_week=0,
                    workout_type=WorkoutType.EASY,
                    description="Easy run",
                    target_duration_min=40,
                    target_load=40.0,
                )
            ]
            weeks.append(TrainingWeek(
                week_number=i,
                phase=TrainingPhase.BUILD,
                target_load=250.0,
                sessions=sessions,
            ))

        return TrainingPlan(
            id="plan_test",
            goal=goal_partway,
            weeks=weeks,
            periodization=PeriodizationType.LINEAR,
            peak_week=15,
            created_at=datetime.now(),
            athlete_context=sample_athlete_context,
            constraints=sample_constraints,
        )

    @pytest.mark.asyncio
    async def test_adapt_plan_records_history(self, sample_plan):
        """Test that adaptation is recorded in history."""
        # Create a mock LLM client first
        mock_llm = AsyncMock()
        mock_llm.completion.return_value = json.dumps({
            "adaptation_reason": "Performance adjustment",
            "adaptation_magnitude": "minor",
            "changes_summary": {"load_adjustment_pct": -5},
            "weeks": [
                {
                    "week_number": 1,
                    "phase": "build",
                    "target_load": 237.5,
                    "sessions": [],
                }
            ],
        })

        # Initialize agent with the mock LLM client
        agent = PlanAgent(llm_client=mock_llm)

        performance_data = {
            "current_ctl": 48,
            "current_atl": 55,
            "current_tsb": -7,
        }

        adapted_plan = await agent.adapt_plan(
            plan=sample_plan,
            performance_data=performance_data,
        )

        assert len(adapted_plan.adaptation_history) > 0
        assert adapted_plan.updated_at is not None


# ============================================================================
# Test Error Handling
# ============================================================================

class TestErrorHandling:
    """Tests for error handling in plan agent."""

    @pytest.mark.asyncio
    async def test_generate_plan_with_invalid_goal(self, sample_athlete_context, sample_constraints):
        """Test that invalid goal raises appropriate error."""
        # Goal with race date in the past
        past_goal = RaceGoal(
            race_date=date.today() - timedelta(days=7),
            distance=RaceDistance.MARATHON,
            target_time_seconds=12600,
        )

        agent = PlanAgent()

        with pytest.raises(PlanGenerationError):
            await agent.generate_plan(
                goal=past_goal,
                athlete_context=sample_athlete_context,
                constraints=sample_constraints,
            )


# ============================================================================
# Test State Machine
# ============================================================================

class TestStateMachine:
    """Tests for the LangGraph state machine."""

    @pytest.mark.asyncio
    async def test_state_progression(
        self, sample_goal, sample_athlete_context, sample_constraints
    ):
        """Test that state progresses through all stages."""
        agent = PlanAgent()

        # Create initial state
        initial_state: PlanState = {
            "goal": sample_goal.to_dict(),
            "constraints": sample_constraints.to_dict(),
            "athlete_context": sample_athlete_context.to_dict(),
            "periodization_type": "",
            "phase_distribution": [],
            "weeks": [],
            "current_week_index": 0,
            "plan": None,
            "errors": [],
            "status": "initialized",
        }

        # Run through analyze_goal
        state_after_analyze = await agent._analyze_goal(initial_state)
        assert state_after_analyze["status"] == "analyzed"
        assert "weeks_available" in state_after_analyze["athlete_context"]

        # Run through determine_structure
        state_after_structure = await agent._determine_structure(state_after_analyze)
        assert state_after_structure["status"] == "structured"
        assert len(state_after_structure["phase_distribution"]) > 0

        # Run through generate_weeks
        state_after_weeks = await agent._generate_weeks(state_after_structure)
        assert state_after_weeks["status"] == "generated"
        assert len(state_after_weeks["weeks"]) > 0

        # Run through validate_plan
        state_after_validate = await agent._validate_plan(state_after_weeks)
        assert state_after_validate["status"] == "validated"

        # Run through finalize
        final_state = await agent._finalize(state_after_validate)
        assert final_state["status"] == "completed"
        assert final_state["plan"] is not None


# ============================================================================
# Test Helper Functions
# ============================================================================

class TestHelperFunctions:
    """Tests for helper functions in plan agent."""

    def test_estimate_target_ctl(self):
        """Test target CTL estimation by distance."""
        agent = PlanAgent()

        # Longer distances should have higher target CTL
        five_k_ctl = agent._estimate_target_ctl("5k")
        marathon_ctl = agent._estimate_target_ctl("marathon")

        assert marathon_ctl > five_k_ctl

    def test_get_long_run_duration_progression(self):
        """Test long run duration increases through build phase."""
        agent = PlanAgent()

        week1_duration = agent._get_long_run_duration(
            phase=TrainingPhase.BUILD,
            week_in_phase=1,
            is_cutback=False,
        )

        week4_duration = agent._get_long_run_duration(
            phase=TrainingPhase.BUILD,
            week_in_phase=4,
            is_cutback=False,
        )

        assert week4_duration > week1_duration

    def test_get_long_run_duration_capped(self):
        """Test long run duration is capped at max."""
        agent = PlanAgent()

        duration = agent._get_long_run_duration(
            phase=TrainingPhase.BUILD,
            week_in_phase=20,  # Very late in phase
            is_cutback=False,
        )

        assert duration <= 150  # Max 2.5 hours

    def test_get_phase_focus(self):
        """Test phase focus descriptions."""
        agent = PlanAgent()

        base_focus = agent._get_phase_focus(
            phase=TrainingPhase.BASE,
            week_in_phase=1,
            total_weeks=4,
        )
        assert "aerobic" in base_focus.lower() or "endurance" in base_focus.lower()

        taper_focus = agent._get_phase_focus(
            phase=TrainingPhase.TAPER,
            week_in_phase=1,
            total_weeks=1,
        )
        assert "recovery" in taper_focus.lower() or "fresh" in taper_focus.lower()

    def test_format_athlete_context(self):
        """Test athlete context formatting for prompts."""
        agent = PlanAgent()

        context = {
            "current_ctl": 45.0,
            "current_atl": 50.0,
            "max_hr": 185,
            "threshold_hr": 165,
        }

        formatted = agent._format_athlete_context(context)

        assert "CTL" in formatted
        assert "45.0" in formatted
        assert "185" in formatted


# ============================================================================
# Test Synchronous Wrapper
# ============================================================================

class TestSyncWrapper:
    """Tests for the synchronous wrapper function."""

    def test_generate_plan_sync(
        self, sample_goal, sample_athlete_context, sample_constraints
    ):
        """Test synchronous plan generation."""
        # This should work without requiring an async context
        plan = generate_plan_sync(
            goal=sample_goal,
            athlete_context=sample_athlete_context,
            constraints=sample_constraints,
        )

        assert isinstance(plan, TrainingPlan)
        assert plan.total_weeks > 0


# ============================================================================
# Test JSON Parsing
# ============================================================================

class TestJsonParsing:
    """Tests for JSON response parsing."""

    def test_parse_json_response_direct(self):
        """Test parsing direct JSON."""
        agent = PlanAgent()

        response = '{"key": "value"}'
        result = agent._parse_json_response(response)

        assert result == {"key": "value"}

    def test_parse_json_response_markdown_block(self):
        """Test parsing JSON from markdown code block."""
        agent = PlanAgent()

        response = '''Here is the plan:
```json
{"key": "value"}
```
'''
        result = agent._parse_json_response(response)

        assert result == {"key": "value"}

    def test_parse_json_response_embedded(self):
        """Test parsing embedded JSON."""
        agent = PlanAgent()

        response = 'Some text before {"key": "value"} some text after'
        result = agent._parse_json_response(response)

        assert result == {"key": "value"}

    def test_parse_json_response_invalid(self):
        """Test parsing invalid JSON raises error."""
        agent = PlanAgent()

        response = "This is not JSON at all"

        with pytest.raises(ValueError):
            agent._parse_json_response(response)
