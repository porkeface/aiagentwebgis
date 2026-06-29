"""Ollama LLM adapter for local development.

Wraps langchain_ollama ChatOllama for running models locally.
"""

import uuid
from typing import Any, AsyncIterator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from agent.llm.base import BaseLLMAdapter, LLMChunk, LLMResponse, ToolCall


class OllamaAdapter(BaseLLMAdapter):
    """Ollama adapter for local model inference.

    Uses langchain_ollama ChatOllama for local development and testing.
    """

    def __init__(
        self,
        model: str = "qwen2.5:7b",
        base_url: str = "http://localhost:11434",
    ) -> None:
        """Initialize Ollama adapter.

        Args:
            model: Model name to use
            base_url: Ollama server URL
        """
        self.model = model
        self.base_url = base_url
        self._client = None

    def _get_client(self) -> Any:
        """Lazy-load and return the ChatOllama client."""
        if self._client is None:
            try:
                from langchain_ollama import ChatOllama
            except ImportError:
                raise ImportError(
                    "langchain_ollama is required for OllamaAdapter. "
                    "Install with: uv add langchain-ollama"
                )
            self._client = ChatOllama(
                model=self.model,
                base_url=self.base_url,
                temperature=0.3,
            )
        return self._client

    def _convert_messages(self, messages: list[dict[str, Any]]) -> list:
        """Convert dict messages to LangChain message objects."""
        lc_messages = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "user":
                lc_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
        return lc_messages

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        """Send chat request.

        Note: Ollama tool calling support varies by model.

        Args:
            messages: Conversation messages
            tools: Optional tool schemas (limited support)

        Returns:
            LLMResponse with content and/or tool_calls
        """
        client = self._get_client()
        lc_messages = self._convert_messages(messages)

        response = await client.ainvoke(lc_messages)
        return self._parse_response(response)

    async def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[LLMChunk]:
        """Stream chat response.

        Args:
            messages: Conversation messages
            tools: Optional tool schemas

        Yields:
            LLMChunk objects as they arrive
        """
        client = self._get_client()
        lc_messages = self._convert_messages(messages)

        async for chunk in client.astream(lc_messages):
            content = chunk.content if hasattr(chunk, "content") else str(chunk)
            yield LLMChunk(content=content, is_done=False)

        yield LLMChunk(is_done=True)

    def _parse_response(self, response: Any) -> LLMResponse:
        """Parse a LangChain response into LLMResponse."""
        content = response.content if hasattr(response, "content") else str(response)

        tool_calls = []
        if hasattr(response, "tool_calls") and response.tool_calls:
            for tc in response.tool_calls:
                if isinstance(tc, dict):
                    tool_call = ToolCall(
                        id=tc.get("id", f"call_{uuid.uuid4().hex[:8]}"),
                        name=tc.get("name", ""),
                        arguments=tc.get("args", {}),
                    )
                else:
                    tool_call = ToolCall(
                        id=getattr(tc, "id", f"call_{uuid.uuid4().hex[:8]}"),
                        name=getattr(tc, "name", ""),
                        arguments=getattr(tc, "args", {}),
                    )
                tool_calls.append(tool_call)

        usage = {}
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            usage = {
                "prompt_tokens": response.usage_metadata.get("input_tokens", 0),
                "completion_tokens": response.usage_metadata.get("output_tokens", 0),
                "total_tokens": response.usage_metadata.get("total_tokens", 0),
            }

        return LLMResponse(content=content, tool_calls=tool_calls, usage=usage)
