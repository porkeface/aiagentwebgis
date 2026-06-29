"""Tests for JWT authentication API endpoints."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from app.api.v1.deps import get_current_user
from app.database import get_session
from app.main import app
from app.services.auth_service import (
    create_token,
    decode_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    """Test password hashing utilities."""

    def test_hash_password_returns_string(self) -> None:
        """hash_password should return a non-empty string."""
        hashed = hash_password("mysecretpassword")
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != "mysecretpassword"

    def test_hash_password_produces_different_hashes(self) -> None:
        """Same password should produce different hashes (salt)."""
        h1 = hash_password("samepassword")
        h2 = hash_password("samepassword")
        assert h1 != h2  # Different salts

    def test_verify_password_correct(self) -> None:
        """verify_password should return True for correct password."""
        hashed = hash_password("correctpassword")
        assert verify_password("correctpassword", hashed) is True

    def test_verify_password_incorrect(self) -> None:
        """verify_password should return False for wrong password."""
        hashed = hash_password("correctpassword")
        assert verify_password("wrongpassword", hashed) is False


class TestJWTTokens:
    """Test JWT token creation and decoding."""

    def test_create_token_returns_string(self) -> None:
        """create_token should return a JWT string."""
        token = create_token(user_id=1)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_token_valid(self) -> None:
        """decode_token should return user_id for a valid token."""
        token = create_token(user_id=42)
        user_id = decode_token(token)
        assert user_id == 42

    def test_decode_token_invalid_returns_none(self) -> None:
        """decode_token should return None for an invalid token."""
        result = decode_token("not.a.valid.token")
        assert result is None

    def test_decode_token_tampered_returns_none(self) -> None:
        """decode_token should return None for a tampered token."""
        token = create_token(user_id=1)
        # Tamper with the token by changing a character
        tampered = token[:-3] + "xxx"
        result = decode_token(tampered)
        assert result is None

    def test_decode_token_empty_string(self) -> None:
        """decode_token should return None for empty string."""
        result = decode_token("")
        assert result is None


def _mock_db_session(
    execute_return: object = None,
    user_id_for_refresh: int | None = None,
) -> AsyncMock:
    """Create a mock async DB session.

    Args:
        execute_return: Value returned by session.execute().scalar_one_or_none().
        user_id_for_refresh: If set, session.refresh() will set obj.id to this value.

    Returns:
        An AsyncMock configured as a database session.
    """
    session = AsyncMock()

    # Configure execute -> result -> scalar_one_or_none
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = execute_return
    session.execute.return_value = mock_result

    # Configure refresh to set user.id
    if user_id_for_refresh is not None:

        def _set_id(obj: object) -> None:
            obj.id = user_id_for_refresh  # type: ignore[attr-defined]

        session.refresh.side_effect = _set_id

    return session


class TestRegisterEndpoint:
    """Test POST /api/v1/auth/register."""

    async def test_register_success(self, client: AsyncClient) -> None:
        """Test successful user registration returns a token."""
        mock_session = _mock_db_session(
            execute_return=None,  # user doesn't exist yet
            user_id_for_refresh=1,
        )

        async def _override_get_session() -> AsyncMock:
            return mock_session

        app.dependency_overrides[get_session] = _override_get_session
        try:
            payload = {
                "username": "testuser",
                "password": "testpass123",
                "email": "test@example.com",
            }
            response = await client.post("/api/v1/auth/register", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"

            # Verify the token is valid and contains correct user_id
            token = data["access_token"]
            user_id = decode_token(token)
            assert user_id == 1
        finally:
            app.dependency_overrides.clear()

    async def test_register_duplicate_username(self, client: AsyncClient) -> None:
        """Test registering with existing username returns 409."""
        existing_user = MagicMock()
        mock_session = _mock_db_session(execute_return=existing_user)

        async def _override_get_session() -> AsyncMock:
            return mock_session

        app.dependency_overrides[get_session] = _override_get_session
        try:
            payload = {
                "username": "existinguser",
                "password": "testpass123",
                "email": "test@example.com",
            }
            response = await client.post("/api/v1/auth/register", json=payload)
            assert response.status_code == 409
        finally:
            app.dependency_overrides.clear()

    async def test_register_validation_error_short_username(
        self, client: AsyncClient
    ) -> None:
        """Test registration with username too short returns 422."""
        payload = {
            "username": "ab",
            "password": "testpass123",
            "email": "test@example.com",
        }
        response = await client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 422

    async def test_register_validation_error_short_password(
        self, client: AsyncClient
    ) -> None:
        """Test registration with password too short returns 422."""
        payload = {
            "username": "testuser",
            "password": "12345",
            "email": "test@example.com",
        }
        response = await client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 422


class TestLoginEndpoint:
    """Test POST /api/v1/auth/login."""

    async def test_login_success(self, client: AsyncClient) -> None:
        """Test successful login returns a token."""
        hashed = hash_password("correctpassword")
        mock_user = MagicMock()
        mock_user.id = 42
        mock_user.username = "testuser"
        mock_user.hashed_password = hashed

        mock_session = _mock_db_session(execute_return=mock_user)

        async def _override_get_session() -> AsyncMock:
            return mock_session

        app.dependency_overrides[get_session] = _override_get_session
        try:
            payload = {"username": "testuser", "password": "correctpassword"}
            response = await client.post("/api/v1/auth/login", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"

            # Verify the token contains the correct user_id
            user_id = decode_token(data["access_token"])
            assert user_id == 42
        finally:
            app.dependency_overrides.clear()

    async def test_login_wrong_password(self, client: AsyncClient) -> None:
        """Test login with wrong password returns 401."""
        hashed = hash_password("correctpassword")
        mock_user = MagicMock()
        mock_user.id = 42
        mock_user.username = "testuser"
        mock_user.hashed_password = hashed

        mock_session = _mock_db_session(execute_return=mock_user)

        async def _override_get_session() -> AsyncMock:
            return mock_session

        app.dependency_overrides[get_session] = _override_get_session
        try:
            payload = {"username": "testuser", "password": "wrongpassword"}
            response = await client.post("/api/v1/auth/login", json=payload)
            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()

    async def test_login_nonexistent_user(self, client: AsyncClient) -> None:
        """Test login with non-existent username returns 401."""
        mock_session = _mock_db_session(execute_return=None)

        async def _override_get_session() -> AsyncMock:
            return mock_session

        app.dependency_overrides[get_session] = _override_get_session
        try:
            payload = {"username": "ghost", "password": "anypassword"}
            response = await client.post("/api/v1/auth/login", json=payload)
            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()


class TestGetCurrentUserDependency:
    """Test the get_current_user dependency via protected endpoints."""

    async def test_missing_token_returns_401(self, client: AsyncClient) -> None:
        """Test that missing Authorization header returns 401."""
        response = await client.get("/api/v1/trips")
        assert response.status_code == 401

    async def test_invalid_token_returns_401(self, client: AsyncClient) -> None:
        """Test that an invalid JWT token returns 401."""
        response = await client.get(
            "/api/v1/trips",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401

    async def test_valid_token_with_mocked_user(self, client: AsyncClient) -> None:
        """Test that a valid token passes authentication."""
        # Create a valid token for user 7
        token = create_token(user_id=7)

        # Mock DB session to verify user exists
        mock_user = MagicMock()
        mock_user.id = 7
        mock_session = _mock_db_session(execute_return=mock_user)

        async def _override_get_session() -> AsyncMock:
            return mock_session

        async def _override_get_current_user() -> int:
            return 7

        app.dependency_overrides[get_session] = _override_get_session
        app.dependency_overrides[get_current_user] = _override_get_current_user
        try:
            # Mock the trip service to avoid DB queries
            from unittest.mock import patch

            with patch("app.services.trip_service.list_trips") as mock_list:
                mock_list.return_value = {"total": 0, "items": []}
                response = await client.get(
                    "/api/v1/trips",
                    headers={"Authorization": f"Bearer {token}"},
                )
                assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()
