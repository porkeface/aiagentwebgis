# Capability: LLM Adapter

## Overview

Adapter pattern providing unified LLM interface with fallback mechanism. Supports runtime switching between providers.

## Interface

```python
class BaseLLMAdapter(ABC):
    async def chat(self, messages: list[dict], tools: list[Tool] | None = None) -> LLMResponse
    async def stream(self, messages: list[dict], tools: list[Tool] | None = None) -> AsyncIterator[LLMChunk]

class LLMResponse:
    content: str
    tool_calls: list[ToolCall] | None
    usage: dict  # {prompt_tokens, completion_tokens}

class ToolCall:
    id: str
    name: str
    arguments: dict
```

## Implementations

### TongyiAdapter (Primary)
- Uses `langchain_community.chat_models.ChatTongyi`
- Normal path: LangChain tool calling (function call format)
- Fallback path: When tool_call parsing fails, inject tool descriptions into system prompt, request JSON output, parse with regex/JSON

### OpenAIAdapter
- Uses `langchain_openai.ChatOpenAI`
- Standard tool calling support

### OllamaAdapter
- Uses `langchain_community.chat_models.ChatOllama`
- For local development/testing without API keys

## Provider Selection

```python
# Via environment variable
LLM_PROVIDER=tongyi  # or openai, ollama

# Via factory function
def get_llm_adapter() -> BaseLLMAdapter:
    provider = os.getenv("LLM_PROVIDER", "tongyi")
    adapters = {"tongyi": TongyiAdapter, "openai": OpenAIAdapter, "ollama": OllamaAdapter}
    return adapters[provider]()
```

## Fallback Mechanism

When tool_call response format is invalid:
1. Log the error and raw response
2. Construct a prompt that describes available tools in natural language
3. Request the LLM to output tool calls as JSON in its response text
4. Parse the JSON from response text
5. If parsing still fails, return error message to user

## Acceptance Scenarios

1. TongyiAdapter receives valid tool_call response → parsed normally → tool executed
2. TongyiAdapter receives malformed tool_call → fallback triggered → prompt-based extraction succeeds
3. Fallback also fails → graceful error message returned to user
4. Switch LLM_PROVIDER from tongyi to openai → same agent code works without changes
