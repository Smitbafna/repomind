from __future__ import annotations

import logging

from backend.core.retrieval.keyword_retriever import KeywordRetriever
from backend.core.retrieval.retriever import BaseRetriever, RetrievalResult
from backend.core.retrieval.vector_retriever import VectorRetriever

logger = logging.getLogger(__name__)


class HybridRetriever(BaseRetriever):
    """Retriever that combines vector and keyword search using fusion.

    Performs both vector and keyword retrieval, then fuses the results
    using reciprocal rank fusion (RRF) for improved relevance.
    """

    def __init__(
        self,
        vector_retriever: VectorRetriever | None = None,
        keyword_retriever: KeywordRetriever | None = None,
        rrf_k: int = 60,
    ) -> None:
        self._vector_retriever = vector_retriever or VectorRetriever()
        self._keyword_retriever = keyword_retriever or KeywordRetriever()
        self._rrf_k = rrf_k

    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[RetrievalResult]:
        """Retrieve documents using hybrid vector + keyword search.

        Args:
            query: The search query.
            top_k: Maximum number of results.

        Returns:
            A list of ``RetrievalResult`` instances fused by RRF.
        """
        # Run both retrievers in parallel.
        import asyncio

        vector_task = self._vector_retriever.retrieve(query, top_k=top_k * 2)
        keyword_task = self._keyword_retriever.retrieve(query, top_k=top_k * 2)

        vector_results, keyword_results = await asyncio.gather(
            vector_task, keyword_task
        )

        # Reciprocal rank fusion.
        content_scores: dict[str, dict] = {}

        for rank, result in enumerate(vector_results):
            key = self._result_key(result)
            if key not in content_scores:
                content_scores[key] = {
                    "result": result,
                    "score": 0.0,
                }
            content_scores[key]["score"] += 1.0 / (self._rrf_k + rank + 1)

        for rank, result in enumerate(keyword_results):
            key = self._result_key(result)
            if key not in content_scores:
                content_scores[key] = {
                    "result": result,
                    "score": 0.0,
                }
            content_scores[key]["score"] += 1.0 / (self._rrf_k + rank + 1)

        # Sort by fused score descending.
        sorted_results = sorted(
            content_scores.values(),
            key=lambda x: x["score"],
            reverse=True,
        )

        return [
            RetrievalResult(
                content=item["result"].content,
                score=item["score"],
                document_type=item["result"].document_type,
                file=item["result"].file,
                symbol=item["result"].symbol,
                line_start=item["result"].line_start,
                line_end=item["result"].line_end,
            )
            for item in sorted_results[:top_k]
        ]

    @staticmethod
    def _result_key(result: RetrievalResult) -> str:
        """Generate a unique key for a retrieval result."""
        return f"{result.file}:{result.symbol}:{result.line_start}"