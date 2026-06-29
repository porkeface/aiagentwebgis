"""Tongyi (通义千问) LLM adapter with fallback tool calling.

Supports both native tool_call format and prompt-based JSON extraction
for models that don't support structured function calling.

Includes retry logic for timeout and connection errors.
"""

import asyncio
import json
import logging
import re
import uuid
from typing import Any, AsyncIterator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from agent.llm.base import BaseLLMAdapter, LLMChunk, LLMResponse, ToolCall

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 2
RETRY_BACKOFF_BASE = 1.0  # seconds


class TongyiAdapter(BaseLLMAdapter):
    """Tongyi (DashScope) adapter with fallback mechanism.

    Attempts native tool calling first, falls back to prompt-based
    JSON extraction if the model doesn't support structured calls.
    """

    def __init__(self, api_key: str, model: str = "qwen-plus") -> None:
        """Initialize Tongyi adapter.

        Args:
            api_key: DashScope API key
            model: Model name to use
        """
        self.api_key = api_key
        self.model = model
        self._client = None

    def _get_client(self) -> Any:
        """Lazy-load and return the ChatTongyi client."""
        if self._client is None:
            try:
                from langchain_community.chat_models import ChatTongyi
            except ImportError:
                raise ImportError(
                    "langchain_community is required for TongyiAdapter. "
                    "Install with: uv add langchain-community"
                )
            self._client = ChatTongyi(
                model=self.model,
                dashscope_api_key=self.api_key,
                temperature=0.3,
            )
        return self._client

    def _convert_messages(self, messages: list[dict[str, Any]]) -> list:
        """Convert dict messages to LangChain message objects.

        Args:
            messages: List of dicts with 'role' and 'content' keys

        Returns:
            List of LangChain message objects
        """
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

    def _format_tools_as_prompt(self, tools: list[dict[str, Any]]) -> str:
        """Convert tool schemas to text descriptions for prompt injection.

        Args:
            tools: List of tool schema dicts

        Returns:
            Formatted string describing available tools
        """
        lines = ["You have access to the following tools:\n"]
        for tool in tools:
            name = tool.get("name", "")
            description = tool.get("description", "")
            params = tool.get("parameters", {})
            properties = params.get("properties", {})
            required = params.get("required", [])

            lines.append(f"Tool: {name}")
            lines.append(f"Description: {description}")
            if properties:
                lines.append("Parameters:")
                for param_name, param_info in properties.items():
                    req_marker = " (required)" if param_name in required else ""
                    param_type = param_info.get("type", "any")
                    param_desc = param_info.get("description", "")
                    lines.append(f"  - {param_name} ({param_type}){req_marker}: {param_desc}")
            lines.append("")

        lines.append(
            'To use a tool, respond with a JSON object in this format:\n'
            '```json\n'
            '{"tool": "tool_name", "args": {"param1": "value1"}}\n'
            '```\n'
            "You can call multiple tools by including multiple JSON objects."
        )
        return "\n".join(lines)

    def _parse_tool_calls_from_text(self, text: str) -> list[ToolCall]:
        """Extract tool calls from text containing JSON.

        Args:
            text: Text that may contain JSON tool calls

        Returns:
            List of ToolCall objects extracted from the text
        """
        tool_calls = []
        # Match JSON objects with "tool" and "args" keys
        # Pattern: {"tool": "...", "args": {...}}
        pattern = r'\{[^{}]*"tool"\s*:\s*"[^"]+"\s*,\s*"args"\s*:\s*\{[^{}]*\}[^{}]*\}'
        matches = re.finditer(pattern, text, re.DOTALL)

        for match in matches:
            try:
                data = json.loads(match.group())
                if "tool" in data and "args" in data:
                    tool_call = ToolCall(
                        id=f"call_{uuid.uuid4().hex[:8]}",
                        name=data["tool"],
                        arguments=data["args"],
                    )
                    tool_calls.append(tool_call)
            except (json.JSONDecodeError, KeyError):
                # Skip invalid JSON, continue parsing
                continue

        return tool_calls

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        """Send chat request with tool call fallback and retry logic.

        Attempts native tool calling first. If no tool calls are returned
        but tools were provided, falls back to prompt-based extraction.
        Retries once on timeout/connection errors before returning friendly error.

        Args:
            messages: Conversation messages
            tools: Optional tool schemas

        Returns:
            LLMResponse with content and/or tool_calls
        """
        client = self._get_client()
        lc_messages = self._convert_messages(messages)

        last_error: Exception | None = None

        # Retry loop for timeout/connection errors
        for attempt in range(MAX_RETRIES):
            try:
                # Try native tool calling first
                if tools:
                    try:
                        response = await client.ainvoke(lc_messages, tools=tools)
                        return self._parse_response(response)
                    except Exception:
                        # Fall back to prompt-based approach
                        pass

                # Normal chat without tools or fallback
                response = await client.ainvoke(lc_messages)
                result = self._parse_response(response)

                # If tools were provided but no tool_calls returned, try prompt fallback
                if tools and not result.tool_calls:
                    tool_prompt = self._format_tools_as_prompt(tools)
                    system_msg = SystemMessage(content=tool_prompt)
                    fallback_messages = [system_msg] + lc_messages
                    fallback_response = await client.ainvoke(fallback_messages)
                    fallback_result = self._parse_response(fallback_response)

                    # Parse tool calls from the text content
                    parsed_calls = self._parse_tool_calls_from_text(fallback_result.content)
                    if parsed_calls:
                        return LLMResponse(
                            content=fallback_result.content,
                            tool_calls=parsed_calls,
                            usage=fallback_result.usage,
                        )

                return result

            except (asyncio.TimeoutError, ConnectionError, TimeoutError) as e:
                last_error = e
                logger.warning(
                    f"LLM request failed (attempt {attempt + 1}/{MAX_RETRIES}): {e}"
                )
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_BACKOFF_BASE * (2 ** attempt)
                    await asyncio.sleep(wait_time)
                    continue

        # All retries exhausted - return friendly error
        error_msg = "抱歉，AI 服务暂时不可用，请稍后重试。"
        if last_error:
            logger.error(f"LLM request failed after {MAX_RETRIES} attempts: {last_error}")
        return LLMResponse(content=error_msg, tool_calls=[], usage={})

    async def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[LLMChunk]:
        """Stream chat response with retry logic.

        Args:
            messages: Conversation messages
            tools: Optional tool schemas

        Yields:
            LLMChunk objects as they arrive
        """
        client = self._get_client()
        lc_messages = self._convert_messages(messages)

        last_error: Exception | None = None

        # Retry loop for timeout/connection errors
        for attempt in range(MAX_RETRIES):
            try:
                async for chunk in client.astream(lc_messages):
                    content = chunk.content if hasattr(chunk, "content") else str(chunk)
                    yield LLMChunk(content=content, is_done=False)

                yield LLMChunk(is_done=True)
                return  # Success - exit retry loop

            except (asyncio.TimeoutError, ConnectionError, TimeoutError) as e:
                last_error = e
                logger.warning(
                    f"LLM stream failed (attempt {attempt + 1}/{MAX_RETRIES}): {e}"
                )
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_BACKOFF_BASE * (2 ** attempt)
                    await asyncio.sleep(wait_time)
                    continue

        # All retries exhausted - yield error message
        error_msg = "抱歉，AI 服务暂时不可用，请稍后重试。"
        if last_error:
            logger.error(f"LLM stream failed after {MAX_RETRIES} attempts: {last_error}")
        yield LLMChunk(content=error_msg, is_done=False)
        yield LLMChunk(is_done=True)

    def _parse_response(self, response: Any) -> LLMResponse:
        """Parse a LangChain response into LLMResponse.

        Args:
            response: LangChain AIMessage response

        Returns:
            LLMResponse with extracted data
        """
        content = response.content if hasattr(response, "content") else str(response)

        tool_calls = []
        if hasattr(response, "tool_calls") and response.tool_calls:
            for tc in response.tool_calls:
                # LangChain tool_calls are dicts
                if isinstance(tc, dict):
                    tool_call = ToolCall(
                        id=tc.get("id", f"call_{uuid.uuid4().hex[:8]}"),
                        name=tc.get("name", ""),
                        arguments=tc.get("args", {}),
                    )
                else:
                    # Handle object-style tool calls
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
