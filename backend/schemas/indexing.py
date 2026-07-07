from __future__ import annotations

from pydantic import BaseModel, Field


class IndexResponse(BaseModel):
    """Response returned after indexing a repository."""

    repository_id: str
    documents_indexed: int
    status: str = "completed"


class SearchResult(BaseModel):
    """A single search result returned from a query."""

    content: str
    score: float
    document_type: str = ""
    file: str = ""
    symbol: str = ""
    line_start: str = ""
    line_end: str = ""


class QueryRequest(BaseModel):
    """Request body for querying an indexed repository."""

    query: str = Field(
        ...,
        description="Natural language query about the repository",
        min_length=1,
    )
    top_k: int = Field(
        default=10,
        description="Maximum number of results to return",
        ge=1,
        le=100,
    )
    retriever: str = Field(
        default="hybrid",
        description="Retriever type: vector, keyword, or hybrid",
        pattern="^(vector|keyword|hybrid)$",
    )


class QueryResponse(BaseModel):
    """Response returned from a query against an indexed repository."""

    repository_id: str
    query: str
    results: list[SearchResult]
    total: int