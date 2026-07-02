"""Async database engine and session factory with retry logic."""

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

logger = logging.getLogger(__name__)

# DB retry configuration
DB_MAX_RETRIES = 3
DB_RETRY_BACKOFF_BASE = 1.0  # seconds

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncSession:
    """Yield an async database session with retry logic (FastAPI dependency).

    Retries up to DB_MAX_RETRIES times with exponential backoff on
    connection failures.
    """
    last_error: Exception | None = None

    for attempt in range(DB_MAX_RETRIES):
        try:
            async with async_session_factory() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise
            return  # Success
        except (ConnectionError, OSError) as e:
            last_error = e
            logger.warning(
                f"DB connection failed (attempt {attempt + 1}/{DB_MAX_RETRIES}): {e}"
            )
            if attempt < DB_MAX_RETRIES - 1:
                wait_time = DB_RETRY_BACKOFF_BASE * (2 ** attempt)
                await asyncio.sleep(wait_time)
                continue
            raise
        except Exception:
            # Non-connection errors should propagate immediately
            raise

    # Should not reach here, but just in case
    if last_error:
        raise last_error
