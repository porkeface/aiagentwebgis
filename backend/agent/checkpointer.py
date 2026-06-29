"""Checkpointer factory for LangGraph state persistence.

Provides a singleton checkpointer instance:
- Dev mode (default): MemorySaver (in-memory)
- Prod mode (DATABASE_URL set): PostgresSaver
"""

from __future__ import annotations

import os
from typing import Optional

from langgraph.checkpoint.base import BaseCheckpointSaver


_checkpointer: Optional[BaseCheckpointSaver] = None


def get_checkpointer() -> BaseCheckpointSaver:
    """Return a cached checkpointer instance.

    Returns:
        BaseCheckpointSaver: MemorySaver for dev, PostgresSaver for prod.
    """
    global _checkpointer
    if _checkpointer is not None:
        return _checkpointer

    database_url = os.environ.get("DATABASE_URL")

    if database_url:
        from langgraph.checkpoint.postgres import PostgresSaver

        _checkpointer = PostgresSaver.from_conn_string(database_url)
    else:
        from langgraph.checkpoint.memory import MemorySaver

        _checkpointer = MemorySaver()

    return _checkpointer


def reset_checkpointer() -> None:
    """Reset the cached checkpointer (for testing)."""
    global _checkpointer
    _checkpointer = None
