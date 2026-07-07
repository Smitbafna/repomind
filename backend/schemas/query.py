from __future__ import annotations

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    """Request body for asking a question about a repository."""

    question: str = Field(
        ...,
        description="Natural language question about the repository",
        min_length=1,
        max_length=10000,
    )


class SourceInfo(BaseModel):
    """Source information for a retrieval result used in answers."""

    file: str = ""
    symbol: str = ""
    score: float = 0.0
    document_type: str = ""
    line_start: str = ""
    line_end: str = ""


class AskResponse(BaseModel):
    """Response returned after asking a question about a repository."""

    repository_id: str
    question: str
    answer: str
    sources: list[SourceInfo]
    intent: str = ""
    retrieval_strategy: str = ""
    keywords: list[str] = Field(default_factory=list)