from __future__ import annotations

import logging
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qdrant_models

from backend.config.settings import get_settings

logger = logging.getLogger(__name__)


class VectorStore:
    """Qdrant vector store for storing and searching embeddings.

    Manages collection lifecycle and provides CRUD operations
    for vector points with payload filtering.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client: AsyncQdrantClient | None = None
        self._collection_name = self._settings.qdrant_collection_name
        self._vector_size = self._settings.qdrant_vector_size

    async def _get_client(self) -> AsyncQdrantClient:
        """Get or create the Qdrant client."""
        if self._client is None:
            self._client = AsyncQdrantClient(url=self._settings.qdrant_url)
            await self._ensure_collection()
        return self._client

    async def _ensure_collection(self) -> None:
        """Create the collection if it does not exist."""
        client = self._client
        if client is None:
            return

        collections = await client.get_collections()
        existing = {c.name for c in collections.collections}

        if self._collection_name not in existing:
            await client.create_collection(
                collection_name=self._collection_name,
                vectors_config=qdrant_models.VectorParams(
                    size=self._vector_size,
                    distance=qdrant_models.Distance.COSINE,
                ),
            )
            logger.info(
                "Created Qdrant collection '%s' (size=%d)",
                self._collection_name,
                self._vector_size,
            )

    def make_point(
        self,
        doc_id: str,
        vector: list[float],
        payload: dict[str, Any],
    ) -> qdrant_models.PointStruct:
        """Create a Qdrant point struct.

        Args:
            doc_id: Unique document identifier.
            vector: The embedding vector.
            payload: Metadata payload.

        Returns:
            A ``PointStruct`` ready for upsert.
        """
        return qdrant_models.PointStruct(
            id=doc_id,
            vector=vector,
            payload=payload,
        )

    async def upsert(self, points: list[qdrant_models.PointStruct]) -> None:
        """Upsert points into the collection.

        Args:
            points: List of points to upsert.
        """
        client = await self._get_client()
        await client.upsert(
            collection_name=self._collection_name,
            points=points,
        )

    async def search(
        self,
        vector: list[float],
        repository_id: str | None = None,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Search for similar vectors.

        Args:
            vector: The query vector.
            repository_id: Optional repository ID to filter by.
            top_k: Maximum number of results.

        Returns:
            A list of result dictionaries with ``content``, ``metadata``,
            and ``score`` keys.
        """
        client = await self._get_client()

        query_filter = None
        if repository_id:
            query_filter = qdrant_models.Filter(
                must=[
                    qdrant_models.FieldCondition(
                        key="repository_id",
                        match=qdrant_models.MatchValue(value=repository_id),
                    )
                ]
            )

        query_response = await client.query_points(
            collection_name=self._collection_name,
            query=vector,
            limit=top_k,
            query_filter=query_filter,
        )

        return [
            {
                "content": point.payload.get("content", ""),
                "score": point.score,
                "document_type": point.payload.get("document_type", ""),
                "file": point.payload.get("file", ""),
                "symbol": point.payload.get("symbol", ""),
                "class": point.payload.get("class", ""),
                "function": point.payload.get("function", ""),
                "line_start": point.payload.get("line_start", ""),
                "line_end": point.payload.get("line_end", ""),
                "docstring": point.payload.get("docstring", ""),
            }
            for point in query_response.points
        ]

    async def delete_repository_points(self, repository_id: str) -> None:
        """Delete all points belonging to a repository.

        Args:
            repository_id: The repository ID to delete.
        """
        client = await self._get_client()
        try:
            await client.delete(
                collection_name=self._collection_name,
                points_selector=qdrant_models.FilterSelector(
                    filter=qdrant_models.Filter(
                        must=[
                            qdrant_models.FieldCondition(
                                key="repository_id",
                                match=qdrant_models.MatchValue(value=repository_id),
                            )
                        ]
                    )
                ),
            )
        except Exception as exc:
            logger.warning(
                "Failed to delete points for repository %s: %s",
                repository_id,
                exc,
            )

    async def count(self, repository_id: str | None = None) -> int:
        """Count points in the collection, optionally filtered by repository.

        Args:
            repository_id: Optional repository ID to filter by.

        Returns:
            The number of matching points.
        """
        client = await self._get_client()
        query_filter = None
        if repository_id:
            query_filter = qdrant_models.Filter(
                must=[
                    qdrant_models.FieldCondition(
                        key="repository_id",
                        match=qdrant_models.MatchValue(value=repository_id),
                    )
                ]
            )
        result = await client.count(
            collection_name=self._collection_name,
            count_filter=query_filter,
        )
        return result.count