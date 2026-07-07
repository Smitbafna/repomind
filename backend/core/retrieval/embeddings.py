from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from backend.config.settings import get_settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generates embeddings using Ollama's embedding API.

    Supports configurable embedding models via settings.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._base_url = self._settings.ollama_base_url.rstrip("/")
        self._model = self._settings.ollama_embedding_model
        self._timeout = self._settings.ollama_timeout_seconds

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed.

        Returns:
            A list of embedding vectors (list of floats).

        Raises:
            ConnectionError: If Ollama is unreachable.
            RuntimeError: If the embedding API returns an error.
        """
        if not texts:
            return []

        url = f"{self._base_url}/api/embed"
        payload: dict[str, Any] = {
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

    async def embed_query(self, text: str) -> list[float]:
        """Generate an embedding for a single query string.

        Args:
            text: The query text.

        Returns:
            An embedding vector.
        """
        results = await self.embed([text])
        return results[0] if results else []