from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_env: str = Field(default="development", description="Application environment")
    debug: bool = Field(default=True, description="Debug mode")

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
    dashscope_api_key: str = Field(default="", description="DashScope API key")
    llm_provider: str = Field(default="dashscope", description="LLM provider name")

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

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


settings = Settings()
