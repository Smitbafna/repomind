from __future__ import annotations

from pathlib import Path
from typing import Final

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Database ---
    database_url: str = "sqlite+aiosqlite:///./repomind.db"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "repomind"
    postgres_password: str = "repomind"
    postgres_db: str = "repomind"

    # --- Repositories ---
    repositories_base_path: str = str(Path.cwd() / "repositories")

    # --- GitHub ---
    github_token: str | None = None

    # --- Server ---
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # --- Ingestion ---
    max_file_size_bytes: int = 10 * 1024 * 1024  # 10 MB
    clone_timeout_seconds: int = 300  # 5 minutes

    # --- LLM Provider ---
    llm_provider: str = "ollama"
    gemini_api_key: str | None = None
    openai_api_key: str | None = None

    # --- Ollama (fallback when LLM_PROVIDER=ollama) ---
    ollama_base_url: str = "http://localhost:11434"
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_timeout_seconds: int = 60
    ollama_chat_model: str = "llama3.2"

    # --- Embedding Provider ---
    embedding_provider: str = "ollama"

    # --- Qdrant ---
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection_name: str = "repomind"
    qdrant_vector_size: int = 768  # nomic-embed-text default

    # --- Query ---
    max_context_tokens: int = 4096
    default_top_k: int = 10

    # --- Auth ---
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60 * 24  # 24 hours
    allow_registration: bool = True

    # --- CORS ---
    cors_allowed_origins: str = ""  # Comma-separated list of allowed origins

    # --- Feature Flags ---
    enable_github_sync: bool = True

    # --- Rate Limiting ---
    rate_limit_requests: int = 60
    rate_limit_window_minutes: int = 60

    # --- Logging ---
    log_level: str = "INFO"

    # --- Redis (for background jobs) ---
    redis_url: str = "redis://localhost:6379/0"

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate that SECRET_KEY is not the default value in production.

        Raises:
            ValueError: If the default secret key is used.
        """
        if v == "change-me-in-production":
            raise ValueError(
                "SECRET_KEY is set to the default value 'change-me-in-production'. "
                "This is a security vulnerability. Please set a secure random secret key "
                "in your environment: export SECRET_KEY='your-secure-random-key'"
            )
        return v


_GLOBAL_INSTANCE: Settings | None = None


def get_settings() -> Settings:
    """Return a singleton Settings instance."""
    global _GLOBAL_INSTANCE  # noqa: PLW0603
    if _GLOBAL_INSTANCE is None:
        _GLOBAL_INSTANCE = Settings()
    return _GLOBAL_INSTANCE