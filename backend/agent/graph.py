"""ReAct Agent graph — powered by LangGraph create_react_agent.

Architecture (v2):
    User Input → create_react_agent(LLM + tools) → stream events → SSE → Frontend

The agent loop is handled entirely by LangGraph.  We configure it with
ChatTongyi (qwen-plus), our @tool-decorated functions, and a system prompt.
The API layer maps astream_events to SSE events for the frontend.
"""

from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent

from agent.state import AgentState
from agent.tools import AGENT_TOOLS
from agent.prompts.system import AGENT_SYSTEM_PROMPT
from agent.checkpointer import get_checkpointer


# ---------------------------------------------------------------------------
# Module-level cache
# ---------------------------------------------------------------------------

_compiled_graph: CompiledStateGraph | None = None


def reset_compiled_graph() -> None:
    """Drop the cached compiled graph (used by tests / config hot-reload)."""
    global _compiled_graph
    _compiled_graph = None


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


def build_graph(
    checkpointer: object | None = None,
) -> CompiledStateGraph:
    """Build the ReAct travel agent graph.

    ``create_react_agent`` returns an already-compiled ``CompiledStateGraph``
    so we only need to wire in the checkpointer.

    Args:
        checkpointer: Optional checkpointer override.
            - None (default): use the process-wide checkpointer and cache.
            - False: skip checkpointer (for tests without thread_id).
            - BaseCheckpointSaver: use the supplied instance.

    Returns:
        A compiled LangGraph ready for astream_events / ainvoke.
    """
    global _compiled_graph

    use_default = checkpointer is None
    if use_default and _compiled_graph is not None:
        return _compiled_graph

    # --- Build the LLM -------------------------------------------------------
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage
    from app.config import settings

    model = ChatOpenAI(
        model="qwen-plus",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key=settings.dashscope_api_key,
        temperature=0.0,
        streaming=True,
    )

    # Wrap prompt in a SystemMessage so LangGraph binds it to the model
    # as a system instruction rather than a user message.
    system_message = SystemMessage(content=AGENT_SYSTEM_PROMPT)

    # --- Build the agent -----------------------------------------------------
    # create_react_agent returns a CompiledStateGraph already.
    graph = create_react_agent(
        model=model,
        tools=AGENT_TOOLS,
        prompt=system_message,
        state_schema=AgentState,
    )

    # --- Wire checkpointer ---------------------------------------------------
    if use_default:
        cp = get_checkpointer()
        if cp:
            graph.checkpointer = cp
        _compiled_graph = graph
        return graph

    if checkpointer:
        graph.checkpointer = checkpointer
    return graph
