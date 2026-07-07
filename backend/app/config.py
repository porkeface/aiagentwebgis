import logging
import warnings

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings


logger = logging.getLogger(__name__)

# Minimum acceptable length for the JWT secret. Anything shorter is brute-
# forceable; 32 chars (256 bits) matches HS256's block size.
MIN_SECRET_LENGTH = 32


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_env: str = Field(default="development", description="Application environment")
    debug: bool = Field(default=False, description="Debug mode")

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://travel_planner:changeme@localhost:5432/travel_planner",
        description="PostgreSQL database URL",
    )

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )

    # LLM
    llm_api_key: str = Field(default="", description="LLM API key")
    llm_provider: str = Field(default="dashscope", description="LLM provider name")
    llm_model: str = Field(default="qwen-plus", description="LLM model name")
    llm_base_url: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        description="LLM API base URL",
    )

    # Map
    amap_api_key: str = Field(default="", description="Amap (Gaode) API key")

    # Security
    jwt_secret_key: str = Field(
        default="change-this-to-a-random-secret-key",
        description="Secret key for JWT signing",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm")
    jwt_expire_minutes: int = Field(
        default=60 * 24, description="JWT token expiration in minutes"
    )

    # CORS
    cors_origins: str = Field(
        default="http://localhost:5173",
        description="Comma-separated list of allowed CORS origins",
    )

    model_config = {
        "env_file": (".env", "../.env", "../../.env"),  # backend/.env, then project root
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }

    @model_validator(mode="after")
    def _warn_insecure_defaults(self) -> "Settings":
        """Reject insecure defaults in non-dev environments.

        The app refuses to start in production / staging with the placeholder
        JWT secret or the ``changeme`` database password. In development we
        keep a warning so the local quickstart still works without forcing
        every contributor to set environment variables.
        """
        if self.app_env in ("production", "staging"):
            if self.jwt_secret_key == "change-this-to-a-random-secret-key":
                raise ValueError(
                    "JWT_SECRET_KEY must be set to a strong random value "
                    "in production/staging"
                )
            if len(self.jwt_secret_key) < MIN_SECRET_LENGTH:
                raise ValueError(
                    f"JWT_SECRET_KEY must be at least {MIN_SECRET_LENGTH} characters "
                    "in production/staging"
                )
            if self.jwt_algorithm not in ("HS256", "HS384", "HS512", "RS256"):
                raise ValueError(
                    f"JWT_ALGORITHM={self.jwt_algorithm!r} is not in the allowed set"
                )
            if "changeme" in self.database_url:
                raise ValueError(
                    "DATABASE_URL must not contain the placeholder password 'changeme' "
                    "in production/staging"
                )
            if self.debug:
                raise ValueError("DEBUG must be false in production/staging")
        else:
            if self.jwt_secret_key == "change-this-to-a-random-secret-key":
                warnings.warn(
                    "JWT_SECRET_KEY is using the insecure default value. "
                    "Set a strong random secret in production via JWT_SECRET_KEY env var.",
                    stacklevel=2,
                )
                logger.warning(
                    "JWT_SECRET_KEY is using the insecure default value. "
                    "Set a strong random secret in production."
                )
            if "changeme" in self.database_url:
                warnings.warn(
                    "DATABASE_URL contains the default password 'changeme'. "
                    "Set a secure database URL in production via DATABASE_URL env var.",
                    stacklevel=2,
                )
                logger.warning(
                    "DATABASE_URL contains default password 'changeme'. "
                    "Use a secure password in production."
                )
        return self


settings = Settings()
