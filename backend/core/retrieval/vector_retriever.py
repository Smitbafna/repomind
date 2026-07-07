from __future__ import annotations

import logging

from backend.core.retrieval.embeddings import EmbeddingService
from backend.core.retrieval.retriever import BaseRetriever, RetrievalResult
from backend.core.retrieval.vector_store import VectorStore

logger = logging.getLogger(__name__)


class VectorRetriever(BaseRetriever):
    """Retriever that uses vector similarity search.

    Embeds the query and searches the Qdrant vector store for
    semantically similar documents.
    """

    def __init__(
        self,
        vector_store: VectorStore | None = None,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self._vector_store = vector_store or VectorStore()
        self._embedding_service = embedding_service or EmbeddingService()

    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[RetrievalResult]:
        """Retrieve documents using vector similarity.

        Args:
            query: The search query.
            top_k: Maximum number of results.

        Returns:
            A list of ``RetrievalResult`` instances.
        """
        query_vector = await self._embedding_service.embed_query(query)
        results = await self._vector_store.search(
            vector=query_vector,
            top_k=top_k,
        )

        return [
            RetrievalResult(
                content=r["content"],
                score=r["score"],
                document_type=r.get("document_type", ""),
                file=r.get("file", ""),
                symbol=r.get("symbol", "") or r.get("class", "") or r.get("function", ""),
                line_start=r.get("line_start", ""),
                line_end=r.get("line_end", ""),
            )
            for r in results
        ]