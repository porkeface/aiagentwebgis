"""Authentication Pydantic schemas."""

from pydantic import BaseModel, Field, field_validator


class RegisterRequest(BaseModel):
    """Request schema for user registration."""

    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=6, max_length=128)
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email format")
        return v.lower()

    @field_validator("username")
    @classmethod
    def normalize_username(cls, v: str) -> str:
        # Strip whitespace and lowercase so "Alice"/"alice " don't create
        # duplicate accounts on a case-sensitive collation.
        cleaned = v.strip().lower()
        if len(cleaned) < 3:
            raise ValueError("Username must be at least 3 characters after trimming")
        return cleaned


class LoginRequest(BaseModel):
    """Request schema for user login."""

    username: str
    password: str

    @field_validator("username")
    @classmethod
    def normalize_username(cls, v: str) -> str:
        return v.strip().lower()


class TokenResponse(BaseModel):
    """Response schema for JWT token."""

    access_token: str
    token_type: str = "bearer"


class LogoutResponse(BaseModel):
    """Response schema for token revocation."""

    revoked: bool
