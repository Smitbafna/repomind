from __future__ import annotations

import logging
from typing import Any

from backend.config.settings import get_settings
from backend.core.retrieval.providers.embedding_provider import EmbeddingProvider

logger = logging.getLogger(__name__)


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Generates embeddings using Google's Generative AI API."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._api_key = self._settings.gemini_api_key
        self._model = "text-embedding-004"  # Default model
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazy-import and initialize the Google Generative AI client."""
        if self._client is not None:
            return self._client
        try:
            import google.generativeai as genai  # type: ignore[import-untyped]
            genai.configure(api_key=self._api_key)
            self._client = genai
            return self._client
        except ImportError:
            raise RuntimeError(
                "google-generativeai package is not installed. "
                "Install it with: pip install google-generativeai"
            )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using Gemini."""
        if not texts:
            return []

        genai = self._get_client()

        try:
            result = genai.embed_content(
                model=self._model,
                content=texts,
            )
            embeddings = result.get("embedding", [])
            if not embeddings:
                raise RuntimeError("Gemini returned empty embeddings")
            return embeddings
        except Exception as exc:
            raise RuntimeError(f"Gemini embedding error: {exc}") from exc