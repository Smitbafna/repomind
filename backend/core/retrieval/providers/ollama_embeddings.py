from __future__ import annotations

import logging

import httpx

from backend.config.settings import get_settings
from backend.core.retrieval.providers.embedding_provider import EmbeddingProvider

logger = logging.getLogger(__name__)


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Generates embeddings using Ollama's embedding API."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._base_url = self._settings.ollama_base_url.rstrip("/")
        self._model = self._settings.ollama_embedding_model
        self._timeout = self._settings.ollama_timeout_seconds

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using Ollama."""
        if not texts:
            return []

        url = f"{self._base_url}/api/embed"
        payload: dict = {
            "model": self._model,
            "input": texts,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.RequestError as exc:
            raise ConnectionError(
                f"Failed to connect to Ollama at {self._base_url}: {exc}"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Ollama embedding API returned {exc.response.status_code}: {exc.response.text}"
            ) from exc

        embeddings = data.get("embeddings", [])
        if not embeddings:
            raise RuntimeError(
                f"Ollama returned empty embeddings for model '{self._model}'"
            )

        return embeddings