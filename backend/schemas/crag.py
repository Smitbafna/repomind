from __future__ import annotations

from pydantic import BaseModel


class EvaluationResponse(BaseModel):
    """Response from retrieval evaluation."""

    confidence: float
    coverage: float
    redundancy: float
    evidence_diversity: float
    missing_information: list[str]
    recommended_actions: list[str]


class RetrieveResponse(BaseModel):
    """Response from retrieval-only endpoint."""

    iterations: int
    retrieval_history: list[dict]
    confidence: float
    missing_information: list[str]


class CRAGQueryResponse(BaseModel):
    """Response from CRAG query."""

    repository_id: str
    question: str
    answer: str
    confidence: float
    sources: list[dict]
    retrieval_history: list[dict]
    answer_valid: bool
    validation_message: str