"""
Base agent class for LangGraph agents.

Provides common functionality for all agents in the trAIner App.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Generic, Optional, TypeVar

from langgraph.graph import StateGraph

from ..llm.providers import get_llm_client, LLMClient, ModelType


# Type variable for agent state
StateT = TypeVar("StateT")


@dataclass
class AgentMetrics:
    """Metrics collected during agent execution."""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    llm_calls: int = 0
    errors: int = 0

    def finish(self) -> None:
        """Mark the agent execution as finished."""
        self.end_time = datetime.now()

    @property
    def duration_seconds(self) -> float:
        """Get the duration of the agent execution in seconds."""
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "total_tokens": self.total_tokens,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "llm_calls": self.llm_calls,
            "errors": self.errors,
        }


class BaseAgent(ABC, Generic[StateT]):
    """
    Base class for LangGraph agents.

    Provides:
    - LLM client management
    - Metrics collection
    - Common utility methods
    - Graph building structure
    - User ID tracking for usage billing
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        model_type: ModelType = ModelType.SMART,
        user_id: Optional[str] = None,
    ):
        """
        Initialize the base agent.

        Args:
            llm_client: Optional LLM client. If not provided, uses default.
            model_type: Default model type for this agent (FAST or SMART).
            user_id: Optional user ID for usage tracking and billing.
        """
        self._llm_client = llm_client
        self._model_type = model_type
        self._user_id = user_id
        self._graph: Optional[StateGraph] = None
        self._metrics = AgentMetrics()

    @property
    def llm_client(self) -> LLMClient:
        """Lazy-load LLM client."""
        if self._llm_client is None:
            self._llm_client = get_llm_client()
        return self._llm_client

    @property
    def user_id(self) -> Optional[str]:
        """Get the user ID for usage tracking."""
        return self._user_id

    @user_id.setter
    def user_id(self, value: Optional[str]) -> None:
        """Set the user ID for usage tracking."""
        self._user_id = value

    @property
    def metrics(self) -> AgentMetrics:
        """Get current metrics."""
        return self._metrics

    def reset_metrics(self) -> None:
        """Reset metrics for a new run."""
        self._metrics = AgentMetrics()

    @property
    def graph(self) -> StateGraph:
        """Get or build the workflow graph."""
        if self._graph is None:
            self._graph = self._build_graph()
        return self._graph

    @abstractmethod
    def _build_graph(self) -> StateGraph:
        """
        Build the LangGraph workflow.

        Subclasses must implement this to define their workflow.

        Returns:
            Configured StateGraph
        """
        pass

    def _call_llm(
        self,
        messages: list,
        model_type: Optional[ModelType] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Call the LLM with metrics tracking.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model_type: Override default model type
            temperature: LLM temperature
            max_tokens: Max tokens for response

        Returns:
            LLM response text
        """
        self._metrics.llm_calls += 1

        model = model_type or self._model_type

        try:
            response = self.llm_client.chat(
                messages=messages,
                model_type=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Track token usage if available
            if hasattr(response, 'usage'):
                self._metrics.input_tokens += response.usage.get('prompt_tokens', 0)
                self._metrics.output_tokens += response.usage.get('completion_tokens', 0)
                self._metrics.total_tokens += response.usage.get('total_tokens', 0)

            return response.content

        except Exception as e:
            self._metrics.errors += 1
            raise

    async def _call_llm_async(
        self,
        messages: list,
        model_type: Optional[ModelType] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Async version of LLM call with metrics tracking.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model_type: Override default model type
            temperature: LLM temperature
            max_tokens: Max tokens for response

        Returns:
            LLM response text
        """
        self._metrics.llm_calls += 1

        model = model_type or self._model_type

        try:
            response = await self.llm_client.chat_async(
                messages=messages,
                model_type=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Track token usage if available
            if hasattr(response, 'usage'):
                self._metrics.input_tokens += response.usage.get('prompt_tokens', 0)
                self._metrics.output_tokens += response.usage.get('completion_tokens', 0)
                self._metrics.total_tokens += response.usage.get('total_tokens', 0)

            return response.content

        except Exception as e:
            self._metrics.errors += 1
            raise

    def _create_message(self, role: str, content: str) -> Dict[str, str]:
        """Create a message dict for LLM calls."""
        return {"role": role, "content": content}

    def _system_message(self, content: str) -> Dict[str, str]:
        """Create a system message."""
        return self._create_message("system", content)

    def _user_message(self, content: str) -> Dict[str, str]:
        """Create a user message."""
        return self._create_message("user", content)

    def _assistant_message(self, content: str) -> Dict[str, str]:
        """Create an assistant message."""
        return self._create_message("assistant", content)
