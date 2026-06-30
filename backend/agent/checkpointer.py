"""Checkpointer factory for LangGraph state persistence.

Provides a singleton checkpointer instance:
- Dev mode (default): MemorySaver (in-memory)
- Prod mode (DATABASE_URL set): PostgresSaver
"""

from __future__ import annotations

import logging
from typing import Optional

from langgraph.checkpoint.base import BaseCheckpointSaver

logger = logging.getLogger(__name__)

_checkpointer: Optional[BaseCheckpointSaver] = None


def get_checkpointer() -> BaseCheckpointSaver:
    """Return a cached checkpointer instance.

    Returns:
        BaseCheckpointSaver: MemorySaver for dev, PostgresSaver for prod.
    """
    global _checkpointer
    if _checkpointer is not None:
        return _checkpointer

    from app.config import settings

    if settings.app_env == "production" and settings.database_url:
        # Use PostgresSaver in production environment
        try:
            from langgraph.checkpoint.postgres import PostgresSaver

            # Convert async driver to sync psycopg2 for checkpointer
            url = settings.database_url.replace("+asyncpg", "+psycopg2")
            _checkpointer = PostgresSaver.from_conn_string(url)
            _checkpointer.setup()
            logger.info("PostgresSaver initialized for production")
        except Exception as e:
            logger.warning(
                f"Failed to create PostgresSaver, falling back to MemorySaver: {e}"
            )
            from langgraph.checkpoint.memory import MemorySaver

            _checkpointer = MemorySaver()
    else:
        from langgraph.checkpoint.memory import MemorySaver

        _checkpointer = MemorySaver()

    return _checkpointer


def reset_checkpointer() -> None:
    """Reset the cached checkpointer (for testing)."""
    global _checkpointer
    _checkpointer = None
