"""Tests for the ChatAgent."""

import pytest
from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from training_analyzer.agents.chat_agent import (
    ChatAgent,
    ChatIntent,
    ChatState,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    client = MagicMock()

    # Mock completion for response generation
    client.completion = AsyncMock(return_value=(
        "Based on your training data, you've had a solid week! "
        "Your CTL is at 45, which shows good base fitness. "
        "You completed 3 workouts totaling 45km with an average HR of 145 bpm. "
        "Your TSB of -5 indicates you're slightly fatigued but well within optimal range."
    ))

    # Mock completion_json for intent classification
    client.completion_json = AsyncMock(return_value={
        "intent": "training_status",
        "time_period": "last week",
        "specific_date": None,
        "comparison_type": None,
        "entities": ["training", "week"],
        "confidence": 0.9,
    })

    # Mock get_model_name
    client.get_model_name = MagicMock(return_value="gpt-5-mini")

    return client


@pytest.fixture
def mock_coach_service():
    """Create a mock coach service."""
    service = MagicMock()

    # Mock daily briefing
    service.get_daily_briefing.return_value = {
        "training_status": {
            "ctl": 45.0,
            "atl": 50.0,
            "tsb": -5.0,
            "acwr": 1.1,
            "risk_zone": "optimal",
        },
        "readiness": {
            "score": 75.0,
            "zone": "green",
            "recommendation": "Ready for moderate training",
        },
        "weekly_load": {
            "current": 150.0,
            "target": 200.0,
            "workout_count": 3,
        },
        "recommendation": {
            "workout_type": "tempo",
            "duration_min": 45,
            "reason": "Good recovery, time for quality work",
        },
    }

    # Mock recent activities
    service.get_recent_activities.return_value = [
        {
            "activity_id": "act1",
            "date": "2025-12-27",
            "activity_type": "running",
            "distance_km": 10.0,
            "duration_min": 55.0,
            "avg_hr": 145,
            "hrss": 75.0,
        },
        {
            "activity_id": "act2",
            "date": "2025-12-25",
            "activity_type": "running",
            "distance_km": 8.0,
            "duration_min": 45.0,
            "avg_hr": 140,
            "hrss": 55.0,
        },
    ]

    # Mock LLM context
    service.get_llm_context.return_value = {
        "fitness_metrics": {
            "ctl": 45.0,
            "atl": 50.0,
            "tsb": -5.0,
            "acwr": 1.1,
            "risk_zone": "optimal",
        },
        "readiness": {
            "score": 75.0,
            "zone": "green",
        },
        "race_goals": [
            {
                "distance": "Marathon",
                "target_time_formatted": "3:30:00",
                "race_date": "2025-04-15",
            }
        ],
    }

    # Mock fitness metrics
    service.get_fitness_metrics.return_value = {
        "ctl": 45.0,
        "atl": 50.0,
        "tsb": -5.0,
        "acwr": 1.1,
        "risk_zone": "optimal",
    }

    # Mock weekly summary
    service.get_weekly_summary.return_value = {
        "week_start": "2025-12-23",
        "total_load": 150.0,
        "total_distance_km": 45.0,
        "workout_count": 3,
        "ctl_change": 2.5,
    }

    return service


@pytest.fixture
def mock_training_db():
    """Create a mock training database."""
    db = MagicMock()

    db.get_race_goals.return_value = [
        {
            "distance": "Marathon",
            "target_time_sec": 12600,
            "target_time_formatted": "3:30:00",
            "race_date": "2025-04-15",
        }
    ]

    return db


# ============================================================================
# Intent Classification Tests
# ============================================================================

class TestIntentClassification:
    """Tests for intent classification."""

    @pytest.mark.asyncio
    async def test_classifies_training_status_intent(self, mock_llm_client, mock_coach_service):
        """Test classification of training status questions."""
        agent = ChatAgent(
            llm_client=mock_llm_client,
            coach_service=mock_coach_service,
        )

        result = await agent.chat("How is my training going?")

        # Verify intent was classified
        assert result.get("intent") == "training_status"
        mock_llm_client.completion_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_classifies_readiness_intent(self, mock_llm_client, mock_coach_service):
        """Test classification of readiness questions."""
        mock_llm_client.completion_json = AsyncMock(return_value={
            "intent": "readiness",
            "time_period": "today",
            "confidence": 0.95,
        })

        agent = ChatAgent(
            llm_client=mock_llm_client,
            coach_service=mock_coach_service,
        )

        result = await agent.chat("Am I ready to train hard today?")

        assert result.get("intent") == "readiness"

    @pytest.mark.asyncio
    async def test_classifies_comparison_intent(self, mock_llm_client, mock_coach_service):
        """Test classification of comparison questions."""
        mock_llm_client.completion_json = AsyncMock(return_value={
            "intent": "workout_comparison",
            "time_period": "this week",
            "comparison_type": "week to week",
            "confidence": 0.88,
        })

        agent = ChatAgent(
            llm_client=mock_llm_client,
            coach_service=mock_coach_service,
        )

        result = await agent.chat("Compare this week to last week")

        assert result.get("intent") == "workout_comparison"

    @pytest.mark.asyncio
    async def test_defaults_to_general_on_classification_error(
        self, mock_llm_client, mock_coach_service
    ):
        """Test fallback to general intent on error."""
        mock_llm_client.completion_json = AsyncMock(side_effect=Exception("API Error"))

        agent = ChatAgent(
            llm_client=mock_llm_client,
            coach_service=mock_coach_service,
        )

        result = await agent.chat("What's the meaning of life?")

        # Should default to general, not crash
        assert result.get("intent") == "general"


# ============================================================================
# Context Gathering Tests
# ============================================================================

class TestContextGathering:
    """Tests for context gathering."""

    @pytest.mark.asyncio
    async def test_gathers_athlete_context(self, mock_llm_client, mock_coach_service):
        """Test that athlete context is gathered from coach service."""
        agent = ChatAgent(
            llm_client=mock_llm_client,
            coach_service=mock_coach_service,
        )

        result = await agent.chat("How was my training?")

        # Verify coach service was called
        mock_coach_service.get_llm_context.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_missing_coach_service(self, mock_llm_client):
        """Test handling when coach service is not available."""
        agent = ChatAgent(
            llm_client=mock_llm_client,
            coach_service=None,
        )

        # Should not crash, just have limited context
        result = await agent.chat("How is my training?")

        assert "response" in result
        assert result.get("status") in ["completed", "no_data_source"]


# ============================================================================
# Data Fetching Tests
# ============================================================================

class TestDataFetching:
    """Tests for training data fetching."""

    @pytest.mark.asyncio
    async def test_fetches_status_data_for_status_intent(
        self, mock_llm_client, mock_coach_service
    ):
        """Test fetching status data for training status questions."""
        agent = ChatAgent(
            llm_client=mock_llm_client,
            coach_service=mock_coach_service,
        )

        result = await agent.chat("What's my current fitness level?")

        # Verify daily briefing was fetched
        mock_coach_service.get_daily_briefing.assert_called()
        assert "fitness_metrics" in result.get("data_sources", [])

    @pytest.mark.asyncio
    async def test_fetches_comparison_data_for_comparison_intent(
        self, mock_llm_client, mock_coach_service
    ):
        """Test fetching comparison data for comparison questions."""
        mock_llm_client.completion_json = AsyncMock(return_value={
            "intent": "workout_comparison",
            "time_period": "last week",
            "comparison_type": "week",
            "confidence": 0.9,
        })

        agent = ChatAgent(
            llm_client=mock_llm_client,
            coach_service=mock_coach_service,
        )

        result = await agent.chat("Compare this week to last week")

        # Verify weekly summaries were fetched
        assert mock_coach_service.get_weekly_summary.call_count >= 1

    @pytest.mark.asyncio
    async def test_fetches_race_readiness_data(
        self, mock_llm_client, mock_coach_service, mock_training_db
    ):
        """Test fetching race readiness data."""
        mock_llm_client.completion_json = AsyncMock(return_value={
            "intent": "race_readiness",
            "time_period": None,
            "confidence": 0.92,
        })

        agent = ChatAgent(
            llm_client=mock_llm_client,
            coach_service=mock_coach_service,
            training_db=mock_training_db,
        )

        result = await agent.chat("Am I ready for my marathon?")

        # Verify briefing with race data was fetched
        mock_coach_service.get_daily_briefing.assert_called()


# ============================================================================
# Response Generation Tests
# ============================================================================

class TestResponseGeneration:
    """Tests for response generation."""

    @pytest.mark.asyncio
    async def test_generates_response(self, mock_llm_client, mock_coach_service):
        """Test that a response is generated."""
        agent = ChatAgent(
            llm_client=mock_llm_client,
            coach_service=mock_coach_service,
        )

        result = await agent.chat("How was my training last week?")

        # Verify response was generated
        assert "response" in result
        assert len(result["response"]) > 0

    @pytest.mark.asyncio
    async def test_response_includes_training_data(
        self, mock_llm_client, mock_coach_service
    ):
        """Test that response references training data."""
        agent = ChatAgent(
            llm_client=mock_llm_client,
            coach_service=mock_coach_service,
        )

        result = await agent.chat("What's my CTL?")

        # The response should include CTL info (from mock)
        assert "CTL" in result["response"] or "45" in result["response"]

    @pytest.mark.asyncio
    async def test_handles_generation_error(self, mock_llm_client, mock_coach_service):
        """Test error handling during response generation."""
        mock_llm_client.completion = AsyncMock(side_effect=Exception("LLM Error"))

        agent = ChatAgent(
            llm_client=mock_llm_client,
            coach_service=mock_coach_service,
        )

        result = await agent.chat("How is my training?")

        # Should return an error response, not crash
        assert "response" in result
        response = result.get("response") or ""
        status = result.get("status", "")
        assert "apologize" in response.lower() or "error" in status or "failed" in status


# ============================================================================
# Conversation History Tests
# ============================================================================

class TestConversationHistory:
    """Tests for conversation history handling."""

    @pytest.mark.asyncio
    async def test_includes_history_in_context(
        self, mock_llm_client, mock_coach_service
    ):
        """Test that conversation history is included in context."""
        agent = ChatAgent(
            llm_client=mock_llm_client,
            coach_service=mock_coach_service,
        )

        history = [
            {"role": "user", "content": "What's my CTL?"},
            {"role": "assistant", "content": "Your CTL is 45."},
        ]

        result = await agent.chat(
            "And what about my ATL?",
            conversation_history=history,
        )

        # Verify completion was called with history context
        mock_llm_client.completion.assert_called()
        call_args = mock_llm_client.completion.call_args

        # The user prompt should reference previous conversation
        user_prompt = call_args[1].get("user", "")
        assert "previous" in user_prompt.lower() or "CTL" in user_prompt

    @pytest.mark.asyncio
    async def test_works_without_history(self, mock_llm_client, mock_coach_service):
        """Test that chat works without conversation history."""
        agent = ChatAgent(
            llm_client=mock_llm_client,
            coach_service=mock_coach_service,
        )

        result = await agent.chat("How is my training?")

        assert "response" in result


# ============================================================================
# Time Period Parsing Tests
# ============================================================================

class TestTimePeriodParsing:
    """Tests for time period parsing."""

    @pytest.mark.asyncio
    async def test_parses_last_week(self, mock_llm_client, mock_coach_service):
        """Test parsing 'last week' time period."""
        agent = ChatAgent(
            llm_client=mock_llm_client,
            coach_service=mock_coach_service,
        )

        days = agent._parse_time_period("last week")
        assert days == 7

    @pytest.mark.asyncio
    async def test_parses_past_month(self, mock_llm_client, mock_coach_service):
        """Test parsing 'past month' time period."""
        agent = ChatAgent(
            llm_client=mock_llm_client,
            coach_service=mock_coach_service,
        )

        days = agent._parse_time_period("past month")
        assert days == 30

    @pytest.mark.asyncio
    async def test_parses_specific_days(self, mock_llm_client, mock_coach_service):
        """Test parsing specific number of days."""
        agent = ChatAgent(
            llm_client=mock_llm_client,
            coach_service=mock_coach_service,
        )

        days = agent._parse_time_period("last 14 days")
        assert days == 14

    @pytest.mark.asyncio
    async def test_defaults_to_week(self, mock_llm_client, mock_coach_service):
        """Test default to 7 days for unknown periods."""
        agent = ChatAgent(
            llm_client=mock_llm_client,
            coach_service=mock_coach_service,
        )

        days = agent._parse_time_period("sometime recently")
        assert days == 7


# ============================================================================
# Data Source Tracking Tests
# ============================================================================

class TestDataSourceTracking:
    """Tests for data source tracking."""

    @pytest.mark.asyncio
    async def test_tracks_data_sources_for_status(
        self, mock_llm_client, mock_coach_service
    ):
        """Test that data sources are tracked for status queries."""
        agent = ChatAgent(
            llm_client=mock_llm_client,
            coach_service=mock_coach_service,
        )

        result = await agent.chat("What's my current training status?")

        assert "data_sources" in result
        assert len(result["data_sources"]) > 0
        assert "fitness_metrics" in result["data_sources"] or "readiness" in result["data_sources"]

    @pytest.mark.asyncio
    async def test_tracks_data_sources_for_recommendation(
        self, mock_llm_client, mock_coach_service
    ):
        """Test that data sources are tracked for recommendation queries."""
        mock_llm_client.completion_json = AsyncMock(return_value={
            "intent": "recommendation",
            "time_period": None,
            "confidence": 0.9,
        })

        agent = ChatAgent(
            llm_client=mock_llm_client,
            coach_service=mock_coach_service,
        )

        result = await agent.chat("What should I do today?")

        assert "data_sources" in result
        assert "readiness" in result["data_sources"]


# ============================================================================
# Integration Tests
# ============================================================================

class TestChatAgentIntegration:
    """Integration tests for the complete chat workflow."""

    @pytest.mark.asyncio
    async def test_full_workflow(
        self, mock_llm_client, mock_coach_service, mock_training_db
    ):
        """Test the complete chat workflow."""
        agent = ChatAgent(
            llm_client=mock_llm_client,
            coach_service=mock_coach_service,
            training_db=mock_training_db,
        )

        result = await agent.chat("How was my training last week?")

        # Verify all expected fields are present
        assert "response" in result
        assert "data_sources" in result
        assert "intent" in result
        assert "chat_id" in result
        assert "status" in result

        # Verify response is meaningful
        assert len(result["response"]) > 50

        # Verify chat_id is a UUID
        import uuid
        try:
            uuid.UUID(result["chat_id"])
        except ValueError:
            pytest.fail("chat_id is not a valid UUID")

    @pytest.mark.asyncio
    async def test_handles_race_readiness_question(
        self, mock_llm_client, mock_coach_service, mock_training_db
    ):
        """Test handling a race readiness question."""
        mock_llm_client.completion_json = AsyncMock(return_value={
            "intent": "race_readiness",
            "time_period": None,
            "confidence": 0.92,
        })

        agent = ChatAgent(
            llm_client=mock_llm_client,
            coach_service=mock_coach_service,
            training_db=mock_training_db,
        )

        result = await agent.chat("Am I ready for my upcoming marathon?")

        assert result.get("intent") == "race_readiness"
        assert "response" in result

    @pytest.mark.asyncio
    async def test_handles_trend_question(
        self, mock_llm_client, mock_coach_service
    ):
        """Test handling a trend analysis question."""
        mock_llm_client.completion_json = AsyncMock(return_value={
            "intent": "trend_analysis",
            "time_period": "past month",
            "confidence": 0.88,
        })

        agent = ChatAgent(
            llm_client=mock_llm_client,
            coach_service=mock_coach_service,
        )

        result = await agent.chat("What's my fitness trend over the past month?")

        assert result.get("intent") == "trend_analysis"
        assert "response" in result
