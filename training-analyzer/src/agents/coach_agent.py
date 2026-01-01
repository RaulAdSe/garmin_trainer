"""
Conversational AI Coach for context-aware training recommendations.

Provides natural language interface for:
- Context-aware workout recommendations
- Post-workout coaching feedback
- Training questions and advice
- Natural language workout requests
"""

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from ..llm.providers import LLMClient, ModelType, get_llm_client
from ..services.fatigue_prediction import (
    DailyReadiness,
    FatiguePredictionService,
    get_fatigue_service,
)
from ..services.adaptation import (
    WorkoutAdaptationEngine,
    get_adaptation_engine,
)
from ..models.workouts import AthleteContext


class CoachingIntent(str, Enum):
    """Types of coaching intents from user messages."""
    WORKOUT_REQUEST = "workout_request"  # "I want to do a tempo run"
    ADVICE_REQUEST = "advice_request"    # "Should I train hard today?"
    FEEDBACK_REQUEST = "feedback_request"  # "How was my workout?"
    PLAN_QUESTION = "plan_question"      # "What should I do this week?"
    METRIC_QUESTION = "metric_question"  # "What's my CTL?"
    GENERAL_QUESTION = "general_question"  # "How do I improve my VO2max?"
    ADJUSTMENT_REQUEST = "adjustment_request"  # "I'm tired, can we go easier?"


@dataclass
class CoachingContext:
    """
    Context for the AI coach to provide personalized recommendations.
    """
    # Athlete context
    athlete_context: Optional[AthleteContext] = None
    
    # Current fitness state
    ctl: float = 40.0
    atl: float = 40.0
    tsb: float = 0.0
    acwr: float = 1.0
    
    # Recovery data
    last_workout_date: Optional[date] = None
    last_workout_type: Optional[str] = None
    last_workout_load: Optional[float] = None
    consecutive_hard_days: int = 0
    
    # Goals
    upcoming_race_date: Optional[date] = None
    upcoming_race_name: Optional[str] = None
    primary_goal: Optional[str] = None  # "5k PR", "marathon", "general fitness"
    
    # Current state
    current_fatigue_level: Optional[str] = None  # from FatiguePrediction
    recovery_state: Optional[str] = None
    
    # Recent history summary
    weekly_hours: float = 0.0
    weekly_distance_km: float = 0.0
    weekly_load: float = 0.0
    
    def to_prompt_context(self) -> str:
        """Format context for LLM prompt."""
        lines = [
            "=== ATHLETE CONTEXT ===",
            "",
            "Current Fitness State:",
            f"- CTL (Fitness): {self.ctl:.1f}",
            f"- ATL (Fatigue): {self.atl:.1f}",
            f"- TSB (Form): {self.tsb:.1f}",
            f"- ACWR: {self.acwr:.2f}",
        ]
        
        if self.current_fatigue_level:
            lines.extend([
                "",
                "Recovery Status:",
                f"- Fatigue Level: {self.current_fatigue_level}",
                f"- Recovery State: {self.recovery_state or 'unknown'}",
            ])
        
        if self.last_workout_date:
            lines.extend([
                "",
                "Recent Training:",
                f"- Last Workout: {self.last_workout_date.isoformat()} ({self.last_workout_type})",
                f"- Last Workout Load: {self.last_workout_load:.1f}" if self.last_workout_load else "",
                f"- Consecutive Hard Days: {self.consecutive_hard_days}",
            ])
        
        lines.extend([
            "",
            "This Week:",
            f"- Hours: {self.weekly_hours:.1f}",
            f"- Distance: {self.weekly_distance_km:.1f} km",
            f"- Load: {self.weekly_load:.1f}",
        ])
        
        if self.upcoming_race_date:
            days_to_race = (self.upcoming_race_date - date.today()).days
            lines.extend([
                "",
                "Goals:",
                f"- Upcoming Race: {self.upcoming_race_name} on {self.upcoming_race_date.isoformat()} ({days_to_race} days away)",
            ])
        
        if self.primary_goal:
            lines.append(f"- Primary Goal: {self.primary_goal}")
        
        return "\n".join(lines)


@dataclass
class CoachingResponse:
    """
    Response from the AI coach.
    """
    intent: CoachingIntent
    message: str
    
    # Structured recommendations (optional)
    recommended_workout: Optional[Dict[str, Any]] = None
    recommended_intensity: Optional[str] = None
    cautions: List[str] = field(default_factory=list)
    
    # Action items
    action_items: List[str] = field(default_factory=list)
    
    # Follow-up questions
    follow_up_questions: List[str] = field(default_factory=list)
    
    # Confidence in response
    confidence: float = 0.8
    
    def to_dict(self) -> dict:
        return {
            "intent": self.intent.value,
            "message": self.message,
            "recommended_workout": self.recommended_workout,
            "recommended_intensity": self.recommended_intensity,
            "cautions": self.cautions,
            "action_items": self.action_items,
            "follow_up_questions": self.follow_up_questions,
            "confidence": self.confidence,
        }


# System prompts for the coach
COACH_SYSTEM_PROMPT = """You are an expert endurance coach with deep knowledge of:
- Training periodization and load management
- Recovery science and fatigue monitoring
- Running, cycling, and swimming training principles
- Race preparation and tapering
- Injury prevention

You provide personalized, evidence-based coaching advice. Your communication style is:
- Warm and encouraging
- Direct and actionable
- Evidence-based but accessible
- Adaptive to the athlete's current state

When giving recommendations:
1. Always consider the athlete's current fatigue and fitness state
2. Prioritize injury prevention
3. Explain the "why" behind your recommendations
4. Be specific with workout details when appropriate
5. Acknowledge when rest is the best option

IMPORTANT GUIDELINES:
- If ACWR > 1.3, recommend reduced training
- If ACWR > 1.5, strongly recommend rest or very easy activity
- If TSB < -20, prioritize recovery
- Consider race proximity when making recommendations
- Account for consecutive hard training days

Respond in a conversational but professional tone."""


INTENT_CLASSIFICATION_PROMPT = """Classify the user's intent from their message. 

Possible intents:
- WORKOUT_REQUEST: User wants to do a specific workout or asks for workout suggestions
- ADVICE_REQUEST: User asks whether they should train, how hard, etc.
- FEEDBACK_REQUEST: User asks about their recent workout or performance
- PLAN_QUESTION: User asks about their training plan or schedule
- METRIC_QUESTION: User asks about their metrics (CTL, TSB, etc.)
- GENERAL_QUESTION: User asks general training questions
- ADJUSTMENT_REQUEST: User wants to modify their training due to fatigue, time, etc.

User message: {message}

Respond with ONLY the intent name (e.g., "WORKOUT_REQUEST"). No explanation."""


class ConversationalCoach:
    """
    AI-powered conversational coach for personalized training guidance.

    Features:
    - Context-aware recommendations
    - Natural language workout requests
    - Post-workout coaching feedback
    - Adaptive training advice
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        fatigue_service: Optional[FatiguePredictionService] = None,
        adaptation_engine: Optional[WorkoutAdaptationEngine] = None,
        user_id: Optional[str] = None,
    ):
        """Initialize the conversational coach."""
        self._llm_client = llm_client
        self._fatigue_service = fatigue_service or get_fatigue_service()
        self._adaptation_engine = adaptation_engine or get_adaptation_engine()
        self._user_id = user_id
        self._conversation_history: List[Dict[str, str]] = []

    @property
    def user_id(self) -> Optional[str]:
        """Get the user ID for usage tracking."""
        return self._user_id

    @user_id.setter
    def user_id(self, value: Optional[str]) -> None:
        """Set the user ID for usage tracking."""
        self._user_id = value
    
    @property
    def llm(self) -> LLMClient:
        """Get LLM client, creating if needed."""
        if self._llm_client is None:
            self._llm_client = get_llm_client()
        return self._llm_client
    
    async def chat(
        self,
        message: str,
        context: CoachingContext,
    ) -> CoachingResponse:
        """
        Process a user message and return coaching response.
        
        Args:
            message: User's natural language message
            context: Current coaching context
        
        Returns:
            Coaching response with recommendations
        """
        # Classify intent
        intent = await self._classify_intent(message)
        
        # Build response based on intent
        if intent == CoachingIntent.WORKOUT_REQUEST:
            return await self._handle_workout_request(message, context)
        elif intent == CoachingIntent.ADVICE_REQUEST:
            return await self._handle_advice_request(message, context)
        elif intent == CoachingIntent.FEEDBACK_REQUEST:
            return await self._handle_feedback_request(message, context)
        elif intent == CoachingIntent.ADJUSTMENT_REQUEST:
            return await self._handle_adjustment_request(message, context)
        elif intent == CoachingIntent.PLAN_QUESTION:
            return await self._handle_plan_question(message, context)
        elif intent == CoachingIntent.METRIC_QUESTION:
            return self._handle_metric_question(message, context)
        else:
            return await self._handle_general_question(message, context)
    
    def chat_sync(
        self,
        message: str,
        context: CoachingContext,
    ) -> CoachingResponse:
        """
        Synchronous version of chat for non-async contexts.
        
        Uses rule-based logic instead of LLM.
        """
        intent = self._classify_intent_sync(message)
        
        if intent == CoachingIntent.ADVICE_REQUEST:
            return self._generate_advice_sync(context)
        elif intent == CoachingIntent.WORKOUT_REQUEST:
            return self._generate_workout_suggestion_sync(message, context)
        elif intent == CoachingIntent.ADJUSTMENT_REQUEST:
            return self._generate_adjustment_sync(message, context)
        elif intent == CoachingIntent.METRIC_QUESTION:
            return self._handle_metric_question(message, context)
        else:
            return self._generate_general_response_sync(message, context)
    
    async def _classify_intent(self, message: str) -> CoachingIntent:
        """Classify user intent using LLM."""
        try:
            prompt = INTENT_CLASSIFICATION_PROMPT.format(message=message)
            response = await self.llm.completion(
                system="You are an intent classifier. Respond with only the intent name.",
                user=prompt,
                model=ModelType.FAST,
                temperature=0.0,
                max_tokens=50,
                user_id=self._user_id,
                analysis_type="intent_classification",
            )
            
            intent_str = response.strip().upper()
            
            # Map to enum
            intent_map = {
                "WORKOUT_REQUEST": CoachingIntent.WORKOUT_REQUEST,
                "ADVICE_REQUEST": CoachingIntent.ADVICE_REQUEST,
                "FEEDBACK_REQUEST": CoachingIntent.FEEDBACK_REQUEST,
                "PLAN_QUESTION": CoachingIntent.PLAN_QUESTION,
                "METRIC_QUESTION": CoachingIntent.METRIC_QUESTION,
                "GENERAL_QUESTION": CoachingIntent.GENERAL_QUESTION,
                "ADJUSTMENT_REQUEST": CoachingIntent.ADJUSTMENT_REQUEST,
            }
            
            return intent_map.get(intent_str, CoachingIntent.GENERAL_QUESTION)
        except Exception:
            return self._classify_intent_sync(message)
    
    def _classify_intent_sync(self, message: str) -> CoachingIntent:
        """Classify intent using keyword matching."""
        message_lower = message.lower()
        
        # Adjustment keywords - check first (higher priority than workout)
        if any(kw in message_lower for kw in [
            "tired", "sore", "exhausted", "easier", "reduce",
            "skip", "rest day", "don't feel", "feeling tired",
            "too sore", "can we go easier", "back off"
        ]):
            return CoachingIntent.ADJUSTMENT_REQUEST
        
        # Plan keywords - check before advice (more specific)
        if any(kw in message_lower for kw in [
            "this week", "my plan", "schedule", "next few days",
            "training block", "weekly plan", "upcoming week"
        ]):
            return CoachingIntent.PLAN_QUESTION
        
        # Workout request keywords
        if any(kw in message_lower for kw in [
            "want to do", "workout", "run", "ride", "swim",
            "training session", "exercise", "suggest a"
        ]):
            return CoachingIntent.WORKOUT_REQUEST
        
        # Advice keywords
        if any(kw in message_lower for kw in [
            "should i", "can i", "is it ok", "ready",
            "how hard", "train today", "train hard"
        ]):
            return CoachingIntent.ADVICE_REQUEST
        
        # Feedback keywords
        if any(kw in message_lower for kw in [
            "how was", "my workout", "performance", "did i do",
            "went well", "struggled"
        ]):
            return CoachingIntent.FEEDBACK_REQUEST
        
        # Metric keywords
        if any(kw in message_lower for kw in [
            "ctl", "atl", "tsb", "fitness", "fatigue score",
            "what's my", "my stats"
        ]):
            return CoachingIntent.METRIC_QUESTION
        
        # Plan keywords
        if any(kw in message_lower for kw in [
            "this week", "plan", "schedule", "next few days",
            "training block"
        ]):
            return CoachingIntent.PLAN_QUESTION
        
        return CoachingIntent.GENERAL_QUESTION
    
    async def _handle_workout_request(
        self,
        message: str,
        context: CoachingContext,
    ) -> CoachingResponse:
        """Handle request for a workout."""
        # Build prompt with context
        user_prompt = f"""The athlete says: "{message}"

{context.to_prompt_context()}

Based on their current state, provide a specific workout recommendation.
If they asked for a specific type, adapt it to their current fatigue level.
If they just want a workout, suggest the most appropriate one.

Respond with:
1. A brief acknowledgment
2. Your recommendation with specific details (duration, intensity, pace ranges if applicable)
3. Why this workout is appropriate given their current state
4. Any cautions or modifications needed

Keep your response conversational but specific."""

        try:
            response = await self.llm.completion(
                system=COACH_SYSTEM_PROMPT,
                user=user_prompt,
                model=ModelType.SMART,
                temperature=0.7,
                max_tokens=500,
                user_id=self._user_id,
                analysis_type="coach_response",
            )

            # Determine recommended intensity from context
            if context.current_fatigue_level in ["exhausted", "fatigued"]:
                intensity = "easy"
                cautions = ["Current fatigue levels are elevated - consider additional recovery"]
            elif context.acwr > 1.3:
                intensity = "easy"
                cautions = ["ACWR is elevated - prioritize lower intensity"]
            elif context.tsb < -15:
                intensity = "moderate"
                cautions = ["Fitness is building but fatigue is present"]
            else:
                intensity = "as_planned"
                cautions = []
            
            return CoachingResponse(
                intent=CoachingIntent.WORKOUT_REQUEST,
                message=response,
                recommended_intensity=intensity,
                cautions=cautions,
                action_items=["Complete suggested workout", "Log how you feel after"],
            )
        except Exception as e:
            return self._generate_workout_suggestion_sync(message, context)
    
    async def _handle_advice_request(
        self,
        message: str,
        context: CoachingContext,
    ) -> CoachingResponse:
        """Handle request for training advice."""
        user_prompt = f"""The athlete asks: "{message}"

{context.to_prompt_context()}

Provide advice on whether and how they should train today.
Consider their fatigue, recent training, and goals.
Be specific about intensity recommendations."""

        try:
            response = await self.llm.completion(
                system=COACH_SYSTEM_PROMPT,
                user=user_prompt,
                model=ModelType.SMART,
                temperature=0.7,
                max_tokens=400,
                user_id=self._user_id,
                analysis_type="coach_response",
            )

            return CoachingResponse(
                intent=CoachingIntent.ADVICE_REQUEST,
                message=response,
                recommended_intensity=self._determine_recommended_intensity(context),
                cautions=self._generate_cautions(context),
            )
        except Exception:
            return self._generate_advice_sync(context)
    
    async def _handle_feedback_request(
        self,
        message: str,
        context: CoachingContext,
    ) -> CoachingResponse:
        """Handle request for workout feedback."""
        user_prompt = f"""The athlete asks about their workout: "{message}"

{context.to_prompt_context()}

Provide constructive feedback on their recent training.
Acknowledge what went well and provide suggestions for improvement."""

        try:
            response = await self.llm.completion(
                system=COACH_SYSTEM_PROMPT,
                user=user_prompt,
                model=ModelType.SMART,
                temperature=0.7,
                max_tokens=400,
                user_id=self._user_id,
                analysis_type="coach_response",
            )

            return CoachingResponse(
                intent=CoachingIntent.FEEDBACK_REQUEST,
                message=response,
                follow_up_questions=[
                    "How did you feel during the hard efforts?",
                    "Any lingering soreness or fatigue?",
                ],
            )
        except Exception:
            return CoachingResponse(
                intent=CoachingIntent.FEEDBACK_REQUEST,
                message=self._generate_generic_feedback(context),
            )
    
    async def _handle_adjustment_request(
        self,
        message: str,
        context: CoachingContext,
    ) -> CoachingResponse:
        """Handle request to adjust training."""
        return self._generate_adjustment_sync(message, context)
    
    async def _handle_plan_question(
        self,
        message: str,
        context: CoachingContext,
    ) -> CoachingResponse:
        """Handle questions about training plan."""
        user_prompt = f"""The athlete asks about their plan: "{message}"

{context.to_prompt_context()}

Provide guidance on their upcoming training.
Consider their current fatigue and any upcoming races."""

        try:
            response = await self.llm.completion(
                system=COACH_SYSTEM_PROMPT,
                user=user_prompt,
                model=ModelType.SMART,
                temperature=0.7,
                max_tokens=500,
                user_id=self._user_id,
                analysis_type="plan_generation",
            )

            return CoachingResponse(
                intent=CoachingIntent.PLAN_QUESTION,
                message=response,
            )
        except Exception:
            return self._generate_general_response_sync(message, context)
    
    def _handle_metric_question(
        self,
        message: str,
        context: CoachingContext,
    ) -> CoachingResponse:
        """Handle questions about metrics."""
        message_lower = message.lower()
        
        metrics_info = []
        
        if "ctl" in message_lower or "fitness" in message_lower:
            metrics_info.append(
                f"Your CTL (Chronic Training Load/Fitness) is {context.ctl:.1f}. "
                "This represents your accumulated fitness from training over the past ~6 weeks."
            )
        
        if "atl" in message_lower or "fatigue" in message_lower:
            metrics_info.append(
                f"Your ATL (Acute Training Load/Fatigue) is {context.atl:.1f}. "
                "This represents your recent training fatigue from the past ~1 week."
            )
        
        if "tsb" in message_lower or "form" in message_lower:
            metrics_info.append(
                f"Your TSB (Training Stress Balance/Form) is {context.tsb:.1f}. "
                f"{'You are well-rested and ready for hard training.' if context.tsb > 10 else 'You are carrying some fatigue.' if context.tsb > -10 else 'You have significant accumulated fatigue - consider recovery.'}"
            )
        
        if "acwr" in message_lower:
            metrics_info.append(
                f"Your ACWR (Acute:Chronic Workload Ratio) is {context.acwr:.2f}. "
                f"{'Optimal training zone (0.8-1.3)' if 0.8 <= context.acwr <= 1.3 else 'Elevated injury risk zone - reduce load' if context.acwr > 1.3 else 'Undertraining zone - consider increasing load'}"
            )
        
        if not metrics_info:
            metrics_info = [
                f"Here's your current training state:",
                f"- CTL (Fitness): {context.ctl:.1f}",
                f"- ATL (Fatigue): {context.atl:.1f}",
                f"- TSB (Form): {context.tsb:.1f}",
                f"- ACWR: {context.acwr:.2f}",
                "",
                self._interpret_metrics(context),
            ]
        
        return CoachingResponse(
            intent=CoachingIntent.METRIC_QUESTION,
            message="\n\n".join(metrics_info),
        )
    
    async def _handle_general_question(
        self,
        message: str,
        context: CoachingContext,
    ) -> CoachingResponse:
        """Handle general training questions."""
        user_prompt = f"""The athlete asks: "{message}"

{context.to_prompt_context()}

Provide helpful, evidence-based training advice.
Be specific and actionable where possible."""

        try:
            response = await self.llm.completion(
                system=COACH_SYSTEM_PROMPT,
                user=user_prompt,
                model=ModelType.SMART,
                temperature=0.7,
                max_tokens=500,
                user_id=self._user_id,
                analysis_type="coach_response",
            )

            return CoachingResponse(
                intent=CoachingIntent.GENERAL_QUESTION,
                message=response,
            )
        except Exception:
            return self._generate_general_response_sync(message, context)
    
    # === Sync Helper Methods ===
    
    def _generate_advice_sync(self, context: CoachingContext) -> CoachingResponse:
        """Generate advice synchronously using rules."""
        intensity = self._determine_recommended_intensity(context)
        cautions = self._generate_cautions(context)
        
        if intensity == "rest":
            message = (
                f"Based on your current state (TSB: {context.tsb:.1f}, ACWR: {context.acwr:.2f}), "
                "I'd recommend a rest day today. Your body needs time to absorb recent training. "
                "Some light stretching or a walk is fine, but no structured training."
            )
        elif intensity == "easy":
            message = (
                f"You can train today, but keep it easy. Your fatigue levels are elevated "
                f"(TSB: {context.tsb:.1f}). An easy {30 if context.weekly_hours < 5 else 45} minute "
                "session would be appropriate - think Zone 2, conversational pace."
            )
        elif intensity == "moderate":
            message = (
                "You're in a good spot for moderate training today. Your body has recovered "
                f"enough (TSB: {context.tsb:.1f}) for quality work. A tempo session or "
                "steady-state aerobic work would be great choices."
            )
        else:
            message = (
                f"You're fresh and ready! (TSB: {context.tsb:.1f}). Today would be a great day "
                "for a key workout - intervals, threshold work, or a long endurance session. "
                "Take advantage of your good form."
            )
        
        return CoachingResponse(
            intent=CoachingIntent.ADVICE_REQUEST,
            message=message,
            recommended_intensity=intensity,
            cautions=cautions,
            action_items=self._generate_action_items(intensity),
        )
    
    def _generate_workout_suggestion_sync(
        self,
        message: str,
        context: CoachingContext,
    ) -> CoachingResponse:
        """Generate workout suggestion synchronously."""
        intensity = self._determine_recommended_intensity(context)
        
        if intensity == "rest":
            workout_type = "rest"
            description = "Complete rest or very light activity (walk, stretching)"
            duration = 0
        elif intensity == "easy":
            workout_type = "easy"
            description = "Easy aerobic session at conversational pace"
            duration = 30 if context.weekly_hours < 5 else 45
        elif intensity == "moderate":
            workout_type = "tempo"
            description = "Moderate tempo work with good aerobic stimulus"
            duration = 45
        else:
            workout_type = "intervals" if context.consecutive_hard_days < 2 else "threshold"
            description = f"Quality {workout_type} session"
            duration = 60
        
        message = (
            f"Given your current state, I recommend a **{workout_type}** session today.\n\n"
            f"**Duration:** {duration} minutes\n"
            f"**Description:** {description}\n\n"
            f"This is appropriate because your form is {'good' if context.tsb > 0 else 'moderate' if context.tsb > -10 else 'low'} "
            f"and ACWR is {'optimal' if context.acwr <= 1.3 else 'elevated'}."
        )
        
        return CoachingResponse(
            intent=CoachingIntent.WORKOUT_REQUEST,
            message=message,
            recommended_workout={
                "type": workout_type,
                "duration_min": duration,
                "description": description,
            },
            recommended_intensity=intensity,
            cautions=self._generate_cautions(context),
        )
    
    def _generate_adjustment_sync(
        self,
        message: str,
        context: CoachingContext,
    ) -> CoachingResponse:
        """Generate adjustment recommendation synchronously."""
        message = (
            "I hear you. It's important to listen to your body. "
            f"Based on your current metrics (TSB: {context.tsb:.1f}), "
        )
        
        if context.tsb < -15 or context.acwr > 1.3:
            message += (
                "you're right to want to back off. I recommend either a rest day "
                "or a very easy active recovery session (20-30 min Zone 1). "
                "Recovery is when adaptation happens!"
            )
            intensity = "rest"
        else:
            message += (
                "while your metrics look okay, your subjective feeling matters a lot. "
                "Let's do an easy session today - we can always push harder when you're feeling better. "
                "A 30-minute easy run or ride would be perfect."
            )
            intensity = "easy"
        
        return CoachingResponse(
            intent=CoachingIntent.ADJUSTMENT_REQUEST,
            message=message,
            recommended_intensity=intensity,
            action_items=[
                "Take it easy today",
                "Get extra sleep tonight",
                "Check in tomorrow on how you feel",
            ],
        )
    
    def _generate_general_response_sync(
        self,
        message: str,
        context: CoachingContext,
    ) -> CoachingResponse:
        """Generate a general response synchronously."""
        return CoachingResponse(
            intent=CoachingIntent.GENERAL_QUESTION,
            message=(
                "That's a great question! Training is highly individual, but here are some general principles:\n\n"
                "1. **Progressive overload** - gradually increase training stress\n"
                "2. **Recovery matters** - adaptation happens during rest\n"
                "3. **Consistency** - regular training beats occasional hard efforts\n"
                "4. **Listen to your body** - fatigue and soreness are signals\n\n"
                f"Based on your current state (CTL: {context.ctl:.1f}, TSB: {context.tsb:.1f}), "
                f"you're in a {'good' if context.tsb > 0 else 'fatigued'} position. "
                "Would you like specific advice about your training?"
            ),
            follow_up_questions=[
                "What specific aspect of training would you like to discuss?",
                "Are you preparing for any particular event?",
            ],
        )
    
    def _generate_generic_feedback(self, context: CoachingContext) -> str:
        """Generate generic workout feedback."""
        if context.last_workout_load and context.last_workout_load > 80:
            return (
                "That was a solid session! The training load was significant, "
                "so make sure to prioritize recovery today. Good hydration, "
                "nutrition, and sleep will help you absorb the training."
            )
        else:
            return (
                "Nice work getting out there! Even easier sessions contribute "
                "to your fitness. These aerobic miles are the foundation of endurance."
            )
    
    def _determine_recommended_intensity(self, context: CoachingContext) -> str:
        """Determine recommended intensity based on context."""
        if context.acwr > 1.5:
            return "rest"
        elif context.acwr > 1.3 or context.tsb < -20:
            return "easy"
        elif context.tsb < -10 or context.consecutive_hard_days >= 2:
            return "moderate"
        elif context.tsb > 5:
            return "hard"
        else:
            return "moderate"
    
    def _generate_cautions(self, context: CoachingContext) -> List[str]:
        """Generate caution messages based on context."""
        cautions = []
        
        if context.acwr > 1.5:
            cautions.append("⚠️ ACWR is in danger zone (>1.5) - high injury risk")
        elif context.acwr > 1.3:
            cautions.append("⚠️ ACWR is elevated - reduce training load")
        
        if context.tsb < -20:
            cautions.append("⚠️ Significant accumulated fatigue - prioritize recovery")
        
        if context.consecutive_hard_days >= 3:
            cautions.append("⚠️ Multiple consecutive hard days - recovery day recommended")
        
        if context.upcoming_race_date:
            days_to_race = (context.upcoming_race_date - date.today()).days
            if days_to_race <= 7:
                cautions.append(f"🏁 Race in {days_to_race} days - taper phase")
        
        return cautions
    
    def _generate_action_items(self, intensity: str) -> List[str]:
        """Generate action items based on recommended intensity."""
        if intensity == "rest":
            return [
                "Complete rest or light stretching",
                "Focus on nutrition and hydration",
                "Get 8+ hours of sleep",
            ]
        elif intensity == "easy":
            return [
                "Keep heart rate in Zone 1-2",
                "Maintain conversational pace",
                "Log subjective feelings after",
            ]
        elif intensity == "moderate":
            return [
                "Warm up properly before intensity",
                "Stay within target zones",
                "Cool down and stretch after",
            ]
        else:
            return [
                "Warm up thoroughly (10-15 min)",
                "Execute the key intervals at target intensity",
                "Cool down and refuel within 30 minutes",
            ]
    
    def _interpret_metrics(self, context: CoachingContext) -> str:
        """Provide interpretation of current metrics."""
        if context.tsb > 15:
            return "You're very fresh - great time for a key workout or race!"
        elif context.tsb > 5:
            return "Good form - ready for quality training."
        elif context.tsb > -5:
            return "Balanced state - normal training appropriate."
        elif context.tsb > -15:
            return "Some fatigue accumulation - moderate intensity recommended."
        else:
            return "Significant fatigue - prioritize recovery over training."


# Singleton instance
_coach: Optional[ConversationalCoach] = None


def get_conversational_coach() -> ConversationalCoach:
    """Get the conversational coach singleton."""
    global _coach
    if _coach is None:
        _coach = ConversationalCoach()
    return _coach

