from __future__ import annotations

from pathlib import Path
from typing import Final

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
    database_url: str = "sqlite:///./repomind.db"

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

    # --- Ollama ---
    ollama_base_url: str = "http://localhost:11434"
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_timeout_seconds: int = 60
    ollama_chat_model: str = "llama3.2"

    # --- Qdrant ---
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection_name: str = "repomind"
    qdrant_vector_size: int = 768  # nomic-embed-text default

    # --- Query ---
    max_context_tokens: int = 4096
    default_top_k: int = 10


_GLOBAL_INSTANCE: Settings | None = None


def get_settings() -> Settings:
    """Return a singleton Settings instance."""
    global _GLOBAL_INSTANCE  # noqa: PLW0603
    if _GLOBAL_INSTANCE is None:
        _GLOBAL_INSTANCE = Settings()
    return _GLOBAL_INSTANCE