"""Emotional Support Messaging Service.

Provides contextual supportive messages based on athlete state and training context.
Designed to offer empathetic, supportive, and encouraging messages for different
training scenarios like red zone readiness, streak breaks, plateaus, and comebacks.
"""

import logging
import random
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class EmotionalContext(str, Enum):
    """Training contexts that trigger emotional support messages."""

    RED_ZONE_READINESS = "red_zone_readiness"
    STREAK_BREAK = "streak_break"
    PLATEAU = "plateau"
    BAD_WORKOUT = "bad_workout"
    COMEBACK = "comeback"
    CONSISTENCY_MILESTONE = "consistency_milestone"
    RECOVERY_DAY = "recovery_day"


class MessageTone(str, Enum):
    """Tone of the message."""

    EMPATHETIC = "empathetic"
    SUPPORTIVE = "supportive"
    ENCOURAGING = "encouraging"


class EmotionalMessage(BaseModel):
    """An emotional support message with metadata."""

    context: EmotionalContext = Field(..., description="The context that triggered this message")
    message: str = Field(..., description="The main supportive message")
    tone: MessageTone = Field(..., description="The emotional tone of the message")
    action_suggestion: Optional[str] = Field(None, description="Optional suggested action")
    recovery_tips: Optional[List[str]] = Field(None, description="Recovery tips for red zone/recovery contexts")
    alternative_activities: Optional[List[str]] = Field(None, description="Alternative activity suggestions")


# Message bank with multiple variations per context
MESSAGE_BANK: Dict[EmotionalContext, List[Dict[str, Any]]] = {
    EmotionalContext.RED_ZONE_READINESS: [
        {
            "message": "Your body is telling you something important. Rest isn't weakness - it's wisdom.",
            "tone": MessageTone.EMPATHETIC,
            "action_suggestion": "Consider a gentle walk or stretching today.",
            "recovery_tips": [
                "Prioritize sleep tonight",
                "Stay hydrated throughout the day",
                "Light stretching can help recovery"
            ],
            "alternative_activities": [
                "Gentle yoga",
                "Light walking",
                "Foam rolling",
                "Meditation"
            ]
        },
        {
            "message": "Your body is asking for rest. Listening to it is a sign of a smart athlete.",
            "tone": MessageTone.SUPPORTIVE,
            "action_suggestion": "Take today to recharge - you'll come back stronger.",
            "recovery_tips": [
                "Focus on quality nutrition",
                "Try a contrast shower (hot/cold)",
                "Elevate your legs for 10 minutes"
            ],
            "alternative_activities": [
                "Swimming (easy)",
                "Light stretching",
                "Breathwork",
                "Massage"
            ]
        },
        {
            "message": "Recovery is when adaptation happens. Your body is building strength right now.",
            "tone": MessageTone.ENCOURAGING,
            "action_suggestion": "Use this time to mentally prepare for your next session.",
            "recovery_tips": [
                "Get extra sleep if possible",
                "Consider an Epsom salt bath",
                "Protein-rich meal for recovery"
            ],
            "alternative_activities": [
                "Visualization exercises",
                "Mobility work",
                "Gentle cycling",
                "Reading about training"
            ]
        }
    ],
    EmotionalContext.STREAK_BREAK: [
        {
            "message": "Life happens. One day doesn't erase all your progress.",
            "tone": MessageTone.EMPATHETIC,
            "action_suggestion": "Start fresh tomorrow - your body remembers every workout."
        },
        {
            "message": "Missing a day is part of being human. What matters is getting back on track.",
            "tone": MessageTone.SUPPORTIVE,
            "action_suggestion": "Plan your next workout now to make it easier to start again."
        },
        {
            "message": "Consistency isn't about perfection - it's about getting back up. You've got this.",
            "tone": MessageTone.ENCOURAGING,
            "action_suggestion": "A short, easy session can help you feel back in the rhythm."
        }
    ],
    EmotionalContext.PLATEAU: [
        {
            "message": "Plateaus are your body consolidating gains. They often precede breakthroughs.",
            "tone": MessageTone.EMPATHETIC,
            "action_suggestion": "Trust the process - your next PR might be just around the corner."
        },
        {
            "message": "Progress isn't always linear. Your body is adapting in ways you can't see yet.",
            "tone": MessageTone.SUPPORTIVE,
            "action_suggestion": "Consider varying your training - sometimes change sparks growth."
        },
        {
            "message": "Every great athlete has faced plateaus. They're not walls - they're launching pads.",
            "tone": MessageTone.ENCOURAGING,
            "action_suggestion": "Focus on technique or try a different type of workout."
        }
    ],
    EmotionalContext.BAD_WORKOUT: [
        {
            "message": "Some days the legs just aren't there. That's normal and okay.",
            "tone": MessageTone.EMPATHETIC,
            "action_suggestion": "Rest well tonight - tomorrow is a new opportunity."
        },
        {
            "message": "One tough workout doesn't define your fitness. It's just one data point.",
            "tone": MessageTone.SUPPORTIVE,
            "action_suggestion": "Reflect on possible factors: sleep, nutrition, stress."
        },
        {
            "message": "Even the pros have off days. What separates them is showing up anyway.",
            "tone": MessageTone.ENCOURAGING,
            "action_suggestion": "Give yourself credit for putting in the effort."
        }
    ],
    EmotionalContext.COMEBACK: [
        {
            "message": "Every champion has comebacks. This is your story.",
            "tone": MessageTone.ENCOURAGING,
            "action_suggestion": "Start slow and build gradually - your body will remember."
        },
        {
            "message": "Welcome back. Your past fitness is still there - let's bring it out again.",
            "tone": MessageTone.SUPPORTIVE,
            "action_suggestion": "Ease into training - patience now means faster progress later."
        },
        {
            "message": "The hardest part of a comeback is starting. You've already done that.",
            "tone": MessageTone.EMPATHETIC,
            "action_suggestion": "Celebrate this moment - you're back in the game."
        }
    ],
    EmotionalContext.CONSISTENCY_MILESTONE: [
        {
            "message": "Showing up is the hardest part. You've mastered it.",
            "tone": MessageTone.ENCOURAGING,
            "action_suggestion": "Keep this momentum going - you're building an unshakeable habit."
        },
        {
            "message": "Consistency beats intensity every time. You're proving that.",
            "tone": MessageTone.SUPPORTIVE,
            "action_suggestion": "Your dedication is inspiring. Keep showing up for yourself."
        },
        {
            "message": "Day after day, you've chosen to prioritize your health. That's powerful.",
            "tone": MessageTone.EMPATHETIC,
            "action_suggestion": "Take a moment to appreciate how far you've come."
        }
    ],
    EmotionalContext.RECOVERY_DAY: [
        {
            "message": "Recovery isn't falling behind - it's building strength.",
            "tone": MessageTone.EMPATHETIC,
            "action_suggestion": "Use this time for mobility work or mental preparation.",
            "recovery_tips": [
                "Light stretching helps circulation",
                "Stay active without taxing your system",
                "Mental rehearsal is training too"
            ],
            "alternative_activities": [
                "Easy walking",
                "Yoga",
                "Swimming",
                "Foam rolling"
            ]
        },
        {
            "message": "Rest is training too. Your body is adapting and getting stronger.",
            "tone": MessageTone.SUPPORTIVE,
            "action_suggestion": "Enjoy this recovery - you've earned it.",
            "recovery_tips": [
                "Focus on quality sleep",
                "Nutrition supports recovery",
                "Stay hydrated"
            ],
            "alternative_activities": [
                "Gentle stretching",
                "Light cycling",
                "Meditation",
                "Nature walk"
            ]
        },
        {
            "message": "Active recovery accelerates your progress. Embrace the slower pace.",
            "tone": MessageTone.ENCOURAGING,
            "action_suggestion": "Try something gentle that brings you joy.",
            "recovery_tips": [
                "Movement promotes blood flow",
                "Don't skip sleep",
                "Protein aids muscle repair"
            ],
            "alternative_activities": [
                "Easy swim",
                "Mobility routine",
                "Light hike",
                "Dance"
            ]
        }
    ]
}


class EmotionalMessagingService:
    """Service for providing contextual emotional support messages."""

    def __init__(self):
        """Initialize the emotional messaging service."""
        self._logger = logger

    def get_contextual_message(
        self,
        context: EmotionalContext,
        include_tips: bool = True,
        preferred_tone: Optional[MessageTone] = None
    ) -> EmotionalMessage:
        """
        Get an appropriate emotional support message based on context.

        Args:
            context: The training context triggering the message
            include_tips: Whether to include recovery tips/alternatives
            preferred_tone: Optional preferred tone for the message

        Returns:
            EmotionalMessage with supportive content
        """
        messages = MESSAGE_BANK.get(context, [])

        if not messages:
            # Fallback message
            self._logger.warning(f"No messages found for context: {context}")
            return EmotionalMessage(
                context=context,
                message="You're doing great. Keep going.",
                tone=MessageTone.SUPPORTIVE
            )

        # Filter by preferred tone if specified
        if preferred_tone:
            filtered = [m for m in messages if m.get("tone") == preferred_tone]
            if filtered:
                messages = filtered

        # Select random message for variety
        selected = random.choice(messages)

        return EmotionalMessage(
            context=context,
            message=selected["message"],
            tone=selected["tone"],
            action_suggestion=selected.get("action_suggestion"),
            recovery_tips=selected.get("recovery_tips") if include_tips else None,
            alternative_activities=selected.get("alternative_activities") if include_tips else None
        )

    def get_all_messages_for_context(
        self,
        context: EmotionalContext
    ) -> List[EmotionalMessage]:
        """
        Get all available messages for a given context.

        Useful for UI to show rotation or let user choose.

        Args:
            context: The training context

        Returns:
            List of all messages for the context
        """
        messages = MESSAGE_BANK.get(context, [])

        return [
            EmotionalMessage(
                context=context,
                message=m["message"],
                tone=m["tone"],
                action_suggestion=m.get("action_suggestion"),
                recovery_tips=m.get("recovery_tips"),
                alternative_activities=m.get("alternative_activities")
            )
            for m in messages
        ]

    def get_recovery_message(
        self,
        readiness_score: float
    ) -> Optional[EmotionalMessage]:
        """
        Get a recovery-focused message based on readiness score.

        Args:
            readiness_score: Current readiness score (0-100)

        Returns:
            EmotionalMessage if readiness is in red zone, None otherwise
        """
        if readiness_score < 40:
            # Red zone - needs rest
            return self.get_contextual_message(EmotionalContext.RED_ZONE_READINESS)
        elif readiness_score < 60:
            # Yellow zone - recovery focus
            return self.get_contextual_message(EmotionalContext.RECOVERY_DAY)

        return None

    def detect_context_from_data(
        self,
        readiness_score: Optional[float] = None,
        current_streak: Optional[int] = None,
        previous_streak: Optional[int] = None,
        days_since_last_workout: Optional[int] = None,
        weeks_without_improvement: Optional[int] = None,
        last_workout_score: Optional[float] = None,
        days_since_comeback: Optional[int] = None,
        consecutive_training_days: Optional[int] = None
    ) -> Optional[EmotionalContext]:
        """
        Detect the appropriate emotional context from athlete data.

        Args:
            readiness_score: Current readiness score (0-100)
            current_streak: Current workout streak in days
            previous_streak: Previous streak before break
            days_since_last_workout: Days since last logged workout
            weeks_without_improvement: Weeks without PR or improvement
            last_workout_score: Score of the most recent workout (0-100)
            days_since_comeback: Days since returning from a break
            consecutive_training_days: Days of consecutive training

        Returns:
            Detected EmotionalContext or None if no special context
        """
        # Priority order for context detection

        # 1. Red zone readiness is highest priority
        if readiness_score is not None and readiness_score < 40:
            return EmotionalContext.RED_ZONE_READINESS

        # 2. Streak break detection
        if (current_streak == 0 and
            previous_streak is not None and
            previous_streak >= 7):
            return EmotionalContext.STREAK_BREAK

        # 3. Comeback detection
        if (days_since_comeback is not None and
            days_since_comeback <= 7 and
            days_since_last_workout is not None and
            days_since_last_workout > 14):
            return EmotionalContext.COMEBACK

        # 4. Bad workout detection
        if (last_workout_score is not None and
            last_workout_score < 50):
            return EmotionalContext.BAD_WORKOUT

        # 5. Plateau detection
        if (weeks_without_improvement is not None and
            weeks_without_improvement >= 3):
            return EmotionalContext.PLATEAU

        # 6. Consistency milestone detection
        if consecutive_training_days is not None:
            milestones = [7, 14, 21, 30, 60, 90, 180, 365]
            if consecutive_training_days in milestones:
                return EmotionalContext.CONSISTENCY_MILESTONE

        # 7. Recovery day detection
        if (readiness_score is not None and
            readiness_score >= 40 and
            readiness_score < 60):
            return EmotionalContext.RECOVERY_DAY

        return None


# Singleton instance
_service_instance: Optional[EmotionalMessagingService] = None


def get_emotional_messaging_service() -> EmotionalMessagingService:
    """Get the emotional messaging service singleton instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = EmotionalMessagingService()
    return _service_instance
