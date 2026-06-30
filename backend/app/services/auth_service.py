"""Authentication service: password hashing and JWT token management."""

import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from app.config import settings


JWT_ISSUER = "travel-planner"
JWT_AUDIENCE = "travel-planner-web"


def hash_password(password: str) -> str:
    """Hash a plain-text password using bcrypt with a random salt.

    Args:
        password: The plain-text password to hash.

    Returns:
        The bcrypt hash string.
    """
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against a bcrypt hash.

    Args:
        plain: The plain-text password to check.
        hashed: The bcrypt hash to verify against.

    Returns:
        True if the password matches, False otherwise.
    """
    try:
        return bcrypt.checkpw(
            plain.encode("utf-8"),
            hashed.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


def create_token(user_id: int) -> str:
    """Create a JWT access token for the given user.

    Payload includes standard ``iss`` / ``aud`` / ``iat`` / ``exp`` claims
    plus a unique ``jti`` so individual tokens can be revoked (e.g. after
    a password change) by adding the jti to a denylist.

    Args:
        user_id: The ID of the authenticated user.

    Returns:
        A signed JWT token string.
    """
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": str(user_id),
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "iat": now,
        "exp": expire,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> int | None:
    """Decode and validate a JWT token, returning the user_id.

    Validates signature, expiry, and ``iss`` / ``aud`` claims. Returns
    ``None`` for any failure (expired, bad signature, wrong issuer/aud).

    Args:
        token: The JWT token string to decode.

    Returns:
        The user_id (int) if the token is valid, None otherwise.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
        )
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            return None
        return int(user_id_str)
    except (JWTError, ValueError, TypeError):
        return None


def token_jti(token: str) -> str | None:
    """Return the ``jti`` claim of a token without raising.

    Used by the logout / revocation flow to record which tokens are no
    longer valid. The token is NOT re-validated here; pair with
    ``decode_token`` if you need signature/expiry checks too.
    """
    try:
        payload = jwt.get_unverified_claims(token)
        jti = payload.get("jti")
        return str(jti) if jti else None
    except (JWTError, ValueError, TypeError):
        return None
