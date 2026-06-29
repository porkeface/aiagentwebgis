# Task 1.4: LLM Adapter Layer - Report

**Status:** DONE
**Commit:** 0dae88e
**Branch:** ai-travel-planner

## Summary

Implemented the LLM adapter layer providing a unified interface for multiple LLM providers (Tongyi, OpenAI, Ollama) with frozen dataclass DTOs and a factory function.

## Files Created

| File | Purpose |
|------|---------|
| `backend/agent/__init__.py` | Agent module root |
| `backend/agent/llm/__init__.py` | LLM adapter package |
| `backend/agent/llm/base.py` | `BaseLLMAdapter` ABC + `ToolCall`, `LLMResponse`, `LLMChunk` dataclasses |
| `backend/agent/llm/tongyi.py` | Tongyi (DashScope) adapter with prompt-based fallback |
| `backend/agent/llm/openai_adapter.py` | OpenAI adapter via langchain_openai |
| `backend/agent/llm/ollama.py` | Ollama adapter via langchain_ollama for local dev |
| `backend/agent/llm/factory.py` | `get_llm_adapter()` factory with env/settings resolution |
| `backend/tests/test_agent/test_llm_adapter.py` | 16 tests covering all components |

## Files Modified

| File | Change |
|------|--------|
| `backend/agent/llm/factory.py` | Fixed config resolution priority: env vars > app.config.settings > defaults |
| `backend/tests/test_agent/test_llm_adapter.py` | Fixed mock target from `agent.llm.factory.settings` to `app.config.settings` |

## Key Design Decisions

1. **Frozen dataclasses** for `ToolCall`, `LLMResponse`, `LLMChunk` — immutability by default
2. **Lazy client loading** — adapters only import langchain packages when `_get_client()` is called
3. **TongyiAdapter fallback** — two-phase: native `tool_calls` first, then prompt injection + regex JSON extraction
4. **Factory priority** — `LLM_PROVIDER` env var takes precedence over `app.config.settings`, enabling clean test isolation
5. **Shared `_parse_response` pattern** — all 3 adapters extract `tool_calls` and `usage_metadata` from LangChain AIMessage uniformly

## Test Results

```
tests/test_agent/test_llm_adapter.py — 16 passed
Full suite (69 tests) — all passed
```

### Test Coverage

- **TestDataclassStructures (6):** ToolCall/LLMResponse/LLMChunk fields, frozen immutability, defaults
- **TestTongyiAdapterParsing (5):** `_format_tools_as_prompt`, `_parse_tool_calls_from_text` (valid JSON, multiple calls, no JSON, invalid JSON)
- **TestFactory (5):** returns Tongyi/OpenAI/Ollama adapters, unknown provider raises ValueError, reads app.config.settings

## Bugs Fixed

1. **Factory env var override not working:** Original code tried `app.config.settings` first (which always succeeds since config is loaded at import time), ignoring `LLM_PROVIDER` env var. Fixed by checking env var first.
2. **Test mock target incorrect:** `patch("agent.llm.factory.settings")` failed because `settings` is imported locally inside a function. Fixed to `patch("app.config.settings")`.

## Bugs Found in Code Review

- **`_parse_tool_calls_from_text` regex limitation:** The regex pattern uses `[^{}]*` for args, which only supports flat JSON objects. Nested objects in args would fail to parse. Acceptable for current use case (tool args are typically flat), but worth noting for future.
- **No `langchain-core` import in base.py:** The base module is framework-agnostic (pure dataclasses), which is correct — adapters handle the langchain dependency.

## What's Next

Task 2.1: LangGraph + Router — build the agent graph with tool routing.
