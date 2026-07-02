"""Authentication API endpoints: register, login, logout."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import revoke_jti
from app.database import get_session
from app.models.user import User
from app.schemas.auth import LoginRequest, LogoutResponse, RegisterRequest, TokenResponse
from app.services.auth_service import (
    create_token,
    hash_password,
    token_jti,
    verify_password,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])

# Local token extractor used by the logout endpoint. We don't reuse the one
# in deps.py because that one pulls a DB session via Depends, which would
# force a useless DB round-trip just to read the bearer token.
_oauth2_scheme_logout = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@router.post(
    "/register",
    response_model=TokenResponse,
    summary="Register a new user",
    description="Create a new user account with hashed password. Returns JWT token. 409 if username already taken.",
)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """Register a new user account.

    Creates a new user with hashed password and returns a JWT token.
    Returns 409 if the username is already taken.

    Args:
        request: Registration data (username, password, email).
        db: Async database session.

    Returns:
        TokenResponse with access_token and token_type.

    Raises:
        HTTPException: 409 if username already exists.
    """
    # Use db.execute() + scalar_one_or_none() instead of db.run_sync so we
    # don't serialize a synchronous bcrypt call behind the async session lock.
    normalized_username = request.username.strip().lower()
    now = datetime.now(UTC)
    created_at = now.strftime("%Y-%m-%d %H:%M:%S")

    # Check existence with a lightweight query first — avoids holding
    # the session during the slow bcrypt hash when the username is taken.
    result = await db.execute(select(User).where(User.username == normalized_username))
    existing_user = result.scalar_one_or_none()
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already registered",
        )

    # Hash *before* touching the DB to keep the session short
    hashed = hash_password(request.password)

    new_user = User(
        username=normalized_username,
        hashed_password=hashed,
        nickname=normalized_username,
        email=request.email,
    )
    try:
        db.add(new_user)
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already registered",
        )
    await db.refresh(new_user)
    await db.commit()  # commit the tx before the token call


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login user",
    description="Authenticate with username/password and receive a JWT token. Returns 401 on invalid credentials.",
)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """Authenticate user and return a JWT token.

    Verifies username and password. Returns 401 if credentials are invalid.

    Args:
        request: Login data (username, password).
        db: Async database session.

    Returns:
        TokenResponse with access_token and token_type.

    Raises:
        HTTPException: 401 if credentials are invalid.
    """
    normalized_username = request.username.strip().lower()
    now = datetime.now(UTC)
    created_at = now.strftime("%Y-%m-%d %H:%M:%S")

    result = await db.execute(select(User).where(User.username == normalized_username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_token(user_id=user.id)
    await db.commit()  # release the session immediately
    return TokenResponse(access_token=token)


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="Logout and revoke the current token",
    description="Adds the bearer token's jti to the revocation denylist so the same token cannot be reused.",
)
async def logout(token: str = Depends(_oauth2_scheme_logout)) -> LogoutResponse:
    """Revoke the caller's JWT so it can no longer be used.

    The token's jti is added to the in-memory denylist checked by
    ``get_current_user``. The client must also discard the token locally.
    """
    jti = token_jti(token)
    if jti:
        revoke_jti(jti)
    return LogoutResponse(revoked=bool(jti))
