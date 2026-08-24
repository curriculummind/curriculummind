"""
Application settings, loaded from environment variables (see .env.example).
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven configuration for the FastAPI service."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5"
    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    database_url: str = ""

    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide Settings instance, loaded once and cached."""
    return Settings()
