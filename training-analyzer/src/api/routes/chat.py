"""Chat API routes for conversational AI training coach."""

import json
import logging
import uuid
from enum import Enum
from typing import AsyncGenerator, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..deps import get_coach_service, get_training_db, get_current_user, CurrentUser, get_consent_service_dep
from ..middleware.rate_limit import limiter, RATE_LIMIT_AI
from ..middleware.quota import require_quota
from ...services.chat_service import (
    ChatService,
    ChatRequest,
    ChatResponse,
)
from ...agents.chat_agent import ChatAgent
from ...agents.langchain_agent import get_langchain_agent, StreamEvent
from ...db.repositories.ai_usage_repository import get_ai_usage_repository
from ...observability.langfuse_config import get_langfuse_callback, is_langfuse_enabled
from ...observability.scoring import score_response_quality
from ...llm.prompt_sanitizer import sanitize_prompt, get_user_warning


router = APIRouter()
logger = logging.getLogger(__name__)


# ============================================================================
# Error Classification and User-Friendly Messages
# ============================================================================

class ChatErrorType(str, Enum):
    """Classification of chat errors for user-friendly messaging."""
    RATE_LIMITED = "rate_limited"
    QUOTA_EXCEEDED = "quota_exceeded"
    AI_UNAVAILABLE = "ai_unavailable"
    NO_TRAINING_DATA = "no_training_data"
    CONTEXT_ERROR = "context_error"
    TOOL_FAILURE = "tool_failure"
    NETWORK_ERROR = "network_error"
    UNKNOWN = "unknown"


def classify_error(error: Exception) -> tuple[ChatErrorType, str]:
    """Classify an error and return a user-friendly message.

    Returns:
        Tuple of (error_type, user_friendly_message)
    """
    error_str = str(error).lower()

    # Rate limiting errors
    if "rate" in error_str and "limit" in error_str:
        return (
            ChatErrorType.RATE_LIMITED,
            "You're sending messages too quickly. Please wait a moment and try again."
        )

    # Quota exceeded
    if "quota" in error_str or "exceeded" in error_str:
        return (
            ChatErrorType.QUOTA_EXCEEDED,
            "You've reached your AI usage limit for today. Please try again tomorrow or upgrade your plan."
        )

    # AI/LLM unavailable
    if any(term in error_str for term in ["api key", "anthropic", "openai", "llm", "model"]):
        return (
            ChatErrorType.AI_UNAVAILABLE,
            "The AI service is temporarily unavailable. Please try again in a few minutes."
        )

    # No training data
    if any(term in error_str for term in ["no data", "no training", "no workouts", "empty"]):
        return (
            ChatErrorType.NO_TRAINING_DATA,
            "I don't have enough training data to answer this question. Try syncing your workouts first."
        )

    # Context/service errors
    if any(term in error_str for term in ["coach", "context", "profile"]):
        return (
            ChatErrorType.CONTEXT_ERROR,
            "I couldn't load your training context. Please refresh the page and try again."
        )

    # Tool/function errors
    if any(term in error_str for term in ["tool", "function", "query"]):
        return (
            ChatErrorType.TOOL_FAILURE,
            "I had trouble accessing your training data. Please try rephrasing your question."
        )

    # Network errors
    if any(term in error_str for term in ["connection", "timeout", "network", "refused"]):
        return (
            ChatErrorType.NETWORK_ERROR,
            "A connection error occurred. Please check your internet and try again."
        )

    # Default unknown error
    return (
        ChatErrorType.UNKNOWN,
        "I encountered an unexpected error. Please try again or rephrase your question."
    )


def create_error_response(
    error: Exception,
    session_id: str,
    include_details: bool = False,
) -> dict:
    """Create a structured error response with user-friendly messaging.

    Args:
        error: The exception that occurred
        session_id: The conversation session ID
        include_details: Whether to include technical details (for debugging)

    Returns:
        Dict suitable for ChatMessageResponse or SSE error event
    """
    error_type, user_message = classify_error(error)

    response = {
        "error_type": error_type.value,
        "message": user_message,
    }

    if include_details:
        response["details"] = str(error)

    return response


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
    language: str = Field(
        default="en",
        description="Language code for the response (en=English, es=Spanish)",
        json_schema_extra={
            "examples": ["en", "es"]
        }
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
    # Agentic mode fields (optional)
    tools_used: Optional[List[str]] = Field(
        default=None,
        description="Tools used by the agentic AI (only in agentic mode)",
    )
    token_usage: Optional[dict] = Field(
        default=None,
        description="Token usage stats (only in agentic mode)",
    )
    trace_id: Optional[str] = Field(
        default=None,
        description="Langfuse trace ID for debugging (only in agentic mode)",
    )
    is_agentic: bool = Field(
        default=False,
        description="Whether this response was generated in agentic mode",
    )
    # Error handling fields (optional - only present when error occurred)
    error_type: Optional[str] = Field(
        default=None,
        description="Type of error if one occurred (rate_limited, quota_exceeded, ai_unavailable, etc.)",
    )
    has_error: bool = Field(
        default=False,
        description="Whether an error occurred during processing",
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
    current_user: CurrentUser = Depends(require_quota("chat")),
    coach_service=Depends(get_coach_service),
    training_db=Depends(get_training_db),
) -> ChatService:
    """Get the chat service instance."""
    global _chat_service, _chat_agent

    # Get user_id for usage tracking
    user_id = current_user.id

    if _chat_agent is None:
        logger.info("Initializing ChatAgent...")
        try:
            _chat_agent = ChatAgent(
                coach_service=coach_service,
                training_db=training_db,
                user_id=user_id,
            )
            logger.info("ChatAgent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ChatAgent: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to initialize chat agent. Please try again later."
            )
    else:
        # Update user_id on each request
        _chat_agent.user_id = user_id

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
@limiter.limit(RATE_LIMIT_AI)
async def send_message(
    request: Request,
    chat_request: ChatMessageRequest,
    use_agentic: bool = Query(
        False,
        description="Use agentic LangChain mode with tool calling for dynamic data access",
    ),
    stream: bool = Query(
        False,
        description="Enable SSE streaming mode. When true, returns StreamingResponse with real-time events.",
    ),
    current_user: CurrentUser = Depends(require_quota("chat")),
    coach_service=Depends(get_coach_service),
    training_db=Depends(get_training_db),
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

    Query Parameters:
        use_agentic: If True, uses the new LangChain agent with tool calling
                     for dynamic data access and Langfuse tracing.
        stream: If True, returns SSE streaming response. Implies use_agentic=True.
                Use POST /api/chat/stream for a dedicated streaming endpoint.

    Args:
        request: ChatMessageRequest with the user's message

    Returns:
        ChatMessageResponse with the AI's response and metadata
        OR StreamingResponse with SSE events if stream=true
    """
    # If streaming is requested, delegate to the stream endpoint
    if stream:
        return await send_message_stream(
            request_obj=request_obj,
            request=request,
            current_user=current_user,
            coach_service=coach_service,
            training_db=training_db,
        )

    logger.info(f"[chat] Processing message: {chat_request.message[:50]}... (agentic={use_agentic})")

    user_id = current_user.id
    session_id = chat_request.conversation_id or str(uuid.uuid4())

    # =========================================================================
    # CONSENT CHECK: Verify user has consented to LLM data sharing
    # =========================================================================
    consent_service = get_consent_service_dep()
    if not consent_service.check_llm_consent(user_id):
        raise HTTPException(
            status_code=403,
            detail="LLM data sharing consent required. Please accept the data sharing agreement to use AI features."
        )

    # =========================================================================
    # PROMPT SANITIZATION: Detect and log potential injection patterns
    # =========================================================================
    sanitization_result = sanitize_prompt(
        message=chat_request.message,
        user_id=user_id,
        session_id=session_id,
        log_suspicious=True,
    )

    # Log sanitization result for monitoring (non-blocking)
    if sanitization_result.is_suspicious:
        logger.info(
            f"[chat] Sanitization result: risk={sanitization_result.risk_level.value}, "
            f"patterns={sanitization_result.patterns_detected}"
        )

    # =========================================================================
    # AGENTIC MODE: Use LangChain agent with tool calling
    # =========================================================================
    if use_agentic:
        try:
            # Get the LangChain agent
            agent = get_langchain_agent(
                coach_service=coach_service,
                training_db=training_db,
                user_id=user_id,
            )

            # Process through the agentic agent
            result = await agent.chat(
                message=chat_request.message,
                chat_history=[],  # TODO: Load from conversation history if needed
                session_id=session_id,
                language=chat_request.language or "en",
            )

            # Log token usage to ai_usage_logs
            try:
                usage_repo = get_ai_usage_repository()
                token_usage = result.get("token_usage", {})
                usage_repo.log_usage(
                    request_id=str(uuid.uuid4()),
                    user_id=user_id,
                    model_id=result.get("model", "claude-sonnet-4-20250514"),
                    input_tokens=token_usage.get("input_tokens", 0),
                    output_tokens=token_usage.get("output_tokens", 0),
                    total_cost_cents=0.0,  # Cost calculated by repository
                    analysis_type="chat_agentic",
                    duration_ms=result.get("duration_ms"),
                    model_type="smart",
                    status="completed" if not result.get("error") else "failed",
                    error_message=result.get("error"),
                )
            except Exception as e:
                logger.warning(f"[chat] Failed to log agentic usage: {e}")

            # Score the response quality (if Langfuse enabled)
            trace_id = result.get("trace_id")
            if trace_id and is_langfuse_enabled():
                try:
                    score_response_quality(
                        trace_id=trace_id,
                        response=result.get("response", ""),
                        tools_used=result.get("tools_used", []),
                    )
                except Exception as e:
                    logger.warning(f"[chat] Failed to score response: {e}")

            logger.info(
                f"[chat] Agentic response generated, tools={result.get('tools_used', [])}, "
                f"tokens={result.get('token_usage', {}).get('total_tokens', 0)}"
            )

            return ChatMessageResponse(
                response=result.get("response", ""),
                data_sources=result.get("tools_used", []),
                intent="agentic",
                conversation_id=session_id,
                tools_used=result.get("tools_used"),
                token_usage=result.get("token_usage"),
                trace_id=trace_id,
                is_agentic=True,
            )

        except Exception as e:
            logger.error(f"[chat] Error in agentic mode: {e}", exc_info=True)

            # Classify error and create user-friendly response
            error_info = create_error_response(e, session_id)

            # Return a response with error info instead of raising HTTPException
            # This allows the frontend to show a more helpful message
            return ChatMessageResponse(
                response=error_info["message"],
                data_sources=[],
                intent="error",
                conversation_id=session_id,
                is_agentic=True,
                error_type=error_info["error_type"],
                has_error=True,
            )

    # =========================================================================
    # STANDARD MODE: Use existing ChatService
    # =========================================================================
    try:
        # Get the standard chat service
        chat_service = get_chat_service_instance(
            current_user=current_user,
            coach_service=coach_service,
            training_db=training_db,
        )

        # Create internal request
        chat_request = ChatRequest(
            message=chat_request.message,
            conversation_id=chat_request.conversation_id,
            language=chat_request.language,
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
            is_agentic=False,
        )

    except Exception as e:
        logger.error(f"[chat] Error processing message: {e}", exc_info=True)

        # Classify error and create user-friendly response
        error_info = create_error_response(e, session_id)

        return ChatMessageResponse(
            response=error_info["message"],
            data_sources=[],
            intent="error",
            conversation_id=session_id,
            is_agentic=False,
            error_type=error_info["error_type"],
            has_error=True,
        )


# ============================================================================
# Streaming Chat Endpoint
# ============================================================================

@router.post("/stream")
@limiter.limit(RATE_LIMIT_AI)
async def send_message_stream(
    request: Request,
    chat_request: ChatMessageRequest,
    current_user: CurrentUser = Depends(require_quota("chat")),
    coach_service=Depends(get_coach_service),
    training_db=Depends(get_training_db),
):
    """
    Send a message to the AI training coach with Server-Sent Events (SSE) streaming.

    This endpoint streams the response in real-time as the AI generates it.
    Uses the agentic LangChain mode with tool calling.

    Event Types:
        - status: Initial status message (e.g., "Thinking...")
        - tool_start: When a tool call begins (includes tool name and message)
        - tool_end: When a tool call completes
        - token: Each token of the response content
        - done: Final event with metadata (tools_used, token_usage)
        - error: If an error occurs

    SSE Format:
        data: {"type": "status", "message": "Thinking..."}

        data: {"type": "tool_start", "tool": "get_athlete_profile", "message": "Fetching athlete profile..."}

        data: {"type": "tool_end", "tool": "get_athlete_profile"}

        data: {"type": "token", "content": "Based on"}

        data: {"type": "token", "content": " your data"}

        data: {"type": "done", "tools_used": ["get_athlete_profile"], "token_usage": {...}}

    Args:
        request: ChatMessageRequest with the user's message

    Returns:
        StreamingResponse with SSE events
    """
    logger.info(f"[chat/stream] Processing message: {chat_request.message[:50]}...")

    user_id = current_user.id
    session_id = chat_request.conversation_id or str(uuid.uuid4())

    # =========================================================================
    # CONSENT CHECK: Verify user has consented to LLM data sharing
    # =========================================================================
    consent_service = get_consent_service_dep()
    if not consent_service.check_llm_consent(user_id):
        raise HTTPException(
            status_code=403,
            detail="LLM data sharing consent required. Please accept the data sharing agreement to use AI features."
        )

    # =========================================================================
    # PROMPT SANITIZATION: Detect and log potential injection patterns
    # =========================================================================
    sanitization_result = sanitize_prompt(
        message=chat_request.message,
        user_id=user_id,
        session_id=session_id,
        log_suspicious=True,
    )

    # Log sanitization result for monitoring (non-blocking)
    if sanitization_result.is_suspicious:
        logger.info(
            f"[chat/stream] Sanitization result: risk={sanitization_result.risk_level.value}, "
            f"patterns={sanitization_result.patterns_detected}"
        )

    async def generate_events() -> AsyncGenerator[str, None]:
        """Generate SSE events from the agent stream."""
        try:
            # Get the LangChain agent
            agent = get_langchain_agent(
                coach_service=coach_service,
                training_db=training_db,
                user_id=user_id,
            )

            # Track token usage for quota logging
            final_token_usage = {}
            final_tools_used = []

            # Stream events from the agent
            async for event in agent.chat_stream(
                message=chat_request.message,
                chat_history=[],  # TODO: Load from conversation history if needed
                session_id=session_id,
                language=chat_request.language or "en",
            ):
                # Convert StreamEvent to SSE format
                event_data = event.to_dict()
                yield f"data: {json.dumps(event_data)}\n\n"

                # Capture final metadata from done event
                if event.type == "done":
                    final_token_usage = event.token_usage or {}
                    final_tools_used = event.tools_used or []

                    # Log token usage to ai_usage_logs
                    try:
                        usage_repo = get_ai_usage_repository()
                        usage_repo.log_usage(
                            request_id=str(uuid.uuid4()),
                            user_id=user_id,
                            model_id="claude-sonnet-4-20250514",
                            input_tokens=final_token_usage.get("input_tokens", 0),
                            output_tokens=final_token_usage.get("output_tokens", 0),
                            total_cost_cents=0.0,  # Cost calculated by repository
                            analysis_type="chat_agentic_stream",
                            duration_ms=None,  # Duration not tracked in streaming
                            model_type="smart",
                            status="completed",
                            error_message=None,
                        )
                    except Exception as e:
                        logger.warning(f"[chat/stream] Failed to log usage: {e}")

                    # Score the response quality (if Langfuse enabled)
                    trace_id = event.trace_id
                    if trace_id and is_langfuse_enabled():
                        try:
                            # We don't have the full response here, but can still score
                            score_response_quality(
                                trace_id=trace_id,
                                response="",  # Response streamed, not available
                                tools_used=final_tools_used,
                            )
                        except Exception as e:
                            logger.warning(f"[chat/stream] Failed to score response: {e}")

                elif event.type == "error":
                    # Log error usage
                    try:
                        usage_repo = get_ai_usage_repository()
                        usage_repo.log_usage(
                            request_id=str(uuid.uuid4()),
                            user_id=user_id,
                            model_id="claude-sonnet-4-20250514",
                            input_tokens=0,
                            output_tokens=0,
                            total_cost_cents=0.0,
                            analysis_type="chat_agentic_stream",
                            duration_ms=None,
                            model_type="smart",
                            status="failed",
                            error_message=event.error,
                        )
                    except Exception as e:
                        logger.warning(f"[chat/stream] Failed to log error usage: {e}")

            # Send final [DONE] marker
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"[chat/stream] Error in stream: {e}", exc_info=True)

            # Classify error and create user-friendly response
            error_info = create_error_response(e, session_id)

            error_event = {
                "type": "error",
                "error": error_info["error_type"],
                "message": error_info["message"],
            }
            yield f"data: {json.dumps(error_event)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable proxy buffering
            "X-Conversation-Id": session_id,  # Include conversation ID in headers
        },
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
    conversation_id = str(uuid.uuid4())

    return {
        "conversation_id": conversation_id,
        "message": "New conversation started. Use this ID for follow-up messages.",
    }
