"""
Chat Service for handling conversational AI interactions.

This service orchestrates:
- Message processing
- Context gathering
- Intent classification
- Response generation
- Conversation history management
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .base import BaseService, CacheProtocol
from ..agents.chat_agent import ChatAgent


class ChatMessage(BaseModel):
    """A single chat message."""
    role: str = Field(..., description="user or assistant")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatRequest(BaseModel):
    """Request for chat processing."""
    message: str = Field(..., min_length=1, max_length=2000)
    conversation_id: Optional[str] = Field(None, description="Optional conversation ID for context")
    language: str = Field(default="en", description="Language code for response (en, es)")


class ChatResponse(BaseModel):
    """Response from chat processing."""
    response: str = Field(..., description="The AI's response")
    data_sources: List[str] = Field(default_factory=list, description="Data sources used")
    intent: str = Field(default="general", description="Classified intent")
    chat_id: str = Field(..., description="Unique chat turn ID")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for follow-ups")


class ConversationContext(BaseModel):
    """Context for a conversation session."""
    conversation_id: str
    messages: List[ChatMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)


class ChatService(BaseService):
    """
    Service for managing chat interactions with the AI training coach.

    Features:
    - Message processing via ChatAgent
    - Conversation history tracking
    - Context management
    - Response formatting
    """

    # Maximum conversation history to maintain
    MAX_HISTORY_LENGTH = 10
    # Cache TTL for conversations (1 hour)
    CONVERSATION_TTL_SECONDS = 3600

    def __init__(
        self,
        chat_agent: Optional[ChatAgent] = None,
        coach_service: Any = None,
        training_db: Any = None,
        cache: Optional[CacheProtocol] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """
        Initialize the chat service.

        Args:
            chat_agent: Optional ChatAgent instance
            coach_service: CoachService for athlete context
            training_db: TrainingDatabase for data queries
            cache: Optional cache for conversation history
            logger: Optional logger instance
        """
        super().__init__(cache=cache, logger=logger)
        self._coach_service = coach_service
        self._training_db = training_db

        # Initialize or create chat agent
        if chat_agent:
            self._chat_agent = chat_agent
        else:
            self._chat_agent = ChatAgent(
                coach_service=coach_service,
                training_db=training_db,
            )

        # In-memory conversation store (for simplicity)
        # In production, this could be Redis or a database
        self._conversations: Dict[str, ConversationContext] = {}

    async def process_message(
        self,
        request: ChatRequest,
    ) -> ChatResponse:
        """
        Process a chat message and return a response.

        Args:
            request: ChatRequest with the user's message

        Returns:
            ChatResponse with the AI's response and metadata
        """
        # Get or create conversation context
        conversation_id = request.conversation_id or self._generate_conversation_id()
        conversation = await self._get_or_create_conversation(conversation_id)

        # Build conversation history for context
        history = self._build_history_for_agent(conversation)

        # Add user message to history
        user_message = ChatMessage(
            role="user",
            content=request.message,
        )
        conversation.messages.append(user_message)

        try:
            # Process through chat agent
            result = await self._chat_agent.chat(
                message=request.message,
                conversation_history=history,
                language=request.language,
            )

            # Add assistant response to history
            assistant_message = ChatMessage(
                role="assistant",
                content=result.get("response", ""),
            )
            conversation.messages.append(assistant_message)

            # Update conversation
            conversation.last_activity = datetime.utcnow()
            await self._save_conversation(conversation)

            # Trim history if too long
            self._trim_conversation_history(conversation)

            return ChatResponse(
                response=result.get("response", "I couldn't generate a response."),
                data_sources=result.get("data_sources", []),
                intent=result.get("intent", "general"),
                chat_id=result.get("chat_id", ""),
                conversation_id=conversation_id,
            )

        except Exception as e:
            self.logger.error(f"Chat processing error: {e}")

            # Return error response
            return ChatResponse(
                response=(
                    "I apologize, but I encountered an error processing your message. "
                    "Please try again or rephrase your question."
                ),
                data_sources=[],
                intent="error",
                chat_id="",
                conversation_id=conversation_id,
            )

    async def get_conversation_history(
        self,
        conversation_id: str,
    ) -> Optional[ConversationContext]:
        """
        Get conversation history by ID.

        Args:
            conversation_id: The conversation ID

        Returns:
            ConversationContext if found, None otherwise
        """
        return await self._get_conversation(conversation_id)

    async def clear_conversation(
        self,
        conversation_id: str,
    ) -> bool:
        """
        Clear a conversation's history.

        Args:
            conversation_id: The conversation ID

        Returns:
            True if cleared, False if not found
        """
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            await self._delete_from_cache(f"chat:conversation:{conversation_id}")
            return True
        return False

    def get_suggested_questions(self) -> List[str]:
        """
        Get a list of suggested questions for the user.

        Returns:
            List of example questions
        """
        return [
            "How was my training last week?",
            "Am I ready for my upcoming race?",
            "What's my fitness trend over the past month?",
            "Compare this week to last week",
            "What should I do for today's workout?",
            "Why am I feeling fatigued?",
            "How is my CTL progressing?",
            "What was my best workout this week?",
        ]

    # ========================================================================
    # Private Methods
    # ========================================================================

    def _generate_conversation_id(self) -> str:
        """Generate a unique conversation ID."""
        import uuid
        return str(uuid.uuid4())

    async def _get_or_create_conversation(
        self,
        conversation_id: str,
    ) -> ConversationContext:
        """Get existing conversation or create new one."""
        conversation = await self._get_conversation(conversation_id)

        if not conversation:
            conversation = ConversationContext(
                conversation_id=conversation_id,
            )
            self._conversations[conversation_id] = conversation

        return conversation

    async def _get_conversation(
        self,
        conversation_id: str,
    ) -> Optional[ConversationContext]:
        """Get conversation from memory or cache."""
        # Check memory first
        if conversation_id in self._conversations:
            return self._conversations[conversation_id]

        # Check cache
        cached = await self._get_from_cache(f"chat:conversation:{conversation_id}")
        if cached:
            try:
                conversation = ConversationContext(**cached)
                self._conversations[conversation_id] = conversation
                return conversation
            except Exception:
                pass

        return None

    async def _save_conversation(
        self,
        conversation: ConversationContext,
    ) -> None:
        """Save conversation to memory and cache."""
        self._conversations[conversation.conversation_id] = conversation

        # Save to cache
        await self._set_in_cache(
            f"chat:conversation:{conversation.conversation_id}",
            conversation.model_dump(mode="json"),
            self.CONVERSATION_TTL_SECONDS,
        )

    def _build_history_for_agent(
        self,
        conversation: ConversationContext,
    ) -> List[Dict[str, str]]:
        """Build conversation history in format expected by agent."""
        history = []
        for msg in conversation.messages[-self.MAX_HISTORY_LENGTH:]:
            history.append({
                "role": msg.role,
                "content": msg.content,
            })
        return history

    def _trim_conversation_history(
        self,
        conversation: ConversationContext,
    ) -> None:
        """Trim conversation history if too long."""
        if len(conversation.messages) > self.MAX_HISTORY_LENGTH:
            # Keep only the most recent messages
            conversation.messages = conversation.messages[-self.MAX_HISTORY_LENGTH:]


# ============================================================================
# Singleton Pattern
# ============================================================================

_chat_service: Optional[ChatService] = None


def get_chat_service(
    coach_service: Any = None,
    training_db: Any = None,
) -> ChatService:
    """
    Get or create the chat service singleton.

    Args:
        coach_service: Optional CoachService instance
        training_db: Optional TrainingDatabase instance

    Returns:
        ChatService instance
    """
    global _chat_service

    if _chat_service is None:
        _chat_service = ChatService(
            coach_service=coach_service,
            training_db=training_db,
        )

    return _chat_service


def reset_chat_service() -> None:
    """Reset the chat service singleton (for testing)."""
    global _chat_service
    _chat_service = None
