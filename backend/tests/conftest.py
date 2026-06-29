import pytest
import pytest_asyncio
import httpx
from httpx import AsyncClient

from app.main import app


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    """Provide an async HTTP client for testing."""
    async with AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac
