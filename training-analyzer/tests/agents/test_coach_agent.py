"""Tests for the ConversationalCoach agent."""

import pytest
from datetime import date, timedelta
from training_analyzer.agents.coach_agent import (
    CoachingContext,
    CoachingIntent,
    CoachingResponse,
    ConversationalCoach,
    get_conversational_coach,
)


class TestCoachingContext:
    """Tests for CoachingContext."""

    def test_basic_context(self):
        """Test basic context creation."""
        context = CoachingContext(
            ctl=50.0,
            atl=45.0,
            tsb=5.0,
            acwr=0.9,
        )

        assert context.ctl == 50.0
        assert context.tsb == 5.0

    def test_context_with_race(self):
        """Test context with upcoming race."""
        race_date = date.today() + timedelta(weeks=4)
        context = CoachingContext(
            ctl=55.0,
            atl=50.0,
            tsb=5.0,
            acwr=0.91,
            upcoming_race_date=race_date,
            upcoming_race_name="Spring Marathon",
        )

        assert context.upcoming_race_date == race_date
        assert context.upcoming_race_name == "Spring Marathon"

    def test_to_prompt_context(self):
        """Test prompt context formatting."""
        context = CoachingContext(
            ctl=50.0,
            atl=45.0,
            tsb=5.0,
            acwr=0.9,
            weekly_hours=6.5,
            weekly_distance_km=45.0,
            weekly_load=350.0,
        )

        prompt = context.to_prompt_context()

        assert "CTL" in prompt
        assert "50.0" in prompt
        assert "TSB" in prompt
        assert "5.0" in prompt
        assert "45.0 km" in prompt


class TestCoachingIntentClassification:
    """Tests for intent classification."""

    @pytest.fixture
    def coach(self):
        """Create coach instance."""
        return ConversationalCoach()

    def test_classify_workout_request(self, coach):
        """Test classification of workout requests."""
        intent = coach._classify_intent_sync("I want to do a tempo run today")
        assert intent == CoachingIntent.WORKOUT_REQUEST

        intent = coach._classify_intent_sync("Suggest a workout for me")
        assert intent == CoachingIntent.WORKOUT_REQUEST

    def test_classify_advice_request(self, coach):
        """Test classification of advice requests."""
        intent = coach._classify_intent_sync("Should I train hard today?")
        assert intent == CoachingIntent.ADVICE_REQUEST

        intent = coach._classify_intent_sync("Can I do intervals?")
        assert intent == CoachingIntent.ADVICE_REQUEST

    def test_classify_adjustment_request(self, coach):
        """Test classification of adjustment requests."""
        intent = coach._classify_intent_sync("I'm feeling tired, can we go easier?")
        assert intent == CoachingIntent.ADJUSTMENT_REQUEST

        intent = coach._classify_intent_sync("I'm too sore for the planned workout")
        assert intent == CoachingIntent.ADJUSTMENT_REQUEST

    def test_classify_metric_question(self, coach):
        """Test classification of metric questions."""
        intent = coach._classify_intent_sync("What's my CTL?")
        assert intent == CoachingIntent.METRIC_QUESTION

        intent = coach._classify_intent_sync("Show me my fitness stats")
        assert intent == CoachingIntent.METRIC_QUESTION

    def test_classify_plan_question(self, coach):
        """Test classification of plan questions."""
        intent = coach._classify_intent_sync("What should I do this week?")
        assert intent == CoachingIntent.PLAN_QUESTION

        intent = coach._classify_intent_sync("Tell me about my training schedule")
        assert intent == CoachingIntent.PLAN_QUESTION

    def test_classify_general_question(self, coach):
        """Test classification of general questions."""
        intent = coach._classify_intent_sync("How do I improve my VO2max?")
        assert intent == CoachingIntent.GENERAL_QUESTION


class TestConversationalCoach:
    """Tests for ConversationalCoach."""

    @pytest.fixture
    def coach(self):
        """Create coach instance."""
        return ConversationalCoach()

    @pytest.fixture
    def fresh_context(self):
        """Create a fresh athlete context."""
        return CoachingContext(
            ctl=50.0,
            atl=45.0,
            tsb=10.0,  # Fresh
            acwr=0.9,
            weekly_hours=5.0,
            weekly_distance_km=40.0,
            weekly_load=300.0,
        )

    @pytest.fixture
    def fatigued_context(self):
        """Create a fatigued athlete context."""
        return CoachingContext(
            ctl=45.0,
            atl=65.0,
            tsb=-20.0,  # Fatigued
            acwr=1.44,  # Elevated
            consecutive_hard_days=3,
            weekly_hours=8.0,
            weekly_load=500.0,
        )

    def test_chat_sync_advice_fresh(self, coach, fresh_context):
        """Test advice for fresh athlete."""
        response = coach.chat_sync("Should I train hard today?", fresh_context)

        assert response.intent == CoachingIntent.ADVICE_REQUEST
        assert response.message is not None
        assert response.recommended_intensity in ["hard", "moderate"]

    def test_chat_sync_advice_fatigued(self, coach, fatigued_context):
        """Test advice for fatigued athlete."""
        response = coach.chat_sync("Should I train today?", fatigued_context)

        assert response.intent == CoachingIntent.ADVICE_REQUEST
        assert response.recommended_intensity in ["rest", "easy"]
        assert len(response.cautions) > 0  # Should have warnings

    def test_chat_sync_workout_request(self, coach, fresh_context):
        """Test workout request handling."""
        response = coach.chat_sync("I want to do a workout today", fresh_context)

        assert response.intent == CoachingIntent.WORKOUT_REQUEST
        assert response.recommended_workout is not None
        assert "type" in response.recommended_workout

    def test_chat_sync_adjustment(self, coach, fresh_context):
        """Test adjustment request handling."""
        response = coach.chat_sync("I'm feeling tired, can we go easier?", fresh_context)

        assert response.intent == CoachingIntent.ADJUSTMENT_REQUEST
        assert response.recommended_intensity in ["rest", "easy"]
        assert len(response.action_items) > 0

    def test_chat_sync_metric_question(self, coach, fresh_context):
        """Test metric question handling."""
        response = coach.chat_sync("What's my CTL?", fresh_context)

        assert response.intent == CoachingIntent.METRIC_QUESTION
        assert "CTL" in response.message
        assert "50" in response.message

    def test_chat_sync_general(self, coach, fresh_context):
        """Test general question handling."""
        response = coach.chat_sync("How do I get faster?", fresh_context)

        assert response.intent == CoachingIntent.GENERAL_QUESTION
        assert response.message is not None

    def test_determine_intensity_fresh(self, coach, fresh_context):
        """Test intensity determination for fresh athlete."""
        intensity = coach._determine_recommended_intensity(fresh_context)
        assert intensity in ["hard", "moderate"]

    def test_determine_intensity_fatigued(self, coach, fatigued_context):
        """Test intensity determination for fatigued athlete."""
        intensity = coach._determine_recommended_intensity(fatigued_context)
        assert intensity in ["rest", "easy"]

    def test_determine_intensity_high_acwr(self, coach):
        """Test intensity determination for high ACWR."""
        context = CoachingContext(
            ctl=40.0,
            atl=65.0,
            tsb=-25.0,
            acwr=1.6,  # Danger zone
        )

        intensity = coach._determine_recommended_intensity(context)
        assert intensity == "rest"

    def test_generate_cautions_high_acwr(self, coach):
        """Test caution generation for high ACWR."""
        context = CoachingContext(
            ctl=40.0,
            atl=65.0,
            tsb=-25.0,
            acwr=1.6,
        )

        cautions = coach._generate_cautions(context)

        assert any("ACWR" in c for c in cautions)
        assert any("danger" in c.lower() for c in cautions)

    def test_generate_cautions_consecutive_hard_days(self, coach):
        """Test caution generation for consecutive hard days."""
        context = CoachingContext(
            ctl=50.0,
            atl=55.0,
            tsb=-5.0,
            acwr=1.1,
            consecutive_hard_days=4,
        )

        cautions = coach._generate_cautions(context)

        assert any("consecutive" in c.lower() for c in cautions)

    def test_generate_cautions_upcoming_race(self, coach):
        """Test caution generation for upcoming race."""
        context = CoachingContext(
            ctl=50.0,
            atl=50.0,
            tsb=0.0,
            acwr=1.0,
            upcoming_race_date=date.today() + timedelta(days=5),
            upcoming_race_name="Local 5K",
        )

        cautions = coach._generate_cautions(context)

        assert any("race" in c.lower() or "🏁" in c for c in cautions)

    def test_generate_action_items(self, coach):
        """Test action item generation."""
        rest_items = coach._generate_action_items("rest")
        assert any("rest" in item.lower() for item in rest_items)

        hard_items = coach._generate_action_items("hard")
        assert any("warm" in item.lower() for item in hard_items)

    def test_interpret_metrics(self, coach):
        """Test metric interpretation."""
        fresh_context = CoachingContext(ctl=50.0, atl=45.0, tsb=20.0, acwr=0.9)
        interpretation = coach._interpret_metrics(fresh_context)
        assert "fresh" in interpretation.lower() or "key workout" in interpretation.lower()

        tired_context = CoachingContext(ctl=50.0, atl=65.0, tsb=-20.0, acwr=1.3)
        interpretation = coach._interpret_metrics(tired_context)
        assert "fatigue" in interpretation.lower() or "recovery" in interpretation.lower()

    def test_singleton(self):
        """Test singleton pattern."""
        coach1 = get_conversational_coach()
        coach2 = get_conversational_coach()
        assert coach1 is coach2


class TestCoachingResponse:
    """Tests for CoachingResponse."""

    def test_response_to_dict(self):
        """Test response serialization."""
        response = CoachingResponse(
            intent=CoachingIntent.ADVICE_REQUEST,
            message="You should take it easy today.",
            recommended_intensity="easy",
            cautions=["Fatigue is elevated"],
            action_items=["Rest", "Hydrate"],
            confidence=0.85,
        )

        data = response.to_dict()

        assert data["intent"] == "advice_request"
        assert data["recommended_intensity"] == "easy"
        assert len(data["cautions"]) == 1
        assert len(data["action_items"]) == 2

    def test_response_with_workout(self):
        """Test response with workout recommendation."""
        response = CoachingResponse(
            intent=CoachingIntent.WORKOUT_REQUEST,
            message="Here's your workout",
            recommended_workout={
                "type": "tempo",
                "duration_min": 45,
                "description": "Tempo run",
            },
        )

        data = response.to_dict()

        assert data["recommended_workout"]["type"] == "tempo"
        assert data["recommended_workout"]["duration_min"] == 45



