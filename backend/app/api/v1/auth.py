"""Authentication API endpoints: register and login."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.services.auth_service import create_token, hash_password, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


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
    # Check if username already exists
    result = await db.execute(select(User).where(User.username == request.username))
    existing_user = result.scalar_one_or_none()
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already registered",
        )

    # Create the new user
    new_user = User(
        username=request.username,
        hashed_password=hash_password(request.password),
        nickname=request.username,
    )
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)

    # Generate and return token
    token = create_token(user_id=new_user.id)
    return TokenResponse(access_token=token)


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
    # Find user by username
    result = await db.execute(select(User).where(User.username == request.username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate and return token
    token = create_token(user_id=user.id)
    return TokenResponse(access_token=token)
