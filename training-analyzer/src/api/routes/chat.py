"""Chat API routes for conversational AI training coach."""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import get_coach_service, get_training_db
from ...services.chat_service import (
    ChatService,
    ChatRequest,
    ChatResponse,
)
from ...agents.chat_agent import ChatAgent


router = APIRouter()
logger = logging.getLogger(__name__)


# ============================================================================
# Request/Response Models
# ============================================================================

class ChatMessageRequest(BaseModel):
    """Request body for sending a chat message."""
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The user's message or question",
        json_schema_extra={
            "examples": [
                "How was my training last week?",
                "Am I ready for my upcoming race?",
                "What's my fitness trend?",
                "Compare this week to last week",
            ]
        }
    )
    conversation_id: Optional[str] = Field(
        None,
        description="Optional conversation ID for maintaining context across messages",
    )


class ChatMessageResponse(BaseModel):
    """Response from the chat endpoint."""
    response: str = Field(..., description="The AI coach's response")
    data_sources: List[str] = Field(
        default_factory=list,
        description="Data sources used to generate the response",
    )
    intent: str = Field(
        default="general",
        description="The classified intent of the user's question",
    )
    conversation_id: str = Field(
        ...,
        description="Conversation ID for follow-up messages",
    )


class SuggestedQuestionsResponse(BaseModel):
    """Response with suggested questions."""
    questions: List[str] = Field(..., description="List of suggested questions")


class ConversationHistoryResponse(BaseModel):
    """Response with conversation history."""
    conversation_id: str
    messages: List[dict] = Field(default_factory=list)
    message_count: int


# ============================================================================
# Chat Service Dependency
# ============================================================================

# Singleton chat service and agent
_chat_service: Optional[ChatService] = None
_chat_agent: Optional[ChatAgent] = None


def get_chat_service_instance(
    coach_service=Depends(get_coach_service),
    training_db=Depends(get_training_db),
) -> ChatService:
    """Get the chat service instance."""
    global _chat_service, _chat_agent

    if _chat_agent is None:
        logger.info("Initializing ChatAgent...")
        try:
            _chat_agent = ChatAgent(
                coach_service=coach_service,
                training_db=training_db,
            )
            logger.info("ChatAgent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ChatAgent: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize chat agent: {str(e)}"
            )

    if _chat_service is None:
        logger.info("Initializing ChatService...")
        _chat_service = ChatService(
            chat_agent=_chat_agent,
            coach_service=coach_service,
            training_db=training_db,
        )
        logger.info("ChatService initialized successfully")

    return _chat_service


# ============================================================================
# API Routes
# ============================================================================

@router.post("", response_model=ChatMessageResponse)
async def send_message(
    request: ChatMessageRequest,
    chat_service: ChatService = Depends(get_chat_service_instance),
):
    """
    Send a message to the AI training coach and get a response.

    The chat interface allows natural language queries about training data:
    - "How was my training last week?"
    - "Am I ready for my upcoming race?"
    - "What's my fitness trend?"
    - "Compare this week to last week"
    - "What should I do for today's workout?"

    The AI uses your training data, fitness metrics, and goals to provide
    personalized, contextual responses.

    Args:
        request: ChatMessageRequest with the user's message

    Returns:
        ChatMessageResponse with the AI's response and metadata
    """
    logger.info(f"[chat] Processing message: {request.message[:50]}...")

    try:
        # Create internal request
        chat_request = ChatRequest(
            message=request.message,
            conversation_id=request.conversation_id,
        )

        # Process through service
        result = await chat_service.process_message(chat_request)

        logger.info(
            f"[chat] Response generated, intent={result.intent}, "
            f"sources={result.data_sources}"
        )

        return ChatMessageResponse(
            response=result.response,
            data_sources=result.data_sources,
            intent=result.intent,
            conversation_id=result.conversation_id or "",
        )

    except Exception as e:
        logger.error(f"[chat] Error processing message: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process chat message: {str(e)}"
        )


@router.get("/suggestions", response_model=SuggestedQuestionsResponse)
async def get_suggested_questions(
    chat_service: ChatService = Depends(get_chat_service_instance),
):
    """
    Get a list of suggested questions to help users get started.

    Returns common questions that work well with the AI coach.
    """
    questions = chat_service.get_suggested_questions()

    return SuggestedQuestionsResponse(questions=questions)


@router.get("/history/{conversation_id}", response_model=ConversationHistoryResponse)
async def get_conversation_history(
    conversation_id: str,
    chat_service: ChatService = Depends(get_chat_service_instance),
):
    """
    Get the conversation history for a specific conversation.

    Args:
        conversation_id: The conversation ID

    Returns:
        ConversationHistoryResponse with the message history
    """
    conversation = await chat_service.get_conversation_history(conversation_id)

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail=f"Conversation {conversation_id} not found"
        )

    messages = [
        {
            "role": msg.role,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat(),
        }
        for msg in conversation.messages
    ]

    return ConversationHistoryResponse(
        conversation_id=conversation_id,
        messages=messages,
        message_count=len(messages),
    )


@router.delete("/history/{conversation_id}")
async def clear_conversation_history(
    conversation_id: str,
    chat_service: ChatService = Depends(get_chat_service_instance),
):
    """
    Clear the conversation history for a specific conversation.

    Args:
        conversation_id: The conversation ID

    Returns:
        Success status
    """
    cleared = await chat_service.clear_conversation(conversation_id)

    return {
        "conversation_id": conversation_id,
        "cleared": cleared,
    }


@router.post("/new")
async def start_new_conversation(
    chat_service: ChatService = Depends(get_chat_service_instance),
):
    """
    Start a new conversation and get a conversation ID.

    This can be used to explicitly start a new conversation context.

    Returns:
        A new conversation ID
    """
    import uuid

    conversation_id = str(uuid.uuid4())

    return {
        "conversation_id": conversation_id,
        "message": "New conversation started. Use this ID for follow-up messages.",
    }
