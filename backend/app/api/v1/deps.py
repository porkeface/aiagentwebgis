"""Authentication dependencies for FastAPI endpoints."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.user import User
from app.services.auth_service import decode_token, token_jti

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# ---------------------------------------------------------------------------
# In-memory revoked-jti denylist.
# ---------------------------------------------------------------------------
# A production deployment should back this with Redis (TTL = remaining token
# lifetime) so it survives process restarts and works across multiple
# workers. The in-memory implementation is sufficient for single-process
# dev / staging and gives a single, well-known hook (`revoke_jti`) for
# the auth router to call on logout / password change.
# ---------------------------------------------------------------------------

_REVOKED_JTIS: set[str] = set()


def revoke_jti(jti: str) -> None:
    """Mark a token's ``jti`` as revoked.

    Subsequent calls to ``get_current_user`` with a token carrying this
    jti will return 401. Idempotent — revoking the same jti twice is a
    no-op.
    """
    if jti:
        _REVOKED_JTIS.add(jti)


def is_jti_revoked(jti: str | None) -> bool:
    """Return True if the jti has been explicitly revoked."""
    return bool(jti) and jti in _REVOKED_JTIS


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_session),
) -> int:
    """Extract and validate the JWT token from the Authorization header.

    Decodes the token, checks the revocation denylist, and verifies the
    user still exists in the database. Raises 401 if any check fails.

    Args:
        token: JWT token from the Authorization: Bearer header.
        db: Async database session.

    Returns:
        The authenticated user's ID.

    Raises:
        HTTPException: 401 if token is invalid, revoked, or user not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user_id = decode_token(token)
    if user_id is None:
        raise credentials_exception

    # Reject tokens that have been revoked (e.g. on password change or logout).
    if is_jti_revoked(token_jti(token)):
        raise credentials_exception

    # Verify the user still exists in the database.
    # Username/primary-key query is lightweight but still hits the DB pool;
    # in-memory token validation above already covers the fast path.
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception

    await db.commit()  # release session immediately
    return user_id
