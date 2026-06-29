### Task 1.4: LLM Adapter Layer

**Files:**
- Create: `backend/agent/__init__.py`, `backend/agent/llm/__init__.py`
- Create: `backend/agent/llm/base.py` (BaseLLMAdapter ABC, LLMResponse, ToolCall, LLMChunk dataclasses)
- Create: `backend/agent/llm/tongyi.py` (TongyiAdapter with tool_call + prompt fallback)
- Create: `backend/agent/llm/openai_adapter.py` (OpenAIAdapter)
- Create: `backend/agent/llm/ollama.py` (OllamaAdapter)
- Create: `backend/agent/llm/factory.py` (get_llm_adapter() factory)
- Test: `backend/tests/test_agent/test_llm_adapter.py`

**Consumes:** config.py (LLM_PROVIDER, DASHSCOPE_API_KEY)
**Produces:** BaseLLMAdapter ABC, 3 adapter implementations, factory function

**Steps:**

1. Define dataclasses in base.py:
   - ToolCall(id, name, arguments)
   - LLMResponse(content, tool_calls, usage)
   - LLMChunk(content, tool_call_delta, is_done)
   - BaseLLMAdapter ABC: chat(messages, tools?) -> LLMResponse, stream(messages, tools?) -> AsyncIterator[LLMChunk]

2. TongyiAdapter:
   - Uses langchain_community ChatTongyi
   - _tool_call_chat: normal path with tools param
   - _prompt_based_fallback: injects tool descriptions into system prompt, parses JSON from response text
   - _format_tools_as_prompt: converts tool schemas to text descriptions
   - _parse_tool_calls_from_text: regex extract JSON with "tool" and "args" fields

3. OpenAIAdapter: uses langchain_openai ChatOpenAI, standard tool calling
4. OllamaAdapter: uses langchain_community ChatOllama, for local dev
5. factory.py: get_llm_adapter() reads LLM_PROVIDER env, returns correct adapter

6. Write tests:
   - test_llm_response_structure
   - test_tool_call_structure
   - test_tongyi_parse_tool_calls_from_json_text
   - test_tongyi_parse_tool_calls_handles_no_json
   - test_tongyi_format_tools_as_prompt
   - test_factory_returns_tongyi

7. Run: `pytest tests/test_agent/test_llm_adapter.py -v` -- all 6 pass
8. Commit: `feat: LLM adapter layer - Tongyi with fallback, OpenAI, Ollama`

---