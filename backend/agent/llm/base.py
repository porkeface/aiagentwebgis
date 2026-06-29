"""Base LLM adapter interface and data classes.

Defines the abstract base class and data structures for LLM provider adapters.
All adapters must implement the BaseLLMAdapter interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator


@dataclass(frozen=True)
class ToolCall:
    """Represents a tool call made by the LLM.

    Attributes:
        id: Unique identifier for the tool call
        name: Name of the tool to invoke
        arguments: Arguments to pass to the tool
    """

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class LLMResponse:
    """Response from a non-streaming LLM call.

    Attributes:
        content: Text content from the LLM
        tool_calls: List of tool calls requested by the LLM
        usage: Token usage statistics
    """

    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class LLMChunk:
    """A chunk from a streaming LLM call.

    Attributes:
        content: Partial text content
        tool_call_delta: Partial tool call information (if any)
        is_done: Whether this is the final chunk
    """

    content: str = ""
    tool_call_delta: ToolCall | None = None
    is_done: bool = False


class BaseLLMAdapter(ABC):
    """Abstract base class for LLM provider adapters.

    All LLM adapters must implement chat() and stream() methods
    to provide a unified interface across different providers.
    """

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        """Send a chat request and return a complete response.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            tools: Optional list of tool schemas for function calling

        Returns:
            LLMResponse with content and/or tool_calls
        """
        pass

    @abstractmethod
    async def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[LLMChunk]:
        """Send a chat request and stream the response.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            tools: Optional list of tool schemas for function calling

        Yields:
            LLMChunk objects as they arrive from the LLM
        """
        pass
