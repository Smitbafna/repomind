from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RetrievalResult:
    """A single retrieval result."""

    content: str
    score: float
    document_type: str = ""
    file: str = ""
    symbol: str = ""
    line_start: str = ""
    line_end: str = ""


class BaseRetriever(ABC):
    """Abstract interface for all retrievers.

    Every retriever implementation must expose a ``retrieve`` method
    that takes a query string and returns ranked results.
    """

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[RetrievalResult]:
        """Retrieve documents relevant to the query.

        Args:
            query: The search query.
            top_k: Maximum number of results to return.

        Returns:
            A list of ``RetrievalResult`` instances ranked by relevance.
        """
        ...