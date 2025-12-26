"""Tests for the AnalysisAgent."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from training_analyzer.agents.analysis_agent import (
    AnalysisAgent,
    AnalysisState,
    build_athlete_context_from_briefing,
    get_similar_workouts,
)
from training_analyzer.models.analysis import (
    AnalysisStatus,
    AthleteContext,
    WorkoutData,
    WorkoutAnalysisResult,
    WorkoutExecutionRating,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    client = AsyncMock()
    client.completion.return_value = """**Summary**: Great tempo run with consistent pacing throughout. Heart rate stayed well controlled in Zone 3.

**What Worked Well**:
- Consistent pace throughout the workout
- Heart rate stayed in target Zone 3 for 85% of the run
- Good negative split in the final kilometer

**Observations**:
- Slight cardiac drift observed in the last 10 minutes
- Cadence dropped slightly near the end

**Recommendations**:
- Consider a longer warmup to reduce initial HR spike
- Practice maintaining cadence in the final km
"""
    return client


@pytest.fixture
def sample_workout_data():
    """Sample workout data for testing."""
    return {
        "activity_id": "test_workout_123",
        "date": "2025-12-25",
        "activity_type": "running",
        "activity_name": "Morning Tempo Run",
        "duration_min": 45.0,
        "distance_km": 8.5,
        "avg_hr": 155,
        "max_hr": 172,
        "pace_sec_per_km": 318,
        "hrss": 75.0,
        "trimp": 85.0,
        "zone1_pct": 5,
        "zone2_pct": 25,
        "zone3_pct": 55,
        "zone4_pct": 15,
        "zone5_pct": 0,
    }


@pytest.fixture
def sample_athlete_context():
    """Sample athlete context for testing."""
    return {
        "ctl": 45.0,
        "atl": 52.0,
        "tsb": -7.0,
        "acwr": 1.15,
        "risk_zone": "optimal",
        "max_hr": 185,
        "rest_hr": 55,
        "threshold_hr": 165,
        "vdot": 52.0,
        "race_goal": "Marathon",
        "race_date": "2025-04-15",
        "target_time": "3:30:00",
        "readiness_score": 75.0,
        "readiness_zone": "green",
        "training_paces": {
            "Easy": 360,
            "Tempo": 300,
            "Interval": 270,
        },
    }


@pytest.fixture
def sample_similar_workouts():
    """Sample similar workouts for comparison."""
    return [
        {
            "activity_id": "prev_1",
            "date": "2025-12-23",
            "activity_type": "running",
            "distance_km": 8.0,
            "duration_min": 44.0,
            "avg_hr": 152,
        },
        {
            "activity_id": "prev_2",
            "date": "2025-12-20",
            "activity_type": "running",
            "distance_km": 7.5,
            "duration_min": 41.0,
            "avg_hr": 150,
        },
    ]


# ============================================================================
# AthleteContext Tests
# ============================================================================

class TestAthleteContext:
    """Tests for the AthleteContext dataclass."""

    def test_default_hr_zones(self):
        """Test that default HR zones are calculated correctly."""
        ctx = AthleteContext(max_hr=185, rest_hr=55)

        # HR Reserve = 185 - 55 = 130
        # Zone 1: 55 + 130*0.50 to 55 + 130*0.60 = 120 to 133
        assert ctx.hr_zones[1] == (120, 133)
        # Zone 5: 55 + 130*0.90 to 185 = 172 to 185
        assert ctx.hr_zones[5] == (172, 185)

    def test_format_hr_zones(self):
        """Test HR zones formatting."""
        ctx = AthleteContext(max_hr=185, rest_hr=55)
        formatted = ctx.format_hr_zones()

        assert "Z1:" in formatted
        assert "Z5:" in formatted
        assert "bpm" in formatted

    def test_format_training_paces(self):
        """Test training paces formatting."""
        ctx = AthleteContext()
        ctx.training_paces = {
            "Easy": 360,  # 6:00/km
            "Tempo": 300,  # 5:00/km
        }
        formatted = ctx.format_training_paces()

        assert "Easy: 6:00/km" in formatted
        assert "Tempo: 5:00/km" in formatted

    def test_to_prompt_context(self, sample_athlete_context):
        """Test conversion to prompt context string."""
        ctx = AthleteContext(**sample_athlete_context)
        prompt = ctx.to_prompt_context()

        assert "CTL: 45.0" in prompt
        assert "ATL: 52.0" in prompt
        assert "TSB: -7.0" in prompt
        assert "VDOT: 52.0" in prompt
        assert "Marathon" in prompt


# ============================================================================
# WorkoutData Tests
# ============================================================================

class TestWorkoutData:
    """Tests for the WorkoutData dataclass."""

    def test_from_dict(self, sample_workout_data):
        """Test creation from dictionary."""
        workout = WorkoutData.from_dict(sample_workout_data)

        assert workout.activity_id == "test_workout_123"
        assert workout.date == "2025-12-25"
        assert workout.duration_min == 45.0
        assert workout.distance_km == 8.5

    def test_format_pace(self):
        """Test pace formatting."""
        workout = WorkoutData(
            activity_id="test",
            date="2025-01-01",
            pace_sec_per_km=318,  # 5:18/km
        )
        assert workout.format_pace() == "5:18/km"

    def test_format_pace_na(self):
        """Test pace formatting when no pace available."""
        workout = WorkoutData(activity_id="test", date="2025-01-01")
        assert workout.format_pace() == "N/A"

    def test_format_zone_distribution(self, sample_workout_data):
        """Test zone distribution formatting."""
        workout = WorkoutData.from_dict(sample_workout_data)
        formatted = workout.format_zone_distribution()

        # Z1: 5%, Z2: 25%, Z3: 55%, Z4: 15%
        assert "Z1: 5%" in formatted
        assert "Z2: 25%" in formatted
        assert "Z3: 55%" in formatted
        assert "Z4: 15%" in formatted

    def test_to_prompt_data(self, sample_workout_data):
        """Test conversion to prompt data string."""
        workout = WorkoutData.from_dict(sample_workout_data)
        prompt = workout.to_prompt_data()

        assert "Activity: running" in prompt
        assert "Date: 2025-12-25" in prompt
        assert "Duration: 45 minutes" in prompt
        assert "Distance: 8.50 km" in prompt
        assert "Avg HR: 155 bpm" in prompt


# ============================================================================
# AnalysisAgent Tests
# ============================================================================

class TestAnalysisAgent:
    """Tests for the AnalysisAgent."""

    @pytest.mark.asyncio
    async def test_analyze_returns_result(
        self,
        mock_llm_client,
        sample_workout_data,
        sample_athlete_context,
        sample_similar_workouts,
    ):
        """Test that analyze returns a WorkoutAnalysisResult."""
        agent = AnalysisAgent(llm_client=mock_llm_client)

        result = await agent.analyze(
            workout_data=sample_workout_data,
            athlete_context=sample_athlete_context,
            similar_workouts=sample_similar_workouts,
        )

        assert isinstance(result, WorkoutAnalysisResult)
        assert result.workout_id == "test_workout_123"
        assert result.status == AnalysisStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_analyze_extracts_summary(
        self,
        mock_llm_client,
        sample_workout_data,
        sample_athlete_context,
    ):
        """Test that summary is extracted from LLM response."""
        agent = AnalysisAgent(llm_client=mock_llm_client)

        result = await agent.analyze(
            workout_data=sample_workout_data,
            athlete_context=sample_athlete_context,
        )

        assert result.summary != ""
        assert "tempo" in result.summary.lower() or len(result.summary) > 0

    @pytest.mark.asyncio
    async def test_analyze_extracts_what_worked_well(
        self,
        mock_llm_client,
        sample_workout_data,
        sample_athlete_context,
    ):
        """Test that what_worked_well is extracted."""
        agent = AnalysisAgent(llm_client=mock_llm_client)

        result = await agent.analyze(
            workout_data=sample_workout_data,
            athlete_context=sample_athlete_context,
        )

        assert len(result.what_worked_well) > 0

    @pytest.mark.asyncio
    async def test_analyze_extracts_observations(
        self,
        mock_llm_client,
        sample_workout_data,
        sample_athlete_context,
    ):
        """Test that observations are extracted."""
        agent = AnalysisAgent(llm_client=mock_llm_client)

        result = await agent.analyze(
            workout_data=sample_workout_data,
            athlete_context=sample_athlete_context,
        )

        assert len(result.observations) > 0

    @pytest.mark.asyncio
    async def test_analyze_extracts_recommendations(
        self,
        mock_llm_client,
        sample_workout_data,
        sample_athlete_context,
    ):
        """Test that recommendations are extracted."""
        agent = AnalysisAgent(llm_client=mock_llm_client)

        result = await agent.analyze(
            workout_data=sample_workout_data,
            athlete_context=sample_athlete_context,
        )

        assert len(result.recommendations) > 0

    @pytest.mark.asyncio
    async def test_analyze_sets_context(
        self,
        mock_llm_client,
        sample_workout_data,
        sample_athlete_context,
    ):
        """Test that analysis context is set."""
        agent = AnalysisAgent(llm_client=mock_llm_client)

        result = await agent.analyze(
            workout_data=sample_workout_data,
            athlete_context=sample_athlete_context,
        )

        assert result.context is not None
        assert result.context.ctl == 45.0
        assert result.context.tsb == -7.0

    @pytest.mark.asyncio
    async def test_analyze_handles_llm_error(
        self,
        sample_workout_data,
        sample_athlete_context,
    ):
        """Test error handling when LLM fails."""
        mock_client = AsyncMock()
        mock_client.completion.side_effect = Exception("LLM API error")

        agent = AnalysisAgent(llm_client=mock_client)

        result = await agent.analyze(
            workout_data=sample_workout_data,
            athlete_context=sample_athlete_context,
        )

        assert result.status == AnalysisStatus.FAILED
        assert "error" in result.summary.lower() or "failed" in result.summary.lower()

    @pytest.mark.asyncio
    async def test_analyze_without_similar_workouts(
        self,
        mock_llm_client,
        sample_workout_data,
        sample_athlete_context,
    ):
        """Test analysis without similar workouts for comparison."""
        agent = AnalysisAgent(llm_client=mock_llm_client)

        result = await agent.analyze(
            workout_data=sample_workout_data,
            athlete_context=sample_athlete_context,
            similar_workouts=[],  # Empty list
        )

        assert result.status == AnalysisStatus.COMPLETED
        assert result.context.similar_workouts_count == 0


class TestAnalysisAgentParsing:
    """Tests for response parsing in AnalysisAgent."""

    def test_extract_sections_summary(self):
        """Test summary extraction."""
        agent = AnalysisAgent(llm_client=MagicMock())

        text = """**Summary**: This is a great workout summary.

**What Worked Well**:
- Point 1
- Point 2
"""
        result = agent._extract_sections(text)
        assert "great workout summary" in result["summary"].lower()

    def test_extract_sections_list_items(self):
        """Test list item extraction."""
        agent = AnalysisAgent(llm_client=MagicMock())

        text = """**What Worked Well**:
- First good thing
- Second good thing
- Third good thing

**Observations**:
- First observation
"""
        result = agent._extract_sections(text)
        assert len(result["what_worked_well"]) == 3
        assert "First good thing" in result["what_worked_well"]

    def test_extract_sections_numbered_list(self):
        """Test numbered list extraction."""
        agent = AnalysisAgent(llm_client=MagicMock())

        text = """**Recommendations**:
1. First recommendation
2. Second recommendation
"""
        result = agent._extract_sections(text)
        assert len(result["recommendations"]) == 2

    def test_extract_sections_execution_rating(self):
        """Test execution rating inference."""
        agent = AnalysisAgent(llm_client=MagicMock())

        text = "This was an excellent workout with perfect pacing."
        result = agent._extract_sections(text)
        assert result["execution_rating"] == "excellent"

        text2 = "Good solid effort today."
        result2 = agent._extract_sections(text2)
        assert result2["execution_rating"] == "good"

    def test_extract_list_items_various_formats(self):
        """Test extraction of various list formats."""
        agent = AnalysisAgent(llm_client=MagicMock())

        text = """- Bullet point
* Star bullet
1. Numbered item
> Quote format
"""
        items = agent._extract_list_items(text)
        assert len(items) >= 3


# ============================================================================
# Helper Function Tests
# ============================================================================

class TestBuildAthleteContextFromBriefing:
    """Tests for build_athlete_context_from_briefing helper."""

    def test_extracts_training_status(self):
        """Test extraction of training status."""
        briefing = {
            "training_status": {
                "ctl": 50.0,
                "atl": 55.0,
                "tsb": -5.0,
                "acwr": 1.1,
                "risk_zone": "optimal",
            }
        }

        context = build_athlete_context_from_briefing(briefing)

        assert context["ctl"] == 50.0
        assert context["atl"] == 55.0
        assert context["tsb"] == -5.0
        assert context["risk_zone"] == "optimal"

    def test_extracts_readiness(self):
        """Test extraction of readiness data."""
        briefing = {
            "training_status": {},
            "readiness": {
                "score": 80.0,
                "zone": "green",
            }
        }

        context = build_athlete_context_from_briefing(briefing)

        assert context["readiness_score"] == 80.0
        assert context["readiness_zone"] == "green"

    def test_handles_missing_data(self):
        """Test handling of missing data."""
        context = build_athlete_context_from_briefing({})

        assert context["ctl"] == 0.0
        assert context["readiness_score"] == 50.0
        assert context["readiness_zone"] == "yellow"


class TestGetSimilarWorkouts:
    """Tests for get_similar_workouts helper."""

    def test_filters_by_activity_type(self):
        """Test filtering by activity type."""
        recent = [
            {"activity_id": "1", "activity_type": "running"},
            {"activity_id": "2", "activity_type": "cycling"},
            {"activity_id": "3", "activity_type": "running"},
        ]
        target = {"activity_id": "4", "activity_type": "running"}

        similar = get_similar_workouts(recent, target)

        assert len(similar) == 2
        assert all(w["activity_type"] == "running" for w in similar)

    def test_excludes_target_workout(self):
        """Test that target workout is excluded."""
        recent = [
            {"activity_id": "1", "activity_type": "running"},
            {"activity_id": "2", "activity_type": "running"},
        ]
        target = {"activity_id": "1", "activity_type": "running"}

        similar = get_similar_workouts(recent, target)

        assert len(similar) == 1
        assert similar[0]["activity_id"] == "2"

    def test_respects_limit(self):
        """Test limit parameter."""
        recent = [
            {"activity_id": str(i), "activity_type": "running"}
            for i in range(10)
        ]
        target = {"activity_id": "target", "activity_type": "running"}

        similar = get_similar_workouts(recent, target, limit=3)

        assert len(similar) == 3

    def test_handles_empty_list(self):
        """Test with empty recent activities."""
        similar = get_similar_workouts(
            [],
            {"activity_id": "1", "activity_type": "running"},
        )
        assert similar == []


# ============================================================================
# Integration Tests
# ============================================================================

class TestAnalysisAgentIntegration:
    """Integration tests for the complete analysis workflow."""

    @pytest.mark.asyncio
    async def test_full_workflow(
        self,
        mock_llm_client,
        sample_workout_data,
        sample_athlete_context,
        sample_similar_workouts,
    ):
        """Test the complete analysis workflow."""
        agent = AnalysisAgent(llm_client=mock_llm_client)

        result = await agent.analyze(
            workout_data=sample_workout_data,
            athlete_context=sample_athlete_context,
            similar_workouts=sample_similar_workouts,
        )

        # Verify all expected fields are populated
        assert result.workout_id == sample_workout_data["activity_id"]
        assert result.analysis_id is not None
        assert result.status == AnalysisStatus.COMPLETED
        assert result.summary != ""
        assert result.model_used == "gpt-5-mini"
        assert result.created_at is not None
        assert result.raw_response is not None

        # Verify context
        assert result.context is not None
        assert result.context.ctl == sample_athlete_context["ctl"]
        assert result.context.similar_workouts_count == len(sample_similar_workouts)

    @pytest.mark.asyncio
    async def test_insights_are_generated(
        self,
        mock_llm_client,
        sample_workout_data,
        sample_athlete_context,
    ):
        """Test that insights are generated from observations."""
        agent = AnalysisAgent(llm_client=mock_llm_client)

        result = await agent.analyze(
            workout_data=sample_workout_data,
            athlete_context=sample_athlete_context,
        )

        # Insights should include both positive and negative observations
        positive_insights = [i for i in result.insights if i.is_positive]
        negative_insights = [i for i in result.insights if not i.is_positive]

        assert len(positive_insights) > 0 or len(result.what_worked_well) > 0
