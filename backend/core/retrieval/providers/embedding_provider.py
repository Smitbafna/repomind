from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Abstract interface for embedding providers.

    Every embedding implementation must expose an ``embed`` method
    that returns vector embeddings for input texts.
    """

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed.

        Returns:
            A list of embedding vectors (list of floats).
        """
        ...

    async def embed_query(self, text: str) -> list[float]:
        """Generate an embedding for a single query string.

        Args:
            text: The query text.

        Returns:
            An embedding vector.
        """
        results = await self.embed([text])
        return results[0] if results else []