"""OpenAI LLM adapter.

Wraps langchain_openai ChatOpenAI for GPT-4 and other OpenAI models.
"""

import uuid
from typing import Any, AsyncIterator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from agent.llm.base import BaseLLMAdapter, LLMChunk, LLMResponse, ToolCall


class OpenAIAdapter(BaseLLMAdapter):
    """OpenAI adapter for GPT models.

    Uses langchain_openai ChatOpenAI with native tool calling support.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        base_url: str | None = None,
    ) -> None:
        """Initialize OpenAI adapter.

        Args:
            api_key: OpenAI API key
            model: Model name to use
            base_url: Optional custom API endpoint
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self._client = None

    def _get_client(self) -> Any:
        """Lazy-load and return the ChatOpenAI client."""
        if self._client is None:
            try:
                from langchain_openai import ChatOpenAI
            except ImportError:
                raise ImportError(
                    "langchain_openai is required for OpenAIAdapter. "
                    "Install with: uv add langchain-openai"
                )
            kwargs = {
                "model": self.model,
                "api_key": self.api_key,
                "temperature": 0.3,
            }
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = ChatOpenAI(**kwargs)
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
        """Send chat request with native tool calling.

        Args:
            messages: Conversation messages
            tools: Optional tool schemas

        Returns:
            LLMResponse with content and/or tool_calls
        """
        client = self._get_client()
        lc_messages = self._convert_messages(messages)

        if tools:
            # Bind tools to the model for native function calling
            client = client.bind(tools=tools)

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

        if tools:
            client = client.bind(tools=tools)

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
