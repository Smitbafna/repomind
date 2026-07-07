from __future__ import annotations

import logging
import re
from collections import Counter

from backend.core.retrieval.retriever import BaseRetriever, RetrievalResult
from backend.core.retrieval.vector_store import VectorStore

logger = logging.getLogger(__name__)


class KeywordRetriever(BaseRetriever):
    """Retriever that uses keyword-based (BM25-like) search.

    Fetches all documents from the vector store and scores them
    using term frequency matching. This is a simple fallback when
    vector search is unavailable or for hybrid fusion.
    """

    def __init__(
        self,
        vector_store: VectorStore | None = None,
    ) -> None:
        self._vector_store = vector_store or VectorStore()

    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[RetrievalResult]:
        """Retrieve documents using keyword matching.

        Args:
            query: The search query.
            top_k: Maximum number of results.

        Returns:
            A list of ``RetrievalResult`` instances.
        """
        query_terms = self._tokenize(query)
        if not query_terms:
            return []

        # Fetch all documents (limited to a reasonable batch).
        # In production, this would use a proper inverted index.
        all_results = await self._vector_store.search(
            vector=[0.0] * 768,  # Dummy vector, we only use payload
            top_k=1000,
        )

        scored: list[tuple[float, dict]] = []
        for result in all_results:
            content = result.get("content", "")
            doc_terms = self._tokenize(content)
            if not doc_terms:
                continue

            # Simple term frequency scoring.
            doc_counter = Counter(doc_terms)
            score = sum(doc_counter.get(term, 0) for term in query_terms)
            # Normalize by document length.
            score = score / (len(doc_terms) + 1)

            if score > 0:
                scored.append((score, result))

        # Sort by score descending.
        scored.sort(key=lambda x: x[0], reverse=True)
        scored = scored[:top_k]

        return [
            RetrievalResult(
                content=r["content"],
                score=score,
                document_type=r.get("document_type", ""),
                file=r.get("file", ""),
                symbol=r.get("symbol", "") or r.get("class", "") or r.get("function", ""),
                line_start=r.get("line_start", ""),
                line_end=r.get("line_end", ""),
            )
            for score, r in scored
        ]

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Tokenize text into lowercase terms."""
        text = text.lower()
        # Split on non-alphanumeric characters.
        tokens = re.findall(r"[a-z0-9_]+", text)
        # Filter out very short tokens.
        return [t for t in tokens if len(t) > 1]