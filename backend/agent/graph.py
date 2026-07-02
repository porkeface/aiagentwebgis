"""Custom ReAct Agent graph — hand-built StateGraph.

Replaces ``create_react_agent`` with explicit ``agent_node`` and ``tools_node``
connected by a conditional edge.  Key improvements over the prebuilt version:

* ``tool_call_count`` only increments on actual tool invocations (LLM chatter is free).
* Multiple parallelizable tool calls within one turn are dispatched in parallel
  via ``asyncio.gather`` with per-call timeouts.
* ``agent_node`` streams per-token text for responsive SSE rendering.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Literal

from langchain_core.messages import AIMessage, AIMessageChunk, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import StreamWriter

from agent.checkpointer import get_checkpointer
from agent.prompts.system import AGENT_SYSTEM_PROMPT
from agent.state import AgentState
from agent.tools import AGENT_TOOLS, get_amap
from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_TOOL_CALLS = 25
AGENT_LLM_TIMEOUT_SEC = 60
TOOL_TIMEOUT_SEC = 30
PARALLELIZABLE_TOOLS = frozenset({
    "search_pois", "search_nearby", "geocode", "get_weather", "score_pois",
})

# ---------------------------------------------------------------------------
# Module-level cache
# ---------------------------------------------------------------------------

_compiled_graph: CompiledStateGraph | None = None
_tool_map: dict[str, Any] = {}


def _build_tool_map() -> dict[str, Any]:
    """Lazily build name→tool lookup from AGENT_TOOLS."""
    global _tool_map
    if not _tool_map:
        _tool_map = {t.name: t for t in AGENT_TOOLS}
    return _tool_map


def _get_model() -> ChatOpenAI:
    """Return the shared ChatOpenAI instance with tools bound."""
    model = ChatOpenAI(
        model="qwen-plus",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key=settings.dashscope_api_key,
        temperature=0.0,
        streaming=True,
        timeout=60,
        max_retries=1,
    )
    return model.bind_tools(AGENT_TOOLS)


def reset_compiled_graph() -> None:
    """Drop the cached compiled graph (used by tests / config hot-reload)."""
    global _compiled_graph
    _compiled_graph = None


# ---------------------------------------------------------------------------
# Tool-call chunk merger
# ---------------------------------------------------------------------------

# Adapted from langgraph.prebuilt.tool_node._handle_tool_call_chunks
def _merge_tool_call_chunks(
    accumulated: AIMessage,
    raw_chunks: list[dict[str, Any]] | None,
) -> None:
    """Merge incremental tool_call chunks into the accumulated AIMessage.

    ChatOpenAI with streaming emits tool_calls in pieces across multiple
    chunks (id in one, name in the next, arguments spread across several).
    This helper accumulates them so the final AIMessage has complete
    ``tool_calls`` with fully populated ``args``.
    """
    if not raw_chunks:
        return

    if not accumulated.tool_calls:
        accumulated.tool_calls = []

    for chunk in raw_chunks:
        idx = chunk.get("index", 0)
        # Grow tool_calls list if needed
        while len(accumulated.tool_calls) <= idx:
            accumulated.tool_calls.append(
                {"name": "", "args": {}, "id": "", "type": "tool_call"}
            )

        tc = accumulated.tool_calls[idx]
        if chunk.get("id"):
            tc["id"] = chunk["id"]
        if chunk.get("name"):
            tc["name"] = chunk["name"]

        args_chunk = chunk.get("args", "")
        if args_chunk:
            # args arrive as JSON snippets that must be concatenated
            existing = tc.get("args")
            if isinstance(existing, dict):
                existing = ""
            tc["args"] = existing + args_chunk

    # Parse all accumulated args strings → dict
    for tc in accumulated.tool_calls:
        if isinstance(tc.get("args"), str) and tc["args"].strip():
            try:
                tc["args"] = json.loads(tc["args"])
            except json.JSONDecodeError:
                pass  # keep as string if incomplete


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------


async def agent_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    """LLM call node — streams tokens for responsive UI.

    Uses model.astream() so LangGraph emits on_chat_model_stream events
    for per-token SSE text streaming.  LangChain 1.0 does not export
    chunk_messages_to_message, so we manually merge tool_call chunks.

    Timeout is enforced by ChatOpenAI(timeout=60) — see _get_model().
    """
    model = _get_model()
    system_prompt = SystemMessage(content=AGENT_SYSTEM_PROMPT)
    full_messages = [system_prompt] + state["messages"]

    accumulated = AIMessage(content="")
    async for chunk in model.astream(full_messages):
        if isinstance(chunk, AIMessageChunk):
            if chunk.content:
                accumulated.content += chunk.content
            if chunk.tool_call_chunks:
                tool_chunks = []
                for tc in chunk.tool_call_chunks:
                    tool_chunks.append({
                        "index": tc.get("index", 0),
                        "id": tc.get("id"),
                        "name": tc.get("name"),
                        "args": tc.get("args", ""),
                    })
                _merge_tool_call_chunks(accumulated, tool_chunks)

    # Merge accumulated JSON args strings to dicts BEFORE returning
    if hasattr(accumulated, "tool_calls") and accumulated.tool_calls:
        for tc in accumulated.tool_calls:
            args = tc.get("args")
            if isinstance(args, str) and args.strip():
                try:
                    tc["args"] = json.loads(args)
                except json.JSONDecodeError:
                    pass  # keep malformed args as string, tool will fail cleanly

    return {"messages": [accumulated]}


async def tools_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    """Dispatch tool calls from the last AIMessage.

    *Tools like plan_day_route* (PARALLELIZABLE_TOOLS) run concurrently
    via ``asyncio.gather`` with per-call timeouts.
    *All other tools* run sequentially (they're fast or have side-effects).

    Each result is wrapped in a ``ToolMessage`` so the LLM sees tool output
    on the next ``agent_node`` invocation.
    """
    tool_map = _build_tool_map()
    messages = state["messages"]
    last_msg = messages[-1]

    tool_calls = getattr(last_msg, "tool_calls", None) or []
    if not tool_calls:
        return {}

    parallel_calls: list[tuple[int, dict[str, Any]]] = []
    sequential_calls: list[tuple[int, dict[str, Any]]] = []

    for tc in tool_calls:
        name = tc.get("name", "")
        if name in PARALLELIZABLE_TOOLS:
            parallel_calls.append((tc["id"], tc))
        else:
            sequential_calls.append((tc["id"], tc))

    tool_messages: list[ToolMessage] = []

    # --- Sequential calls ---------------------------------------------------
    for call_id, tc in sequential_calls:
        tool_fn = tool_map.get(tc["name"])
        if tool_fn is None:
            tool_messages.append(ToolMessage(
                content=json.dumps({"error": f"未知工具: {tc['name']}"}),
                tool_call_id=call_id,
            ))
            continue

        try:
            result = await asyncio.wait_for(
                tool_fn.ainvoke(tc["args"], config),
                timeout=TOOL_TIMEOUT_SEC,
            )
            tool_messages.append(_to_tool_message(result, tc["name"], call_id))
        except asyncio.TimeoutError:
            logger.warning("Tool %s timed out after %ds", tc["name"], TOOL_TIMEOUT_SEC)
            tool_messages.append(ToolMessage(
                content=json.dumps({"error": f"工具 '{tc['name']}' 执行超时"}),
                tool_call_id=call_id,
            ))
        except Exception as exc:
            logger.warning("Tool %s failed: %s", tc["name"], exc.__class__.__name__)
            tool_messages.append(ToolMessage(
                content=json.dumps({"error": "工具执行失败"}),
                tool_call_id=call_id,
            ))

    # --- Parallel calls ----------------------------------------------------
    async def _call_parallel(call_id: str, tc: dict[str, Any]) -> ToolMessage:
        tool_fn = tool_map[tc["name"]]
        try:
            result = await asyncio.wait_for(
                tool_fn.ainvoke(tc["args"], config),
                timeout=TOOL_TIMEOUT_SEC,
            )
            return _to_tool_message(result, tc["name"], call_id)
        except asyncio.TimeoutError:
            logger.warning("Tool %s timed out after %ds", tc["name"], TOOL_TIMEOUT_SEC)
            return ToolMessage(
                content=json.dumps({"error": f"工具 '{tc['name']}' 执行超时"}),
                tool_call_id=call_id,
            )
        except Exception as exc:
            logger.exception("Tool %s failed", tc["name"])
            return ToolMessage(
                content=json.dumps({"error": str(exc)}),
                tool_call_id=call_id,
            )

    if parallel_calls:
        parallel_results = await asyncio.gather(
            *(_call_parallel(cid, tc) for cid, tc in parallel_calls),
            return_exceptions=True,
        )
        for item in parallel_results:
            if isinstance(item, ToolMessage):
                tool_messages.append(item)
            else:
                tool_messages.append(ToolMessage(
                    content=json.dumps({"error": "工具执行失败"}),
                    tool_call_id="unknown",
                ))

    new_count = state.get("tool_call_count", 0) + len(tool_calls)
    return {"messages": tool_messages, "tool_call_count": new_count}


def _to_tool_message(result: Any, tool_name: str, call_id: str) -> ToolMessage:
    """Wrap a raw tool return value in a ToolMessage."""
    if not isinstance(result, str):
        result = json.dumps(result, ensure_ascii=False, default=str)
    return ToolMessage(content=result, name=tool_name, tool_call_id=call_id)


# ---------------------------------------------------------------------------
# Conditional routing
# ---------------------------------------------------------------------------


def _should_continue(state: AgentState) -> Literal["tools_node", "__end__"]:
    """Route after agent_node: tools if we have calls and budget, else end."""
    messages = state.get("messages", [])
    if not messages:
        return END

    last_msg = messages[-1]
    tool_calls = getattr(last_msg, "tool_calls", None) or []
    if not tool_calls:
        return END

    if state.get("tool_call_count", 0) >= MAX_TOOL_CALLS:
        logger.warning("tool_call_count=%d reached MAX=%d, forcing end",
                       state.get("tool_call_count"), MAX_TOOL_CALLS)
        return END

    return "tools_node"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


def build_graph(checkpointer: object | None = None) -> CompiledStateGraph:
    """Build the custom ReAct travel agent graph.

    Args:
        checkpointer: Optional checkpointer override.
            - None (default): use the process-wide checkpointer and cache.
            - False: skip checkpointer (for tests without thread_id).
            - BaseCheckpointSaver: use the supplied instance.

    Returns:
        A compiled LangGraph ready for astream / ainvoke.
    """
    global _compiled_graph

    use_default = checkpointer is None
    if use_default and _compiled_graph is not None:
        return _compiled_graph

    workflow = StateGraph(AgentState)

    workflow.add_node("agent_node", agent_node)
    workflow.add_node("tools_node", tools_node)

    workflow.add_edge(START, "agent_node")
    workflow.add_edge("tools_node", "agent_node")
    workflow.add_conditional_edges("agent_node", _should_continue, {
        "tools_node": "tools_node",
        "__end__": END,
    })

    graph = workflow.compile()

    if use_default:
        cp = get_checkpointer()
        if cp:
            graph.checkpointer = cp
        _compiled_graph = graph
        return graph

    if checkpointer:
        graph.checkpointer = checkpointer
    return graph
