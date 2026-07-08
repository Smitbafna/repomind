from __future__ import annotations

import logging

from backend.core.retrieval.providers.embedding_provider import EmbeddingProvider
from backend.core.retrieval.providers.factory import get_embedding_provider

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generates embeddings using the configured embedding provider.

    Delegates to the provider selected by ``EMBEDDING_PROVIDER`` env var.
    """

    def __init__(self, provider: EmbeddingProvider | None = None) -> None:
        self._provider = provider or get_embedding_provider()

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed.

        Returns:
            A list of embedding vectors (list of floats).
        """
        return await self._provider.embed(texts)

    async def embed_query(self, text: str) -> list[float]:
        """Generate an embedding for a single query string.

        Args:
            text: The query text.

        Returns:
            An embedding vector.
        """
        return await self._provider.embed_query(text)